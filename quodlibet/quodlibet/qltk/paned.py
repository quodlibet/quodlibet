# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import config
from . import add_css, gtk_version


class Paned(Gtk.Paned):

    def __init__(self, *args, **kwargs):
        super(Paned, self).__init__(*args, **kwargs)
        self.ensure_wide_handle()

    def ensure_wide_handle(self):
        if gtk_version >= (3, 19):
            self.props.wide_handle = True
            add_css(self, """
                paned separator {
                    border-width: 0;
                    background-image: none;
                }
            """)
            return

        if hasattr(self.props, "wide_handle"):
            # gtk 3.16
            self.props.wide_handle = True
            add_css(self, """
                GtkPaned {
                    border-width: 0;
                }
            """)
            return

        # gtk 3.14
        add_css(self, """
            GtkPaned {
                -GtkPaned-handle-size: 6;
                background-image: none;
                margin: 0;
                border-width: 0;
            }
        """)


class RPaned(Paned):
    """A Paned that supports relative (percentage) width/height setting."""

    ORIENTATION = None

    def __init__(self, *args, **kwargs):
        if self.ORIENTATION is not None:
            kwargs["orientation"] = self.ORIENTATION
        super(RPaned, self).__init__(*args, **kwargs)
        # before first alloc: save value in relative and set on the first alloc
        # after the first alloc: use the normal properties
        self.__alloced = False
        self.__relative = None

    def set_relative(self, v):
        """Set the relative position of the separator, [0..1]."""

        if self.__alloced:
            max_pos = self.get_property('max-position')
            if not max_pos:
                # no children
                self.__relative = v
                return
            self.set_position(int(v * max_pos))
        else:
            self.__relative = v

    def get_relative(self):
        """Return the relative position of the separator, [0..1]."""

        if self.__alloced:
            max_pos = self.get_property('max-position')
            if not max_pos:
                # no children
                return self.__relative
            return (float(self.get_position()) / max_pos)
        elif self.__relative is not None:
            return self.__relative
        else:
            # before first alloc and set_relative not called
            return 0.5

    def do_size_allocate(self, *args):
        ret = Gtk.HPaned.do_size_allocate(self, *args)
        if not self.__alloced and self.__relative is not None:
            self.__alloced = True
            self.set_relative(self.__relative)
            # call again so the children get alloced
            ret = Gtk.HPaned.do_size_allocate(self, *args)
        self.__alloced = True
        return ret


class RHPaned(RPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class RVPaned(RPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL


class ConfigRPaned(RPaned):
    def __init__(self, section, option, default, *args, **kwargs):
        super(ConfigRPaned, self).__init__(*args, **kwargs)
        self.set_relative(config.getfloat(section, option, default))
        self.connect('notify::position', self.__changed, section, option)

    def __changed(self, widget, event, section, option):
        if self.get_property('position-set'):
            config.set(section, option, str(self.get_relative()))


class ConfigRHPaned(ConfigRPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class ConfigRVPaned(ConfigRPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL
