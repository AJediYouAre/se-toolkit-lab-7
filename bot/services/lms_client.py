"""LMS API client — handles all HTTP calls to the backend.

Separated from handlers so the same client can be used from tests,
--test mode, or Telegram without duplication.
"""

import httpx

from bot.config import LMS_API_BASE_URL, LMS_API_KEY

_client = httpx.Client(
    base_url=LMS_API_BASE_URL,
    headers={"Authorization": f"Bearer {LMS_API_KEY}"},
    timeout=10.0,
)


class LmsError(Exception):
    """Raised when the LMS backend returns an error or is unreachable."""

    def __init__(self, message: str, detail: str = ""):
        self.detail = detail
        super().__init__(message)


def _request(method: str, path: str, **kwargs) -> httpx.Response:
    """Make an HTTP request, raising LmsError on failure."""
    try:
        resp = _client.request(method, path, **kwargs)
    except httpx.ConnectError as exc:
        raise LmsError(
            f"Backend error: connection refused ({LMS_API_BASE_URL}). "
            "Check that the services are running.",
            detail=str(exc),
        ) from exc
    except httpx.TimeoutException as exc:
        raise LmsError(
            "Backend error: request timed out. The backend may be overloaded.",
            detail=str(exc),
        ) from exc
    except httpx.HTTPError as exc:
        raise LmsError(
            f"Backend error: {exc}",
            detail=str(exc),
        ) from exc

    if resp.status_code >= 400:
        raise LmsError(
            f"Backend error: HTTP {resp.status_code} {resp.reason_phrase}. "
            "The backend service may be down.",
            detail=resp.text,
        )

    return resp


def get_items() -> list[dict]:
    """Fetch all items (labs and tasks) from the backend."""
    resp = _request("GET", "/items/")
    return resp.json()


def get_pass_rates(lab: str) -> list[dict]:
    """Fetch per-task pass rates for a given lab."""
    resp = _request("GET", "/analytics/pass-rates", params={"lab": lab})
    return resp.json()
