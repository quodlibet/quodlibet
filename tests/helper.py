# Copyright 2013 Christoph Reiter
#           2015 Anton Shestakov
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import contextlib
import sys
import shutil
import locale
import errno
from io import StringIO

from gi.repository import Gtk, Gdk

from quodlibet.util.i18n import GlibTranslations
from senf import fsnative, environ

from quodlibet.qltk import find_widgets, get_primary_accel_mod
from quodlibet.util.path import normalize_path


def dummy_path(path):
    path = fsnative(path)
    if os.name == "nt":
        return normalize_path(u"z:\\" + path.replace(u"/", u"\\"))
    return path


@contextlib.contextmanager
def locale_numeric_conv(
        decimal_point=".", grouping=[3, 3, 0], thousands_sep=","):
    """Temporarely change number formatting conventions.

    By default this uses en_US conventions.
    """

    # XXX: locale internals
    override = locale._override_localeconv
    old = override.copy()
    try:
        override["decimal_point"] = decimal_point
        override["grouping"] = grouping
        override["thousands_sep"] = thousands_sep
        yield
    finally:
        override.clear()
        override.update(old)


def _send_key_click_event(widget, **kwargs):
    """Returns True if the event was handled"""

    assert widget.get_realized()
    assert widget.get_visible()

    ev = Gdk.Event()
    ev.any.window = widget.get_window()

    for key, value in kwargs.items():
        assert hasattr(ev.key, key)
        setattr(ev.key, key, value)

    ev.any.type = Gdk.EventType.KEY_PRESS
    handled = widget.event(ev)
    ev.any.type = Gdk.EventType.KEY_RELEASE
    handled |= widget.event(ev)
    return handled


def send_key_click(widget, accel, recursive=False):
    """Send a key press and release event to a widget or
    to all widgets in the hierarchy if recursive is True.

    The widget has to be visible for this to work, so this is needed:

    with visible(widget):
        send_key_click(widget, "<ctrl>a")

    Returns how often the event was handled.
    """

    key, mods = Gtk.accelerator_parse(accel)
    assert key is not None
    assert mods is not None

    assert isinstance(widget, Gtk.Widget)
    handled = _send_key_click_event(widget, state=mods, keyval=key)

    if recursive:
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                handled += send_key_click(child, accel, recursive)

    return handled


def _send_button_click_event(widget, **kwargs):
    """Returns True if the event was handled"""

    assert widget.get_realized()
    assert widget.get_visible()

    ev = Gdk.Event()
    window = widget.get_window()
    ev.any.window = window

    ev.button.x = window.get_width() / 2.0
    ev.button.y = window.get_height() / 2.0

    for key, value in kwargs.items():
        assert hasattr(ev.button, key)
        setattr(ev.button, key, value)

    ev.any.type = Gdk.EventType.BUTTON_PRESS
    handled = widget.event(ev)
    ev.any.type = Gdk.EventType.BUTTON_RELEASE
    handled |= widget.event(ev)
    return handled


def send_button_click(widget, button, primary=False, shift=False,
                      recursive=False):
    """See send_key_click_event"""

    state = Gdk.ModifierType(0)
    if primary:
        state |= get_primary_accel_mod()
    if shift:
        state |= Gdk.ModifierType.SHIFT_MASK

    assert isinstance(widget, Gtk.Widget)
    handled = _send_button_click_event(widget, button=button, state=state)

    if recursive:
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                handled += send_button_click(
                    child, button, primary, shift, recursive)

    return handled


@contextlib.contextmanager
def realized(widget):
    """Makes sure the widget is realized.

    view = Gtk.TreeView()
    with realized(view):
        do_something(view)
    """

    own_window = False
    toplevel = widget.get_toplevel()
    if not isinstance(toplevel, Gtk.Window):
        window = Gtk.Window(type=Gtk.WindowType.POPUP)
        window.add(widget)
        own_window = True
    else:
        window = toplevel

    # realize all widgets without showing them
    for sub in find_widgets(window, Gtk.Widget):
        sub.realize()
    widget.realize()
    while Gtk.events_pending():
        Gtk.main_iteration()
    assert widget.get_realized()
    assert window.get_realized()
    yield widget

    if own_window:
        window.remove(widget)
        window.destroy()

    while Gtk.events_pending():
        Gtk.main_iteration()


@contextlib.contextmanager
def visible(widget, width=None, height=None):
    """Makes sure the widget is visible.

    view = Gtk.TreeView()
    with visible(view):
        do_something(view)
    """

    own_window = False
    toplevel = widget.get_toplevel()
    if not isinstance(toplevel, Gtk.Window):
        window = Gtk.Window(type=Gtk.WindowType.POPUP)
        window.add(widget)
        own_window = True
    else:
        window = toplevel

    if width is not None and height is not None:
        window.resize(width, height)

    window.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()
    assert widget.get_visible()
    assert window.get_visible()
    yield widget
    while Gtk.events_pending():
        Gtk.main_iteration()
    window.hide()

    if own_window:
        window.remove(widget)
        window.destroy()

    while Gtk.events_pending():
        Gtk.main_iteration()


@contextlib.contextmanager
def preserve_environ():
    old = environ.copy()
    yield
    # don't touch existing values as os.environ is broken for empty
    # keys on Windows: http://bugs.python.org/issue20658
    for key, value in list(environ.items()):
        if key not in old:
            del environ[key]
    for key, value in old.items():
        if key not in environ or environ[key] != value:
            environ[key] = value


@contextlib.contextmanager
def capture_output():
    """
    with capture_output() as (stdout, stderr):
        some_action()
    print stdout.getvalue(), stderr.getvalue()
    """

    err = StringIO()
    out = StringIO()
    old_err = sys.stderr
    old_out = sys.stdout
    sys.stderr = err
    sys.stdout = out

    try:
        yield (out, err)
    finally:
        sys.stderr = old_err
        sys.stdout = old_out


@contextlib.contextmanager
def temp_filename(*args, **kwargs):
    """Creates an empty file and removes it when done.

        with temp_filename() as filename:
            with open(filename, 'w') as h:
                h.write("foo")
            do_stuff(filename)
    """

    from tests import mkstemp

    fd, filename = mkstemp(*args, **kwargs)
    os.close(fd)

    yield filename

    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def get_temp_copy(path):
    """Returns a copy of the file with the same extension"""

    from tests import mkstemp

    ext = os.path.splitext(path)[-1]
    fd, filename = mkstemp(suffix=ext)
    os.close(fd)
    shutil.copy(path, filename)
    return filename


class ListWithUnused:
    """ This class stores a set of elements and provides the interface to check
        if it contains an arbitrary element, and then to know if some of the
        elements stored were never accessed.

        Some tests use this class to store whitelisted/blacklisted things that
        are deemed acceptable, but would trigger those tests if they weren't
        made special cases (e.g.  UI messages that conform to a particular
        writing style, but can't be tested automatically). Since such
        whitelists reside in tests and not in the code that produces those
        special cases, it's easy to change (fix) the code and then forget to
        remove the special case from tests, leaving it there to never be used
        again.

        This class then provides a way to see if such particular element
        doesn't actually need to be in the whitelist anymore.
    """
    def __init__(self, *args):
        self.store = set(args)
        self.unused = set(args)

    def __contains__(self, item):
        self.unused.discard(item)
        return item in self.store

    def check_unused(self):
        if self.unused:
            from quodlibet import print_w
            print_w('ListWithUnused has unused items: %s' % self.unused)


def __(message):
    """See `quodlibet._`. Avoids triggering PO scanners"""
    t = GlibTranslations()
    return t.wrap_text(t.ugettext(message))
