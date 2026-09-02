from apt_helper.parsing import parse_submissions, parse_upload_result


def test_parses_submission_table() -> None:
    page = "<table><tr><th>problem</th></tr><tr><td>gravity</td><td>100</td><td>10</td><td>08-26-2026</td></tr></table>"

    assert parse_submissions(page)[0].problem == "gravity"


def test_parses_upload_summary() -> None:
    page = """
    <b>Problem</b>: accesslevel<br><b>Files</b>: AccessLevel.java<br>
    Compiling...<p>compile succeeded<p># of correct: 12 out of 12
    <li>logged entry score = 1.00000</li>number of submissions for accesslevel : 2
    """

    result = parse_upload_result(page)

    assert result.problem == "accesslevel"
    assert result.file_name == "AccessLevel.java"
    assert result.compile_succeeded is True
    assert (result.correct, result.total, result.score, result.submission_count) == (
        12,
        12,
        1.0,
        2,
    )
