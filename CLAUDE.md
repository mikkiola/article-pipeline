# Article Pipeline project entry point

This repository contains reusable publication product code. Personal execution,
credentials, account-specific schedules and deployment glue belong outside this
public repository, including outside its ignored directories.

## Sources and task selection

Read [CONSTITUTION](docs/CONSTITUTION.md), [PROJECT](docs/PROJECT.md),
[ARCHITECTURE](docs/ARCHITECTURE.md), [ROADMAP](docs/ROADMAP.md),
[BACKLOG](docs/BACKLOG.md) and [CURRENT_MISSION](CURRENT_MISSION.md) before
choosing work. An active mission's operational fields take precedence over a
lagging roadmap pointer; [SPEC](SPEC.md) is the bounded implementation contract.
Use [docs/adr](docs/adr/) for accepted decisions. This file routes to these
sources; it does not maintain a second architecture, roadmap or goal registry.

Neighboring repositories are separate systems. Consume established data contracts
rather than reading their private checkouts or adding implicit integrations.
Access other repositories only within the current task’s explicit allowlist.

## Work areas

- Extraction, context and evidence packages feed the strategy/authoring layers.
- Strategy policy modules use their adapters; consult
  [pyproject.toml](pyproject.toml) for the enforced import boundary.
- Authoring produces drafts. Draft acceptance, permission to publish and a
  confirmed external publication are distinct outcomes.
- Publisher and registry work must retain the product/private-runtime boundary;
  see `.claude/rules/publication.md`.

## Offline verification

Python version and dependencies are declared in [pyproject.toml](pyproject.toml).
Inspect the selected test module and its doubles before running it. Existing
component commands include:

```bash
python3 -m pytest strategy_layer -q
python3 -m pytest author -q
python3 -m pytest linkedin_publisher publication_registry -q
```

These are component test commands, not permission to run production entry points
or a claim that they were executed by an instruction edit. For instruction-only
changes, check links, rule scopes, exact diff and `git diff --check`.
Do not run daily publishing/authoring entry points, dispatch workflows or exercise
external services merely to validate these instructions.

The existing [session-end skill](.claude/skills/session-end/SKILL.md) is explicitly
owner-triggered. Reuse it and the installed shared skills rather than copying
their procedures into project agents or additional skills. Consumer pin updates
and tooling synchronization are separate changes, not startup actions.

Preserve existing work and keep permission to prepare implementation separate
from permission to commit/push it. This offline phase changes no settings,
permissions, hooks, MCP activation or private runtime state.
