# -*- coding: utf-8 -*-
# Copyright 2013 Simonas Kazlauskas
#        2016-17 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import json

from gi.repository import Soup, Gio, GLib, GObject
from gi.repository.GObject import ParamFlags, SignalFlags

if not hasattr(Gio.MemoryOutputStream, 'new_resizable'):
    raise ImportError(
        'GLib and gobject-introspection libraries are too old. GLib since ' +
        '2.36 and gobject-introspection since 1.36 are known to work fine.')

from quodlibet.const import VERSION, WEBSITE
from quodlibet.util import print_d, print_w


PARAM_READWRITECONSTRUCT = \
    ParamFlags.CONSTRUCT_ONLY | ParamFlags.READABLE | ParamFlags.WRITABLE
SoupStatus = Soup.Status if hasattr(Soup, 'Status') else Soup.KnownStatusCode


class DefaultHTTPRequest(GObject.Object):
    """
    Class encapsulating a single HTTP request. These are meant to be sent
    and received only once. Behaviour is undefined otherwise.
    """

    __gsignals__ = {
        # Successes
        'sent': (SignalFlags.RUN_LAST, None, (Soup.Message,)),
        'received': (SignalFlags.RUN_LAST, None, (Gio.OutputStream,)),
        # Failures
        'send-failure': (SignalFlags.RUN_LAST, None, (object,)),
        'receive-failure': (SignalFlags.RUN_LAST, None, (object,)),
        # Common failure signal which will be emitted when either of above
        # failure signals are.
        'failure': (SignalFlags.RUN_LAST, None, (object,)),
    }

    message = GObject.Property(type=Soup.Message,
                               flags=PARAM_READWRITECONSTRUCT)
    cancellable = GObject.Property(type=Gio.Cancellable,
                                   flags=PARAM_READWRITECONSTRUCT)
    istream = GObject.Property(type=Gio.InputStream, default=None)
    ostream = GObject.Property(type=Gio.OutputStream, default=None)

    def __init__(self, message, cancellable):
        if message is None:
            raise ValueError('Message may not be None')

        inner_cancellable = Gio.Cancellable()
        super(DefaultHTTPRequest, self).__init__(message=message,
                                                 cancellable=inner_cancellable)
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
        """
        print_d('Sending {1} request to {0}'.format(self._uri,
                                                    self.message.method))
        session.send_async(self.message, self.cancellable, self._sent, None)

    def _sent(self, session, task, data):
        try:
            status = int(self.message.get_property('status-code'))
            if status >= 400:
                msg = 'HTTP {0} error in {1} request to {2}'.format(
                    status, self.message.method, self._uri)
                print_w(msg)
                return self.emit('send-failure', Exception(msg))
            self.istream = session.send_finish(task)
            print_d('Sent {1} request to {0}'.format(self._uri,
                                                     self.message.method))
            self.emit('sent', self.message)
        except GLib.GError as e:
            print_w('Failed sending request to {0} ({1})'.format(self._uri, e))
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
            session.cancel_message(self.message, SoupStatus.CANCELLED)

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
            raise RuntimeError('Cannot receive unsent request')
        if not self.ostream:
            raise RuntimeError('Cannot receive request without output stream')
        if self._receive_started:
            raise RuntimeError('Can receive only once')
        self._receive_started = True

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


class FallbackHTTPRequest(DefaultHTTPRequest):
    """
    Fallback code which does not use Gio.InputStream based APIs which are
    not available before libsoup 2.44 introspection.

    To be used with Soup.SessionAsync instead of regular Soup.Session.

    Unlike DefaultHTTPRequest, keeps downloaded content in memory until
    the request is completed. Also it keeps downloading the content even if
    receive function is not called (it does, however, stop if the request is
    cancelled).
    """
    _is_done = False

    def send(self):
        print_d('Sending request to {0}'.format(self._uri))
        self.message.get_property('response-body').set_accumulate(False)
        session.queue_message(self.message, lambda *x: None, None)
        self.message.connect('got-headers', self._sent)
        self.message.connect('finished', self._finished)

    def _sent(self, message):
        if self.cancellable.is_cancelled():
            return self.emit('send-failure', Exception('Cancelled'))
        if 300 <= message.get_property('status-code') < 400:
            return # redirection, wait for another emission of got-headers
        self.istream = Gio.MemoryInputStream()
        self.message.connect('got-chunk', self._chunk)
        self.emit('sent', self.message)

    def _chunk(self, message, buffer):
        self.istream.add_bytes(buffer.get_as_bytes())

    def _finished(self, *args):
        self._is_done = True
        self.notify('istream')

    def receive(self):
        def do_receive(*args):
            self.disconnect(istr_id)
            super(FallbackHTTPRequest, self).receive()
        istr_id = 0
        if not self._is_done and self.istream:
            istr_id = self.connect('notify::istream', do_receive)
        else:
            do_receive()

    def cancel(self):
        if self.cancellable.is_cancelled():
            return False
        session.cancel_message(self.message, SoupStatus.CANCELLED)
        super(FallbackHTTPRequest, self).cancel()


def download(message, cancellable, callback, data, try_decode=False):
    def received(request, ostream):
        ostream.close(None)
        bs = ostream.steal_as_bytes().get_data()
        if not try_decode:
            callback(message, bs, data)
            return
        # Otherwise try to decode data
        code = int(message.get_property('status-code'))
        if code >= 400:
            print_w("HTTP %d error received on %s" % (code, request._uri))
            return
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


if hasattr(Soup.Session, 'send_finish'):
    # We're using Soup >= 2.44
    session = Soup.Session()
    HTTPRequest = DefaultHTTPRequest
else:
    print_d('Using fallback HTTPRequest implementation. libsoup is too old')
    session = Soup.SessionAsync()
    HTTPRequest = FallbackHTTPRequest

ua_string = "Quodlibet/{0} (+{1})".format(VERSION, WEBSITE)
session.set_properties(user_agent=ua_string, timeout=15)
