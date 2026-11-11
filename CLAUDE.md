# Article Pipeline project entry point

This repository contains reusable publication product code. The boundary
between product and private runtime is Constitution rules AP-9 to AP-11.

## Sources and task selection

Start with the section "How every repository works" of the
[universal rules](docs/tooltempest/universal-rules.md): the reading order, the
file that wins on a conflict, how a rule changes, and what each document is for.
Its rules are binding. The file is installed from the pin; if it is absent, run
"Setup of a fresh clone" in [README](README.md). If
`docs/tooltempest/universal-rules.md` is missing: stop and run this from the
repository root:

```bash
( set -eu; D=$(mktemp -d "${TMPDIR:-/tmp}/tooltempest.XXXXXX"); trap 'rm -rf "$D"' EXIT; R=$(python3 -c 'import json; print(json.load(open(".tooltempest.lock"))["repository"])'); C=$(python3 -c 'import json; print(json.load(open(".tooltempest.lock"))["commit"])'); git clone -q --no-checkout "$R" "$D"; git -C "$D" checkout -q --detach "$C"; python3 "$D/scripts/tooling.py" materialize --root . --source "$D" --apply )
```

It clones the `repository` named in `.tooltempest.lock` into a new temporary
directory, checks out the lock's `commit` there, installs from that checkout, and
removes the directory on exit. Its exit status is that of `materialize`; it fails
if the commit is absent from the repository. No local ToolTempest clone is used.
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
