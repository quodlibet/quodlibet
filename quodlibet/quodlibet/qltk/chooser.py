# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import contextlib

from gi.repository import Gtk
from senf import fsnative, path2fsn, fsn2bytes, bytes2fsn

from quodlibet import _
from quodlibet import config
from quodlibet.qltk import get_top_parent, gtk_version
from quodlibet.util.path import fsn2glib, glib2fsn, get_home_dir
from quodlibet.util import is_windows


def _get_chooser(accept_label, cancel_label):
    """
    Args:
        accept_label (text_type)
        cancel_label (text_type)
    Returns:
        Gtk.FileChooser
    """

    if hasattr(Gtk, "FileChooserNative"):
        FileChooser = Gtk.FileChooserNative
    else:
        FileChooser = Gtk.FileChooserDialog

    # https://github.com/quodlibet/quodlibet/issues/2406
    if is_windows() and gtk_version < (3, 22, 16):
        FileChooser = Gtk.FileChooserDialog

    chooser = FileChooser()

    if hasattr(chooser, "set_accept_label"):
        chooser.set_accept_label(accept_label)
    else:
        chooser.add_button(accept_label, Gtk.ResponseType.ACCEPT)
        chooser.set_default_response(Gtk.ResponseType.ACCEPT)

    if hasattr(chooser, "set_cancel_label"):
        chooser.set_cancel_label(cancel_label)
    else:
        chooser.add_button(cancel_label, Gtk.ResponseType.CANCEL)

    return chooser


_response = None


@contextlib.contextmanager
def with_response(resp):
    # for testing
    global _response

    _response = resp
    yield
    _response = None


def _run_chooser(parent, chooser):
    """Run the chooser ("blocking") and return a list of paths.

    Args:
        parent (Gtk.Widget)
        chooser (Gtk.FileChooser)
    Returns:
        List[fsnative]
    """

    chooser.set_current_folder(fsn2glib(get_current_dir()))
    chooser.set_transient_for(get_top_parent(parent))

    if _response is not None:
        response = _response
        while Gtk.events_pending():
            Gtk.main_iteration()
    else:
        response = chooser.run()

    if response == Gtk.ResponseType.ACCEPT:
        result = [glib2fsn(fn) for fn in chooser.get_filenames()]

        current_dir = chooser.get_current_folder()
        if current_dir:
            set_current_dir(glib2fsn(current_dir))
    else:
        result = []
    chooser.destroy()
    return result


def find_nearest_dir(path):
    """Given a path return the closes existing directory. Either itself
    or a parent. In case it can't find one it returns None.

    Returns:
        fsnative or None
    """

    path = os.path.abspath(path)

    def is_ok(p):
        return os.path.exists(p) and os.path.isdir(p)

    while not is_ok(path):
        dirname = os.path.dirname(path)
        if dirname == path:
            return None
        path = dirname

    return path


def get_current_dir():
    """Returns the currently active chooser directory path.
    The path might not actually exist.

    Returns:
        fsnative
    """

    data = config.getbytes("memory", "chooser_dir", b"")
    try:
        path = bytes2fsn(data, "utf-8") or None
    except ValueError:
        path = None

    # the last user dir might not be there any more, try showing a parent
    # instead
    if path is not None:
        path = find_nearest_dir(path)

    if path is None:
        path = get_home_dir()

    return path


def set_current_dir(path):
    """Set the current chooser directory.

    Args:
        path (fsnative)
    """

    assert isinstance(path, fsnative)
    data = fsn2bytes(path, "utf-8")
    config.setbytes("memory", "chooser_dir", data)


def create_chooser_filter(name, patterns):
    """Create a Gtk.FileFilter that also works on Windows

    Args:
        name (text_type): The name of the filter
        patterns (List[pathlike]): A list of glob patterns
    Returns:
        Gtk.FileFilter
    """

    # The Windows FileChooserNative implementation only supports patterns
    filter_ = Gtk.FileFilter()
    filter_.set_name(name)
    for pattern in sorted(set(patterns)):
        filter_.add_pattern(fsn2glib(path2fsn(pattern)))
    return filter_


def choose_folders(parent, title, action_title):
    """Opens a folder chooser widget and returns a list of folders selected.

    Args:
        parent (Gtk.Widget)
        title (text_type): The window title
        action_title (text_type): The button title
    Returns:
        List[fsnative]
    """

    chooser = _get_chooser(action_title, _("_Cancel"))
    chooser.set_title(title)
    chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
    chooser.set_local_only(True)
    chooser.set_select_multiple(True)

    return _run_chooser(parent, chooser)


def choose_files(parent, title, action_title, filter_=None):
    """Opens a folder chooser widget and returns a list of folders selected.

    Args:
        parent (Gtk.Widget)
        title (text_type): The window title
        action_title (text_type): The button title
        filter_ (Gtk.FileFilter or None)
    Returns:
        List[fsnative]
    """

    chooser = _get_chooser(action_title, _("_Cancel"))
    chooser.set_title(title)
    chooser.set_action(Gtk.FileChooserAction.OPEN)
    chooser.set_local_only(True)
    chooser.set_select_multiple(True)

    if filter_ is not None:
        chooser.add_filter(filter_)

    return _run_chooser(parent, chooser)


def choose_target_file(parent, title, action_title, name_suggestion=None):
    """Opens a file chooser for saving a file.

    Args:
        parent (Gtk.Widget)
        title (text_type): The window title
        action_title (text_type): The button title
        name_suggestion (text_type): The suggested file name (not fsnative)
    Returns:
        fsnative or None
    """

    chooser = _get_chooser(action_title, _("_Cancel"))
    chooser.set_title(title)
    chooser.set_action(Gtk.FileChooserAction.SAVE)
    chooser.set_local_only(True)
    if name_suggestion is not None:
        chooser.set_current_name(name_suggestion)

    result = _run_chooser(parent, chooser)
    if result:
        return result[0]


def choose_target_folder(parent, title, action_title, name_suggestion=None):
    """Opens a file chooser for saving a file.

    Args:
        parent (Gtk.Widget)
        title (text_type): The window title
        action_title (text_type): The button title
        name_suggestion (text_type): The suggested folder name (not fsnative)
    Returns:
        fsnative or None
    """

    chooser = _get_chooser(action_title, _("_Cancel"))
    chooser.set_title(title)
    chooser.set_action(Gtk.FileChooserAction.CREATE_FOLDER)
    chooser.set_local_only(True)
    if name_suggestion is not None:
        chooser.set_current_name(name_suggestion)

    result = _run_chooser(parent, chooser)
    if result:
        return result[0]
