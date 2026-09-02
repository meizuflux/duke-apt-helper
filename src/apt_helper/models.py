from dataclasses import dataclass


@dataclass(frozen=True)
class Submission:
    problem: str
    percent: str
    score: str
    submitted_at: str


@dataclass(frozen=True)
class UploadResult:
    problem: str
    file_name: str
    compile_succeeded: bool
    correct: int | None
    total: int | None
    score: float | None
    submission_count: int | None
