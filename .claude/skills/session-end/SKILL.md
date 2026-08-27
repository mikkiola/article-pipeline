---
name: session-end
description: "Explicit, owner-triggered session-end doc-sync for article-pipeline: reviews this session's commits for docs/BACKLOG.md items to close (Closes: B-NNN trailers, per SPEC.md's M1/M3) and for structural facts to sync into docs/ARCHITECTURE.md/docs/ROADMAP.md/README.md (Syncs: <path> trailers, per SPEC.md's M6), presenting/writing per each mechanism's own confirmation rules. Triggers on: /session-end only — never invoked by the model on its own judgment. NOT for: autonomous session-end detection (that trigger already exists and was found impractical — see SPEC.md's M2/M5, docs/BACKLOG.md's [B-043])."
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Edit, Bash
---

# /session-end

Explicit, human-triggered supplement to `SPEC.md`'s M2/M5
autonomous-judgment plan-completion trigger — not a replacement, not a
redesign. `SPEC.md`'s M2/M5 is unchanged; this command exists because
its autonomous trigger cannot fire without a `docs/CONSTITUTION.md`-
required "opening stated plan" (Session protocol), which a session
made of many independently-scoped tasks never produces — confirmed by
a real dry-run test, see `docs/BACKLOG.md`'s `[B-043]`. The owner
types `/session-end`; invoking it *is* the signal — this command does
not try to infer whether the session is "done."

## Trailer-detection rule (applies to both scans below)

**Never use a naive line-start text match** (e.g. grep for lines
beginning with "Closes:"/"Syncs:") — a commit body can contain
ordinary prose that happens to start a wrapped line with that same
text. Found for real, 2026-08-25 (`/session-end`'s first live run): a
body sentence discussing `Syncs: ARCHITECTURE.md` as a hypothetical
example was initially caught by a naive line-start match, then had to
be manually excluded because it wasn't in the trailing trailer-block
position and had trailing punctuation breaking a bare-path match. That
manual catch was luck, not a built-in guarantee — fixed here.

Use git's own trailer parser instead — it already knows the real
trailer-block convention (a contiguous `key: value` block at the very
end of the message, per `git-interpret-trailers`), so this class of
bug can't recur:

```bash
git log <session-commit-range> --format="%H %(trailers:key=Closes,valueonly)"
git log <session-commit-range> --format="%H %(trailers:key=Syncs,valueonly)"
```

Each output line is `<full SHA> <value-or-blank>` — filter out blank
values; a commit with no trailer of that key produces a trailing space
and nothing after it. Regression-tested 2026-08-25 against this
session's own real range (`9e87733^..3380376`): `Closes` correctly
returns exactly `B-039`/`B-035`/`B-037`/`B-036`; `Syncs` correctly
returns nothing at all for every commit — including `22c38f5`, whose
body contains the false-positive sentence above, confirmed via
`git log -1 --format="%(trailers)" 22c38f5` showing only `Closes:
B-035` as the actual trailer block, with the body-prose line
correctly invisible to git's own parser.

**Fallback, only if `git log`'s trailer format is unavailable for some
reason:** a manual check must require (a) the candidate line sits in
the last contiguous non-blank block of the commit message — after the
final blank line, with nothing else following it — and (b) the value
has no trailing punctuation or continuation into further prose, a bare
`key: value` line and nothing else on it. Never fall back to a plain
line-start grep under any circumstance — that is the exact bug this
rule exists to prevent.

## What this does — `docs/BACKLOG.md` closure (M1/M3, fully wired)

1. **Find this session's `Closes: B-NNN` trailers**, per the
   trailer-detection rule above — never scan further back than this
   session's own commits, no repo-wide history scan.
2. **Look up each `B-NNN`'s current title** in `docs/BACKLOG.md` (its
   `### [B-NNN] <title>` heading line) — verbatim, exactly as written,
   no summarizing or rewording.
3. **Zero candidates found:** say so plainly (e.g. "No `Closes:`
   trailers found in this session's commits — nothing to close.").
   Stop here; skip to the structural-fact-sync section below.
4. **Exactly one candidate:** per `SPEC.md`'s M1 step 6 — write the
   `docs/BACKLOG.md` edit and commit/push it directly. Invoking
   `/session-end` already is the owner's "close now" signal (the same
   role M2's step-4 "close now, or continue?" ask plays in the
   autonomous-trigger design) — no separate per-item confirmation
   prompt needed on top of that.
5. **More than one candidate:** present them using `SPEC.md`'s M3
   format, verbatim, no deviation:

   ```
   This session's work might close one or more of these tasks:

   1. [B-NNN] <entry's title, exactly as written in docs/BACKLOG.md>
   2. [B-MMM] <entry's title, exactly as written in docs/BACKLOG.md>
   ...

   Which one(s) should I mark done, if any?
   ```

   No git/implementation jargon in this prompt (no "trailer," "commit,"
   "candidate," `Closes:` syntax — that's internal mechanism, not
   something the owner needs to answer the question). "If any" stays
   explicit — declining to close anything is a normal answer. Wait for
   the owner's explicit pick before writing anything; never guess.
6. **If a closure later turns out wrong:** an ordinary follow-up
   edit/commit fixes it — no supersession ritual, same as M1's own
   design.
7. Never touches `docs/CONSTITUTION.md` — permanently excluded, per
   `SPEC.md`'s own stated scope (see its "`docs/CONSTITUTION.md` —
   explicitly excluded" section).

## What this does — structural fact-sync (M6, fully wired, decided 2026-08-25)

`SPEC.md`'s M6 design ties `docs/ARCHITECTURE.md`/`docs/ROADMAP.md`/
`README.md` direct-writes to their own commit trailer, distinct from
`Closes: B-NNN`. **Decided: `Syncs: <path>`, one line per file** —
sourced from git's own `git-interpret-trailers` documentation on
repeated trailers of the same key, plus this repo's existing
`Closes: B-NNN` one-per-line precedent. Path strings must match
`scripts/doc_sync_tier2.py`'s own `TIER2_DOCS` entries exactly:
`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `README.md` (no `docs/`
prefix on this last one — check `TIER2_DOCS` directly if unsure,
don't assume). Worked example, a commit touching two files:

```
Syncs: docs/ARCHITECTURE.md
Syncs: docs/ROADMAP.md
```

1. **Find this session's `Syncs:` trailers**, per the
   trailer-detection rule above — same session-scoped commit range as
   the `Closes:` scan, never a repo-wide history scan.
2. **Deduplicate paths.** If the same path appears in more than one
   commit's `Syncs:` trailers this session, sync it once, using its
   current on-disk content (not any specific commit's snapshot — see
   next step).
3. **Zero `Syncs:` trailers found:** say so plainly, same style as the
   zero-`Closes:`-trailers case above (e.g. "No `Syncs:` trailers
   found in this session's commits — nothing to sync."). Not an error.
4. **For each unique path found:** read its current on-disk content —
   this session's own work already produced it correctly (per
   ADR-0034's established pattern: content is supplied by whoever
   authored it this session, not regenerated by automation) — and
   call `apply_tier2_sync()` (`scripts/doc_sync_tier2.py`, vendored,
   gitignored) with `interactive=False`, reusing that function
   unmodified rather than reimplementing its snapshot/diff/rollback
   logic:
   ```bash
   python3 -c "
   import sys
   sys.path.insert(0, 'scripts')
   from pathlib import Path
   from doc_sync_tier2 import apply_tier2_sync

   repo_root = Path('.').resolve()  # must be absolute -- snapshot_tier2_docs()
                                     # internally calls .relative_to(root), which
                                     # raises if root isn't already resolved
   paths = [...]  # the deduplicated Syncs: paths found this session
   proposed = {p: (repo_root / p).read_text(encoding='utf-8') for p in paths}
   result = apply_tier2_sync(repo_root, proposed, interactive=False)
   print(result)
   "
   ```
   Smoke-tested 2026-08-25 against all three real target files
   (`docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `README.md`), each fed
   its own current on-disk content (a guaranteed no-op — empty diff,
   nothing written): clean run, `status: "no_changes"`, no
   `GATED_DOCS` rejection for any of the three, confirming the call
   pattern above actually works against this repo's real files, not
   just in theory.
   No confirmation gate for these three files, per M6/decision A2 —
   `apply_tier2_sync()`'s own snapshot-before-write/atomic-apply/
   rollback-on-failure infrastructure is the safety mechanism, not an
   owner prompt.
5. **If `apply_tier2_sync()` raises** (e.g. a path unexpectedly
   appears in `GATED_DOCS` — shouldn't happen for these three files
   per `[B-035]`'s fix, but check `GATED_DOCS`'s actual current
   contents rather than assuming): report the exact error to the
   owner. Do not swallow it or retry silently.
6. Never touches `docs/CONSTITUTION.md` or `docs/BACKLOG.md` in this
   half — `docs/BACKLOG.md` closure stays in the `Closes:`/M1 half
   above, kept separate; `docs/CONSTITUTION.md` stays permanently
   excluded, per `SPEC.md`'s own stated scope.
