# Copyright 2026 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
import os
import sys

from quodlibet.errorreport.main import get_sentry
from quodlibet.errorreport.minisentry import (
    CapturedException,
    ParsedDsn,
    _encode_envelope,
    _encode_item_envelope,
    _event_payload,
    _normalize_path,
    _safe_repr,
)

from . import TestCase


class Tminisentry(TestCase):
    def test_normalize_path(self):
        path = os.path.join("foo", "bar", "baz.py")
        assert _normalize_path(path) == "foo/bar/baz.py"

    def test_safe_repr_truncates(self):
        assert _safe_repr("x" * 10, max_length=6) == "'xx..."

    def test_parsed_dsn(self):
        parsed = ParsedDsn("https://public@example.com/sentry/project/42")
        assert parsed.project_id == "42"
        assert parsed.envelope_url == (
            "https://example.com/sentry/project/api/42/envelope/"
        )

    def test_event_payload_promotes_special_tags(self):
        try:
            raise ValueError("boom")
        except ValueError:
            exc_info = sys.exc_info()

        event = _event_payload(
            exc_info,
            {
                "release": "4.7",
                "environment": "test",
                "server_name": "host1",
                "plain": 123,
            },
            fingerprint=["group-a"],
        )

        assert event["release"] == "4.7"
        assert event["environment"] == "test"
        assert event["server_name"] == "host1"
        assert event["fingerprint"] == ["group-a"]
        assert event["tags"] == {"plain": "123"}

    def test_event_payload_includes_exception_context(self):
        local_value = "hello"
        try:
            raise RuntimeError("broken")
        except RuntimeError:
            exc_info = sys.exc_info()

        event = _event_payload(exc_info, {})
        exception = event.get("exception")
        assert isinstance(exception, dict)

        values = exception.get("values")
        assert isinstance(values, list)
        assert values

        first_value = values[0]
        assert isinstance(first_value, dict)

        stacktrace = first_value.get("stacktrace")
        assert isinstance(stacktrace, dict)

        frames = stacktrace.get("frames")
        assert isinstance(frames, list)
        assert frames

        frame = frames[-1]
        assert isinstance(frame, dict)

        frame_vars = frame.get("vars")
        assert isinstance(frame_vars, dict)

        assert first_value["type"] == "RuntimeError"
        assert first_value["value"] == "broken"
        assert frame["function"] == "test_event_payload_includes_exception_context"
        assert frame_vars["local_value"] == repr(local_value)
        assert frame["context_line"]
        assert isinstance(frame["pre_context"], list)
        assert isinstance(frame["post_context"], list)

    def test_event_payload_includes_chained_exceptions(self):
        try:
            try:
                raise ValueError("inner")
            except ValueError as exc:
                raise RuntimeError("outer") from exc
        except RuntimeError:
            exc_info = sys.exc_info()

        event = _event_payload(exc_info, {})
        exception = event.get("exception")
        assert isinstance(exception, dict)

        values = exception.get("values")
        assert isinstance(values, list)
        assert len(values) == 2

        inner = values[0]
        outer = values[1]
        assert isinstance(inner, dict)
        assert isinstance(outer, dict)

        assert inner["type"] == "ValueError"
        assert inner["value"] == "inner"
        assert outer["type"] == "RuntimeError"
        assert outer["value"] == "outer"

    def test_encode_envelope(self):
        event: dict[str, object] = {
            "event_id": "abc123",
            "message": "boom",
        }
        payload = _encode_envelope(ParsedDsn("https://key@example.com/42"), event)
        header, item_header, body, trailing = payload.split(b"\n")
        header_data = json.loads(header)

        assert header_data["event_id"] == "abc123"
        assert header_data["dsn"] == "https://key@example.com/42"
        assert isinstance(header_data["sent_at"], str)
        assert json.loads(item_header) == {
            "type": "event",
            "length": len(body),
            "content_type": "application/json",
        }
        assert json.loads(body) == event
        assert trailing == b""

    def test_encode_user_report_envelope(self):
        payload = {
            "event_id": "abc123",
            "name": "default",
            "email": "email@example.com",
            "comments": "It broke!",
        }
        envelope = _encode_item_envelope(
            ParsedDsn("https://key@example.com/42"),
            "abc123",
            "user_report",
            payload,
        )
        header, item_header, body, trailing = envelope.split(b"\n")
        header_data = json.loads(header)

        assert header_data["event_id"] == "abc123"
        assert header_data["dsn"] == "https://key@example.com/42"
        assert isinstance(header_data["sent_at"], str)
        assert json.loads(item_header) == {
            "type": "user_report",
            "length": len(body),
            "content_type": "application/json",
        }
        assert json.loads(body) == payload
        assert trailing == b""

    def test_main(self):
        sentry = get_sentry()
        try:
            raise Exception
        except Exception:
            exc_info = sys.exc_info()

        err = sentry.capture(exc_info)
        assert isinstance(err, CapturedException)
        report = err.get_report()
        assert isinstance(report, str)
        assert "'event_id':" in report
        assert "'exception':" in report
        assert "'vars':" in report
        assert "'release':" in report

        err.set_comment("foo")
        err.set_comment("bar")
