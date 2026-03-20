# Copyright 2017 Christoph Reiter
#           2020 Nick Boultbee
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""A small Sentry client tailored to the GUI error reporting flow.

We split the capture phase from the submit phase so the user can inspect the
payload before it is sent.
"""

import datetime
import json
import linecache
import os
import platform
import pprint
import sys
import types
import uuid
from collections.abc import Iterator, Mapping
from typing import Any, TypeAlias
from urllib.parse import urlsplit

import quodlibet
from quodlibet.util.urllib import Request, urlopen


SDK_NAME = "quodlibet-minisentry"
SDK_VERSION = quodlibet.get_build_description()
USER_AGENT = f"{SDK_NAME}/{SDK_VERSION}"
FEEDBACK_NAME = "default"
FEEDBACK_EMAIL = "email@example.com"

ContextLines: TypeAlias = tuple[str | None, list[str], list[str]]
ExcInfo: TypeAlias = tuple[
    type[BaseException] | None,
    BaseException | None,
    types.TracebackType | None,
]


class SentryError(Exception):
    """Exception type for all the API below."""


class ParsedDsn:
    """A parsed Sentry DSN."""

    dsn: str
    scheme: str
    project_id: str
    store_base: str
    envelope_url: str

    def __init__(self, dsn: str) -> None:
        parts = urlsplit(dsn)
        if not parts.scheme or not parts.hostname:
            raise SentryError("Invalid DSN")
        if not parts.username:
            raise SentryError("DSN is missing the public key")

        path = parts.path.rstrip("/")
        if not path or "/" not in path:
            raise SentryError("DSN is missing the project id")

        project_id = path.split("/")[-1]
        base_path = path[: -len(project_id)].rstrip("/")
        host = parts.hostname
        if parts.port is not None:
            host = f"{host}:{parts.port}"

        self.dsn = dsn
        self.scheme = parts.scheme
        self.project_id = project_id
        self.store_base = f"{self.scheme}://{host}{base_path}"
        self.envelope_url = f"{self.store_base}/api/{self.project_id}/envelope/"


def _encode_item_envelope(
    parsed_dsn: ParsedDsn,
    event_id: str,
    item_type: str,
    payload: Mapping[str, object],
) -> bytes:
    payload_bytes = json.dumps(
        payload, default=_json_default, separators=(",", ":")
    ).encode("utf-8")
    headers = {
        "event_id": event_id,
        "dsn": parsed_dsn.dsn,
        "sent_at": _event_timestamp(),
    }
    item_headers = {
        "type": item_type,
        "length": len(payload_bytes),
        "content_type": "application/json",
    }
    return (
        json.dumps(headers, separators=(",", ":")).encode("utf-8")
        + b"\n"
        + json.dumps(item_headers, separators=(",", ":")).encode("utf-8")
        + b"\n"
        + payload_bytes
        + b"\n"
    )


def send_feedback(
    dsn: str,
    event_id: str,
    name: str,
    email: str,
    comment: str,
    timeout: float,
) -> None:
    """Send feedback, blocking."""

    parsed = ParsedDsn(dsn)
    payload = {
        "event_id": event_id,
        "name": str(name),
        "email": str(email),
        "comments": str(comment),
    }
    data = _encode_item_envelope(parsed, event_id, "user_report", payload)

    headers = {
        "Content-Type": "application/x-sentry-envelope",
        "User-Agent": USER_AGENT,
    }

    try:
        req = Request(parsed.envelope_url, data=data, headers=headers)
        urlopen(req, timeout=timeout).close()
    except OSError as e:
        raise SentryError(e) from e


def _normalize_path(path: str) -> str:
    return path.replace(os.sep, "/")


def _safe_repr(value: Any, max_length: int = 4096) -> str:
    try:
        rendered = repr(value)
    except Exception as exc:
        rendered = f"<repr failed: {exc!r}>"
    if len(rendered) > max_length:
        rendered = rendered[: max_length - 3] + "..."
    return rendered


def _json_default(value: Any) -> str:
    return _safe_repr(value)


def _serialize_context(abs_path: str, lineno: int, context: int = 5) -> ContextLines:
    if not abs_path or not os.path.isfile(abs_path):
        return None, [], []

    lines = linecache.getlines(abs_path)
    if not lines:
        return None, [], []

    index = max(lineno - 1, 0)

    def clean(text: str) -> str:
        return text.rstrip("\r\n")

    context_line = lines[index] if index < len(lines) else ""
    pre_start = max(index - context, 0)
    post_end = min(index + context + 1, len(lines))
    pre_context = [clean(line) for line in lines[pre_start:index]]
    post_context = [clean(line) for line in lines[index + 1 : post_end]]
    return clean(context_line), pre_context, post_context


def _abs_path(filename: str) -> str:
    if not filename:
        return "<unknown>"
    if filename.startswith("<") and filename.endswith(">"):
        return filename
    if os.path.isabs(filename):
        return _normalize_path(filename)
    return _normalize_path(os.path.abspath(filename))


def _serialize_frame(tb: types.TracebackType) -> dict[str, object]:
    frame = tb.tb_frame
    code = frame.f_code
    raw_filename = code.co_filename or "<unknown>"
    abs_path = _abs_path(raw_filename)
    lineno = tb.tb_lineno
    context_line, pre_context, post_context = _serialize_context(abs_path, lineno)

    data: dict[str, object] = {
        "filename": _normalize_path(raw_filename),
        "abs_path": abs_path,
        "function": code.co_name,
        "lineno": lineno,
        "module": frame.f_globals.get("__name__") or None,
        "vars": {key: _safe_repr(value) for key, value in frame.f_locals.items()},
    }

    if context_line is not None:
        data["context_line"] = context_line
        data["pre_context"] = pre_context
        data["post_context"] = post_context

    return data


def _serialize_traceback(tb: types.TracebackType | None) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    while tb is not None:
        frames.append(_serialize_frame(tb))
        tb = tb.tb_next
    return frames


def _chained_exceptions(exc_info: ExcInfo) -> Iterator[ExcInfo]:
    exc_type, exc, _exc_traceback = exc_info
    if exc_type is None or exc is None:
        return

    yield exc_info

    seen = {exc}
    while True:
        suppress_context = getattr(exc, "__suppress_context__", False)
        if suppress_context:
            exc = exc.__cause__
        else:
            exc = exc.__context__

        if exc is None or exc in seen:
            break

        seen.add(exc)
        yield type(exc), exc, exc.__traceback__


def _event_timestamp() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )


def _event_payload(
    exc_info: ExcInfo,
    tags: Mapping[str, object],
    fingerprint: list[str] | None = None,
) -> dict[str, object]:
    exc_type, _exc_value, _tb = exc_info
    if exc_type is None:
        raise SentryError("No active exception")

    values: list[dict[str, object]] = []
    for chained_type, chained_value, chained_tb in _chained_exceptions(exc_info):
        if chained_type is None or chained_value is None:
            continue
        values.insert(
            0,
            {
                "type": chained_type.__name__,
                "value": str(chained_value),
                "module": getattr(chained_type, "__module__", None),
                "stacktrace": {"frames": _serialize_traceback(chained_tb)},
            },
        )

    event: dict[str, object] = {
        "event_id": uuid.uuid4().hex,
        "timestamp": _event_timestamp(),
        "platform": "python",
        "level": "error",
        "message": exc_type.__name__,
        "sdk": {
            "name": SDK_NAME,
            "version": SDK_VERSION,
        },
        "modules": {"python": platform.python_version()},
        "extra": {
            "sys.argv": [_safe_repr(arg) for arg in sys.argv],
        },
        "exception": {
            "values": values,
        },
    }

    event_tags = {str(key): str(value) for key, value in tags.items()}

    release = event_tags.pop("release", None)
    if release is not None:
        event["release"] = release

    environment = event_tags.pop("environment", None)
    if environment is not None:
        event["environment"] = environment

    server_name = event_tags.pop("server_name", None)
    event["server_name"] = server_name or "default"

    if event_tags:
        event["tags"] = event_tags

    if fingerprint:
        event["fingerprint"] = [str(part) for part in fingerprint]

    return event


def _encode_envelope(parsed_dsn: ParsedDsn, event: dict[str, object]) -> bytes:
    return _encode_item_envelope(parsed_dsn, str(event["event_id"]), "event", event)


def _send_event(dsn: str, event: dict[str, object], timeout: float) -> None:
    parsed = ParsedDsn(dsn)
    data = _encode_envelope(parsed, event)
    headers = {
        "Content-Type": "application/x-sentry-envelope",
        "User-Agent": USER_AGENT,
    }

    try:
        req = Request(parsed.envelope_url, data=data, headers=headers)
        urlopen(req, timeout=timeout).close()
    except OSError as e:
        raise SentryError(e) from e


class CapturedException:
    """Contains the event data to be sent to Sentry."""

    _dsn: str
    _event: dict[str, object]
    _comment: str | None

    def __init__(self, dsn: str, event: dict[str, object]) -> None:
        self._dsn = dsn
        self._event = event
        self._comment = None

    def get_report(self) -> str:
        return pprint.pformat(self._event, width=40)

    def set_comment(self, comment: str) -> None:
        self._comment = comment

    def send(self, timeout: float) -> str:
        _send_event(self._dsn, self._event, timeout)
        event_id = str(self._event["event_id"])

        if self._comment:
            send_feedback(
                self._dsn,
                event_id,
                FEEDBACK_NAME,
                FEEDBACK_EMAIL,
                self._comment,
                timeout,
            )

        return event_id


class Sentry:
    """The main object of our Sentry API wrapper."""

    _dsn: str
    _tags: dict[str, object]

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._tags = {}

    def add_tag(self, key: str, value: object) -> None:
        self._tags[key] = value

    def capture(
        self,
        exc_info: ExcInfo | None = None,
        fingerprint: list[str] | None = None,
    ) -> CapturedException:
        if exc_info is None:
            exc_info = sys.exc_info()

        event = _event_payload(exc_info, self._tags, fingerprint=fingerprint)
        return CapturedException(self._dsn, event)
