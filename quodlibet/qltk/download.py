# Copyright 2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from os.path import splitext
from pathlib import Path
from time import sleep
from typing import Tuple, Collection, Any, Set

from gi.repository import Soup, GObject
from urllib3.util import parse_url

from quodlibet import print_d, print_w, _, print_e
from quodlibet.formats import AudioFile
from quodlibet.qltk.notif import Task
from quodlibet.util import http, format_size


class DownloadProgress(GObject.Object):
    """Downloads songs asynchronously, updating a Task"""

    __gsignals__ = {
        'finished': (GObject.SignalFlags.RUN_LAST, None, (object, object)),
    }

    def __init__(self, songs: Collection[AudioFile], task=None) -> None:
        super().__init__()
        self.songs = songs
        self.successful: Set[AudioFile] = set()
        self.failed: Set[AudioFile] = set()
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
        frac = (len(self.successful) + len(self.failed)) / len(self.songs)
        return frac

    def _downloaded(self, msg: Soup.Message, result: Any, data: Tuple) -> None:
        path, song = data
        try:
            headers = msg.get_property('response-headers')
            size = int(headers.get('content-length'))
            content_type = headers.get('content-type')
            print_d(
                f"Downloaded {format_size(size)} of {content_type}: {song('title')}")
            _, ext = splitext(parse_url(song("~uri")).path)
            fn = (song("~artist~title")[:200]
                  or song("~basename")
                  or f"download-{hash(song('~filename'))}")
            path = path / Path(fn + ext)
            if path.is_file() and path.stat():
                print_w(f"{path!s} already exists. Skipping download")
                self.success(song)
                return
            with open(path, "wb") as f:
                f.write(result)
            self.success(song)
            print_d(f"Downloaded to {path} successfully!")
        except Exception as e:
            print_e(f"Failed download ({e}")
            self.failure(song)

    def _failed(self, _req: Any, _exc: Exception, data: Tuple) -> None:
        path, song = data
        self.failure(song)

    def download_songs(self, path: Path):
        for s in self.songs:
            msg = Soup.Message.new('GET', s("~uri"))
            http.download(msg, cancellable=None, callback=self._downloaded,
                          failure_callback=self._failed, data=(path, s))
            yield
        while self.frac < 1 and self.task:
            sleep(0.1)
            yield
        self.task.finish()
        self.emit("finished", len(self.successful), len(self.failed))
