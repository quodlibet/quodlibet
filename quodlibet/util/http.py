# Copyright 2013 Simonas Kazlauskas
#        2016-25 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
from json import JSONDecodeError
from typing import Any
from collections.abc import Callable

from gi.repository import Soup, Gio, GLib, GObject
from gi.repository.GObject import ParamFlags, SignalFlags

from quodlibet.const import VERSION, WEBSITE
from quodlibet.util import print_d, print_w

PARAM_READWRITECONSTRUCT = (
    ParamFlags.CONSTRUCT_ONLY | ParamFlags.READABLE | ParamFlags.WRITABLE
)

JsonDict = dict[str, Any]


class HTTPRequest(GObject.Object):
    """
    Class encapsulating a single HTTP request. These are meant to be sent
    and received only once. Behaviour is undefined otherwise.
    """

    __gsignals__ = {
        # Successes
        "sent": (SignalFlags.RUN_LAST, None, (Soup.Message,)),
        "received": (SignalFlags.RUN_LAST, None, (Gio.OutputStream,)),
        # Failures
        "send-failure": (SignalFlags.RUN_LAST, None, (object,)),
        "receive-failure": (SignalFlags.RUN_LAST, None, (object,)),
        # Common failure signal which will be emitted when either of above
        # failure signals are.
        "failure": (SignalFlags.RUN_LAST, None, (object,)),
    }

    message = GObject.Property(type=Soup.Message, flags=PARAM_READWRITECONSTRUCT)
    cancellable = GObject.Property(type=Gio.Cancellable, flags=PARAM_READWRITECONSTRUCT)
    istream = GObject.Property(type=Gio.InputStream, default=None)
    ostream = GObject.Property(type=Gio.OutputStream, default=None)

    def __init__(self, message: Soup.Message | None, cancellable: Gio.Cancellable):
        if message is None:
            raise ValueError("Message may not be None")

        inner_cancellable = Gio.Cancellable()
        super().__init__(message=message, cancellable=inner_cancellable)
        if cancellable is not None:
            cancellable.connect(lambda *x: self.cancel(), None)

        self.connect("send-failure", lambda r, e: r.emit("failure", e))
        self.connect("receive-failure", lambda r, e: r.emit("failure", e))

        # For simple access
        self._receive_started = False
        self._uri = self.message.get_uri().to_string()

    def send(self):
        """
        Send the request and receive HTTP headers.
        Some of the body might get downloaded too.
        """
        session.send_async(self.message, 1, self.cancellable, self._sent, None)

    def _sent(self, session: Soup.Session, task, data):
        m = self.message
        try:
            status = int(m.get_property("status-code"))
            if status >= 400:
                msg = f"HTTP {status} error in {m.get_method()} request to {self._uri}"
                print_w(msg)
                return self.emit("send-failure", Exception(msg))
            self.istream = session.send_finish(task)
            print_d(f"Got HTTP {status} on {m.get_method()} request to {self._uri}.")
            self.emit("sent", m)
        except GLib.GError as e:
            print_w(f"Failed sending {m.get_method()} request to {self._uri} ({e})")
            self.emit("send-failure", e)

    def provide_target(self, stream):
        if not stream:
            raise ValueError("Provided stream may not be None")
        if not self.ostream:
            self.ostream = stream
        else:
            raise RuntimeError("Only one output stream may be provided")

    def cancel(self):
        """
        Cancels the future and currently running HTTPRequest actions.

        It is safe to run this function before, during and after any action
        made with HTTPRequest.

        After HTTPRequest is cancelled, one usually would not do any more
        actions with it. However, it is safe to do something after
        cancellation, but those actions usually will fail.
        """

        if self.cancellable.is_cancelled():
            return False
        self.cancellable.cancel()

        # If we already have input stream, we can just close it, message
        # will come out as cancelled just fine.
        if self.istream and not self._receive_started:
            if not self.istream.is_closed():
                self.istream.close(None)
        return None

    def receive(self):
        """
        Receive data from the request into provided output stream. The request
        must be already sent, therefore this function will be usually called
        from the 'sent' signal handler.

        On completion of data receipt, HTTPRequest lifetime is ended and
        inner resources are cleaned up (except persistent connections that are
        part of session, not request).

        .. note::
        Be sure to clean up resources you've allocated yourself (e.g. close
        GOutputStreams, delete files on failure et cetera).
        """
        if not self.istream:
            raise RuntimeError("Cannot receive unsent request")
        if not self.ostream:
            raise RuntimeError("Cannot receive request without output stream")
        if self._receive_started:
            raise RuntimeError("Can receive only once")
        self._receive_started = True

        def spliced(ostream, task, data):
            try:
                ostream.splice_finish(task)
                self.istream.close(None)
                self.emit("received", ostream)
            except GLib.GError as e:
                self.istream.close(None)
                self.emit("receive-failure", e)

        # Do not ask splice to close the stream as Soup gets confused and
        # doesn't close connections
        # https://bugzilla.gnome.org/show_bug.cgi?id=711260
        flags = Gio.OutputStreamSpliceFlags.NONE
        self.ostream.splice_async(
            self.istream, flags, GLib.PRIORITY_DEFAULT, self.cancellable, spliced, None
        )


FailureCallback = Callable[[HTTPRequest, Exception, Any], None]


def download(
    message: Soup.Message,
    cancellable: Gio.Cancellable,
    callback: Callable[[Soup.Message, bytes | JsonDict | None, Any], None],
    context: Any,
    try_decode: bool = False,
    failure_callback: FailureCallback | None = None,
):
    def received(request: HTTPRequest, ostream):
        ostream.close(None)
        bs = ostream.steal_as_bytes().get_data()
        if not try_decode:
            callback(message, bs, context)
            return
        # Otherwise try to decode data
        code = int(message.get_property("status-code"))
        if code >= 400:
            print_w("HTTP %d error received on %s" % (code, request._uri))
            return
        ctype = message.get_property("response-headers").get_content_type()
        encoding = ctype[1].get("charset", "utf-8")
        try:
            callback(message, bs.decode(encoding), context)
        except UnicodeDecodeError:
            callback(message, bs, context)

    request = HTTPRequest(message, cancellable)
    request.provide_target(Gio.MemoryOutputStream.new_resizable())
    request.connect("received", received)
    request.connect("sent", lambda r, m: r.receive())
    if failure_callback:
        request.connect("send-failure", failure_callback, context)
    request.send()


def download_json(
    message: Soup.Message,
    cancellable: Gio.Cancellable,
    callback: Callable[[Soup.Message, JsonDict | None, Any], None],
    context: Any,
    failure_callback: FailureCallback | None = None,
):
    def cb(message: Soup.Message, result: Any, _d):
        try:
            callback(message, json.loads(result), context)
        except (ValueError, JSONDecodeError):
            callback(message, None, context)

    download(message, cancellable, cb, None, True, failure_callback=failure_callback)


session = Soup.Session()
ua_string = f"Quodlibet/{VERSION} (+{WEBSITE})"
session.set_properties(user_agent=ua_string, timeout=15)
