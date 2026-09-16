"""Command-line interface for dapt, the Duke APT Helper."""

from __future__ import annotations

import getpass
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Literal

import cyclopts
from cyclopts import Parameter

from .catalog import CATALOG, AptProblem, find_apt_name
from .client import AptClient
from .database import Database
from .models import Submission
from .parsing import parse_submissions, parse_upload_result
from .utils import AptError, sha256

SourceState = Literal["missing", "new", "unchanged", "changed"]
app = cyclopts.App(
    name="dapt",
    help="Check and submit Duke APT solutions using your browser session.",
    exit_on_error=False,
)


def normalise_cookie(value: str) -> str:
    value = value.strip()
    if not value or "=" not in value:
        raise AptError("Cookie must contain at least one name=value pair.")
    return value


def load_cookie(database: Database) -> str:
    return normalise_cookie(database.cookie())


def resolve_source(name: str) -> tuple[AptProblem, Path]:
    problem = find_apt_name(name)
    if problem is None:
        raise AptError(
            f"Unknown APT name {name!r}. Run `dapt problems` to list valid names."
        )
    source_path = problem.source_path(Path.cwd())
    if not source_path.is_file():
        raise AptError(f"Expected source file not found: {source_path}")
    return problem, source_path


def print_submissions(submissions: list[Submission]) -> None:
    if not submissions:
        print("No submissions found.")
    else:
        print(f"{'PROBLEM':24} {'PERCENT':>7} {'SCORE':>7}  TIME")
        for item in submissions:
            print(
                f"{item.problem:24} {item.percent:>7} {item.score:>7}  {item.submitted_at}"
            )


@app.command(name="auth")
def command_auth() -> int:
    """Save a Cookie header locally (input is hidden)."""
    print(
        "Paste the Cookie header value copied from an authenticated apt.cs.duke.edu request."
    )
    with Database() as database:
        database.save_cookie(
            normalise_cookie(getpass.getpass("Cookie (input hidden): "))
        )
        print(f"Saved in local database with owner-only permissions: {database.path}")
    return command_sync()


@app.command(name="sync")
def command_sync() -> int:
    """Fetch and display submitted APT results."""
    with Database() as database:
        submissions = parse_submissions(
            AptClient(load_cookie(database)).submission_page()
        )
        database.save_current_status(submissions)
        database.mark_synced()
        print_submissions(submissions)
    return 0


def file_status(problem: AptProblem, database: Database) -> SourceState:
    source_path = problem.source_path(Path.cwd())
    if not source_path.is_file():
        return "missing"
    previous_hash = database.file_snapshot_hash(problem.catalog_id)
    if previous_hash is None:
        return "new"
    return "unchanged" if sha256(source_path) == previous_hash else "changed"


@app.command(name="status")
def command_status(set_number: int | None = None) -> int:
    """Show local APT/file status without fetching.

    Parameters
    ----------
    set_number
        Show only one APT set.
    """
    with Database() as database:
        submissions = {item.problem: item for item in database.latest_submissions()}
        rows: list[tuple[AptProblem, SourceState, Submission | None]] = []
        for problem in CATALOG:
            source_state = file_status(problem, database)
            if set_number is not None and problem.set_number != set_number:
                continue
            rows.append((problem, source_state, submissions.get(problem.slug)))
        last_synced = database.last_synced_at() or "never"
        print(f"Last synced: {last_synced}")
        print(f"{'GROUP':25} {'CLASS':24} {'FILE STATUS':11} {'RESULT':>10}  SUBMITTED")
        for problem, source_state, submission in rows:
            result = (
                f"{submission.percent}% ({submission.score})"
                if submission and submission.percent.replace(".", "", 1).isdigit()
                else (submission.percent if submission else "--")
            )
            submitted_at = submission.submitted_at if submission else "--"
            print(
                f"{problem.group_id:25} {problem.class_name:24} "
                f"{source_state:11} {result:>10}  {submitted_at}"
            )
    return 0


@app.command(name="problems")
def command_problems() -> int:
    """List hard-coded CS201 APT mappings."""
    print(f"{'GROUP':25} {'CLASS':24} {'SLUG':40}  DETAILS")
    for problem in CATALOG:
        print(
            f"{problem.group_id:25} "
            f"{problem.class_name:24} "
            f"{problem.slug:20}  {problem.details}"
        )
    return 0


@app.command(name="run")
def command_run(apt_name: str) -> int:
    """Run an APT's expected Java source file locally.

    Parameters
    ----------
    apt_name
        APT, class, or catalog ID, e.g. ``gravity`` or ``quiz1/endofwords``.
    """
    _, file_path = resolve_source(apt_name)
    try:
        return subprocess.run(["java", str(file_path)], check=False).returncode
    except FileNotFoundError as exc:
        raise AptError("Java is not installed or is not available on PATH.") from exc


@app.command(name="submit")
def command_submit(
    apt_name: str,
    yes: Annotated[
        bool,
        Parameter(alias="-y", help="Skip the confirmation prompt."),
    ] = False,
) -> int:
    """Upload an APT by its visible class name.

    Parameters
    ----------
    apt_name
        APT, class, or catalog ID, e.g. ``gravity`` or ``quiz1/endofwords``.
    """
    catalog_problem, file_path = resolve_source(apt_name)
    with Database() as database:
        if not yes and input(
            f"Submit {file_path.name} for {catalog_problem.catalog_id}? [y/N] "
        ).strip().lower() not in {"y", "yes"}:
            print("Submission cancelled.")
            return 0
        client = AptClient(load_cookie(database))
        result = parse_upload_result(
            client.submit(
                file_path,
                problem=catalog_problem.slug,
            )
        )
        if result.problem != catalog_problem.slug:
            raise AptError(
                "APT returned an unexpected upload page. Your Duke session may have expired; run `dapt auth` with updated credentials."
            )
        database.save_upload_result(
            result,
            content_hash=sha256(file_path),
            catalog_id=catalog_problem.catalog_id,
        )
        compile_status = (
            "succeeded" if result.compile_succeeded else "failed or was not reported"
        )
        tests = (
            f"{result.correct}/{result.total}"
            if result.correct is not None and result.total is not None
            else "not reported"
        )
        score = (
            f"{result.score * 100:g}%" if result.score is not None else "not reported"
        )
        count = (
            result.submission_count
            if result.submission_count is not None
            else "not reported"
        )
        print(
            f"Processed {result.file_name} for {result.problem}: compile {compile_status}; tests {tests}; score {score}; submissions {count}."
        )
        if not result.compile_succeeded:
            return 2
        if result.score is None:
            return 1
        if result.score < 1:
            return 3
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        result = app(argv, result_action="return_value")
        return result if isinstance(result, int) else 0
    except cyclopts.CycloptsError:
        # Cyclopts has already rendered a useful usage error. Keep the CLI
        # composable by returning the conventional command-line error status.
        return 2
    except AptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
