"""Anti-"junk drawer" safeguard (ADR-0045): a per-source_type whitelist
of allowed CanonicalUnit.metadata keys. Guards against metadata
silently accumulating undeclared keys as sources are added later —
plain dict/set lookup, no new architectural layer.

Implemented now, ahead of M6's synthetic alien-source contract test
(cheap to add immediately; ADR-0045 records this as the plan either
way). Lives alongside collector.py since it's Collector's own adapter
shapes being whitelisted today — a future Brain adapter would add its
own entry to the same METADATA_WHITELIST dict, not a new mechanism.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collector  # noqa: E402


def test_manifest_real_output_keys_are_all_whitelisted():
    manifest = {
        "scan_timestamp": "2026-09-12T00:50:24.808627+00:00",
        "window_days": 7,
        "repos": [
            {"name": "article-pipeline", "branch": "main", "head_sha": "a" * 40, "commit_count": 6, "counts": {"value": 2}},
        ],
    }
    from unittest.mock import patch

    with patch("collector.check_integrity", return_value=("valid", "mocked")):
        units = collector.adapt_manifest(manifest)

    collector.check_metadata_whitelist("collector_manifest", units[0].metadata)  # must not raise


def test_daily_brief_real_output_keys_are_all_whitelisted():
    daily_brief = {
        "schema_version": 2,
        "mode": "fact",
        "date": "2026-09-11",
        "window": "1.day",
        "total_diffstat": 10,
        "files_touched": ["a.py"],
        "commit_messages": [{"repo": "article-pipeline", "sha": "1" * 40, "subject": "fix: bug"}],
        "per_repo": [
            {"name": "article-pipeline", "branch": "main", "head_sha": "a" * 40,
             "commit_count": 2, "diffstat": 10, "files_touched": ["a.py"]},
        ],
        "decision_source": "heuristic",
    }
    from unittest.mock import patch

    with patch("collector.check_integrity", return_value=("valid", "mocked")):
        units = collector.adapt_daily_brief(daily_brief)

    collector.check_metadata_whitelist("collector_daily_brief", units[0].metadata)  # must not raise


def test_whitelist_catches_a_synthetic_unwhitelisted_key():
    bad_metadata = {
        "source_type": "collector_manifest",
        "repo": "x",
        "branch": "main",
        "commit_count": 1,
        "counts": {},
        "window_days": 7,
        "integrity_check_detail": "mocked",
        "totally_undeclared_key": "should never appear",
    }
    with pytest.raises(ValueError, match="totally_undeclared_key"):
        collector.check_metadata_whitelist("collector_manifest", bad_metadata)


def test_whitelist_catches_a_key_from_the_wrong_source_type():
    # commit_messages is daily_brief-only — a manifest unit carrying it
    # would be exactly the kind of cross-source leakage this guards.
    bad_metadata = {
        "source_type": "collector_manifest",
        "repo": "x",
        "branch": "main",
        "commit_count": 1,
        "counts": {},
        "window_days": 7,
        "integrity_check_detail": "mocked",
        "commit_messages": ["should not be here"],
    }
    with pytest.raises(ValueError, match="commit_messages"):
        collector.check_metadata_whitelist("collector_manifest", bad_metadata)


def test_unknown_source_type_raises():
    with pytest.raises(ValueError, match="unknown source_type"):
        collector.check_metadata_whitelist("brain_claim", {})
