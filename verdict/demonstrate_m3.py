"""Demonstrates SPEC.md's M3 `verify` line for real:

    "a verdict recorded for a real M2 publication, and a Weekly
    snapshot with no verdict yet for another"

Weekly (M6) itself is not started — out of scope for M3 — so the
second half is demonstrated as read_verdicts() returning an empty list
for a real, un-verdicted content_id, which is exactly the `missing`
verdict_status a future Weekly snapshot would report for it.

Both content_ids below are real Publication Registry records from the
`registry-data` branch (`git show registry-data:output/<content_id>.json`),
not synthetic:
  - linkedin-2026-09-29 (gate_status: pass) — gets a real verdict here.
  - linkedin-2026-09-28 (gate_status: pass) — deliberately left with
    zero verdict records, to demonstrate the `missing` case.

Run directly: `python3 verdict/demonstrate_m3.py`. Writes one real file
under verdict/output/ (not a tmp_path — this is the actual done-when
evidence, meant to persist in the repo).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract import VerdictRecord  # noqa: E402
from writer import read_verdicts, write_verdict  # noqa: E402

RECORDED_CONTENT_ID = "linkedin-2026-09-29"
MISSING_CONTENT_ID = "linkedin-2026-09-28"


def main() -> None:
    print("=== recorded case ===")
    print(f"content_id: {RECORDED_CONTENT_ID}")
    record = VerdictRecord(
        content_id=RECORDED_CONTENT_ID,
        verdict_type="good",
        received_at=datetime.now(timezone.utc),
        comment="Problem->search->solution structure landed well; kept the reader's attention.",
    )
    path = write_verdict(record)
    print(f"write_verdict() wrote: {path}")

    read_back = read_verdicts(RECORDED_CONTENT_ID)
    print(f"read_verdicts({RECORDED_CONTENT_ID!r}) -> {len(read_back)} record(s):")
    for r in read_back:
        print(f"  {r.model_dump_json()}")
    verdict_status = "recorded" if read_back else "missing"
    print(f"verdict_status: {verdict_status}")

    print()
    print("=== missing case ===")
    print(f"content_id: {MISSING_CONTENT_ID}")
    missing_result = read_verdicts(MISSING_CONTENT_ID)
    print(f"read_verdicts({MISSING_CONTENT_ID!r}) -> {missing_result!r}")
    verdict_status = "recorded" if missing_result else "missing"
    print(f"verdict_status: {verdict_status}")


if __name__ == "__main__":
    main()
