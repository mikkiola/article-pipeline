"""Stage 2: Story Builder — CanonicalEvent -> CanonicalStory.

The ONLY stage in this pipeline allowed to interpret. Everything in
core_problem/change/insight/forward_lesson/outcome must trace to
event.facts, event.evidence, or event.context (all real, all populated
by the Source Adapter from Collector's manifest or its own SPEC.md
goals) — never to information this function invents. Where the input
genuinely doesn't support a specific claim, this leaves an explicit
placeholder string rather than fabricating one, per this pipeline's
own no-fabrication rule.

insight vs. forward_lesson: insight is tactical, in-the-moment — what
this specific window's data shows. forward_lesson is strategic — what
that pattern implies going forward, if it holds. They must say
genuinely different things, not restate one another under a new name.
"""

from dataclasses import dataclass

from source_adapter import CanonicalEvent


@dataclass
class CanonicalStory:
    core_problem: str
    change: str
    insight: str
    forward_lesson: str
    outcome: str
    evidence_refs: list[int]  # indices into event.evidence


def _fact(event: CanonicalEvent, fact_type: str) -> dict | None:
    for f in event.facts:
        if f["type"] == fact_type:
            return f
    return None


def build_story(event: CanonicalEvent) -> CanonicalStory:
    commit_fact = _fact(event, "repo_commit_count")
    class_fact = _fact(event, "repo_classification_counts")

    # core_problem — grounded in event.context["goal"], which itself
    # traces to Collector's own SPEC.md (not invented here).
    core_problem = (
        f"Weekly engineering effort tends to go unmeasured and "
        f"unremarked unless something external forces a checkpoint — "
        f"the motivation {event.context['project']} itself was built "
        f"for ({event.context['goal']})."
    )

    # change — grounded strictly in the repo_commit_count fact.
    if commit_fact is not None:
        change = (
            f"In the {event.time_range_days}-day window this manifest "
            f"covers, the {commit_fact['repo']} repository recorded "
            f"{commit_fact['commit_count']} commit(s) on "
            f"`{commit_fact['branch']}`."
        )
    else:
        change = (
            "[PLACEHOLDER — no repo_commit_count fact was present in "
            "this manifest for the scoped repo; nothing to report here "
            "without inventing a number.]"
        )

    # insight — tactical: what this specific window's classification
    # counts show, grounded strictly in the repo_classification_counts
    # fact. Genuinely thin data (e.g. zero value-files) is itself real
    # information worth stating, not something to paper over.
    total_repo_files = None
    if class_fact is not None:
        total_repo_files = (
            class_fact["value"] + class_fact["explicit_service"] + class_fact["default_service"]
        )
        if class_fact["value"] == 0 and total_repo_files > 0:
            insight = (
                f"Every one of {total_repo_files} tracked file change(s) "
                f"in {class_fact['repo']} this window classified as "
                f"non-value (explicit_service: {class_fact['explicit_service']}, "
                f"default_service: {class_fact['default_service']}) — "
                f"zero landed as value under the current classifier rules."
            )
        elif total_repo_files == 0:
            insight = (
                "[PLACEHOLDER — the classification-counts fact for this "
                "repo shows zero tracked file changes in this window; no "
                "classification pattern to report.]"
            )
        else:
            insight = (
                f"Of {total_repo_files} tracked file change(s), "
                f"{class_fact['value']} classified as value, "
                f"{class_fact['explicit_service']} as explicit_service, "
                f"{class_fact['default_service']} as default_service."
            )
    else:
        insight = (
            "[PLACEHOLDER — no repo_classification_counts fact was "
            "present in this manifest for the scoped repo.]"
        )

    # forward_lesson — strategic: what the *pattern* implies going
    # forward, distinct from insight's report of this one window.
    # Grounded in the same class_fact, but asking a different
    # question: is this a one-window artifact or a standing property
    # of how the classifier's rules are defined for this repo?
    if class_fact is not None and total_repo_files is not None and total_repo_files > 0:
        if class_fact["value"] == 0:
            forward_lesson = (
                f"{class_fact['repo']} has no whole-repo or path-fragment "
                f"rule that classifies any of its own files as value "
                f"(unlike brain/**, articles/**, or docs/adr/** elsewhere) "
                f"— so every future weekly digest will show zero "
                f"value-classified evidence for {class_fact['repo']}'s own "
                f"engineering work by construction, regardless of how much "
                f"real work happens, unless that rule set is deliberately "
                f"revisited. Worth the owner's attention if {class_fact['repo']}'s "
                f"own build work is meant to register as value in future "
                f"digests."
            )
        else:
            forward_lesson = (
                f"{class_fact['repo']}'s value share this window "
                f"({class_fact['value']} of {total_repo_files} files) is a "
                f"single data point — whether it holds as a trend needs "
                f"more than one week's manifest to say; revisit once "
                f"multiple weekly snapshots exist."
            )
    else:
        forward_lesson = (
            "[PLACEHOLDER — no classification-counts fact with any "
            "tracked file changes was available to ground a "
            "forward-looking statement.]"
        )

    # outcome — current, verifiable state, grounded strictly in facts.
    if commit_fact is not None and class_fact is not None:
        outcome = (
            f"As of this manifest (scanned "
            f"{event.context['manifest_scan_timestamp']}), "
            f"{commit_fact['repo']} shows {commit_fact['commit_count']} "
            f"commit(s) in the last {event.context['manifest_window_days']} "
            f"days, with tracked file changes classified as "
            f"{class_fact['value']} value / {class_fact['explicit_service']} "
            f"explicit_service / {class_fact['default_service']} "
            f"default_service."
        )
    else:
        outcome = (
            "[PLACEHOLDER — insufficient facts in this manifest to state "
            "a current, verifiable outcome without inventing a number.]"
        )

    evidence_refs: list[int] = list(range(len(event.evidence)))

    return CanonicalStory(
        core_problem=core_problem,
        change=change,
        insight=insight,
        forward_lesson=forward_lesson,
        outcome=outcome,
        evidence_refs=evidence_refs,
    )


def main() -> CanonicalStory:
    import json

    import source_adapter

    manifest_path = source_adapter.latest_collector_manifest_path()
    manifest = json.loads(manifest_path.read_text())
    event = source_adapter.adapt_collector_manifest(manifest, repo_filter="collector")
    story = build_story(event)
    print(json.dumps(story.__dict__, indent=2, ensure_ascii=False))
    return story


if __name__ == "__main__":
    main()
