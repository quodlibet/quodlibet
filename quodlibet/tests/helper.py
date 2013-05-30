# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import contextlib

from gi.repository import Gtk


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

    if toplevel is None:
        window = Gtk.Window()
        window.add(widget)

    widget.realize()
    while Gtk.events_pending():
        Gtk.main_iteration()
    assert widget.get_realized()
    yield widget

    if toplevel is None:
        window.remove(widget)
        window.destroy()

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
    window.hide()

    if toplevel is None:
        window.remove(widget)
        window.destroy()

    while Gtk.events_pending():
        Gtk.main_iteration()
