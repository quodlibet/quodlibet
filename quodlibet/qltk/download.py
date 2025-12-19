# Copyright 2022-25 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from os.path import splitext
from pathlib import Path
from time import sleep
from typing import Any
from collections.abc import Collection
from urllib.parse import urlparse

from gi.repository import Soup, GObject

from quodlibet import print_d, print_w, _, print_e
from quodlibet.formats import AudioFile
from quodlibet.qltk.notif import Task
from quodlibet.util import http, format_size
from quodlibet.util.path import escape_filename


class DownloadProgress(GObject.Object):
    """Downloads songs asynchronously, updating a Task"""

    __gsignals__ = {
        "finished": (GObject.SignalFlags.RUN_LAST, None, (object, object)),
    }

    def __init__(self, songs: Collection[AudioFile], task=None) -> None:
        super().__init__()
        self.songs = songs
        self.successful: set[AudioFile] = set()
        self.failed: set[AudioFile] = set()
        self.task = task or Task(_("Browser"), _("Downloading files"))

    def success(self, song: AudioFile) -> None:
        self.successful.add(song)
        self._update()

    def failure(self, song: AudioFile) -> None:
        self.failed.add(song)
        self._update()

    def _update(self) -> None:
        frac = self.frac
        print_d(f"At {frac * 100:.0f}% ({len(self.successful)}, {len(self.failed)})")
        self.task.update(frac)

    @property
    def frac(self):
        return (len(self.successful) + len(self.failed)) / len(self.songs)

    def _downloaded(
        self, msg: Soup.Message, result: Any, context: tuple[Path, AudioFile]
    ) -> None:
        path, song = context
        try:
            headers = msg.get_property("response-headers")

            # Size (in bytes) from the HTTP headers
            try:
                size = headers.get_content_length()
            except AttributeError:
                size = None

            # MIME type from the HTTP headers
            try:
                ct = (
                    headers.get_content_type()
                )  # returns (mimetype, params) in libsoup3
                content_type = ct[0] if isinstance(ct, tuple) else str(ct)
            except AttributeError:
                content_type = "application/octet-stream"

            size_str = (
                format_size(size) if (size is not None and size > 0) else "unknown size"
            )
            print_d(f"Downloaded {size_str} of {content_type}: {song('title')}")
            # Determine filename
            _, ext = splitext(urlparse(song("~uri")).path)
            fn = (
                escape_filename(song("~artist~title")[:100], safe=b" ,';")
                or song("~basename")
                or f"download-{hash(song('~filename'))}"
            )
            path = path / Path(fn + ext)

            # If file already exist, no new download
            if path.is_file() and path.stat():
                print_w(f"{path!s} already exists. Skipping download")
                self.success(song)
                return

            # write file
            with open(path, "wb") as f:
                f.write(result)
            self.success(song)
            print_d(f"Downloaded to {path} successfully!")
        except Exception as e:
            print_e(f"Failed download ({e})")
            self.failure(song)

    def _failed(self, _req: Any, _exc: Exception, data: tuple) -> None:
        path, song = data
        self.failure(song)

    def download_songs(self, path: Path):
        for s in self.songs:
            uri = s("~uri")
            if urlparse(uri).scheme not in ("http", "https"):
                print_w(f"Skipping non-HTTP URI {uri} for {s('~filename')}")
                self.failure(s)
                continue
            msg = Soup.Message.new("GET", uri)
            http.download(
                msg,
                cancellable=None,
                callback=self._downloaded,
                failure_callback=self._failed,
                context=(path, s),
            )
            yield
        while self.frac < 1 and self.task:
            sleep(0.1)
            yield
        self.task.finish()
        self.emit("finished", len(self.successful), len(self.failed))
