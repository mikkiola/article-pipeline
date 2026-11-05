# Article Pipeline

Article Pipeline — a publishing conveyor for technical articles (Habr +
LinkedIn): claim extraction, evidence gathering, strategy layer, authoring,
quality gate, and platform adaptation. Claim extraction, evidence gathering,
the strategy layer and authoring exist; the quality gate and platform
adaptation are not started — see `docs/ARCHITECTURE.md`.

Canonical documentation lives in `docs/`: the Constitution, Project,
Architecture, Roadmap and Backlog documents, and the decision records
under `docs/adr/`.

Atom Selector and `graph_reader.py` currently live here as vendored copies
of `brain.git` code; migrating them to a single source is open as `[B-002]`
in `docs/BACKLOG.md`.

Authoring now has a first MVP implementation: it drafts Habr/LinkedIn
articles from Collector's data, now routed through the strategy
layer's verdict rather than read directly — see
`docs/adr/0043-author-mvp-single-source-pilot.md` for the original
pilot architecture and
`docs/adr/0045-post-classification-authoring-context.md`/`docs/adr/0046-habr-multi-claim-digest.md`
for how it's wired today; full per-component status is in
`docs/ARCHITECTURE.md`.

## Setup of a fresh clone

The ToolTempest files this repository uses (`scripts/tooling.py`,
`scripts/docops.py`, `scripts/doc_sync.py`, the other installed `scripts/` and
`schemas/` files, and `docs/tooltempest/consumer-contract.md`) are installed
from the commit pinned in `.tooltempest.lock` and are not tracked. A fresh clone
therefore lacks them, including `scripts/tooling.py`, and its `.git/hooks` holds
no hooks yet; the last step below installs them. Once installed, the hooks block
every commit and every push that carries ref updates for as long as those files
are missing, and the checks that import them fail. From the repository root:

```bash
tt="$HOME/src/tooltempest"   # any directory outside this repository
git clone "$(python3 -c "import json; print(json.load(open('.tooltempest.lock'))['repository'])")" "$tt"
git -C "$tt" checkout --detach "$(python3 -c "import json; print(json.load(open('.tooltempest.lock'))['commit'])")"
python3 "$tt/scripts/tooling.py" materialize --source "$tt"          # dry run: lists what it would write
python3 "$tt/scripts/tooling.py" materialize --source "$tt" --apply  # installs, then verifies
python3 scripts/tooling.py verify --source "$tt"                     # must exit 0
bash scripts/install-hooks.sh                                        # activates the git hooks
```

If a ToolTempest clone already exists, set `tt` to it instead of cloning; it
must hold the pinned commit (`git -C "$tt" cat-file -e <commit>`).

### Optional: ToolTempest skills and rules for an AI client

The client target installs ToolTempest's `skills/` and `rules/` into a client
configuration directory, only when asked and only into the root you name; there
is no default root. Neither the git hooks nor CI use it. The root needs its own
`.tooltempest.lock`, and the materializer never creates a lock (it never pins).
Do not copy this repository's lock: it declares `scripts/doc_sync.py`, a path
the client target does not install, so the target rejects it
(`DECLARED_PATH_NOT_INSTALLABLE`). Write a lock with the same `repository` and
`commit` only, then run the target, with `tt` set as above (steps as in the
"Usage today" section of ToolTempest's README). Run it from the repository root:

```bash
client="$HOME/.claude"   # for Claude Code; any directory works
# writes the lock only if nothing exists at that path (a file, a symlink, even a dangling one);
# if the lock cannot be built, nothing is created, so a rerun is safe
python3 - "$client/.tooltempest.lock" <<'PY'
import json, os, sys
d = json.load(open('.tooltempest.lock'))
text = json.dumps({k: d[k] for k in ('repository', 'commit')}, indent=2) + '\n'
try:
    f = open(sys.argv[1], 'x')  # exclusive create: fails on any existing path
except FileExistsError:
    print('kept the existing', sys.argv[1], file=sys.stderr)
else:
    try:
        f.write(text)
        f.close()  # buffered data reaches the disk here, so close is inside the guard
    except BaseException:
        os.unlink(sys.argv[1])
        raise
PY
python3 "$tt/scripts/tooling.py" materialize --target client --root "$client" --source "$tt"          # dry run
python3 "$tt/scripts/tooling.py" materialize --target client --root "$client" --source "$tt" --apply
```

It refuses to overwrite a file in the client root that it does not manage.
