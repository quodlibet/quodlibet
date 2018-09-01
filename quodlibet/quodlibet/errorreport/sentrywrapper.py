# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
A wrapper API for sentry-raven to make it work in a GUI environment.

We need to split the capturing phase from the submit phase so we can show
the report to the user and provide feedback about the report submit process.
This hacks it together while trying to not touch too many raven internals.

It also only imports raven when needed since it takes quite a lot of time
to import.
"""

import os
import pprint
from urllib.parse import urlencode

from quodlibet.util.urllib import Request, urlopen


class SentryError(Exception):
    """Exception type for all the API below"""

    pass


def send_feedback(dsn, event_id, name, email, comment, timeout):
    """Send feedback, blocking.

    Args:
        dsn (str): The DSN
        event_id (str): The event ID this feedback should be attached to
        name (str): The user name
        email (str): The user email
        comment (str): The feedback text
        timeout (float): The timeout for this request
    Raises:
        SentryError: In case of timeout or other errors
    """

    name = str(name).encode("utf-8")
    email = str(email).encode("utf-8")
    comment = str(comment).encode("utf-8")

    data = urlencode(
        [('name', name), ('email', email), ('comments', comment)])
    if not isinstance(data, bytes):
        # py3
        data = data.encode("utf-8")

    headers = {"Referer": "https://quodlibet.github.io"}
    params = urlencode([("dsn", dsn), ("eventId", event_id)])

    try:
        req = Request(
            "https://sentry.io/api/embed/error-page/?" + params,
            data=data, headers=headers)

        urlopen(req, timeout=timeout).close()
    except EnvironmentError as e:
        raise SentryError(e)


def urlopen_hack(**kwargs):
    # There is no way to make raven use the system cert store. This makes
    # it use the standard urlopen instead.
    url = kwargs["url"]
    data = kwargs["data"]
    timeout = kwargs["timeout"]
    return urlopen(url, data, timeout)


class CapturedException(object):
    """Contains the data to be send to sentry."""

    def __init__(self, dsn, data):
        """
        Args:
            dsn (str): the sentry.io DSN
            data (object): some sentry internals
        """

        self._dsn = dsn
        self._args, self._kwargs = data
        self._comment = None

    def get_report(self):
        """Gives a textual representation of the collected data.

        The goal is to give the user a way to see what is being send to the
        sentry servers.

        Returns:
            str
        """

        lines = []
        if self._args:
            lines += pprint.pformat(self._args, width=40).splitlines()
        if self._kwargs:
            lines += pprint.pformat(self._kwargs, width=40).splitlines()

        def compact(l):
            level = len(l) - len(l.lstrip())
            return u" " * (level // 4) + l.lstrip()

        return u"\n".join(map(compact, lines))

    def set_comment(self, comment):
        """Attach a user provided comment to the error.
        Something like "I clicked button X and then this happened"

        Args:
            comment (str)
        """

        self._comment = comment

    def send(self, timeout):
        """Submit the error including the user feedback. Blocking.

        Args:
            timeout (float): timeout for each request made
        Returns:
            str: The sentry event id
        Raises:
            SentryError
        """

        from raven import Client
        from raven.transport import http
        from raven.transport.http import HTTPTransport

        http.urlopen = urlopen_hack

        try:
            raise Exception
        except Exception:
            client = Client(
                self._dsn + "?timeout=%d" % timeout, install_sys_hook=False,
                install_logging_hook=False, capture_locals=False,
                transport=HTTPTransport)

            # replace the captured data with the one we already have
            old_send = client.send

            def inject_data(*args, **kwargs):
                kw = dict(self._kwargs)
                kw["event_id"] = kwargs.get("event_id", "")
                return old_send(*self._args, **kw)

            client.send = inject_data

            event_id = client.captureException()
            if client.state.did_fail():
                raise SentryError("captureException failed")

            # fix leak
            client.context.deactivate()

            if self._comment:
                send_feedback(self._dsn, event_id,
                              "default", "email@example.com", self._comment,
                              timeout)

            return event_id


class Sentry(object):
    """The main object of our sentry API wrapper"""

    def __init__(self, dsn):
        """
        Args:
            dsn (str)
        """

        self._dsn = dsn
        self._tags = {}

    def add_tag(self, key, value):
        """Attach tags to the error report.

        Args:
            key (str)
            value (str)

        The keys are arbitrary, but some have a special meaning:

        * "release" will show up as a separate page in sentry
        * "environment" will add a dropdown for grouping
        """

        self._tags[key] = value

    def capture(self, exc_info=None, fingerprint=None):
        """Captures the current exception and returns a CapturedException

        The returned object contains everything needed to submit the error
        at a later point in time (e.g. after pushing it to the main thread
        and displaying it in the UI)

        Args:
            exc_info (tuple): a sys.exc_info() return value
            fingerprint (List[str] or None):
                fingerprint for custom grouping
        Returns:
            CapturedException
        Raises:
            SentryError: Raised if raven isn't installed or capturing failed
                for some unknown reason.
        """

        try:
            from raven import Client
            from raven.transport import Transport
            from raven.processors import Processor
        except ImportError as e:
            raise SentryError(e)

        class DummyTransport(Transport):
            """A sync raven transport which does nothing"""

            def send(self, *args, **kwargs):
                pass

        # Some tags have a special meaning and conflict with info given to the
        # client, so pass them to the client instead
        tags = dict(self._tags)
        kwargs = {}
        if "release" in tags:
            kwargs["release"] = tags.pop("release")
        if "environment" in tags:
            kwargs["environment"] = tags.pop("environment")
        if "server_name" in tags:
            kwargs["name"] = tags.pop("server_name")

        # It would default to the hostname otherwise
        kwargs.setdefault("name", "default")

        # We use a dummy transport and intercept the captured data
        client = Client(
            self._dsn, install_sys_hook=False, install_logging_hook=False,
            capture_locals=True, transport=DummyTransport, tags=tags, **kwargs)

        data = [None]

        old_send = client.send

        def save_state(*args, **kwargs):
            data[0] = (args, kwargs)
            return old_send(*args, **kwargs)

        client.send = save_state
        client.captureException(exc_info, fingerprint=fingerprint)
        if data[0] is None:
            raise SentryError("Failed to capture")

        class SanitizePaths(Processor):
            """Makes filename on Windows match the Linux one.
            Also adjust abs_path, so it still contains filename.
            """

            def filter_stacktrace(self, data, **kwargs):
                for frame in data.get('frames', []):
                    if frame.get("abs_path"):
                        frame["abs_path"] = \
                            frame["abs_path"].replace(os.sep, "/")
                    if frame.get("filename"):
                        frame["filename"] = \
                            frame["filename"].replace(os.sep, "/")

        SanitizePaths(client).process(data[0][1])

        # fix leak
        client.context.deactivate()

        return CapturedException(self._dsn, data[0])
