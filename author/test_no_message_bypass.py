"""No raw bypass of the include/exclude gate into the LinkedIn prompt.

Reproduces the real 2026-09-24 bug end to end: a daily brief naming 7
repositories, of which the integrity check accepts exactly one, used to put
EVERY repository's commit messages into the post-generation prompt — because
Collector's flat, cross-repo `commit_messages` list was attached to every
unit and passed straight through the one included unit's AuthoringContext.
(Observed: `per_repo` listed one repo, `total commits: 1`, yet the prompt
carried 19 subjects from four repos.)

TDD per docs/CONSTITUTION.md — this is a gate mechanism ("does an excluded
unit's data reach the prompt"), so it is written first. It goes through the
real adapter, pre-filter, framing, AuthoringContext, verdict reader and
prompt builder; only the integrity decision (an HTTP call in production) and
the gh visibility lookup are replaced.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "author"))
sys.path.insert(0, str(ROOT / "strategy_layer"))
sys.path.insert(0, str(ROOT / "strategy_layer" / "adapters"))

import collector  # noqa: E402
import daily_linkedin_author  # noqa: E402
import framing  # noqa: E402
import pre_filter  # noqa: E402
from authoring_context import build_authoring_contexts  # noqa: E402
from linkedin_verdict_reader import build_daily_brief_from_authoring_contexts  # noqa: E402

REPOS = ["archi-kg", "article-pipeline", "brain", "collector", "radar", "radar-vault", "tooltempest"]
MESSAGES = {
    "article-pipeline": ["feat(ap): article-pipeline change one", "fix(ap): article-pipeline change two"],
    "collector": ["chore(data): collector daily run"],
    "radar": ["radar-only subject alpha"],
    "radar-vault": ["radar-vault-only subject beta"],
}


def _brief():
    return {
        "schema_version": 2,
        "mode": "fact",
        "date": "2026-09-24",
        "window": "1.day",
        "total_diffstat": 5615,
        "files_touched": [],
        "commit_messages": [
            {"repo": repo, "sha": f"{i:040d}", "subject": subject}
            for i, (repo, subjects) in enumerate(MESSAGES.items())
            for subject in subjects
        ],
        "per_repo": [
            {
                "name": repo,
                "branch": "vault" if repo == "radar-vault" else "main",
                "head_sha": "f" * 40,
                "commit_count": len(MESSAGES.get(repo, [])),
                "diffstat": 10 * len(MESSAGES.get(repo, [])),
                "files_touched": [f"{repo}.txt"] if repo in MESSAGES else [],
            }
            for repo in REPOS
        ],
        "decision_source": "heuristic",
    }


def _build_prompt(monkeypatch, included_repo):
    def fake_integrity(repo_name, *args, **kwargs):
        return ("valid", "mocked") if repo_name == included_repo else ("invalid", "mocked")

    monkeypatch.setattr(collector, "check_integrity", fake_integrity)
    # Local-checkout branch resolution existed before the API-based check;
    # raising=False lets this same test also run against that older code.
    monkeypatch.setattr(collector, "resolve_current_branch", lambda name: "main", raising=False)
    monkeypatch.setattr(daily_linkedin_author, "_check_repo_visibility", lambda name: False)

    units = collector.adapt_daily_brief(_brief())
    assert len(units) == 7
    results = {r["claim_id"]: r for r in pre_filter.run_pre_filter(units)}
    assert [r["pre_filter_classification"] for r in results.values()].count("include") == 1

    treatments = []
    for unit in units:
        pf = results[unit.unit_id]
        if pf["pre_filter_classification"] == "include":
            treatments.append(
                framing.build_claim_treatment(
                    claim_id=unit.unit_id,
                    pre_filter_classification="include",
                    pre_filter_reason=pf["reason"],
                    framing=f"{unit.metadata['repo']}: {unit.metadata['commit_count']} commit(s).",
                    derivation_kind="restatement",
                    source_status_snapshot={
                        "integrity_status": unit.integrity_status,
                        "corroboration_status": unit.corroboration_status,
                    },
                )
            )
        else:
            treatments.append(
                framing.build_claim_treatment(
                    claim_id=unit.unit_id,
                    pre_filter_classification="exclude",
                    pre_filter_reason=pf["reason"],
                )
            )

    contexts = build_authoring_contexts(units, treatments)
    shaped = build_daily_brief_from_authoring_contexts(contexts, date="2026-09-24")
    return shaped, daily_linkedin_author.build_prompt(shaped)


def test_only_the_one_included_units_messages_reach_the_prompt(monkeypatch):
    shaped, prompt = _build_prompt(monkeypatch, included_repo="collector")

    assert shaped["commit_messages"] == ["chore(data): collector daily run"]
    assert "chore(data): collector daily run" in prompt
    for repo, subjects in MESSAGES.items():
        if repo == "collector":
            continue
        for subject in subjects:
            assert subject not in prompt, f"{repo}'s message leaked into the prompt: {subject!r}"


def test_the_prompts_message_set_is_the_union_of_included_units_slices_only(monkeypatch):
    # Included: article-pipeline. Its own two messages appear; the other
    # repositories' messages (including the collector's) do not.
    shaped, prompt = _build_prompt(monkeypatch, included_repo="article-pipeline")

    assert shaped["commit_messages"] == MESSAGES["article-pipeline"]
    for subject in MESSAGES["article-pipeline"]:
        assert subject in prompt
    for repo in ("collector", "radar", "radar-vault"):
        for subject in MESSAGES[repo]:
            assert subject not in prompt
