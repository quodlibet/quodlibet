# Copyright 2012,2014 Christoph Reiter
#           2014,2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os

from gi.repository import Gtk, Gdk

from quodlibet import config
from quodlibet.qltk import get_top_parent, is_wayland, gtk_version, is_accel
from quodlibet.qltk.x import Button
from quodlibet.util import DeferredSignal, print_d, print_w
from quodlibet.util import connect_obj, connect_destroy


def on_first_map(window, callback, *args, **kwargs):
    """Calls callback when the passed Gtk.Window is first visible
    on screen or it already is.
    """

    assert isinstance(window, Gtk.Window)

    if window.get_mapped():
        callback(*args, **kwargs)
        return False

    id_ = [0]

    def on_map(*otherargs):
        window.disconnect(id_[0])
        callback(*args, **kwargs)

    id_[0] = window.connect("map", on_map)

    return False


def should_use_header_bar():
    settings = Gtk.Settings.get_default()
    if not settings:
        return False
    if not hasattr(settings.props, "gtk_dialogs_use_header"):
        return False
    return settings.get_property("gtk-dialogs-use-header")


def fix_default_size(width, height):
    # https://bugzilla.gnome.org/show_bug.cgi?id=740922
    if gtk_version < (3, 19):
        # fixed with 3.20:
        #   https://bugzilla.gnome.org/show_bug.cgi?id=756618
        if width != -1:
            width += min((width - 174), 56)
        if height != -1:
            height += 84
    return (width, height)


class Dialog(Gtk.Dialog):
    """A Gtk.Dialog subclass which supports the use_header_bar property
    for all Gtk versions and will ignore it if header bars shouldn't be
    used according to GtkSettings.
    """

    def __init__(self, *args, **kwargs):
        if not should_use_header_bar():
            kwargs.pop("use_header_bar", None)
        super().__init__(*args, **kwargs)

    def get_titlebar(self):
        try:
            # gtk+ >=3.16
            return super().get_titlebar()
        except AttributeError:
            return None

    def set_default_size(self, width, height):
        if self.get_titlebar():
            width, height = fix_default_size(width, height)
        else:
            # In case we don't use a headerbar we have to add an additional
            # row of buttons in the content box. To get roughly the same
            # content height make the window a bit taller.
            if height != -1:
                height += 20
        super().set_default_size(width, height)

    def add_icon_button(self, label, icon_name, response_id):
        """Like add_button() but allows to pass an icon name"""

        button = Button(label, icon_name)
        # file chooser uses grab_default() on this
        button.set_can_default(True)
        button.show()
        self.add_action_widget(button, response_id)
        return button


class Window(Gtk.Window):
    """Base window class the keeps track of all window instances.

    All active instances can be accessed through Window.windows.
    By defining dialog=True as a kwarg binds Escape to close, otherwise
    ^W will close the window.
    """

    windows: list[Gtk.Window] = []
    _preven_inital_show = False

    def __init__(self, *args, **kwargs):
        self._header_bar = None
        dialog = kwargs.pop("dialog", True)
        super().__init__(*args, **kwargs)
        type(self).windows.append(self)
        if dialog:
            # Modal is the only way to center the window on the parent
            # with wayland atm
            if is_wayland():
                self.set_modal(True)
            self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_destroy_with_parent(True)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        connect_obj(self, "destroy", type(self).windows.remove, self)
        self.connect("key-press-event", self._on_key_press)

    def _on_key_press(self, widget, event):
        is_dialog = (self.get_type_hint() == Gdk.WindowTypeHint.DIALOG)

        if (is_dialog and is_accel(event, "Escape")) or (
                not is_dialog and is_accel(event, "<Primary>w")):
            # Do not close the window if we edit a Gtk.CellRendererText.
            # Focus the treeview instead.
            if isinstance(self.get_focus(), Gtk.Entry) and \
                isinstance(self.get_focus().get_parent(), Gtk.TreeView):
                self.get_focus().get_parent().grab_focus()
                return Gdk.EVENT_PROPAGATE
            self.close()
            return Gdk.EVENT_STOP

        if not is_dialog and is_accel(event, "F11"):
            self.toggle_fullscreen()
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def toggle_fullscreen(self):
        """Toggle the fullscreen mode of the window depending on its current
        state. If the windows isn't realized it will switch to fullscreen
        when it does.
        """

        window = self.get_window()
        if not window:
            is_fullscreen = False
        else:
            is_fullscreen = window.get_state() & Gdk.WindowState.FULLSCREEN

        if is_fullscreen:
            self.unfullscreen()
        else:
            self.fullscreen()

    def set_default_size(self, width, height):
        if self._header_bar:
            width, height = fix_default_size(width, height)
        super().set_default_size(width, height)

    def use_header_bar(self):
        """Try to use a headerbar, returns the widget or None in case
        GTK+ is too old or headerbars are disabled (under xfce for example)
        """

        assert not self._header_bar

        if not should_use_header_bar():
            return False

        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        header_bar.show()
        old_title = self.get_title()
        self.set_titlebar(header_bar)
        if old_title is not None:
            self.set_title(old_title)
        self._header_bar = header_bar
        self.set_default_size(*self.get_default_size())
        return header_bar

    def has_close_button(self):
        """Returns True in case we are sure that the window decorations include
        a close button.
        """

        if self.get_type_hint() == Gdk.WindowTypeHint.NORMAL:
            return True

        if os.name == "nt":
            return True

        if sys.platform == "darwin":
            return True

        if self._header_bar is not None:
            return self._header_bar.get_show_close_button()

        return True

    def present(self):
        """A version of present that also works if not called from an event
        handler (there is no active input event).
        See https://bugzilla.gnome.org/show_bug.cgi?id=688830
        """

        try:
            from gi.repository import GdkX11
        except ImportError:
            super().present()
        else:
            window = self.get_window()
            if window and isinstance(window, GdkX11.X11Window):
                timestamp = GdkX11.x11_get_server_time(window)
                self.present_with_time(timestamp)
            else:
                super().present()

    def set_transient_for(self, parent):
        """Set a parent for the window.

        In case parent=None, fall back to the main window.

        """

        is_toplevel = parent and parent.props.type == Gtk.WindowType.TOPLEVEL

        if parent is None or not is_toplevel:
            if parent:
                print_w("Not a toplevel window set for: %r" % self)
            from quodlibet import app
            parent = app.window
        super().set_transient_for(parent)

    @classmethod
    def prevent_inital_show(cls, value):
        cls._preven_inital_show = bool(value)

    def show_maybe(self):
        """Show the window, except if prevent_inital_show() was called and
        this is the first time.

        Returns whether the window was shown.
        """

        if not self._preven_inital_show:
            self.show()
        return not self._preven_inital_show


class PersistentWindowMixin:
    """A mixin for saving/restoring window size/position/maximized state"""

    def enable_window_tracking(self, config_prefix, size_suffix=""):
        """Enable tracking/saving of changes and restore size/pos/maximized.

        Make sure to call set_transient_for() before since position is
        restored relative to the parent in this case.

        config_prefix -- prefix for the config key
                         (prefix_size, prefix_position, prefix_maximized)
        size_suffix -- optional suffix for saving the size. For cases where the
                       window has multiple states with different content sizes.
                       (example: edit tags with one song or multiple)

        """

        self.__state = 0
        self.__name = config_prefix
        self.__size_suffix = size_suffix
        self.__save_size_pos_deferred = DeferredSignal(
            self.__do_save_size_pos, timeout=50, owner=self)
        self.connect("configure-event", self.__configure_event)
        self.connect("window-state-event", self.__window_state_changed)
        self.connect("notify::visible", self.__visible_changed)
        parent = self.get_transient_for()
        if parent:
            connect_destroy(
                parent, "configure-event", self.__parent_configure_event)
        self.__restore_window_state()

    def __visible_changed(self, *args):
        if not self.get_visible():
            # https://bugzilla.gnome.org/show_bug.cgi?id=731287
            # if we restore after hide, mutter will remember for the next show
            # hurray!
            self.__restore_window_state()

    def __restore_window_state(self):
        if not is_wayland():
            self.__restore_state()
            self.__restore_position()
        self.__restore_size()

    def __conf(self, name):
        if name == "size":
            name += "_" + self.__size_suffix
        return f"{self.__name}_{name}"

    def __restore_state(self):
        print_d("Restore state")
        if config.getint("memory", self.__conf("maximized"), 0):
            self.maximize()
        else:
            self.unmaximize()

    def __restore_position(self):
        print_d("Restore position")
        pos = config.get("memory", self.__conf("position"), "")
        if not pos:
            return

        try:
            x, y = map(int, pos.split())
        except ValueError:
            return

        parent = self.get_transient_for()
        if parent:
            px, py = parent.get_position()
            x += px
            y += py

        self.move(x, y)

    def __restore_size(self):
        print_d("Restore size")
        value = config.get("memory", self.__conf("size"), "")
        if not value:
            return

        try:
            x, y = map(int, value.split())
        except ValueError:
            return

        screen = self.get_screen()
        x = min(x, screen.get_width())
        y = min(y, screen.get_height())
        if x >= 1 and y >= 1:
            self.resize(x, y)

    def __parent_configure_event(self, window, event):
        # since our position is relative to the parent if we have one,
        # we also need to save our position if the parent position changes
        self.__do_save_pos()
        return False

    def __configure_event(self, window, event):
        # xfwm4 resized the window before it maximizes it, which leads
        # to QL remembering the wrong size. Work around that by waiting
        # until configure-event settles down, at which point the maximized
        # state should be set

        self.__save_size_pos_deferred()
        return False

    def _should_ignore_state(self):
        if self.__state & Gdk.WindowState.MAXIMIZED:
            return True
        elif self.__state & Gdk.WindowState.FULLSCREEN:
            return True
        elif not self.get_visible():
            return True
        return False

    def __do_save_size_pos(self):
        if self._should_ignore_state():
            return

        width, height = self.get_size()
        value = "%d %d" % (width, height)
        config.set("memory", self.__conf("size"), value)

        self.__do_save_pos()

    def __do_save_pos(self):
        if self._should_ignore_state():
            return

        x, y = self.get_position()
        parent = self.get_transient_for()
        if parent:
            px, py = parent.get_position()
            x -= px
            y -= py

        pos_value = f"{x} {y}"
        config.set("memory", self.__conf("position"), pos_value)

    def __window_state_changed(self, window, event):
        self.__state = event.new_window_state
        if self.__state & Gdk.WindowState.WITHDRAWN:
            return
        maximized = int(self.__state & Gdk.WindowState.MAXIMIZED)
        config.set("memory", self.__conf("maximized"), maximized)


class _Unique:
    """A mixin for window-like classes to ensure one instance per class. """

    __window = None

    def __new__(cls, *args, **kwargs):
        window = cls.__window
        if window is None:
            return super().__new__(cls, *args, **kwargs)
        # Look for widgets in the args, if there is one and it has
        # a new top level window, re-parent and reposition the window.
        widgets = [w for w in args if isinstance(w, Gtk.Widget)]
        if widgets:
            parent = window.get_transient_for()
            new_parent = get_top_parent(widgets[0])
            if parent and new_parent and parent is not new_parent:
                window.set_transient_for(new_parent)
                window.hide()
                window.show()
        window.present()
        return window

    @classmethod
    def is_not_unique(cls):
        """Returns True if a window instance already exists."""
        return bool(cls.__window)

    def __init__(self, *args, **kwargs):
        if type(self).__window:
            return
        else:
            type(self).__window = self
        super().__init__(*args, **kwargs)
        connect_obj(self, "destroy", self.__destroy, self)

    def __destroy(self, *args):
        type(self).__window = None


class UniqueWindow(_Unique, Window):
    pass
