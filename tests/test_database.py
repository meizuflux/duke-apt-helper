from pathlib import Path

from apt_helper.database import Database
from apt_helper.models import Submission, UploadResult


def test_sync_updates_current_status_and_last_sync(tmp_path: Path) -> None:
    database = Database(tmp_path / "apt.db")
    try:
        submission = Submission("gravity", "90", "9", "server time")
        database.save_current_status([submission])
        database.mark_synced()

        assert database.last_synced_at() is not None
        assert database.latest_submissions() == [submission]
    finally:
        database.close()


def test_upload_result_updates_current_status_without_changing_last_sync(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "apt.db")
    try:
        database.mark_synced()
        synced_at = database.last_synced_at()
        database.save_upload_result(
            UploadResult("gravity", "Gravity.java", True, 12, 12, 1.0, 2),
            content_hash="test-hash",
            catalog_id="gravity",
        )

        assert database.last_synced_at() == synced_at
        current = database.latest_submissions()
        assert (current[0].problem, current[0].percent, current[0].score) == (
            "gravity",
            "100",
            "1",
        )
        assert database.file_snapshot_hash("gravity") == "test-hash"
    finally:
        database.close()


def test_compile_failure_is_still_a_current_submission(tmp_path: Path) -> None:
    database = Database(tmp_path / "apt.db")
    try:
        database.save_upload_result(
            UploadResult("gravity", "Gravity.java", False, None, None, None, 3),
            content_hash="failed-hash",
            catalog_id="gravity",
        )

        assert database.latest_submissions()[0].percent == "compile failed"
    finally:
        database.close()


def test_repeated_remote_slug_has_separate_local_file_snapshots(tmp_path: Path) -> None:
    database = Database(tmp_path / "apt.db")
    try:
        database.save_file_snapshot("set9/sortedleaves", "assigned-hash")
        database.save_file_snapshot("quiz2-discussion/sortedleaves", "practice-hash")

        assert database.file_snapshot_hash("set9/sortedleaves") == "assigned-hash"
        assert (
            database.file_snapshot_hash("quiz2-discussion/sortedleaves")
            == "practice-hash"
        )
    finally:
        database.close()
