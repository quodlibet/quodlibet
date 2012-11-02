# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import gobject

from quodlibet import config
from quodlibet.qltk import get_top_parent


class Window(gtk.Window):
    """Base window class the keeps track of all window instances.

    All active instances can be accessed through Window.instances.
    By defining dialog=True as a kwarg binds Escape to close, otherwise
    ^W will close the window.
    """

    instances = []

    __gsignals__ = {"close-accel": (
        gobject.SIGNAL_RUN_LAST|gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ())}
    def __init__(self, *args, **kwargs):
        dialog = kwargs.pop("dialog", True)
        super(Window, self).__init__(*args, **kwargs)
        type(self).instances.append(self)
        self.__accels = gtk.AccelGroup()
        if dialog:
            self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_destroy_with_parent(True)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.add_accel_group(self.__accels)
        if not dialog:
            self.add_accelerator(
                'close-accel', self.__accels, ord('w'), gtk.gdk.CONTROL_MASK, 0)
        else:
            esc, mod = gtk.accelerator_parse("Escape")
            self.add_accelerator('close-accel', self.__accels, esc, mod, 0)
        self.connect_object('destroy', type(self).instances.remove, self)

    def set_transient_for(self, parent):
        """Set a parent for the window.

        In case parent=None, fall back to the main window.

        """

        is_toplevel = parent and parent.props.type == gtk.WINDOW_TOPLEVEL

        if parent is None or not is_toplevel:
            if parent:
                print_w("Not a toplevel window set for: %r" % self)
            from quodlibet import app
            parent = app.window
        super(Window, self).set_transient_for(parent)

    def do_close_accel(self):
        #Do not close the window if we edit a gtk.CellRendererText.
        #Focus the treeview instead.
        if isinstance(self.get_focus(), gtk.Entry) and \
            isinstance(self.get_focus().parent, gtk.TreeView):
            self.get_focus().parent.grab_focus()
            return
        if not self.emit('delete-event', gtk.gdk.Event(gtk.gdk.DELETE)):
            self.destroy()


class PersistentWindowMixin(object):
    """A mixin for saving/restoring window size/position/maximized state"""

    def enable_window_tracking(self, config_prefix, size_suffix=""):
        """Enable tracking/saving of changes and restore size/pos/maximized

        config_prefix -- prefix for the config key
                         (prefix_size, prefix_position, prefix_maximized)
        size_suffix -- optional suffix for saving the size. For cases where the
                       window has multiple states with different content sizes.
                       (example: edit tags with one song or multiple)

        """

        self.__state = 0
        self.__name = config_prefix
        self.__size_suffix = size_suffix
        self.connect('configure-event', self.__save_size)
        self.connect('window-state-event', self.__window_state_changed)
        self.connect('map', self.__map)
        self.__restore_window_state()

    def __map(self, *args):
        # Some WMs (metacity..) tend to forget the position randomly
        self.__restore_window_state()

    def __restore_window_state(self):
        self.__restore_size()
        self.__restore_state()
        self.__restore_position()

    def __conf(self, name):
        if name == "size":
            name += "_" + self.__size_suffix
        return "%s_%s" % (self.__name, name)

    def __restore_state(self):
        print_d("Restore state")
        if config.getint("memory", self.__conf("maximized"), 0):
            self.maximize()
        else:
            self.unmaximize()

    def __restore_position(self):
        print_d("Restore position")
        pos = config.get('memory', self.__conf("position"), "-1 -1")
        x, y = map(int, pos.split())
        if x >= 0 and y >= 0:
            self.move(x, y)

    def __restore_size(self):
        print_d("Restore size")
        value = config.get('memory', self.__conf("size"), "-1 -1")
        x, y = map(int, value.split())
        screen = self.get_screen()
        x = min(x, screen.get_width())
        y = min(y, screen.get_height())
        if x >= 0 and y >= 0:
            self.resize(x, y)

    def __save_size(self, window, event):
        if self.__state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
            return

        value = "%d %d" % (event.width, event.height)
        config.set("memory", self.__conf("size"), value)
        if self.get_property("visible"):
            pos_value = '%s %s' % self.get_position()
            config.set('memory', self.__conf("position"), pos_value)

    def __window_state_changed(self, window, event):
        self.__state = event.new_window_state
        if self.__state & gtk.gdk.WINDOW_STATE_WITHDRAWN:
            return
        maximized = int(self.__state & gtk.gdk.WINDOW_STATE_MAXIMIZED)
        config.set("memory", self.__conf("maximized"), maximized)


class UniqueWindow(Window):
    """A wrapper for the window class to get a one instance per class window.
    The is_not_unique method will return True if the window
    is already there."""

    __window = None

    def __new__(klass, *args):
        window = klass.__window
        if window is None:
            return super(UniqueWindow, klass).__new__(klass, *args)
        #Look for widgets in the args, if there is one and it has
        #a new top level window, reparent and reposition the window.
        widgets = filter(lambda x: isinstance(x, gtk.Widget), args)
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
    def is_not_unique(klass):
        if klass.__window:
            return True

    def __init__(self, *args, **kwargs):
        if type(self).__window: return
        else: type(self).__window = self
        super(UniqueWindow, self).__init__(*args, **kwargs)
        self.connect_object('destroy', self.__destroy, self)

    def __destroy(self, *args):
        type(self).__window = None
