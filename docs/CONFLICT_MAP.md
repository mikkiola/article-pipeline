# Article Pipeline — Conflict Map & Repo-Content Classification

Point-in-time record, dated 2026-08-14. Not a living document — a new
audit produces a new dated version, this one isn't edited in place
after the fact. Closes Phase 3 (conflict map) and Phase 4
(classification) of the memory-restructure methodology, both of which
were found inline during the `docs/` migration but not previously
collected into a standalone artifact.

## Conflicts found

| Conflict | Where | Status at time of writing |
|---|---|---|
| `SPEC.md` describes a Bitwarden CLI call (`bw get password ...`) as the mechanism for reading `LINKUP_API_KEY`, in four places. Actual code (`evidence_package/search_backend.py`, function `_get_api_key()`) reads only from the environment — no Bitwarden CLI call exists in the code path. | `SPEC.md` vs `evidence_package/search_backend.py` | Open — tracked as a P0 item in `docs/BACKLOG.md` |
| `README.md` describes the repository as holding "only the structural scaffold," with code to follow as a separate task. Actual repo contains working Claim Extraction and Evidence Package code, plus `docs/adr/` and four top-level canonical docs. | `README.md` vs actual repo contents | Open — tracked as a P1 item in `docs/BACKLOG.md` |
| Two Google Drive files existed under the identical name `CAUSAL_MEMORY_ap_260813` (different internal IDs, overlapping but not identical content, no `SUPERSEDED` marker). Found during the Drive→repo migration. | Google Drive (pre-migration) | Moot — Drive is no longer the canonical source for this project as of the `docs/` migration; not resolved in Drive itself, noted here for the historical record only |

## Repo-content classification (Phase 4)

Using the same categories applied to the Google Drive documents in a
prior session: NORMATIVE / OPERATIONAL / DECISION / EXPERIMENTAL /
HISTORICAL / OBSOLETE / UNKNOWN.

| File | Classification | Why |
|---|---|---|
| `SPEC.md` | NORMATIVE, partially OBSOLETE | Active specification for Evidence Package, but the secret-retrieval section is stale — see conflict above |
| `CHECKPOINT.md` | OPERATIONAL | Milestone tracking for Evidence Package's implementation; reflects work already done, not a standing rule |
| `README.md` | OBSOLETE | Describes a state of the repo that stopped being true once the first real component landed; not currently a reliable description of anything |
| `docs/CONSTITUTION.md` | NORMATIVE | Active role/protocol rules |
| `docs/ARCHITECTURE.md` | NORMATIVE | Active current-state record, rewritten wholesale on structural change |
| `docs/ROADMAP.md` | OPERATIONAL | Active plan, rewritten wholesale on major update |
| `docs/BACKLOG.md` | OPERATIONAL | Active task/decision list, items move in and out continuously |
| `docs/adr/*.md` | DECISION | Immutable once accepted; superseded by new ADRs, never edited in place |
| `claim_extraction/extraction_rules.md` | NORMATIVE | Active extraction checklist |
| `claim_extraction/output/pilot_run_*.json`, `pilot_log_*.json` | HISTORICAL | Immutable pilot-run records, not current specification |
| `evidence_package/output/evidence_run_*.json`, `evidence_log_*.json` | HISTORICAL | Immutable pilot-run records, not current specification |
| `.tooltempest.lock`, `scripts/sync-tooling.sh` | OPERATIONAL | Active mechanism for pulling shared tooling |
