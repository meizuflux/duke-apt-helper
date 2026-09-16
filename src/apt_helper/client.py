"""HTTP client for Duke APT."""

from pathlib import Path
from typing import NotRequired, TypedDict, Unpack
from urllib.parse import urlsplit

import niquests
from niquests.typing import MultiPartFilesAltType

from .utils import AptError

BASE_URL = "https://apt.cs.duke.edu/aptsec"
CHECK_URL = f"{BASE_URL}/checksub201.php"
UPLOAD_URL = f"{BASE_URL}/newalgoupload.php"


class RequestOptions(TypedDict):
    """The request options used by this client."""

    data: NotRequired[dict[str, str]]
    files: NotRequired[MultiPartFilesAltType]


class AptClient:
    def __init__(self, cookie: str) -> None:
        self.session: niquests.Session = niquests.Session()
        self.session.headers.update(
            {
                "Cookie": cookie,
                "User-Agent": "dapt/0.1 (personal Duke APT submission client)",
            }
        )

    def _request(
        self, method: str, url: str, **kwargs: Unpack[RequestOptions]
    ) -> niquests.Response:
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            response.raise_for_status()
        except niquests.RequestException as exc:
            raise AptError(f"Could not reach APT: {exc}") from exc
        if response.url is None or urlsplit(response.url).hostname != "apt.cs.duke.edu":
            raise AptError(
                "Duke session expired. Run `dapt auth` and paste a fresh Cookie header."
            )
        return response

    def submission_page(self) -> str:
        page = self._request("GET", CHECK_URL).text or ""
        if "APT Submissions" not in page:
            raise AptError(
                "Duke session expired or APT returned an unexpected results page. Run `dapt auth` with updated credentials."
            )
        return page

    def submit(self, file_path: Path, *, problem: str) -> str:
        with file_path.open("rb") as upload:
            return self._request(
                "POST",
                UPLOAD_URL,
                data={"course": "compsci201", "language": "java", "problem": problem},
                files={"upfile": (file_path.name, upload, "application/octet-stream")},
            ).text or ""
