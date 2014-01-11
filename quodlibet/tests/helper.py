# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import contextlib
import StringIO
import sys

from gi.repository import Gtk

from quodlibet.qltk import find_widgets


@contextlib.contextmanager
def realized(widget):
    """Makes sure the widget is realized.

    view = Gtk.TreeView()
    with realized(view):
        do_something(view)
    """

    if isinstance(widget, Gtk.Window):
        toplevel = widget
    else:
        toplevel = widget.get_parent_window()

    new_window = None

    if toplevel is None:
        toplevel = Gtk.Window()
        toplevel.add(widget)
        new_window = toplevel

    # realize all widgets without showing them
    for sub in find_widgets(toplevel, Gtk.Widget):
        sub.realize()
    widget.realize()
    while Gtk.events_pending():
        Gtk.main_iteration()
    assert widget.get_realized()
    assert toplevel.get_realized()
    yield widget

    if new_window is not None:
        new_window.remove(widget)
        new_window.destroy()

    while Gtk.events_pending():
        Gtk.main_iteration()


@contextlib.contextmanager
def visible(widget, width=None, height=None):
    """Makes sure the widget is realized.

    view = Gtk.TreeView()
    with visible(view):
        do_something(view)
    """

    if isinstance(widget, Gtk.Window):
        toplevel = widget
    else:
        toplevel = widget.get_parent_window()

    if toplevel is None:
        window = Gtk.Window()
        window.add(widget)

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

    if toplevel is None:
        window.remove(widget)
        window.destroy()

    while Gtk.events_pending():
        Gtk.main_iteration()


@contextlib.contextmanager
def capture_output():
    """
    with capture_output as (stdout, stderr):
        some_action()
    print stdout.getvalue(), stderr.getvalue()
    """

    err = StringIO.StringIO()
    out = StringIO.StringIO()
    old_err = sys.stderr
    old_out = sys.stdout
    sys.stderr = err
    sys.stdout = out

    try:
        yield (out, err)
    finally:
        sys.stderr = old_err
        sys.stdout = old_out
