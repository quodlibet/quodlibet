# Copyright 2016-25 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import datetime
from typing import Any
from collections.abc import Callable

from quodlibet import print_d, _
from quodlibet.qltk import WebImage
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.util import enum

from gi.repository import Soup

from quodlibet.util.http import JsonDict

SOUNDCLOUD_NAME = "Soundcloud"
PROCESS_QL_URLS = True

DEFAULT_BITRATE = 128
EPOCH = datetime(1970, 1, 1)
SITE_URL = "https://soundcloud.com"


class Wrapper:
    """Object-like wrapper for read-only dictionaries"""

    def __init__(self, data: dict[str, Any]):
        self._raw = data
        assert isinstance(data, dict)

        self.data: dict = {}
        for k, v in data.items():
            if isinstance(v, dict):
                self.data[k] = Wrapper(v)
            else:
                self.data[k] = v

    def __getattr__(self, name):
        if name in self.data:
            return self.data.get(name)
        raise AttributeError(f"{name!r} not found")

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def get(self, name, default=None):
        return self.data.get(name, default)

    def __str__(self):
        return f"<Wrapped: {self.data}>"


def json_callback(
    wrapped: Callable[[Any, dict[str, Any], Any], None],
) -> Callable[[Soup.Message, JsonDict | None, Any], None]:
    """Method Decorator for `download_json` callbacks, handling common errors"""

    def _callback(
        self, message: Soup.Message, json: dict[str, Any] | None, context
    ) -> None:
        if json is None:
            print_d(
                f"[HTTP {message.status_code}] Invalid / empty JSON. "
                f"Body: {message.response_body.data!r} (request: {context})"
            )
            return
        if "errors" in json:
            raise ValueError("Got HTTP %d (%s)" % (message.status_code, json["errors"]))
        if "error" in json:
            raise ValueError("Got HTTP %d (%s)" % (message.status_code, json["error"]))
        wrapped(self, json, context)

    return _callback  # type: ignore


def clamp(val, low, high):
    intval = int(val or 0)
    return max(low, min(high, intval))


@enum
class State(int):
    LOGGED_OUT, LOGGING_IN, LOGGED_IN = range(3)


@enum
class FilterType(int):
    SEARCH, FAVORITES, MINE = range(3)


class EnterAuthCodeDialog(GetStringDialog):
    def __init__(self, parent):
        super().__init__(
            parent,
            _("Soundcloud authorisation"),
            _("Enter Soundcloud auth code:"),
            button_icon=None,
        )

    def _verify_clipboard(self, text):
        if len(text) > 10:
            return text
        return None


def sanitise_tag(value):
    """QL doesn't want newlines in tags, but they Soundcloud ones
    are not always best represented as multi-value tags (comments, etc)
    """
    return (value or "").replace("\n", "\t").replace("\r", "")


def sc_btn_image(path, w, h):
    return WebImage(f"https://connect.soundcloud.com/2/btn-{path}.png", w, h)
