# Copyright 2013 Simonas Kazlauskas
#      2016-2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gio, GLib, Soup

from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.util.http import HTTPRequest, download_json
from quodlibet.util import print_w


class HTTPDownloadMixin:
    def download(self, message):
        request = HTTPRequest(message, self.cancellable)
        request.connect("sent", self._download_sent)
        request.connect("received", self._download_received)
        request.connect("failure", self._download_failure)
        request.send()

    def _download_sent(self, request, message):
        status = message.get_property("status-code")
        if not 200 <= status < 400:
            request.cancel()
            return self.fail(f"Bad HTTP code {status}")

        target = Gio.file_new_for_path(self.cover_path)
        flags = Gio.FileCreateFlags.NONE

        def replaced(cover_file, task, data):
            try:
                ostr = cover_file.replace_finish(task)
                request.provide_target(ostr)
                request.connect("receive-failure", self._receive_fail, target)
                request.receive()
            except GLib.GError:
                request.cancel()
                return self.fail("Cannot open cover file")
        target.replace_async(None, True, flags, GLib.PRIORITY_DEFAULT,
                             self.cancellable, replaced, None)

    def _download_received(self, request, ostream):
        try:
            ostream.close(None)
        except GLib.GError as e:
            print_w(f"Got {e!r} trying to close handle after download")
        self.emit("fetch-success", self.cover)

    def _receive_fail(self, request, exception, gfile):
        def deleted(gfile, task, data):
            try:
                gfile.delete_finish(task)
            except GLib.GError:
                print_w("Could not clean up cover which failed to download")
        try:
            request.ostream.close(None)
        except GLib.GError as e:
            print_w(f"Got {e!r} trying to close handle during failure")
        gfile.delete_async(GLib.PRIORITY_DEFAULT, None, deleted, None)

    def _download_failure(self, request, exception):
        try:
            self.fail(exception.message or " ".join(exception.args))
        except AttributeError:
            self.fail("Download error (%s)" % exception)


class ApiCoverSourcePlugin(CoverSourcePlugin, HTTPDownloadMixin):
    MIN_DIMENSION = 300
    """Minimum width / height in pixels for an image to be used"""

    @property
    def url(self):
        """The URL to the image, if remote"""
        return None

    def search(self):
        if not self.url:
            return self.emit("search-complete", [])
        msg = Soup.Message.new("GET", self.url)
        download_json(msg, self.cancellable, self._handle_search_response, None)

    def _handle_search_response(self, message, json_dict, data=None):
        self.emit("search-complete", [])

    def fetch_cover(self):
        if not self.url:
            return self.fail(f"Not enough data to get cover from {type(self).__name__}")

        def search_complete(self, res):
            self.disconnect(sci)
            if res:
                self.download(Soup.Message.new("GET", res[0]["cover"]))
            else:
                return self.fail("No cover was found")

        sci = self.connect("search-complete", search_complete)
        self.search()

    def _album_artists_for(self, song):
        """Returns a comma-separated list of artists indicating the
        "main" artists from the song's album"""
        people = [song.comma(key)
                  for key in ["albumartist", "artist", "composer", "conductor",
                              "performer"]]
        people = list(filter(None, people))
        return people[0] if people else None


def escape_query_value(s):
    return GLib.Uri.escape_string(s, None, True)
