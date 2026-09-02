"""Command-line interface for dapt, the Duke APT Helper."""

from __future__ import annotations

import argparse
import getpass
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from .catalog import CATALOG, AptProblem, find_apt_name
from .client import AptClient
from .database import Database
from .models import Submission
from .parsing import parse_submissions, parse_upload_result
from .utils import AptError, sha256

SourceState = Literal["missing", "new", "unchanged", "changed"]
CommandHandler = Callable[[argparse.Namespace], int]


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


def command_auth(_: argparse.Namespace) -> int:
    print(
        "Paste the Cookie header value copied from an authenticated apt.cs.duke.edu request."
    )
    with Database() as database:
        database.save_cookie(
            normalise_cookie(getpass.getpass("Cookie (input hidden): "))
        )
        print(f"Saved in local database with owner-only permissions: {database.path}")
    return 0


def command_sync(_: argparse.Namespace) -> int:
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


def command_status(args: argparse.Namespace) -> int:
    """Show only local state: no credentials or network request are required."""
    with Database() as database:
        submissions = {item.problem: item for item in database.latest_submissions()}
        rows: list[tuple[AptProblem, SourceState, Submission | None]] = []
        for problem in CATALOG:
            source_state = file_status(problem, database)
            if args.set_number is not None and problem.set_number != args.set_number:
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


def command_problems(_: argparse.Namespace) -> int:
    print(f"{'GROUP':25} {'CLASS':24} {'DETAILS':40}  SLUG")
    for problem in CATALOG:
        print(
            f"{problem.group_id:25} "
            f"{problem.class_name:24} "
            f"{problem.details:40}  {problem.slug}"
        )
    return 0


def command_run(args: argparse.Namespace) -> int:
    """Run an expected Java source file using Java source-file mode."""
    _, file_path = resolve_source(args.apt_name)
    try:
        return subprocess.run(["java", str(file_path)], check=False).returncode
    except FileNotFoundError as exc:
        raise AptError("Java is not installed or is not available on PATH.") from exc


def command_submit(args: argparse.Namespace) -> int:
    catalog_problem, file_path = resolve_source(args.apt_name)
    with Database() as database:
        if not args.yes and input(
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dapt",
        description="Check and submit Duke APT solutions using your browser session.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    auth = subcommands.add_parser(
        "auth", help="save a Cookie header locally (input is hidden)"
    )
    auth.set_defaults(handler=command_auth)
    sync = subcommands.add_parser(
        "sync",
        help="fetch and display submitted APT results",
    )
    sync.set_defaults(handler=command_sync)
    status = subcommands.add_parser(
        "status", help="show local APT/file status without fetching"
    )
    status.add_argument(
        "set_number",
        nargs="?",
        type=int,
        metavar="SET",
        help="show one APT set",
    )
    status.set_defaults(handler=command_status)
    problems = subcommands.add_parser(
        "problems", help="list hard-coded CS201 APT mappings"
    )
    problems.set_defaults(handler=command_problems)
    run = subcommands.add_parser(
        "run", help="run an APT's expected Java source file locally"
    )
    run.add_argument(
        "apt_name",
        help="APT/class/catalog ID, e.g. gravity or quiz1/endofwords",
    )
    run.set_defaults(handler=command_run)
    submit = subcommands.add_parser(
        "submit", help="upload an APT by its visible class name"
    )
    submit.add_argument(
        "apt_name",
        help="APT/class/catalog ID, e.g. gravity or quiz1/endofwords",
    )
    submit.add_argument(
        "-y", "--yes", action="store_true", help="skip the confirmation prompt"
    )
    submit.set_defaults(handler=command_submit)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        handler = args.handler
        return handler(args)
    except AptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
