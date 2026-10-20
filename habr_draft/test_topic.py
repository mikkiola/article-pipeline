from habr_draft import topic
from habr_draft.fragments import FetchResult


def unit(repo, commits=1, why=0, files=1):
    msgs = [{"sha": f"{i}" * 40, "subject": f"s{i}", "why": "w" if i < why else None, "effect": None}
            for i in range(commits)]
    return {"repo": repo, "commit_count": commits, "files_touched": ["f"] * files, "commit_messages": msgs}


FRAG = {"id": "x:frag_01", "content": "c"}


def test_ranking_by_stated_reason_then_commits_then_files_then_name():
    units = [unit("c", commits=5), unit("b", commits=2, why=1), unit("a", commits=2, why=1)]
    assert [u["repo"] for u in topic.rank_candidates(units)] == ["a", "b", "c"]


def test_walks_ranked_candidates_until_first_usable_fragment():
    units = [unit("a", why=1), unit("b")]
    calls = []

    def fetch(u):
        calls.append(u["repo"])
        return FetchResult() if u["repo"] == "a" else FetchResult(fragments=[FRAG])

    result = topic.choose_topic(units, fetch, lambda repo: True)
    assert result.status == "chosen" and result.unit["repo"] == "b"
    assert calls == ["a", "b"]  # a missing patch on the leader does not end the run
    assert [w["outcome"] for w in result.walk] == ["no_usable_fragment", "chosen"]


def test_fetch_error_is_distinct_from_no_eligible_topic():
    result = topic.choose_topic([unit("a")], lambda u: FetchResult(errors=[{"kind": "http", "status": 503}]),
                                lambda repo: True)
    assert result.status == "fetch_error"


def test_error_on_leader_but_usable_later_candidate_is_chosen_and_recorded():
    def fetch(u):
        return FetchResult(errors=[{"kind": "http", "status": 502}]) if u["repo"] == "a" \
            else FetchResult(fragments=[FRAG])

    result = topic.choose_topic([unit("a", why=1), unit("b")], fetch, lambda repo: True)
    assert result.status == "chosen" and result.walk[0]["errors"]


def test_clean_walk_with_nothing_usable_is_no_eligible_topic():
    result = topic.choose_topic([unit("a"), unit("b")], lambda u: FetchResult(), lambda repo: True)
    assert result.status == "no_eligible_topic"


def test_repository_not_confirmed_public_is_skipped_without_fetching():
    fetched = []

    def fetch(u):
        fetched.append(u["repo"])
        return FetchResult(fragments=[FRAG])

    result = topic.choose_topic([unit("a")], fetch, lambda repo: False)
    assert fetched == [] and result.status == "no_eligible_topic"
    assert result.walk[0]["reason"] == "not_confirmed_public"


def test_no_candidates_is_no_eligible_topic():
    assert topic.choose_topic([], lambda u: FetchResult(), lambda r: True).status == "no_eligible_topic"
