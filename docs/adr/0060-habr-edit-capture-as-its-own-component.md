---
id: ADR-0060
status: Accepted
supersedes: null
superseded_by: null
source_type: verbatim
---

# ADR-0060: Habr Edit Capture — a new component, a Drive-metadata dedup key, and an explicit zero-diff record

## Status

Accepted.

## Context & Constraints

ADR-0050 point 4 established the process design: "Manual Habr edits are Evidence, not a
direct prompt change... the diff between the draft and the published text is captured as
an Evidence record — the same kind of signal a `trash` or `style-off` verdict produces."
That decision does not say where this data physically lives, how a repeated scheduled-job
run avoids double-capturing the same edit, or what happens when the owner publishes a
draft completely unedited. A prior read-only architecture-inference pass (this session)
found no shared "Evidence" schema anywhere in this codebase to plug into: `grep` for any
`Evidence` base class/protocol across the repo returns zero hits; `verdict/`'s
`VerdictRecord` and a real `evidence_package/output/` record share zero fields; and
`PatternCandidate.evidence[]` (ADR-0052) has no element-type definition in either
governing ADR. This ADR records the three concrete decisions that pass's inference arrived
at, now implemented.

SPEC.md Functional Requirements 17-21 (M4) describe the domain directly: each Habr article
lives in its own Google Drive folder, containing `YYYY-MM-DD-draft` and `YYYY-MM-DD-final`
files (FR18). No Habr publish event occurs inside this milestone's own scope (FR17/FR20: a
manual Telegram hand-off, no automatic posting, no scraping) — `publication_registry`'s
`content_id` therefore does not exist for a Habr article at the point a diff is captured.

## Decision

**1. A new component, `habr_edit_capture/`, not an extension of `verdict/` or
`evidence_package/`.** `evidence_package/`'s own domain is Claim-verification search
results (`evidence_id`/`claim_id`/`search_query`/`source_url`) — an unrelated pipeline
stage; reusing it would couple two unrelated domains on the shared English word "evidence"
alone. `verdict/`'s `VerdictRecord` is keyed by `content_id` (which does not exist here)
and carries a closed `verdict_type: Literal["good", "trash", "style-off"]` with no slot for
a text diff. `habr_edit_capture/` follows `verdict/`'s own append-only, per-domain-object
JSON-file pattern (not `publication_registry/`'s single-record-per-key reconciliation),
since a re-edit is a new event, not a correction of the first one — matching ADR-0050 point
4's framing of an edit as "the same kind of signal" a verdict is.

**2. Two distinct keys.** The *domain key* (`folder_id` + `date_stem`) identifies which
article a capture belongs to, per FR18's own per-folder, date-stemmed-filename convention.
The *dedup key* (`final_modified_time`, Drive's own metadata field on the `-final` file) is
checked separately, within one domain-key directory, before writing. Confirmed directly
against the live Drive API v3 Files reference (this session): `id` and `modifiedTime` are
available on every file via `files.get`/`files.list`; `headRevisionId` is explicitly
"currently only available for files with binary content in Google Drive" — the owner's
folders hold native Google Docs, not binary uploads, so `modifiedTime` is the field
actually available, not a fallback choice. FR18/FR19 are silent on a same-filename re-edit
(confirmed: neither mentions or anticipates it); a dedup key keyed on filename alone (no
`modifiedTime`) would silently treat a genuine second edit as "already captured," losing
the exact Evidence signal ADR-0050 point 4 exists to collect. `modifiedTime` is standard,
always-available Drive API metadata, not an invented mechanism — closing this gap this way
is implementation detail with sufficient basis, not a fork requiring owner input.

**3. A zero-diff capture is written, not skipped.** When the owner publishes a Habr draft
completely unedited, `difflib.unified_diff` on identical inputs returns an empty sequence
(confirmed directly: `list(difflib.unified_diff(a, a))` is `[]`). This is still written as a
record, with an explicit `has_changes: bool` field — not inferred later from `diff == ""` by
every future reader, and not silently skipped as "nothing happened." This extends two
already-established patterns in this project rather than inventing new policy:
`VerdictRecord.verdict_type`'s `"good"` value is itself a real, written positive outcome,
not an absence; and SPEC.md Functional Requirement 26 states Weekly's `verdict_status` is
"never silently omitted." Silently skipping an unedited draft would bias Weekly's future
pattern detection toward only ever seeing edited cases, undercounting the true approval
rate — the opposite of what ADR-0050's "no verdict is still a complete, valid state"
philosophy, applied here, is for.

## Alternatives & Rationale

| Option | Outcome |
|---|---|
| A. Extend `evidence_package/` to also hold Habr diffs | Rejected — unrelated domain (Claim-verification search vs. owner-edit diff capture); coupling on the shared word "evidence" alone is exactly what this project's own decision rule (checked directly this session) warns against. |
| B. Extend `verdict/` to also hold Habr diffs | Rejected — no `content_id` exists in M4's scope to key on, and `verdict_type`'s closed three-value literal has no slot for a diff. |
| C. Dedup on `(folder_id, date_stem)` alone, filename-presence-triggered | Rejected — FR19's "watches for a new `-final` file" wording would support this reading, but it silently drops a genuine re-edit's Evidence signal, which ordinary, already-available Drive metadata (`modifiedTime`) avoids at no real cost. |
| D. Dedup on `headRevisionId` | Rejected — confirmed against the live Drive API v3 reference as binary-content-only; the owner's folders hold native Google Docs, so this field would not be populated. |
| E. Skip writing a record when draft equals final | Rejected — treats a real, meaningful outcome ("approved as-is") as if it were an error or non-event, contradicting this project's own "never silently omit state" convention. |
| **Chosen — new component (1), domain-key/dedup-key split with `modifiedTime` (2), explicit zero-diff record (3)** | The smallest architecture that satisfies FR17-21 without coupling to either existing component's documented domain or key invariants, and without inventing a mechanism Drive doesn't already provide. |

## Consequences

- `habr_edit_capture/output/` lives on its own branch, `habr-edit-capture-data` — same
  reasoning as ADR-0055's `registry-data`: this component's own scheduled workflow
  (`habr-edit-capture.yml`) writes it, `main` is branch-protected, and a workflow's bot
  identity has no admin bypass (ADR-0039). `HABR_EDIT_CAPTURE_OUTPUT_DIR` follows
  `publication_registry/writer.py`'s own `REGISTRY_OUTPUT_DIR` naming convention.
- A future consumer of `habr_edit_capture/output/` (Weekly, M6, not yet started) reads
  `has_changes` directly rather than re-deriving it from `diff`.
- This ADR does not design Weekly's own `evidence[]` consumption contract — M6 is not yet
  started; `habr_edit_capture/`'s record shape is designed to be a plausible future
  `evidence[]` element, not confirmed as the final one.

## Confirmation & Revisit

Confirmed when: a real scheduled run against the owner's real Drive folders produces one
written record for a genuine edit, one idempotent no-op for a repeated run against an
unmodified file, and one written zero-diff record for an unedited draft — mirroring this
ADR's own unit-test coverage (`habr_edit_capture/test_diff_capture.py`), but against real
Drive data rather than a fake `service` object.

Revisit if Weekly's own `evidence[]` design (once M6 starts) needs a different element
shape than this record provides, or if `modifiedTime` turns out to be unreliable in
practice (e.g., Drive's own internal sync behavior touches it without a real content
change) — via a new, superseding ADR, not an edit to this one.

**Source.** Read-only architecture-inference session (this session, prior turn) plus this
session's own M4 implementation pass — Drive API v3 Files reference fetched and quoted
directly, `difflib.unified_diff`'s empty-diff behavior confirmed by direct execution, not
assumed from either.
