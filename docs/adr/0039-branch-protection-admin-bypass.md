# ADR-0039: Branch Protection on `main` — Admin Bypass Enabled, Permanently

Status: Accepted
Relates to: ADR-0035 (article-pipeline, pre-merge gate for gated docs)
— ADR-0035 decided that `docs/BACKLOG.md`/`docs/ROADMAP.md` become
CODEOWNERS-protected paths requiring branch-protection-enforced review,
and its own Validation section left "whether branch protection actually
blocks a PR ... without the required owner/code-owner approval" as an
open verification step, deferred to the manual configuration this ADR
now confirms happened. Also relates to `docs/BACKLOG.md`'s now-closed
"Manual follow-up, not a code task: configure GitHub branch protection
on `main`" item (the "P1 — Implement ADR-0033's GitHub Actions
workflow" entry) — that item tracked turning branch protection on at
all; this ADR documents one specific facet of that configuration
(admin bypass) which was decided and applied but never separately
recorded anywhere.

**A note on why this ADR exists.** The admin-bypass decision described
below was made and applied in a prior session, not this one — verified
and configured via GitHub's repository settings, working as intended.
It was never written to `docs/adr/` or `docs/BACKLOG.md`. This ADR
closes that documentation gap; it is not re-deciding or re-litigating
anything. The decision itself, and its rationale, are recorded here for
the first time, but the decision predates this ADR's own writing.

## Context

ADR-0035 introduced GitHub branch protection on `main`, requiring a
code-owner-approved pull request before `docs/BACKLOG.md` or
`docs/ROADMAP.md` can merge — the pre-merge confirmation gate that
replaced ADR-0033's superseded post-merge reconciliation-PR design.
Turning branch protection on for `main` at all, as a GitHub repository
setting, necessarily also exposes a separate, adjacent toggle GitHub
calls **"Do not allow bypassing the above settings"** (API field
`enforce_admins`) — independent of the CODEOWNERS-review requirement
ADR-0035 was actually about. Left at its default (bypass allowed),
anyone with admin permission on the repository can push directly to
`main`, or merge a PR without the required review, bypassing every
other rule the branch protection configures — including the very
CODEOWNERS gate ADR-0035 exists to enforce.

This project has exactly one contributor: the owner, working through
Claude Code sessions with direct, routine push access to `main`
(confirmed as this project's established workflow throughout its
history — see, e.g., ADR-0016's git-auth setup and every prior ADR's
own "Source" line naming direct architect/Claude-Code sessions, not a
PR-based flow). Requiring a pull request for every single commit, with
no bypass, would impose real process overhead — opening and
self-merging a PR for routine changes — with no corresponding safety
benefit, since there is no second contributor whose changes the gate
would meaningfully review.

## Decision

The `enforce_admins` setting on `main`'s branch protection rule is
**disabled** (bypass enabled) — deliberately, and permanently, not as
an interim state pending a future hard-enforcement upgrade.

Because GitHub's admin bypass capability is granted per-repository to
users holding the `admin` role, and this repository currently has
**exactly one collaborator, the owner, holding that role**, the bypass
capability is structurally scoped to the owner alone — not a broader
group, and not exercisable by any external contributor's pull request,
which would still need to satisfy the CODEOWNERS review requirement
ADR-0035 configured to reach `main` at all.

### Verification (this session, direct)

Re-run today, per this ADR's own task, using `gh api` against the live
repository — not assumed from the prior session's account of it:

```
$ gh api repos/mikkiola/article-pipeline/collaborators
```

Output (trimmed to the relevant fields; one array element only):

```json
[{"login":"mikkiola", ... ,"permissions":{"admin":true,"maintain":true,"push":true,"triage":true,"pull":true},"role_name":"admin"}]
```

Exactly one collaborator, `mikkiola` (the owner), with `role_name:
"admin"`. No other collaborator exists.

```
$ gh api repos/mikkiola/article-pipeline/branches/main/protection
```

Output (trimmed to the relevant fields):

```json
{
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": true,
    "require_last_push_approval": false,
    "required_approving_review_count": 1
  },
  "required_signatures": {"enabled": false},
  "enforce_admins": {"enabled": false},
  "required_linear_history": {"enabled": false},
  "allow_force_pushes": {"enabled": false},
  "allow_deletions": {"enabled": false}
}
```

`required_pull_request_reviews.require_code_owner_reviews: true` with
`required_approving_review_count: 1` confirms ADR-0035's own gate is
live (a PR touching a CODEOWNERS-protected path requires one owner/
code-owner approval before merging). `enforce_admins.enabled: false`
confirms admin bypass is enabled, exactly as described above. Both
match this ADR's description of the configured state; no discrepancy
found.

## Rationale

**Why permanent, not provisional.** This mirrors the reasoning already
recorded for a structurally similar permanent-by-design choice —
`docs/BACKLOG.md`'s "Resolved — pre-push component/doc pairing check
stays warning-only permanently" entry: a soft, low-friction mechanism
is the *correct* long-term design for a solo-developer repository, not
an interim state en route to something stricter. Requiring the owner's
own pushes to route through a self-approved pull request would add
pure process overhead — the same person opening and approving their
own PR — without gaining any safety property a second, independent
reviewer would normally provide, because no second reviewer exists.
Tightening this only becomes worth reconsidering if the collaborator
set actually changes (see Reversal condition).

**Why this doesn't weaken ADR-0035's actual protection.** ADR-0035's
purpose was gating `docs/BACKLOG.md`/`docs/ROADMAP.md` against an
*external contributor's* unreviewed change once this project accepts
outside contributions (ADR-0033/0034's contributor-governance track).
Admin bypass is scoped to accounts holding the `admin` role on this
repository — today, and for as long as the collaborator list verified
above stays a single owner-admin, that is exactly nobody but the owner
themself. A contributor's pull request, lacking admin permission,
still cannot merge into a CODEOWNERS-protected path without the
required review, regardless of this setting.

## Constraints

Does not change ADR-0035's CODEOWNERS/required-review configuration
for `docs/BACKLOG.md`/`docs/ROADMAP.md` — that remains exactly as
ADR-0035 decided and as verified above. Does not grant bypass to any
account other than the repository's `admin`-role holders. Does not
edit ADR-0033, ADR-0034, or ADR-0035 (Immutable Lineage, ADR-0011).

## Consequences

- The owner continues pushing directly to `main` without opening a
  pull request for routine work, unchanged from this project's
  established workflow throughout its history.
- If a second collaborator is ever added to this repository, this
  ADR's core safety argument (bypass is structurally scoped to "the
  owner" because "the owner" is currently the only admin) stops
  holding the moment that collaborator is granted the `admin` role —
  see Reversal condition.
- `docs/BACKLOG.md`'s "Manual follow-up ... configure GitHub branch
  protection on `main`" item is closed by this ADR plus the
  verification above (the review-requirement half of that
  configuration is independently confirmed live); see that entry for
  the closure note.

## Reversal condition

If a second collaborator is ever granted the `admin` role on this
repository (not `maintain`, `push`, `triage`, or `pull` — GitHub scopes
branch-protection bypass to `admin` specifically), re-verify via `gh
api repos/mikkiola/article-pipeline/collaborators` whether the bypass
scope this ADR describes ("exactly the repo owner") still holds, and
revisit this decision — likely toward enabling `enforce_admins` (no
bypass for anyone) or scoping bypass more narrowly than "any admin,"
via a new, superseding ADR, not an edit to this one.

## Source

Decision made and configured in a prior article-pipeline session (not
this one) — exact session not separately logged, and not
reconstructable beyond what this ADR itself now records; this is the
documentation-gap closure, not the original decision-making session.
Verification re-run and this ADR written in an article-pipeline
session, 2026-08-20, following an owner-directed task to close the
gap after it was found undocumented mid-task in a prior session.
