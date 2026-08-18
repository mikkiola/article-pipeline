#!/usr/bin/env python3
"""Safe derived documentation sync (brief §17).

Step 8 of the SPEC -> checklist -> harness -> drift -> doc-sync
automation track. Acts ONLY on Step 7's DERIVED_UPDATE_REQUIRED
findings, and only where a genuinely mechanical, deterministic fix
exists — never on ARCHITECTURAL_REVIEW_REQUIRED or UNKNOWN findings,
which are always surfaced for a human decision, never touched.

This step PROPOSES, it never applies. A mechanical fix becomes a
unified diff written to doc_sync_proposals/<finding-file>.diff for a
human to review and apply separately — nothing here writes to a
canonical doc directly, and docs/adr/ is never touched under any
circumstances (brief §20).

Component discovery and classification are imported from
scripts/doc_impact.py (Step 7), not duplicated.

The ONE mechanical-fix pattern implemented mirrors brief §17's
"component file path / generated inventory" example as literally as
this repo's actual docs/ARCHITECTURE.md admits: a component's
SPEC-named file (Step 6 part C's file-naming logic, via
doc_impact.spec_named_files) missing from an ALREADY-EXISTING, pure,
uniform `### Files: <component>` enumeration in docs/ARCHITECTURE.md
is proposed as a plain append. If no such enumeration exists yet, or
the existing one mixes literal paths with descriptive prose, this is
explicitly NOT mechanical (would mean inventing document structure or
guessing at ambiguous phrasing) and is left for human judgment.
A component code file that changed without a SPEC/CHECKPOINT update
is always left for human judgment too — deciding what SPEC/CHECKPOINT
prose should say about a code change requires understanding the
change's meaning, never mechanical.

Step 8 extension — Commit-column-only mechanical fix. Scope: ONLY
docs/ARCHITECTURE.md's table's Commit column, for the two rows whose
mapping to a Steps 1-7 discovered component is defensible by a named,
non-fuzzy method (see ARCHITECTURE_ROW_TO_COMPONENT below and this
task's own report for the full per-row audit, including the ten
unresolved rows). A row's Commit cell is only ever a candidate for a
mechanical update when it's currently a single literal SHA — a range
or multiple-SHA cell always requires human judgment about what the
range is meant to represent, never a mechanical extension. Status,
"Depends on", and Validation columns are never touched, proposed, or
even flagged, per explicit owner decision.
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from doc_impact import (  # noqa: E402
    ARCHITECTURE_DOC,
    classify_file,
    code_file_owner,
    discover_components,
    get_changed_files,
    spec_file_owner,
    spec_named_files,
)

FILES_HEADING_TEMPLATE = r"^###\s+Files:\s+{}\s*$"
NEXT_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
LIST_ITEM_RE = re.compile(r"^-\s+(.*)$", re.MULTILINE)
PURE_PATH_ITEM_RE = re.compile(r"^`[\w./-]+\.[A-Za-z0-9]+`$")

# Explicit, human-reviewed ARCHITECTURE.md row -> discovered-component
# mapping for the Commit-column pattern. NOT computed by fuzzy string
# matching at runtime — every row in the table was individually
# audited; only these two resolved via a named, reproducible method,
# and the other ten (Atom Selector, `graph_reader.py`, Claim
# Extraction, Strategy Layer, Author, Quality Gate, Platform Adapter,
# Experiment Log, both ToolTempest rows) do not appear here because
# none of them are in discover_components()'s discovered set (no
# SPEC.md of their own) — see this task's report for the full audit.
ARCHITECTURE_ROW_TO_COMPONENT = {
    # Exact match after normalization (lowercase, strip spaces):
    # "evidencepackage" == "evidencepackage" for discovered component
    # "evidence_package".
    "Evidence Package": "evidence_package",
    # context_layer/SPEC.md (lines 112-113) literally quotes this exact
    # row label as its own docs/ARCHITECTURE.md reference — an exact
    # substring match once markdown line-wrap whitespace is collapsed
    # (verified by direct inspection, not fuzzy similarity).
    "Context/causal-structure layer": "context_layer",
}

SINGLE_SHA_RE = re.compile(r"^`[0-9a-f]{7,40}`$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_or_generate_findings(repo_root: Path, since: str | None, regenerate: bool):
    """Default: read the already-committed doc_reports/doc_impact_report.json
    (Step 7's actual output — what this task's own scope references).
    --since/--regenerate: recompute fresh via doc_impact.py's own
    functions (imported, not duplicated) instead."""
    if since or regenerate:
        changed_files, diff_description = get_changed_files(repo_root, since)
        components = discover_components(repo_root)
        changed_set = set(changed_files)
        architecture_changed = ARCHITECTURE_DOC in changed_set
        findings = [
            {"file": rel_path, "classification": c, "reason": r}
            for rel_path in changed_files
            for c, r in [
                classify_file(rel_path, components, changed_set, architecture_changed, repo_root)
            ]
        ]
        return findings, f"regenerated fresh via {diff_description}"

    report_path = repo_root / "doc_reports" / "doc_impact_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(
            f"{report_path} not found — run scripts/doc_impact.py first, "
            f"or pass --since/--regenerate to doc_sync.py."
        )
    with report_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data["findings"], f"read from {report_path} (generated_at={data.get('generated_at')})"


def find_files_section(text: str, component: str):
    heading_re = re.compile(FILES_HEADING_TEMPLATE.format(re.escape(component)), re.MULTILINE)
    heading_match = heading_re.search(text)
    if not heading_match:
        return None

    start = heading_match.end()
    rest = text[start:]
    next_heading_match = NEXT_HEADING_RE.search(rest)
    end = start + (next_heading_match.start() if next_heading_match else len(rest))
    section_text = text[start:end]

    item_matches = list(LIST_ITEM_RE.finditer(section_text))
    items = [m.group(1).strip() for m in item_matches]
    insert_at = start + item_matches[-1].end() if item_matches else start

    return {"items": items, "insert_at": insert_at}


def is_pure_path_list(items: list) -> bool:
    return len(items) > 0 and all(PURE_PATH_ITEM_RE.match(item) for item in items)


def try_files_enumeration_fix(repo_root: Path, component: str, components: dict):
    """The one implemented mechanical-fix pattern. Returns
    (diff_text_or_None, note)."""
    doc_path = repo_root / ARCHITECTURE_DOC
    if not doc_path.is_file():
        return None, f"{ARCHITECTURE_DOC} does not exist — nothing to propose against."

    text = doc_path.read_text(encoding="utf-8")
    section = find_files_section(text, component)
    if section is None:
        return None, (
            f"No '### Files: {component}' enumeration section found in "
            f"{ARCHITECTURE_DOC} — there is no existing mechanical list to "
            f"append to; adding one would mean inventing new document "
            f"structure, not a mechanical fix. Requires human judgment."
        )

    if not is_pure_path_list(section["items"]):
        return None, (
            f"The '### Files: {component}' section in {ARCHITECTURE_DOC} mixes "
            f"literal file paths with descriptive prose (or is otherwise not a "
            f"uniform enumeration) — a mechanical append risks misinterpreting "
            f"intent, e.g. duplicating an entry already described in different "
            f"words. Requires human judgment."
        )

    named = spec_named_files(repo_root, component, components)
    existing = {item.strip("`") for item in section["items"]}
    missing = sorted(named - existing)
    if not missing:
        return None, (
            f"All of {component}'s SPEC-named files are already listed in the "
            f"'### Files: {component}' section — nothing to add."
        )

    insert_at = section["insert_at"]
    new_text = text[:insert_at] + "".join(f"\n- `{f}`" for f in missing) + text[insert_at:]
    diff_text = "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=str(doc_path.relative_to(repo_root)),
            tofile=str(doc_path.relative_to(repo_root)),
        )
    )
    note = (
        f"Proposed appending {len(missing)} missing SPEC-named file path(s) to "
        f"the existing '### Files: {component}' enumeration in {ARCHITECTURE_DOC}."
    )
    return diff_text, note


def find_table_row(text: str, row_label: str):
    """Locates a docs/ARCHITECTURE.md table row by its exact,
    literal first-column label. Returns the match object (group(4) is
    the Commit cell) or None."""
    row_re = re.compile(
        rf"^\|\s*{re.escape(row_label)}\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$",
        re.MULTILINE,
    )
    return row_re.search(text)


def commit_cell_kind(raw_cell: str) -> str:
    return "single" if SINGLE_SHA_RE.match(raw_cell.strip()) else "complex"


def latest_commit_touching(repo_root: Path, component: str):
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%h", "--", f"{component}/"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha or None


def try_commit_column_fix(repo_root: Path, row_label: str, component: str):
    """The Step 8 extension's one mechanical-fix pattern: a row whose
    Commit cell is currently a single literal SHA, and that SHA no
    longer matches the latest commit touching the mapped component
    directory, gets that one cell replaced — nothing else in the row,
    nothing else in the document. Returns (diff_text_or_None, note)."""
    doc_path = repo_root / ARCHITECTURE_DOC
    text = doc_path.read_text(encoding="utf-8")

    match = find_table_row(text, row_label)
    if match is None:
        return None, f"No table row found for '{row_label}' in {ARCHITECTURE_DOC} — cannot check its Commit cell."

    commit_cell = match.group(4).strip()
    kind = commit_cell_kind(commit_cell)

    latest_sha = latest_commit_touching(repo_root, component)
    if latest_sha is None:
        return None, f"'git log -- {component}/' produced no result — nothing to compare '{row_label}''s Commit cell against."

    if kind == "complex":
        return None, (
            f"'{row_label}' row's Commit cell ({commit_cell!r}) is a range/"
            f"multi-SHA/non-single value — extending or replacing it would "
            f"require judgment about what the range is meant to represent "
            f"(e.g. a specific validated milestone span vs. simply 'the "
            f"latest commit'), not a mechanical fact. Requires human judgment."
        )

    current_sha = commit_cell.strip("`")
    if current_sha == latest_sha:
        return None, (
            f"'{row_label}' row's Commit cell already matches the latest "
            f"commit touching {component}/ ({latest_sha}) — nothing to update."
        )

    new_text = text[: match.start(4)] + f" `{latest_sha}` " + text[match.end(4) :]
    diff_text = "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=str(doc_path.relative_to(repo_root)),
            tofile=str(doc_path.relative_to(repo_root)),
        )
    )
    note = (
        f"Proposed updating '{row_label}' row's Commit cell from "
        f"`{current_sha}` to `{latest_sha}` (latest commit touching "
        f"{component}/). Status/Depends on/Validation columns untouched."
    )
    return diff_text, note


def write_proposal(repo_root: Path, name_stem: str, diff_text: str) -> Path:
    proposals_dir = repo_root / "doc_sync_proposals"
    proposals_dir.mkdir(exist_ok=True)
    safe_name = name_stem.replace("/", "__")
    out_path = proposals_dir / f"{safe_name}.diff"
    out_path.write_text(diff_text, encoding="utf-8")
    return out_path


def process_derived_update_required(repo_root: Path, rel_path: str, components: dict) -> dict:
    notes = []
    proposals = []

    spec_owner = spec_file_owner(rel_path, components, repo_root)
    code_owner = code_file_owner(rel_path, components)
    owner = spec_owner or code_owner

    if spec_owner is not None:
        diff_text, note = try_files_enumeration_fix(repo_root, spec_owner, components)
        if diff_text:
            proposals.append((f"{rel_path}__files_enumeration", diff_text, note))
        else:
            notes.append(note)
    elif code_owner is not None:
        notes.append(
            f"{rel_path} is a {code_owner} code file changed with no "
            f"SPEC/CHECKPOINT update. Deciding what SPEC/CHECKPOINT prose "
            f"should say about a code change requires understanding the "
            f"change's meaning — never mechanical. doc_sync.py does not "
            f"attempt a SPEC/CHECKPOINT-text fix for this at all."
        )
    else:
        notes.append(
            f"{rel_path} is classified DERIVED_UPDATE_REQUIRED but is neither a "
            f"known component's SPEC/CHECKPOINT file nor a known component's "
            f"code file — no recognized mechanical-fix pattern applies; "
            f"treating conservatively as requiring human judgment rather than "
            f"guessing."
        )

    if owner is not None:
        row_labels = [label for label, comp in ARCHITECTURE_ROW_TO_COMPONENT.items() if comp == owner]
        if not row_labels:
            notes.append(
                f"{owner} has no reviewed docs/ARCHITECTURE.md row mapping "
                f"(see ARCHITECTURE_ROW_TO_COMPONENT / this task's audit) — "
                f"Commit-column check does not apply to this component."
            )
        for row_label in row_labels:
            diff_text, note = try_commit_column_fix(repo_root, row_label, owner)
            if diff_text:
                proposals.append((f"{rel_path}__commit_column__{row_label}", diff_text, note))
            else:
                notes.append(note)

    if proposals:
        written = [
            {
                "proposal_path": str(write_proposal(repo_root, stem, diff_text).relative_to(repo_root)),
                "note": note,
            }
            for stem, diff_text, note in proposals
        ]
        return {
            "doc_sync_action": "PROPOSED",
            "doc_sync_note": " | ".join(w["note"] for w in written),
            "proposals": written,
        }

    return {
        "doc_sync_action": "BLOCKED_NEEDS_HUMAN_DECISION",
        "doc_sync_note": " | ".join(notes) if notes else "No mechanical-fix pattern applied.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repo root to scan (default: parent directory of scripts/)",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Regenerate findings fresh via doc_impact.py, diffing this ref against HEAD.",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate findings fresh via doc_impact.py's default range instead of reading doc_reports/doc_impact_report.json.",
    )
    args = parser.parse_args()

    repo_root = (args.repo_root or Path(__file__).resolve().parent.parent).resolve()

    try:
        findings, source_description = load_or_generate_findings(repo_root, args.since, args.regenerate)
    except FileNotFoundError as e:
        print(f"doc_sync: {e}", file=sys.stderr)
        return 1

    components = discover_components(repo_root)

    results = []
    for finding in findings:
        rel_path = finding["file"]
        classification = finding["classification"]

        if classification in ("ARCHITECTURAL_REVIEW_REQUIRED", "UNKNOWN"):
            outcome = {
                "doc_sync_action": "BLOCKED_NEEDS_HUMAN_DECISION",
                "doc_sync_note": f"Never auto-updated by doc_sync.py — {classification} always requires a human decision.",
            }
        elif classification == "NO_IMPACT":
            outcome = {"doc_sync_action": "NONE", "doc_sync_note": "No doc impact; nothing to sync."}
        elif classification == "DERIVED_UPDATE_REQUIRED":
            outcome = process_derived_update_required(repo_root, rel_path, components)
        else:
            outcome = {
                "doc_sync_action": "BLOCKED_NEEDS_HUMAN_DECISION",
                "doc_sync_note": f"Unrecognized classification {classification!r} — not attempting anything.",
            }

        results.append({**finding, **outcome})

    proposed = [r for r in results if r["doc_sync_action"] == "PROPOSED"]

    summary_report = {
        "generated_at": _now_iso(),
        "findings_source": source_description,
        "results": results,
        "summary": {
            "PROPOSED": len(proposed),
            "BLOCKED_NEEDS_HUMAN_DECISION": sum(
                1 for r in results if r["doc_sync_action"] == "BLOCKED_NEEDS_HUMAN_DECISION"
            ),
            "NONE": sum(1 for r in results if r["doc_sync_action"] == "NONE"),
        },
    }

    proposals_dir = repo_root / "doc_sync_proposals"
    proposals_dir.mkdir(exist_ok=True)
    summary_path = proposals_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"doc_sync: {len(results)} findings ({source_description}) -> {summary_path}")
    s = summary_report["summary"]
    print(
        f"doc_sync: {s['PROPOSED']} proposed, "
        f"{s['BLOCKED_NEEDS_HUMAN_DECISION']} blocked/needs human decision, "
        f"{s['NONE']} none"
    )
    for r in proposed:
        for p in r["proposals"]:
            print(f"doc_sync: PROPOSED -> {p['proposal_path']} (from {r['file']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
