import subprocess
from pathlib import Path

import apt_helper.cli as cli
import apt_helper.database as database_module
from apt_helper.cli import main
from apt_helper.database import Database
from apt_helper.models import Submission


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
