import copy

import pytest

from habr_draft import fragments
from habr_draft.testsupport import make_config

SHA = "a" * 40


def commit(files, author=("Olga", "o@example.org", "mikkiola"), message="feat: x", committer=None):
    name, email, login = author
    committer = committer or author
    return {
        "commit": {"author": {"name": name, "email": email},
                   "committer": {"name": committer[0], "email": committer[1]}, "message": message},
        "author": {"login": login}, "committer": {"login": committer[2]},
        "files": files,
    }


def getter_for(body, status=200):
    seen = []

    def get(path, token):
        seen.append((path, token))
        return status, body

    get.seen = seen
    return get


def fetch(files=None, config=None, **commit_kwargs):
    body = commit(files if files is not None else [{"filename": "src/a.py", "patch": "@@\n+x = 1"}],
                  **commit_kwargs)
    get = getter_for(body)
    result = fragments.fetch_fragments(
        "article-pipeline", [{"sha": SHA, "subject": "s"}], "narrow-token",
        config or make_config(), get=get,
    )
    return result, get


def test_fragment_is_fetched_by_commit_sha_with_provenance():
    result, get = fetch()
    assert get.seen == [(f"/repos/mikkiola/article-pipeline/commits/{SHA}", "narrow-token")]
    (frag,) = result.fragments
    assert frag["sha"] == SHA and frag["path"] == "src/a.py" and frag["repo"] == "article-pipeline"
    assert frag["content_sha256"] and result.errors == [] and result.exclusions == []


def test_missing_patch_denylisted_path_and_secret_are_excluded_with_reason():
    token = "gh" + "p_" + "A" * 36
    result, _ = fetch(files=[
        {"filename": "img.png"},
        {"filename": "package-lock.json", "patch": "@@\n+x"},
        {"filename": ".env", "patch": "@@\n+A=1"},
        {"filename": "src/k.py", "patch": f"@@\n+TOKEN = '{token}'"},
        {"filename": "src/ok.py", "patch": "@@\n+ok = 1"},
    ])
    reasons = {e["path"]: e["reason"] for e in result.exclusions}
    assert reasons == {"img.png": "no_patch", "package-lock.json": "denylisted_path",
                       ".env": "denylisted_path", "src/k.py": "secret_pattern"}
    assert [f["path"] for f in result.fragments] == ["src/ok.py"]
    # the exclusion record names the pattern, never the matched text
    assert token not in str(result.exclusions)


def test_path_and_secret_exclusions_come_before_the_authorship_exclusion():
    result, _ = fetch(author=("Someone Else", "x@example.org", "someone"), files=[
        {"filename": "package-lock.json", "patch": "@@\n+x"},
        {"filename": "src/ok.py", "patch": "@@\n+ok = 1"},
    ])
    assert [(e["path"], e["reason"]) for e in result.exclusions] == [
        ("package-lock.json", "denylisted_path"), ("src/ok.py", "authorship:author_not_owner")]


def test_http_and_network_errors_are_recorded_as_errors_not_exclusions():
    get403 = getter_for(None, 403)
    r = fragments.fetch_fragments("article-pipeline", [{"sha": SHA, "subject": "s"}], "t",
                                  make_config(), get=get403)
    assert r.errors == [{"repo": "article-pipeline", "sha": SHA, "kind": "http", "status": 403}]
    assert r.fragments == [] and r.exclusions == []

    def boom(path, token):
        raise OSError("boom")

    r = fragments.fetch_fragments("article-pipeline", [{"sha": SHA, "subject": "s"}], "t",
                                  make_config(), get=boom)
    assert r.errors[0]["kind"] == "network" and r.errors[0]["error_class"] == "OSError"


def test_missing_token_is_an_error():
    r = fragments.fetch_fragments("article-pipeline", [{"sha": SHA, "subject": "s"}], None,
                                  make_config(), get=getter_for({}))
    assert r.errors == [{"repo": "article-pipeline", "kind": "token_missing"}]


def test_volume_cap_is_deterministic_and_reports_what_it_dropped():
    frs = [{"id": "r:frag_01", "content": "a" * 60}, {"id": "r:frag_02", "content": "b" * 60},
           {"id": "r:frag_03", "content": "c" * 10}]
    kept, dropped = fragments.select_within_cap(frs, 80)
    assert [f["id"] for f in kept] == ["r:frag_01", "r:frag_03"]
    assert dropped == [{"id": "r:frag_02", "reason": "volume_cap"}]


# --- repository visibility: a verdict is distinct from "could not check" ----


def _vis(status=200, body=None, raises=False, token="narrow"):
    def getter(path, tok):
        assert path == "/repos/mikkiola/radar" and tok == "narrow"
        if raises:
            raise OSError("network down")
        return status, body
    return fragments.repo_visibility("radar", token, get=getter)


def test_visibility_public_private_and_unverifiable_are_three_distinct_results():
    assert _vis(200, {"private": False}) is True
    assert _vis(200, {"private": True}) is False
    assert _vis(raises=True) is None
    assert _vis(403, None) is None
    assert _vis(404, None) is None
    assert _vis(200, {}) is None
    assert _vis(200, {"private": "yes"}) is None
    assert fragments.repo_visibility("radar", None, get=lambda *a: (200, {"private": False})) is None


# --- admission rule: the commit's author must be an owner identity -----------
#
# Access model behind the rule (ADR-0070): each allow-listed repository has one
# account with write access, so the only way a third party's commit reaches
# `main` is the owner merging it, and a merge keeps the original author.

WEB_FLOW = ("GitHub", "noreply@github.com", "web-flow")
OWNER = ("Olga", "o@example.org", "mikkiola")
OWNER_NOREPLY = "82107567+mikkiola@users.noreply.github.com"
OTHER = ("Someone Else", "x@example.org", "someone")
RADAR_BOT = ("Radar Bot", "radar@gitlab.com", None)
CLAUDE_TRAILER = "feat: x\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"


def _reasons(result):
    return [e["reason"] for e in result.exclusions]


def _decision(result):
    """"admitted" or the exclusion reasons of the single fixture file."""
    if result.fragments:
        assert result.exclusions == []
        return "admitted"
    return _reasons(result)


def test_non_owner_author_is_excluded():
    result, _ = fetch(author=OTHER)
    assert result.fragments == []
    assert _reasons(result) == ["authorship:author_not_owner"]


def test_a_contributors_change_merged_by_the_owner_keeps_the_contributor_as_author():
    # squash merge through the web interface: author stays the contributor,
    # the committer is the platform
    assert _decision(fetch(author=OTHER, committer=WEB_FLOW)[0]) == ["authorship:author_not_owner"]
    # rebase or `git am` by the owner: committer is the owner
    assert _decision(fetch(author=OTHER, committer=OWNER)[0]) == ["authorship:author_not_owner"]


def test_owner_authored_commit_merged_through_web_flow_is_admissible():
    result, _ = fetch(author=OWNER, committer=WEB_FLOW)
    assert len(result.fragments) == 1 and result.exclusions == []


def test_a_platform_or_automation_identity_as_author_is_not_the_owner():
    assert _decision(fetch(author=WEB_FLOW, committer=WEB_FLOW)[0]) == ["authorship:author_not_owner"]
    # `Radar Bot <radar@gitlab.com>` has no GitHub login; the owner has not
    # added its address to owner_identities, so it stays a non-owner author
    assert _decision(fetch(author=RADAR_BOT, committer=RADAR_BOT)[0]) == ["authorship:author_not_owner"]


def test_the_committer_is_not_read():
    for committer in (RADAR_BOT, OTHER, WEB_FLOW):
        assert _decision(fetch(author=OWNER, committer=committer)[0]) == "admitted", committer


def test_commit_message_trailers_are_not_read():
    """No AI-disclosure or co-author policy is applied to a code fragment
    (nothing in SPEC.md or the ADRs requires one): the message is not inspected."""
    for message in (CLAUDE_TRAILER,
                    "feat: x\n\nCo-authored-by: Someone Else <x@example.org>",
                    "feat: x\n\nCo-authored-by: Claude <noreply@anthropic.com>\n"
                    "Co-authored-by: Someone Else <x@example.org>"):
        assert _decision(fetch(message=message)[0]) == "admitted", message
    # a non-owner author is still excluded whatever the message says
    assert _decision(fetch(author=OTHER, message=CLAUDE_TRAILER)[0]) == ["authorship:author_not_owner"]


def test_commit_without_any_author_is_unknown_authorship():
    body = {"commit": {"message": "x"}, "files": [{"filename": "a.py", "patch": "@@\n+x"}]}
    result = fragments.fetch_fragments("article-pipeline", [{"sha": SHA, "subject": "s"}],
                                       "t", make_config(), get=getter_for(body))
    assert result.fragments == []
    assert _reasons(result) == ["authorship:authorship_unknown"]


def test_no_owner_identities_configured_means_nothing_is_owner():
    result, _ = fetch(config=make_config(owner_identities=[]))
    assert result.fragments == []
    assert _reasons(result) == ["authorship:author_not_owner"]


def test_a_display_name_alone_never_establishes_owner_authorship():
    config = make_config(owner_identities=[{"name": "Olga"}])
    result, _ = fetch(author=("Olga", "x@evil.example", "someone"), config=config)
    assert _decision(result) == ["authorship:author_not_owner"]


def test_an_owner_entry_with_a_name_still_matches_by_its_address():
    owners = [{"name": "Olga", "email": "o@example.org"}]
    result, _ = fetch(author=("Whoever", "o@example.org", None), config=make_config(owner_identities=owners))
    assert _decision(result) == "admitted"
    result, _ = fetch(author=("Olga", "other@example.org", None), config=make_config(owner_identities=owners))
    assert _decision(result) == ["authorship:author_not_owner"]


def test_owner_email_is_compared_trimmed_and_case_folded_on_both_sides():
    for config_email, commit_email in (("o@example.org", " O@EXAMPLE.ORG "),
                                       (" O@Example.Org ", "o@example.org"),
                                       ("O@Example.Org", "o@example.org ")):
        result, _ = fetch(author=("Whoever", commit_email, None),
                          config=make_config(owner_identities=[{"email": config_email}]))
        assert _decision(result) == "admitted", (config_email, commit_email)


def test_an_empty_address_never_matches_an_empty_owner_address():
    for owner_email in ("", "   "):
        result, _ = fetch(author=("Whoever", "", None),
                          config=make_config(owner_identities=[{"email": owner_email}]))
        assert _decision(result) == ["authorship:author_not_owner"]


def test_repository_configuration_reflects_the_admission_rule():
    from habr_draft.config import HabrConfig, load_config

    cfg = load_config()
    logins = {i.get("login") for i in cfg.owner_identities}
    assert {"mikkiola", "OStroganova"} <= logins
    # the Radar Bot address is the owner's separate, still undecided confirmation
    assert "radar@gitlab.com" not in {i.get("email") for i in cfg.owner_identities}
    # no AI, bot or waiver policy exists any more
    assert not {"ai_assistant_policy", "bot_policy", "fragment_permissions"} & set(HabrConfig.model_fields)

    # identities exactly as they appear in the three repositories' history
    cases = {
        "owner (local git) with Claude trailer": (("Olga Stroganova", "lyolich777ka@gmail.com", "mikkiola"),
                                                  None, CLAUDE_TRAILER, True),
        "owner (second account) with Claude trailer": (
            ("Olga Stroganova", "second-account@example.org", "OStroganova"), None, CLAUDE_TRAILER, True),
        "owner via web UI, merged by web-flow": (("Olga", OWNER_NOREPLY, "mikkiola"), WEB_FLOW, "x", True),
        "web-flow alone": (WEB_FLOW, WEB_FLOW, "x", False),
        "Radar Bot": (RADAR_BOT, RADAR_BOT, "x", False),
        "owner-authored change re-committed by Radar Bot": (
            ("Olga Stroganova", "lyolich777ka@gmail.com", "mikkiola"), RADAR_BOT, "x", True),
    }
    for label, (author, committer, message, admitted) in cases.items():
        result, _ = fetch(author=author, committer=committer, message=message, config=cfg)
        assert (len(result.fragments) == 1) is admitted, label


# --- malformed responses are errors, never admissions ------------------------

GOOD_FILES = [{"filename": "src/a.py", "patch": "@@\n+x = 1"}]


def _good_body():
    return commit(copy.deepcopy(GOOD_FILES))


def _fetch_body(body, config=None):
    return fragments.fetch_fragments("article-pipeline", [{"sha": SHA, "subject": "s"}], "narrow-token",
                                     config or make_config(), get=getter_for(body))


def _set(path, value):
    def mutate(body):
        target = body
        for key in path[:-1]:
            target = target[key]
        if value is _MISSING:
            del target[path[-1]]
        else:
            target[path[-1]] = value
    return mutate


_MISSING = object()

# Only the fields the rule reads are validated: the author identity and the files.
MALFORMED = [
    ("commit", _set(["commit"], "oops")),
    ("commit.author", _set(["commit", "author"], "Olga")),
    ("commit.author.email", _set(["commit", "author", "email"], 5)),
    ("author", _set(["author"], "mikkiola")),
    ("author.login", _set(["author", "login"], 7)),
    ("files", _set(["files"], {"filename": "src/a.py", "patch": "@@\n+x"})),
    ("files", _set(["files"], "src/a.py")),
    ("files[]", _set(["files"], ["src/a.py"])),
    ("files[].filename", _set(["files", 0, "filename"], 5)),
    ("files[].filename", _set(["files", 0, "filename"], _MISSING)),
    ("files[].filename", _set(["files", 0, "filename"], "")),
    ("files[].patch", _set(["files", 0, "patch"], 5)),
    ("files[].patch", _set(["files", 0, "patch"], {"a": "b"})),
]


@pytest.mark.parametrize("field,mutate", MALFORMED, ids=[f"{f}-{i}" for i, (f, _) in enumerate(MALFORMED)])
def test_malformed_commit_response_is_recorded_as_an_error_and_never_admitted(field, mutate):
    body = _good_body()
    assert len(_fetch_body(copy.deepcopy(body)).fragments) == 1  # the unmutated body is admitted
    mutate(body)
    result = _fetch_body(body)  # must not raise
    assert result.fragments == [] and result.exclusions == []
    assert result.errors == [{"repo": "article-pipeline", "sha": SHA, "kind": "malformed_commit", "field": field}]


def test_a_malformed_commit_does_not_stop_the_next_commit():
    bad = _good_body()
    bad["commit"]["author"] = "Olga"
    good = _good_body()
    other = "b" * 40
    bodies = {SHA: bad, other: good}

    def get(path, token):
        return 200, bodies[path.rsplit("/", 1)[1]]

    result = fragments.fetch_fragments(
        "article-pipeline", [{"sha": SHA, "subject": "s"}, {"sha": other, "subject": "t"}],
        "narrow-token", make_config(), get=get)
    assert [f["sha"] for f in result.fragments] == [other]
    assert result.errors == [{"repo": "article-pipeline", "sha": SHA, "kind": "malformed_commit",
                              "field": "commit.author"}]


def test_null_api_identities_and_null_files_are_valid_shapes():
    body = {"commit": {"author": {"name": "Olga", "email": OWNER_NOREPLY},
                       "committer": {"name": "Olga", "email": OWNER_NOREPLY}, "message": "x"},
            "author": None, "committer": None, "files": copy.deepcopy(GOOD_FILES)}
    cfg = make_config(owner_identities=[{"email": OWNER_NOREPLY}])
    assert _decision(_fetch_body(body, cfg)) == "admitted"
    body["files"] = None
    result = _fetch_body(body, cfg)
    assert result.fragments == [] and result.exclusions == [] and result.errors == []
