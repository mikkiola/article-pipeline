"""Offline tests of extracted sync phases; never invoke sync-tooling.sh.

Source files and destinations exist only in TemporaryDirectory. Cache Git
commands are stubbed; no real Git, hooks, network or model calls are used.
"""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts/sync-tooling.sh").read_text()


def phase(name):
    return SCRIPT.split(f"# BEGIN {name}\n", 1)[1].split(f"# END {name}", 1)[0]


PREFLIGHT = phase("READ-ONLY PREFLIGHT")
PREPARATION = phase("CACHE PREPARATION")
INSTALL = phase("INSTALL TARGETS")


class SyncPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sync-preflight-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cache = self.root / "cache"
        self.repo = self.root / "project"
        self.claude = self.root / "global"
        self.marker = self.root / "cache-write-marker"
        self.env = dict(os.environ)
        self.cache.mkdir()
        self.repo.mkdir()
        self.files = {}
        self.sha = "a" * 40

    def source(self, rel, data=b"pinned contents\n"):
        self.files[rel] = data
        p = self.cache / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def pin(self, entries):
        self.source("MANIFEST.txt", ("\n".join(entries) + "\n").encode())

    def destination(self, rel, data):
        root = self.claude if rel.startswith(("skills/", "rules/")) else self.repo
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def snapshot(self, destinations_only=False):
        roots = [self.repo, self.claude] if destinations_only else [self.root]
        return {
            str(p.relative_to(self.root)): (
                p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns
            ) if p.is_file() else None
            for root in roots for p in ([root] + list(root.rglob("*")))
            if p.exists()
        }

    def run_phases(self, install=True, prepare=False, prepared_sha=None):
        values = {
            "CACHE_DIR": self.cache, "REPO_ROOT": self.repo,
            "CLAUDE_DIR": self.claude, "PINNED_SHA": self.sha,
            "MANIFEST_NAME": "MANIFEST.txt",
            "REMOTE_URL": "fixture://tooltempest",
            "CACHE_SEED": self.root / "cache-seed",
            "CACHE_MARKER": self.marker,
            "PREPARED_SHA": prepared_sha or self.sha,
        }
        setup = "set -euo pipefail\n" + "\n".join(
            f"{key}={shlex.quote(str(value))}" for key, value in values.items()
        ) + '\nfail() { echo "FAIL: $1" >&2; exit 1; }\n'
        # Stub only Git's cache operations. Exercise the actual extracted cache
        # preparation branch, including SHA validation, against fixture files.
        setup += '''
git() {
  if [ "$1" = clone ]; then
    printf 'clone\\n' >> "$CACHE_MARKER"
    cp -R "$CACHE_SEED" "$CACHE_DIR"
    mkdir -p "$CACHE_DIR/.git"
  elif [ "$1" = -C ] && [ "$2" = "$CACHE_DIR" ]; then
    case "$3" in
      fetch|checkout) printf '%s\\n' "$3" >> "$CACHE_MARKER" ;;
      rev-parse) printf '%s\\n' "$PREPARED_SHA" ;;
      *) return 99 ;;
    esac
  else
    return 99
  fi
}
'''
        body = (PREPARATION if prepare else "") + PREFLIGHT
        if install:
            body += INSTALL
            body += '\nprintf "COUNTS: %s installed, %s skipped\\n" "$INSTALLED_COUNT" "$SKIPPED_COUNT"\n'
        return subprocess.run(
            ["/bin/bash"], input=setup + body, capture_output=True,
            text=True, env=self.env,
        )

    def test_matching_destination_passes_without_writes(self):
        rel = "skills/verify/SKILL.md"
        self.source(rel)
        self.pin([rel])
        self.destination(rel, self.files[rel])
        before = self.snapshot()
        result = self.run_phases(install=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_divergence_refuses_and_names_path(self):
        rel = "rules/drift-control.md"
        self.source(rel)
        self.pin([rel])
        dest = self.destination(rel, b"accepted local correction\n")
        before = self.snapshot()
        result = self.run_phases()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(dest), result.stderr)
        self.assertIn("reconcile", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_late_conflicts_leave_all_earlier_targets_and_cache_untouched(self):
        entries = ["scripts/first.py", "schemas/missing.json",
                   "skills/verify/SKILL.md", "rules/last.md"]
        for rel in entries:
            self.source(rel)
        self.pin(entries)
        self.destination(entries[0], self.files[entries[0]])
        conflicts = [self.destination(rel, b"local") for rel in entries[2:]]
        before = self.snapshot()
        result = self.run_phases()
        self.assertNotEqual(result.returncode, 0)
        for dest in conflicts:
            self.assertIn(str(dest), result.stderr)
        # Includes absent earlier destination, file mtimes and cache objects.
        self.assertEqual(before, self.snapshot())

    def test_missing_destination_is_installed(self):
        rel = "skills/new skill/SKILL.md"
        self.source(rel)
        self.pin([rel])
        result = self.run_phases()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.claude / rel).read_bytes(), self.files[rel])

    def test_missing_source_refuses_before_writes(self):
        self.source("scripts/first.py")
        self.pin(["scripts/first.py", "skills/missing/SKILL.md"])
        before = self.snapshot()
        result = self.run_phases()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/missing/SKILL.md", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_wrong_prepared_revision_refuses_before_destination_writes(self):
        self.pin(["skills/verify/SKILL.md"])
        (self.cache / ".git").mkdir()
        before = self.snapshot(destinations_only=True)
        result = self.run_phases(prepare=True, prepared_sha="b" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match lock file", result.stderr)
        self.assertEqual(before, self.snapshot(destinations_only=True))

    def test_unknown_category_refuses_before_writes(self):
        self.source("scripts/first.py")
        self.pin(["scripts/first.py", "unknown/file"])
        before = self.snapshot()
        result = self.run_phases()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the known", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_empty_manifest_refuses_before_writes(self):
        self.pin([])
        before = self.snapshot()
        result = self.run_phases()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lists no files", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_success_preserves_original_mapping_skips_counts_and_contents(self):
        entries = ["rules/example.md", "schemas/example.json", "scripts/example.py",
                   "skills/example/SKILL.md", "docs/reference/example.md"]
        for rel in entries:
            self.source(rel)
        self.pin(entries)
        self.destination(entries[0], self.files[entries[0]])
        result = self.run_phases()
        self.assertEqual(result.returncode, 0, result.stderr)
        for rel in entries[:-1]:
            root = self.claude if rel.startswith(("skills/", "rules/")) else self.repo
            self.assertEqual((root / rel).read_bytes(), self.files[rel])
        self.assertFalse((self.repo / entries[-1]).exists())
        self.assertIn("SKIP: docs/reference/example.md", result.stdout)
        self.assertIn("COUNTS: 4 installed, 1 skipped", result.stdout)

    def test_project_destination_divergence_is_also_protected(self):
        rel = "scripts/local.py"
        self.source(rel)
        self.pin([rel])
        dest = self.destination(rel, b"local project changes")
        before = self.snapshot()
        result = self.run_phases()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(dest), result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_preparation_precedes_preflight_and_preflight_precedes_install(self):
        self.assertLess(SCRIPT.index("# END CACHE PREPARATION"),
                        SCRIPT.index("# BEGIN READ-ONLY PREFLIGHT"))
        end = SCRIPT.index("# END READ-ONLY PREFLIGHT")
        self.assertGreater(SCRIPT.index("# BEGIN INSTALL TARGETS"), end)
        for mutation in ["mkdir -p ", "  cp "]:
            self.assertNotIn(mutation, PREFLIGHT)

    def test_required_clone_then_late_conflicts_preserves_all_destinations(self):
        entries = ["scripts/first.py", "schemas/missing.json",
                   "skills/verify/SKILL.md", "rules/last.md"]
        for rel in entries:
            self.source(rel)
        self.pin(entries)
        self.destination(entries[0], self.files[entries[0]])
        conflicts = [self.destination(rel, b"local") for rel in entries[2:]]
        shutil.move(str(self.cache), str(self.root / "cache-seed"))
        before = self.snapshot(destinations_only=True)
        result = self.run_phases(prepare=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.marker.read_text(), "clone\ncheckout\n")
        for dest in conflicts:
            self.assertIn(str(dest), result.stderr)
        self.assertIn("no installation destinations written", result.stderr)
        self.assertEqual(before, self.snapshot(destinations_only=True))

    def test_required_clone_preserves_fresh_install_behavior(self):
        rel = "skills/verify/SKILL.md"
        self.source(rel)
        self.pin([rel])
        shutil.move(str(self.cache), str(self.root / "cache-seed"))
        result = self.run_phases(prepare=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.marker.read_text(), "clone\ncheckout\n")
        self.assertEqual((self.claude / rel).read_bytes(), self.files[rel])

    def test_existing_cache_fetch_then_conflict_preserves_destinations(self):
        rel = "rules/local.md"
        self.source(rel)
        self.pin([rel])
        (self.cache / ".git").mkdir()
        self.destination(rel, b"accepted local contents")
        before = self.snapshot(destinations_only=True)
        result = self.run_phases(prepare=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.marker.read_text(), "fetch\ncheckout\n")
        self.assertEqual(before, self.snapshot(destinations_only=True))


if __name__ == "__main__":
    unittest.main()
