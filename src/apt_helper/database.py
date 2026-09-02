"""Local SQLite storage for the session cookie and local file state."""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from .models import Submission, UploadResult
from .utils import AptError

DEFAULT_DATABASE: Final = (
    Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    / "dapt"
    / "dapt.db"
)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path: Path = path or DEFAULT_DATABASE
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.path.chmod(0o600)
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS credentials (
              name TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata (
              name TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS current_status (
              problem TEXT PRIMARY KEY, percent TEXT NOT NULL, score TEXT NOT NULL,
              submitted_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS file_snapshots (
              problem TEXT PRIMARY KEY, content_hash TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def save_cookie(self, cookie: str) -> None:
        self.connection.execute(
            "INSERT INTO credentials (name, value) VALUES ('cookie', ?) "
            "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
            (cookie,),
        )
        self.connection.commit()

    def cookie(self) -> str:
        row = self.connection.execute(
            "SELECT value FROM credentials WHERE name = 'cookie'"
        ).fetchone()
        if row is None:
            raise AptError("No browser cookie configured. Run `dapt auth` first.")
        return str(row["value"])

    def save_current_status(self, submissions: list[Submission]) -> None:
        rows = [
            (item.problem, item.percent, item.score, item.submitted_at)
            for item in submissions
        ]
        self.connection.executemany(
            "INSERT INTO current_status (problem, percent, score, submitted_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(problem) DO UPDATE SET percent=excluded.percent, "
            "score=excluded.score, submitted_at=excluded.submitted_at",
            rows,
        )
        self.connection.commit()

    def latest_submissions(self) -> list[Submission]:
        rows = self.connection.execute(
            "SELECT problem, percent, score, submitted_at FROM current_status "
            "ORDER BY problem"
        ).fetchall()
        return [
            Submission(
                str(row["problem"]),
                str(row["percent"]),
                str(row["score"]),
                str(row["submitted_at"]),
            )
            for row in rows
        ]

    def save_upload_result(
        self, result: UploadResult, *, content_hash: str, catalog_id: str
    ) -> None:
        if result.score is not None:
            percent, score = f"{result.score * 100:g}", f"{result.score:g}"
        elif result.compile_succeeded:
            percent, score = "pending", "--"
        else:
            percent, score = "compile failed", "--"
        self.save_current_status([Submission(result.problem, percent, score, now())])
        self.save_file_snapshot(catalog_id, content_hash)

    def mark_synced(self) -> None:
        self.connection.execute(
            "INSERT INTO metadata VALUES ('last_synced_at', ?) "
            "ON CONFLICT(name) DO UPDATE SET value=excluded.value",
            (now(),),
        )
        self.connection.commit()

    def last_synced_at(self) -> str | None:
        row = self.connection.execute(
            "SELECT value FROM metadata WHERE name = 'last_synced_at'"
        ).fetchone()
        return None if row is None else str(row["value"])

    def save_file_snapshot(self, problem: str, content_hash: str) -> None:
        self.connection.execute(
            "INSERT INTO file_snapshots (problem, content_hash) VALUES (?, ?) "
            "ON CONFLICT(problem) DO UPDATE SET content_hash=excluded.content_hash",
            (problem, content_hash),
        )
        self.connection.commit()

    def file_snapshot_hash(self, problem: str) -> str | None:
        row = self.connection.execute(
            "SELECT content_hash FROM file_snapshots WHERE problem = ?", (problem,)
        ).fetchone()
        return None if row is None else str(row["content_hash"])
