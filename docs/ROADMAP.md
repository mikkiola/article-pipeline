# Article Pipeline — Roadmap

Plan only. No rationale here — see `docs/adr/` for why any decision was
made. Rewritten wholesale on a new/expanded spec or a major
architectural update — not every session.

## Status

| Phase | Status |
|---|---|
| 0 — Scaffold + `graph_reader.py` | Closed |
| 1 — Claim Extraction pilot | Closed |
| 2 — Evidence Package | Closed |
| 2.5 — Context/causal-structure layer | Next — not started |
| 3 — Strategy Layer + Author + Quality Gate | Blocked on 2.5 |
| 4 — Platform Adapter (Habr → LinkedIn) + Circuit Breaker | Not started |
| 5+ — Experiment Log, remaining platforms | Not started |

## Next session — start here

Do task A first (independent, no blocker). Then do task B (blocking —
must finish before anything in Phase 3 starts).

### Task A — fix SPEC.md's stale secret-storage references

1. Open `SPEC.md` at repo root.
2. Find every mention of `bw get password` or a Bitwarden CLI call
   inside the described secret-retrieval mechanism (currently four
   occurrences: the retrieval command itself, the CLI-installed note,
   and two further descriptions of the runtime read path).
3. Replace each with a description matching what `evidence_package/
   search_backend.py`'s `_get_api_key()` function actually does:
   read `LINKUP_API_KEY` from the environment only, no Bitwarden CLI
   call anywhere in the code path. Bitwarden is one way to populate
   that environment variable locally, not a runtime dependency.
4. Commit this as its own small commit — don't bundle with task B.

### Task B — design the context/causal-structure layer

**Problem, stated inline (no external file needed to understand it):**
Claim Extraction produces two text fields, `novelty` and `basis`, by
extracting them from a source atom. When these two fields are
concatenated and used as a search query for Evidence Package, the
result systematically loses: (a) the atom's domain/topic context — this
context exists in the atom's tags and wiki-links in the knowledge
graph, but the current extraction schema doesn't carry it into
`novelty`/`basis` at all, and (b) the most concrete, specific parts of
the original claim (named examples, named roles, references to current
discourse) — these get abstracted away during extraction. This was
found by manually comparing the full text of 5 source atoms against
their extracted `novelty`+`basis` output side by side and confirming
the same pattern in 4 of the 5 cases.

**What "design" means here, concretely:** produce a written proposal
(not code) for a new data layer that sits between Claim Extraction's
output and Evidence Package's input, carrying forward the context that
`novelty`+`basis` currently drops. The proposal must specify: what
new field(s) get added, where they're populated from (tags? wiki-links?
a new extraction step?), and how this interacts with the existing
`novelty`/`basis` contract without breaking whatever already consumes
those two fields elsewhere in the pipeline.

**How to produce it:** run a `/spec` session — this project's
established practice is the Claude Code skill at
`skills/spec/SKILL.md` (delivered via the `mikkiola/tooltempest`
shared-tooling repository and synced locally via
`scripts/sync-tooling.sh` — run that script first if
`~/.claude/skills/spec/SKILL.md` doesn't exist yet). That skill runs an
interview (technical implementation / UI-UX / risks / trade-offs, a
few questions at a time) and produces a `SPEC.md`-format document as
output. For this task, the interview topic is exactly the problem
statement above — nothing more, nothing less. Do not use this
`/spec` run to redesign Evidence Package's `verified` criterion (see
constraint below).

**Output location:** a new file, `context_layer/SPEC.md`, in this
repository, following the same section template as the existing
`SPEC.md` at repo root (Overview → Goals → Tech Stack → Functional/
Non-Functional Requirements → Data Model → Test Plan → Milestones →
Open Questions).

**Definition of done for this task:** `context_layer/SPEC.md` exists,
committed, and has been read and confirmed by the project owner before
any implementation code is written against it.

**Blocking constraint — do not violate:** do not modify Evidence
Package's `verified` criterion (in `evidence_package/`) as part of this
task, even if the `/spec` interview surfaces ideas about it. That's a
separate, later decision — mixing it into this design risks conflating
two different fixes and making it impossible to tell which change
caused which effect.

If either task above is unclear once you're in the repo (e.g. the
described code doesn't match what's actually there): stop and ask the
owner one specific clarifying question rather than guessing.

## Blocked on Task B

Phase 3 (Strategy Layer, Author, Quality Gate) — publishing on
unreliable Evidence verdicts is premature until the context-loss
problem is fixed.

## Open decisions (not yet made — see BACKLOG.md for detail)

- Support-type classification for Evidence `verified`
- EN/CN search-query translation — permanent or one-off
- ToolTempest CLI adapter design
- Possible overlap between a specified confidence threshold and the
  interactive assessment actually in use — reconcile or confirm
  they're separate layers
