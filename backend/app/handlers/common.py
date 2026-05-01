import json
import os
from http import HTTPStatus
from typing import Any


def response(status_code: int, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
    base_headers = {
        "content-type": "application/json",
        "cache-control": "no-store",
    }
    if headers:
        base_headers.update(headers)

    return {
        "statusCode": status_code,
        "headers": base_headers,
        "body": json.dumps(body or {}, ensure_ascii=False),
    }


def redirect(location: str, cookies: list[str] | None = None):
    result = {
        "statusCode": HTTPStatus.FOUND,
        "headers": {"location": location},
        "body": "",
    }
    if cookies:
        result["cookies"] = cookies
    return result


def app_url(path: str = "") -> str:
    base = os.environ["APP_URL"].rstrip("/")
    return f"{base}{path}"


def request_path(event: dict[str, Any]) -> str:
    return event.get("rawPath") or event.get("path") or "/"


def request_method(event: dict[str, Any]) -> str:
    return event.get("requestContext", {}).get("http", {}).get("method", "GET").upper()
