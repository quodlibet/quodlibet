# -*- coding: utf-8 -*-
# Copyright 2013 Simonas Kazlauskas
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
import json

from gi.repository import Soup, Gio, GLib, GObject

from quodlibet.const import VERSION, WEBSITE


session = Soup.Session.new()
ua_string = "Quodlibet/{0} (+{1})".format(VERSION, WEBSITE)
session.set_properties(user_agent=ua_string, timeout=15)

PARAM_READWRITECONSTRUCT = GObject.PARAM_CONSTRUCT_ONLY \
                         | GObject.PARAM_READWRITE


class HTTPRequest(GObject.Object):
    """
    Class encapsulating a single HTTP request. These are meant to be sent
    and received only once. Behaviour is undefined otherwise.
    """

    __gsignals__ = {
        # Successes
        'sent': (GObject.SignalFlags.RUN_LAST, None, (Soup.Message,)),
        'received': (GObject.SignalFlags.RUN_LAST, None, (Gio.OutputStream,)),
        # Failures
        'send-failure': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'receive-failure': (GObject.SignalFlags.RUN_LAST, None, (object,)),
        # Common failure signal which will be emited when either of above
        # failure signals are.
        'failure': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    message = GObject.property(type=Soup.Message,
                               flags=PARAM_READWRITECONSTRUCT)
    cancellable = GObject.property(type=Gio.Cancellable,
                                   flags=PARAM_READWRITECONSTRUCT)
    istream = GObject.property(type=Gio.InputStream, default=None)
    ostream = GObject.property(type=Gio.OutputStream, default=None)

    def __init__(self, message, cancellable):
        if message is None:
            raise ValueError('Message may not be None')

        super(HTTPRequest, self).__init__(message=message,
                                          cancellable=Gio.Cancellable.new())
        if cancellable is not None:
            cancellable.connect(lambda *x: self.cancel(), None)

        self.connect('send-failure', lambda r, e: r.emit('failure', e))
        self.connect('receive-failure', lambda r, e: r.emit('failure', e))

        # For simple access
        self._receive_started = False
        self._uri = self.message.get_uri().to_string(False)

    def send(self):
        """
        Send the request and receive HTTP headers. Some of the body might
        get downloaded too.

        Will return True if the request was actually sent. In the case of
        False one is to assume no activity from this specific instance of
        HTTPRequest.
        """
        print_d('Sending request to {0}'.format(self._uri))
        session.send_async(self.message, self.cancellable, self._sent, None)

    def _sent(self, session, task, data):
        try:
            self.istream = session.send_finish(task)
            print_d('Sent request to {0}'.format(self._uri))
            self.emit('sent', self.message)
        except GLib.GError as e:
            print_w('Failed sending request to {0}'.format(self._uri))
            self.emit('send-failure', e)

    def provide_target(self, stream):
        if not stream:
            raise ValueError('Provided stream may not be None')
        if not self.ostream:
            self.ostream = stream
        else:
            raise RuntimeError('Only one output stream may be provided')

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
            # Read contents from input stream (because otherwise in Soup
            # <2.44.1, unread data will leak into the next request and it will
            # become unparsable.
            if not self.istream.is_closed():
                while self.istream.read_bytes(512, None).get_size():
                    pass
                self.istream.close(None)
        else:
            session.cancel_message(self.message, Soup.Status.CANCELLED)

    def receive(self):
        """
        Receive data from the request into provided output stream. The request
        must be already sent, therefore this function will be usually called
        from the 'sent' signal handler.

        With completion of data receival HTTPRequest lifetime is ended and
        inner resources are cleaned up (except persistent connections that are
        part of session, not request).

        .. note::
        Be sure to clean up resources you've allocated yourself (e.g. close
        GOutputStreams, delete files on failure et cetera).
        """
        if self._receive_started:
            raise RuntimeError('Can receive only once')
        self._receive_started = True
        if not self.istream:
            raise RuntimeError('Cannot receive unsent request')
        if not self.ostream:
            raise RuntimeError('Cannot receive request without output stream')

        def spliced(ostream, task, data):
            try:
                ostream.splice_finish(task)
                self.istream.close(None)
                self.emit('received', ostream)
            except GLib.GError as e:
                while self.istream.read_bytes(512, None).get_size():
                    pass
                self.istream.close(None)
                self.emit('receive-failure', e)

        # Do not ask splice to close the stream as Soup gets confused and
        # doesn't close connections
        # https://bugzilla.gnome.org/show_bug.cgi?id=711260
        flags = Gio.OutputStreamSpliceFlags.NONE
        self.ostream.splice_async(self.istream, flags, GLib.PRIORITY_DEFAULT,
                                  self.cancellable, spliced, None)


def download(message, cancellable, callback, data, try_decode=False):
    def received(request, ostream):
        ostream.close(None)
        bs = ostream.steal_as_bytes().get_data()
        if not try_decode:
            callback(message, bs, data)
            return
        #otherwise try to decode data
        ctype = message.get_property('response-headers').get_content_type()
        encoding = ctype[1].get('charset', 'utf-8')
        try:
            callback(message, bs.decode(encoding), data)
        except UnicodeDecodeError:
            callback(message, bs, data)

    request = HTTPRequest(message, cancellable)
    request.provide_target(Gio.MemoryOutputStream.new_resizable())
    request.connect('received', received)
    request.connect('sent', lambda r, m: r.receive())
    request.send()


def download_json(message, cancellable, callback, data):
    def cb(message, result, d):
        try:
            callback(message, json.loads(result), data)
        except ValueError:
            callback(message, None, data)
    download(message, cancellable, cb, None, True)
