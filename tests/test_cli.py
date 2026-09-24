import subprocess
from pathlib import Path

import apt_helper.cli as cli
import apt_helper.database as database_module
from apt_helper.cli import main
from apt_helper.database import Database
from apt_helper.models import Submission
from apt_helper.utils import AptError

SUBMISSIONS_PAGE = """
<title>APT Submissions</title>
<table>
  <tr><th>problem</th></tr>
  <tr><td>gravity</td><td>100</td><td>10</td><td>server time</td></tr>
</table>
"""


def test_auth_saves_cookie_and_syncs_submissions(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    database_path = tmp_path / "apt.db"
    monkeypatch.setattr(database_module, "DEFAULT_DATABASE", database_path)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: "session=fresh")

    class FakeAptClient:
        def __init__(self, cookie: str) -> None:
            assert cookie == "session=fresh"

        def submission_page(self) -> str:
            return SUBMISSIONS_PAGE

    monkeypatch.setattr(cli, "AptClient", FakeAptClient)

    assert main(["auth"]) == 0
    output = capsys.readouterr().out
    with Database(database_path) as database:
        assert database.cookie() == "session=fresh"
        assert database.latest_submissions() == [
            Submission("gravity", "100", "10", "server time")
        ]
        assert database.last_synced_at() is not None
    assert "gravity" in output


def test_auth_keeps_new_cookie_when_sync_verification_fails(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    database_path = tmp_path / "apt.db"
    with Database(database_path) as database:
        database.save_cookie("session=old")
    monkeypatch.setattr(database_module, "DEFAULT_DATABASE", database_path)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: "session=invalid")

    class RejectingAptClient:
        def __init__(self, cookie: str) -> None:
            assert cookie == "session=invalid"

        def submission_page(self) -> str:
            raise AptError("Duke session expired")

    monkeypatch.setattr(cli, "AptClient", RejectingAptClient)

    assert main(["auth"]) == 1
    assert "session expired" in capsys.readouterr().err
    with Database(database_path) as database:
        assert database.cookie() == "session=invalid"


def test_status_reads_local_database_without_a_cookie(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    database_path = tmp_path / "apt.db"
    database = Database(database_path)
    database.save_current_status([Submission("gravity", "100", "10", "server time")])
    database.close()
    (tmp_path / "apts" / "set1").mkdir(parents=True)
    (tmp_path / "apts" / "set1" / "Gravity.java").touch()
    monkeypatch.setattr(database_module, "DEFAULT_DATABASE", database_path)
    monkeypatch.chdir(tmp_path)

    assert main(["status"]) == 0
    output = capsys.readouterr().out
    assert "Last synced:" in output
    assert "Gravity" in output
    assert "new" in output
    assert "100% (10)" in output


def test_status_set_filter_uses_file_hash(monkeypatch, tmp_path: Path, capsys) -> None:
    database_path = tmp_path / "apt.db"
    source = tmp_path / "apts" / "set1" / "Gravity.java"
    source.parent.mkdir(parents=True)
    source.write_text("before")
    database = Database(database_path)
    database.save_file_snapshot("set1/gravity", "old-hash")
    database.close()
    monkeypatch.setattr(database_module, "DEFAULT_DATABASE", database_path)
    monkeypatch.chdir(tmp_path)

    assert main(["status", "1"]) == 0
    output = capsys.readouterr().out
    assert "Gravity" in output
    assert "changed" in output


def test_run_executes_the_catalog_source_file(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "apts" / "set1" / "Gravity.java"
    source.parent.mkdir(parents=True)
    source.write_text("class Gravity {}")
    monkeypatch.chdir(tmp_path)
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], *, check: bool
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert check is False
        return subprocess.CompletedProcess(command, returncode=7)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    assert main(["run", "gravity"]) == 7
    assert commands == [["java", str(source)]]


def test_run_requires_the_catalog_source_file(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["run", "gravity"]) == 1
    assert "Expected source file not found" in capsys.readouterr().err


def test_problems_uses_fixed_width_columns(capsys) -> None:
    assert main(["problems"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert (
        lines[0]
        == "GROUP                     CLASS                    SLUG                                      DETAILS"
    )
    assert lines[1].startswith("set1                      Totality")
    assert "totality" in lines[1]


def test_problems_identifies_practice_group_and_details(capsys) -> None:
    assert main(["problems"]) == 0

    output = capsys.readouterr().out
    assert "quiz1" in output
    assert "practice/quiz1" not in output
    assert "EndOfWords" in output
    assert "level 1" in output


def test_unknown_command_returns_usage_error(capsys) -> None:
    assert main(["statsu"]) == 2
    assert "Unknown command" in capsys.readouterr().err
