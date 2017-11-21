# -*- coding: utf-8 -*-
# Copyright 2013 Simonas Kazlauskas
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gio, GLib

from quodlibet.util.http import HTTPRequest
from quodlibet.util import print_w


class HTTPDownloadMixin(object):
    def download(self, message):
        request = HTTPRequest(message, self.cancellable)
        request.connect('sent', self._download_sent)
        request.connect('received', self._download_received)
        request.connect('failure', self._download_failure)
        request.send()

    def _download_sent(self, request, message):
        status = message.get_property('status-code')
        if not 200 <= status < 300:
            request.cancel()
            return self.fail('Bad HTTP code {0}'.format(status))

        target = Gio.file_new_for_path(self.cover_path)
        flags = Gio.FileCreateFlags.NONE

        def replaced(cover_file, task, data):
            try:
                ostr = cover_file.replace_finish(task)
                request.provide_target(ostr)
                request.connect('receive-failure', self._receive_fail, target)
                request.receive()
            except GLib.GError:
                request.cancel()
                return self.fail('Cannot open cover file')
        target.replace_async(None, True, flags, GLib.PRIORITY_DEFAULT,
                             self.cancellable, replaced, None)

    def _download_received(self, request, ostream):
        ostream.close(None)
        self.emit('fetch-success', self.cover)

    def _receive_fail(self, request, exception, gfile):
        def deleted(gfile, task, data):
            try:
                gfile.delete_finish(task)
            except GLib.GError:
                print_w('Could not clean up cover which failed to download')
        ostream = request.ostream
        ostream.close(None)
        gfile.delete_async(GLib.PRIORITY_DEFAULT, None, deleted, None)

    def _download_failure(self, request, exception):
        try:
            self.fail(exception.message or ' '.join(exception.args))
        except AttributeError:
            self.fail("Download error (%s)" % exception)
