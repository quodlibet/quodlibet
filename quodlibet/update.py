# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Check for new versions of the application

For each "build type" (basically each bundle/installer) we host
an (sparkle appcast) rss feed on quodlibet.github.io.
We download it and compare versions...

Since there can be multiple builds per release for the same release type
(e.g. the installer was broken and had to be redone) the build version
is used and not the release version.
"""

from urllib.request import urlopen

from gi.repository import Gtk
import feedparser

import quodlibet
from quodlibet import _, util
from quodlibet.build import BUILD_TYPE
from quodlibet.qltk.window import Dialog
from quodlibet.util.dprint import print_exc
from quodlibet.util import escape
from quodlibet.util.thread import call_async, Cancellable


class UpdateError(Exception):
    pass


def parse_version(version_string):
    """Might raise ValueError"""

    return tuple(map(int, version_string.split(".")))


def format_version(version_tuple):
    return ".".join(map(str, version_tuple))


def fetch_versions(build_type, timeout=5.0):
    """Fetches the list of available releases and returns a list
    of version tuples. Sorted and oldest version first. The list
    might be empty. Also returns an URL to the download page.

    Args:
        build_type (text): the build type. e.g. "default" or "windows"
        timeout (float): timeout in seconds

    Thread safe.

    Raises UpdateError
    """

    try:
        content = urlopen(
            "https://quodlibet.github.io/appcast/%s.rss" % build_type, timeout=timeout
        ).read()
    except Exception as error:
        raise UpdateError(error) from error

    d = feedparser.parse(content)
    if d.bozo:
        raise UpdateError(d.bozo_exception)

    try:
        link = d.feed.link
        enclosures = [e for entry in d.entries for e in entry.enclosures]
    except AttributeError as error:
        raise UpdateError(error) from error

    try:
        versions = [parse_version(en.version) for en in enclosures]
    except ValueError as error:
        raise UpdateError(error) from error

    return sorted(versions), link


class UpdateDialog(Dialog):
    def __init__(self, parent):
        super().__init__(
            title=_("Checking for Updates"), use_header_bar=True, modal=True
        )

        self.set_default_size(380, 110)
        self.set_transient_for(parent)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.set_default_response(Gtk.ResponseType.CANCEL)

        content = self.get_content_area()
        self._stack = Gtk.Stack(border_width=10)
        self._stack.set_transition_duration(500)
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        content.pack_start(self._stack, True, True, 0)
        content.show_all()

        spinner = Gtk.Spinner()
        spinner.start()
        self._set_widget(spinner)

    def run(self):
        def do_fetch_versions():
            try:
                return fetch_versions(BUILD_TYPE)
            except UpdateError:
                print_exc()
                return None

        cancel = Cancellable()
        self.connect("response", self._on_response, cancel)
        call_async(do_fetch_versions, cancel, self._on_result)

        return super().run()

    def _on_result(self, args):
        if args is None or not args[0]:
            text = _("Connection failed")
        else:
            versions, url = args
            version = quodlibet.get_build_version()

            def f(v):
                return util.bold(format_version(v))

            if version >= versions[-1]:
                text = _("You are already using the newest version " "%(version)s") % {
                    "version": f(version)
                }
            else:
                text = _(
                    "A new version %(new-version)s is available\n\n"
                    "You are currently using version %(old-version)s\n\n"
                    "Visit the <a href='%(url)s'>website</a>"
                ) % {
                    "new-version": f(versions[-1]),
                    "old-version": f(version),
                    "url": escape(url),
                }

        self._set_widget(
            Gtk.Label(
                label=text, use_markup=True, wrap=True, justify=Gtk.Justification.CENTER
            )
        )

        button = self.get_widget_for_response(Gtk.ResponseType.CANCEL)
        button.set_label(_("_Close"))

    def _set_widget(self, widget):
        old = self._stack.get_visible_child()
        self._stack.add(widget)
        widget.show()
        self._stack.set_visible_child(widget)
        if old:
            old.destroy()

    def _on_response(self, dialog, response_id, cancel):
        cancel.cancel()
