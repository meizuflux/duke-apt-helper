from typing import cast

import pytest
import requests
from requests import Response

from apt_helper.client import AptClient
from apt_helper.utils import AptError


class FakeSession:
    def __init__(self, response: Response) -> None:
        self.response = response

    def request(self, *args, **kwargs) -> Response:
        return self.response


def test_submission_page_reports_redirected_expired_session() -> None:
    response = Response()
    response.status_code = 200
    response.url = "https://shib.oit.duke.edu/idp/profile/SAML2/Redirect/SSO"
    response._content = b"sign in"
    client = AptClient("session=old")
    client.session = cast(requests.Session, FakeSession(response))

    with pytest.raises(AptError, match="session expired"):
        client.submission_page()


def test_submission_page_accepts_apt_results_page() -> None:
    response = Response()
    response.status_code = 200
    response.url = "https://apt.cs.duke.edu/aptsec/checksub201.php"
    response._content = b"<title>APT Submissions</title>"
    client = AptClient("session=valid")
    client.session = cast(requests.Session, FakeSession(response))

    client.submission_page()
