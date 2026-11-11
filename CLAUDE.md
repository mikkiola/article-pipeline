# Article Pipeline project entry point

This repository contains reusable publication product code. The boundary
between product and private runtime is Constitution rules AP-9 to AP-11.

## Sources and task selection

Start with the section "How every repository works" of the
[universal rules](docs/tooltempest/universal-rules.md): the reading order, the
file that wins on a conflict, how a rule changes, and what each document is for.
Its rules are binding. The file is installed from the pin; if it is absent, run
"Setup of a fresh clone" in [README](README.md). If
`docs/tooltempest/universal-rules.md` is missing: stop and run, from the
repository root, `D=$(mktemp -d) && git clone -q --no-checkout ~/Dev/github.com/mikkiola/tooltempest "$D" && git -C "$D" checkout -q --detach <commit> && python3 "$D/scripts/tooling.py" materialize --root . --source "$D" --apply; rm -rf "$D"`.
`<commit>` is the `commit` field of `.tooltempest.lock`.
`$D` is a new temporary clean checkout that the last command removes; the
ToolTempest main clone, which can be dirty, is only read.
Project rules are in
[CONSTITUTION](docs/CONSTITUTION.md); [SPEC](SPEC.md) is the bounded
implementation contract. This file routes to these sources. The working rules
for neighboring repositories, outcomes, and verification are Constitution rules
AP-15 and AP-16.

## Work areas

- Components and their status: [ARCHITECTURE](docs/ARCHITECTURE.md). The
  enforced import boundary of the strategy layer: [pyproject.toml](pyproject.toml).
- Publisher and registry rules: `.claude/rules/publication.md`.

## Offline verification

Python version and dependencies are declared in [pyproject.toml](pyproject.toml).
Existing component commands include:

```bash
python3 -m pytest strategy_layer -q
python3 -m pytest author -q
python3 -m pytest linkedin_publisher publication_registry -q
```

The [session-end skill](.claude/skills/session-end/SKILL.md) is the existing
session-closing workflow.

A `git push` needs the Owner's separate explicit permission (universal rule
WR-14). Until the repin delivers that rule, this sentence is the in-repository
statement of it.
