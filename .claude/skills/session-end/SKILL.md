---
name: session-end
description: "Explicit, owner-triggered session-end doc-sync for article-pipeline: reviews this session's commits for docs/BACKLOG.md items to close (Closes: B-NNN trailers), presenting and writing per the confirmation rules below. Triggers on: /session-end only — never invoked by the model on its own judgment. NOT for: autonomous session-end detection (that trigger already exists and was found impractical — see docs/BACKLOG.md's [B-043])."
user-invocable: true
disable-model-invocation: true
allowed-tools: Read, Edit, Bash
---

# /session-end

Explicit, human-triggered supplement to the autonomous-judgment
plan-completion trigger — not a replacement, not a redesign. The autonomous
trigger is unchanged; this command exists because
it cannot fire without the "opening stated plan" that
the universal rules require (their "Reading order"), which a session
made of many independently-scoped tasks never produces — confirmed by
a real dry-run test, see `docs/BACKLOG.md`'s `[B-043]`. The owner
types `/session-end`; invoking it *is* the signal — this command does
not try to infer whether the session is "done."

## Trailer-detection rule

**Never use a naive line-start text match** (e.g. grep for lines
beginning with "Closes:") — a commit body can contain ordinary prose
that happens to start a wrapped line with that same text.

Use git's own trailer parser instead — it already knows the real
trailer-block convention (a contiguous `key: value` block at the very
end of the message, per `git-interpret-trailers`):

```bash
git log <session-commit-range> --format="%H %(trailers:key=Closes,valueonly)"
```

Each output line is `<full SHA> <value-or-blank>` — filter out blank
values; a commit with no trailer of that key produces a trailing space
and nothing after it.

**Fallback, only if `git log`'s trailer format is unavailable for some
reason:** a manual check must require (a) the candidate line sits in
the last contiguous non-blank block of the commit message — after the
final blank line, with nothing else following it — and (b) the value
has no trailing punctuation or continuation into further prose, a bare
`key: value` line and nothing else on it. Never fall back to a plain
line-start grep under any circumstance — that is the exact bug this
rule exists to prevent.

## What this does — `docs/BACKLOG.md` closure

1. **Find this session's `Closes: B-NNN` trailers**, per the
   trailer-detection rule above — never scan further back than this
   session's own commits, no repo-wide history scan.
2. **Look up each `B-NNN`'s current title** in `docs/BACKLOG.md` (its
   `### [B-NNN] <title>` heading line) — verbatim, exactly as written,
   no summarizing or rewording.
3. **Zero candidates found:** say so plainly (e.g. "No `Closes:`
   trailers found in this session's commits — nothing to close.").
   Stop here.
4. **Exactly one candidate:** write the
   `docs/BACKLOG.md` edit and make a local commit. Do not push: a push
   needs the Owner's separate permission (WR-14 of the universal rules),
   requested only after the mandatory checks pass. Invoking
   `/session-end` already is the owner's "close now" signal — no
   separate per-item confirmation prompt needed on top of that.
5. **More than one candidate:** present them in this
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
   edit/commit fixes it — no supersession ritual.
7. Never touches `docs/CONSTITUTION.md` — permanently excluded.
