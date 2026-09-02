"""HTML parsing for APT pages."""

import re

from bs4 import BeautifulSoup

from .models import Submission, UploadResult


def parse_submissions(page: str) -> list[Submission]:
    soup = BeautifulSoup(page, "html.parser")
    result: list[Submission] = []
    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) >= 4:
            result.append(
                Submission(
                    cells[0],
                    cells[1],
                    cells[2],
                    cells[3],
                )
            )
    return result


def parse_upload_result(page: str) -> UploadResult:
    """Extract the stable summary values from an APT upload response."""
    text = BeautifulSoup(page, "html.parser").get_text(" ", strip=True)

    def matched(pattern: str) -> str | None:
        found = re.search(pattern, text, flags=re.I)
        return found.group(1) if found else None

    problem = matched(r"Problem\s*:\s*([^\s]+)") or "unknown"
    file_name = matched(r"Files\s*:\s*([^\s]+)") or "unknown"
    correct_match = re.search(
        r"#\s*of\s*correct\s*:\s*(\d+)\s+out\s+of\s+(\d+)", text, flags=re.I
    )
    score = matched(r"logged entry score\s*=\s*([0-9.]+)")
    submission_count = matched(r"number of submissions for [^:]+\s*:\s*(\d+)")
    return UploadResult(
        problem=problem,
        file_name=file_name,
        compile_succeeded="compile succeeded" in text.lower(),
        correct=int(correct_match.group(1)) if correct_match else None,
        total=int(correct_match.group(2)) if correct_match else None,
        score=float(score) if score else None,
        submission_count=int(submission_count) if submission_count else None,
    )
