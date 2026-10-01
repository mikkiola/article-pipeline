"""habr_edit_capture/run_capture.py — the scheduled-job entry point
(SPEC.md Functional Requirement 19;
`.github/workflows/habr-edit-capture.yml`).

One pass per invocation (see `diff_capture.py`'s own module docstring)
— reads a service-account key file and the owner's Drive root folder
id from the environment, runs `diff_capture.run_capture_pass()`, and
prints a one-line-per-outcome report. Writing to git (committing and
pushing `habr_edit_capture/output/` to the `habr-edit-capture-data`
branch) is the calling workflow's own job, same division of labor as
`linkedin_publisher/daily_publish.py` / `linkedin-daily-publish.yml`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diff_capture  # noqa: E402
import drive_client  # noqa: E402


def main() -> None:
    service_account_file = os.environ["HABR_DRIVE_SERVICE_ACCOUNT_FILE"]
    root_folder_id = os.environ["HABR_DRIVE_ROOT_FOLDER_ID"]

    service = drive_client.build_drive_service(service_account_file)
    report = diff_capture.run_capture_pass(service, root_folder_id)

    written = [r for r in report if r["written"]]
    skipped = [r for r in report if not r["written"]]
    print(
        f"habr edit capture: {len(written)} new record(s), "
        f"{len(skipped)} already captured (skipped)"
    )
    for r in written:
        print(f"  wrote: folder={r['folder_id']} date_stem={r['date_stem']} -> {r['written']}")
    for r in skipped:
        print(f"  skipped (already captured): folder={r['folder_id']} date_stem={r['date_stem']}")


if __name__ == "__main__":
    main()
