---
id: ADR-0073
status: Accepted
supersedes: null
superseded_by: null
source_type: inferred
---

# ADR-0073: Retire post-merge reconciliation

## Status

Accepted on 2026-11-06, recording the Owner-approved direction for B-081.
Supersession is partial and specified below; the file-level fields remain
null, following ADR-0035's point-level precedent. Earlier ADRs remain intact.

## Context & Constraints

Before retirement, the workflow checked out `main`; `reconcile.py` read that
checkout's `docs/ARCHITECTURE.md` as `proposed`, and `apply_tier2_sync()`
compared it with the same file. No document change was produced. Its only
publication attempt was an evidence JSON commit pushed to `main` with the
checkout's `GITHUB_TOKEN`.
No repository consumer uses these records; the shared legacy module also
contains record-writing and retention helpers, not an independent reader.

Runs [40633031024](https://github.com/mikkiola/article-pipeline/actions/runs/40633031024),
[40654307961](https://github.com/mikkiola/article-pipeline/actions/runs/40654307961)
and [42028280263](https://github.com/mikkiola/article-pipeline/actions/runs/42028280263),
re-read on 2026-11-06, each reported `(no changes)` and failed after three
push attempts. The live protection requires a PR and one code-owner review;
the sole admin is the Owner, and the workflow has no authorized bypass.
Git's rejection text is absent from the logs: attributing the rejection to
protection is an inference. At inspection before retirement, local `main`
matched the live branch at `7253c25adf7d325dd1758ea2fa0c9273fafddb78`;
its history contained no
workflow-authored commit changing `docs/ARCHITECTURE.md`.

## Decision

1. Retire the post-merge reconciliation workflow, its dedicated script and
   two dedicated tests, including the workflow's ToolTempest bootstrap step.
2. Supersede the remaining post-merge reconciliation and evidence-publication
   decisions in ADR-0033 points 1 and 6, and the corresponding post-merge
   `ARCHITECTURE.md` automation description in ADR-0035's Decision and
   Consequences. The historical ADRs are not invalidated in full. ADR-0034's
   contributor-authored document model and ADR-0035's pre-merge gate remain.
   ADR-0072's reconciliation-workflow-specific consequences and fetch revisit
   condition cease to apply; its distribution decision remains unchanged.
3. Keep `main` protection, CODEOWNERS and the Owner's existing admin bypass
   unchanged. Add no bot permission or bypass, PAT or GitHub App credential,
   data branch, or replacement persistent evidence store.
4. Retain historical `.tempest/runs/*.json` records. Keep shared legacy
   `doc_sync.py` and `doc_sync_tier2.py`, ToolTempest scripts and schemas:
   Tier 2's CLI/apply/rollback path and the installed `check_manifest.py`
   still use shared helpers. Their retirement is outside B-081.

This decision applies only to `mikkiola/article-pipeline`. It assigns no
Goal ID and does not change the current mission or start Stage 8.

## Alternatives & Rationale

| Option | Verdict |
|---|---|
| Retire the no-op reconciliation and its evidence publication | Chosen by the Owner; removes the failing publisher without losing document updates. |
| Give the bot bypass rights or another credential | Excluded by the Owner; adds authority for a redundant operation. |
| Publish records to another branch or persistent store | Excluded by the Owner; no repository consumer requires a replacement. |

## Consequences

Document updates land in the contributor's original PR. No post-merge
reconciliation or new evidence publication is provided. Historical records
and unrelated workflows remain; local ToolTempest installation still follows
the existing pinned materializer procedure.

## Confirmation & Revisit

Verify removal and dependency references, retained shared DocOps behavior,
ADR structure/numbering and generated index, and the unchanged protection
files, unrelated workflows and historical records. Local verification cannot
establish deployment: the Owner must review and publish the worktree change.
Revisit only if a concrete required post-merge function or evidence consumer
emerges; that requires a separate decision.

**Source.** The Owner's B-081 task supplied in this session, explicitly approving
retirement and its constraints; this record summarizes that decision. Code,
local Git history and read-only GitHub API/log inspection on 2026-11-06 supply
the observations above. No external AI review supplied the decision.
