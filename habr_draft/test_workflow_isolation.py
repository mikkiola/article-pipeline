"""Static isolation checks on the draft runtime workflow.

These read the example workflow as text (no YAML dependency) and assert the
credential boundaries ADR-0069 states. They prove the file's structure, not
the behaviour of a real Actions run; the first real run must still be
inspected."""

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent / "runtime_workflow.example.yml"


def _jobs() -> dict[str, str]:
    text = WORKFLOW.read_text(encoding="utf-8")
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([a-z][a-z0-9_-]*):\s*$", body, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def _steps(job_text: str) -> list[str]:
    steps_text = job_text.split("\n    steps:\n", 1)[1]
    return re.split(r"^      - ", steps_text, flags=re.MULTILINE)[1:]


def _code(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def test_there_are_exactly_three_jobs_in_the_stated_dependency_order():
    jobs = _jobs()
    assert list(jobs) == ["prepare", "draft", "deliver"]
    assert "needs: prepare" in jobs["draft"]
    assert "needs: [prepare, draft]" in jobs["deliver"]
    assert "needs:" not in jobs["prepare"]


def test_each_credential_exists_in_exactly_one_job():
    jobs = {name: _code(text) for name, text in _jobs().items()}
    only = {
        "steps.broad-token": "prepare",
        "repository: mikkiola/collector": "prepare",
        "steps.narrow-token": "draft",
        "ANTHROPIC_API_KEY_HABR_DRAFT": "draft",
        "TELEGRAM_BOT_TOKEN": "deliver",
        "TELEGRAM_CHAT_ID": "deliver",
        "ref: registry-data": "deliver",
        "contents: write": "deliver",
    }
    for needle, owner_job in only.items():
        found = [name for name, text in jobs.items() if needle in text]
        assert found == [owner_job], f"{needle!r} found in {found}"


def test_workflow_level_permission_is_read_only():
    text = _code(WORKFLOW.read_text(encoding="utf-8")).split("\njobs:\n", 1)[0]
    assert re.search(r"^permissions:\n  contents: read$", text, flags=re.MULTILINE)
    assert "contents: write" not in text


def test_every_checkout_drops_credentials_except_the_registry_write_checkout():
    for job_name, job_text in _jobs().items():
        for step in _steps(job_text):
            code = _code(step)
            if "actions/checkout@" not in code:
                continue
            writes_registry = "ref: registry-data" in code
            persists = "persist-credentials: false" not in code
            assert persists == writes_registry, (job_name, code.splitlines()[0])


def test_python_steps_receive_only_the_secrets_their_stage_needs():
    allowed = {
        "prepare": set(),  # the broad token comes from a step output, not a secret
        "draft": {"ANTHROPIC_API_KEY_HABR_DRAFT", "HABR_CALIBRATION_REFERENCE"},
        "deliver": {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"},
    }
    for job_name, job_text in _jobs().items():
        for step in _steps(job_text):
            code = _code(step)
            if "python3 " not in code and "printf" not in code:
                continue
            used = set(re.findall(r"secrets\.([A-Z0-9_]+)", code))
            assert used <= allowed[job_name], (job_name, used)
            assert "GH_APP_PRIVATE_KEY" not in code


def test_draft_job_has_no_registry_data_and_no_broad_token_or_collector_path():
    draft = _code(_jobs()["draft"])
    for forbidden in ("registry", "broad-token", "collector/", "contents: write", "archi-kg", "brain"):
        assert forbidden not in draft, forbidden
    # the narrow token is scoped to three public repositories, read-only
    block = draft.split("narrow-token", 1)[1].split("- name:", 1)[0]
    assert "permission-contents: read" in block
    repos = re.search(r"repositories: \|\n((?:\s+[a-z-]+\n)+)", block).group(1).split()
    assert repos == ["article-pipeline", "radar", "tooltempest"]


def test_deliver_job_has_no_model_key_and_no_collector_and_commits_only_the_run_directory():
    deliver = _code(_jobs()["deliver"])
    assert "ANTHROPIC" not in deliver and "collector" not in deliver
    assert "git add -- output/ state/" not in deliver
    assert 'git add -- "$RUN_DIR"' in deliver
    assert "habr_draft/deliver.py" in deliver
    # the notification is conditional on a successful push
    notify = [s for s in _steps(_jobs()["deliver"]) if "notify.py" in s][0]
    assert "steps.push.outputs.sha != ''" in notify


def test_only_the_selection_input_and_the_output_directory_cross_job_boundaries():
    uploads = {}
    for name, text in _jobs().items():
        for step in _steps(text):
            code = _code(step)
            if "actions/upload-artifact@" in code:
                uploads.setdefault(name, []).append(
                    re.search(r"name: (habr-[a-z-]+)\n\s+path: (.+)", code).groups())
    assert uploads == {
        "prepare": [("habr-selection-input", "${{ runner.temp }}/selection/selection_input.json")],
        "draft": [("habr-draft-output", "${{ runner.temp }}/habr_draft_out")],
    }


def test_app_private_key_is_a_known_residual_in_exactly_two_jobs_and_only_as_a_token_action_input():
    """The key that mints installation tokens is read by `prepare` (broad
    token) and `draft` (narrow token). That is a stated residual (ADR-0070),
    not an isolation claim: this test pins the exact set so that a third job,
    or a use outside the token action, is caught."""
    jobs = _jobs()
    for secret in ("GH_APP_PRIVATE_KEY", "GH_APP_ID"):
        found = [name for name, text in jobs.items() if secret in _code(text)]
        assert found == ["prepare", "draft"], (secret, found)
        for name, text in jobs.items():
            for step in _steps(text):
                code = _code(step)
                if secret in code:
                    assert "actions/create-github-app-token@" in code, (name, secret)
