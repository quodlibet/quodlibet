# -*- coding: utf-8 -*-
# Copyright (C) 2012-13 Nick Boultbee, Thomas Vogt
# Copyright (C) 2008 Andreas Bombe
# Copyright (C) 2005  Michael Urman
# Based on osd.py (C) 2005 Ton van den Heuvel, Joe Wreshnig
#                 (C) 2004 Gustavo J. A. M. Carneiro
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gdk

from quodlibet import _
from quodlibet import app
from quodlibet import qltk
from quodlibet.util import connect_obj
from quodlibet.formats import DUMMY_SONG
from quodlibet.qltk.textedit import PatternEdit
from quodlibet.qltk import Icons


class ConfigLabel(Gtk.Label):
    """Customised Label for configuration, tied to a widget"""

    def __init__(self, text, widget):
        super(Gtk.Label, self).__init__(label=text, use_underline=True)
        self.set_mnemonic_widget(widget)
        self.set_alignment(0.0, 0.5)


class AnimOsdPrefs(Gtk.VBox):

    def __init__(self, plugin):
        super(AnimOsdPrefs, self).__init__(spacing=6)

        self.Conf = plugin.Conf
        self.plugin = plugin

        def __coltofloat(x):
            return x / 65535.0

        def __floattocol(x):
            return int(x * 65535)

        def show_preview():
            preview_song = (app.player.song if app.player.song else DUMMY_SONG)
            self.plugin.plugin_on_song_started(preview_song)

        def on_button_pressed(x=None, y=None):
            show_preview()

        def set_text(button):
            color = button.get_color()
            color = map(__coltofloat,
                        (color.red, color.green, color.blue, 0.0))
            self.Conf.text = tuple(color)
            show_preview()

        def set_fill(button):
            color = button.get_color()
            color = map(__coltofloat, (color.red, color.green, color.blue,
                button.get_alpha()))
            self.Conf.fill = tuple(color)
            show_preview()

        def set_font(button):
            font = button.get_font_name()
            self.Conf.font = font
            show_preview()

        def change_delay(button):
            value = int(button.get_value() * 1000)
            self.Conf.delay = value

        def change_monitor(button):
            """Monitor number config change handler"""
            value = int(button.get_value())
            self.Conf.monitor = value
            show_preview()

        def change_position(button, x, y):
            self.Conf.pos_x = x / 2.0
            self.Conf.pos_y = y / 2.0
            show_preview()

        def change_align(button):
            value = button.get_active()
            self.Conf.align = value
            show_preview()

        def change_shadow(button):
            if button.get_active():
                self.Conf.shadow = (0.0, 0.0, 0.0, self.Conf.fill[3])
            else:
                self.Conf.shadow = (-1.0, 0.0, 0.0, 0.0)
            show_preview()

        def change_outline(button):
            if button.get_active():
                # Vary with fill alpha to create a smoother outline edge
                alpha = (min(1.0, self.Conf.fill[3] * 1.25))
                self.Conf.outline = (0.1, 0.1, 0.1, alpha)
            else:
                self.Conf.outline = (-1.0, 0.0, 0.0)
            show_preview()

        def change_rounded(button):
            if button.get_active():
                self.Conf.corners = 1
            else:
                self.Conf.corners = 0
            show_preview()

        def change_coversize(button):
            value = int(button.get_value())
            self.Conf.coversize = value
            show_preview()

        def edit_pattern(button):
            w = PatternEdit(button, self.Conf.string)
            w.set_default_size(520, 260)
            w.text = self.Conf.string
            connect_obj(w.apply, 'clicked', set_string, w)
            w.show()

        def set_string(window):
            value = window.text
            self.Conf.string = value
            show_preview()

        def build_display_widget():
            vb2 = Gtk.VBox(spacing=3)
            hb = Gtk.HBox(spacing=6)
            # Set monitor to display OSD on if there's more than one
            monitor_cnt = Gdk.Screen.get_default().get_n_monitors()
            if monitor_cnt > 1:
                adj = Gtk.Adjustment(value=self.Conf.monitor, lower=0,
                                     upper=monitor_cnt - 1, step_increment=1)
                monitor = Gtk.SpinButton(adjustment=adj)
                monitor.set_numeric(True)
                monitor.connect('value-changed', change_monitor)
                l2 = ConfigLabel("_Monitor:", monitor)
                hb.pack_start(l2, False, True, 0)
                hb.pack_start(monitor, False, True, 0)
                vb2.pack_start(hb, True, True, 0)
            else:
                # should be this by default anyway
                self.Conf.monitor = 0

            hb = Gtk.HBox(spacing=6)
            grid = Gtk.Grid(column_homogeneous=True,
                            row_homogeneous=True,
                            row_spacing=4,
                            column_spacing=4)
            arrows = [['↖', '↑', '↗'],
                      ['←', '○', '→'],
                      ['↙', '↓', '↘ ']]

            group = None
            for x in range(3):
                for y in range(3):
                    rb = Gtk.RadioButton(group=group, label=arrows[y][x])
                    if (int(self.Conf.pos_x * 2.0) == x and
                            int(self.Conf.pos_y * 2.0) == y):
                        rb.set_active(True)
                    grid.attach(rb, x, y, 1, 1)
                    group = rb

            # Connect to signal after the correct radio button has been
            # selected
            for x in range(3):
                for y in range(3):
                    rb = grid.get_child_at(x, y)
                    rb.connect('toggled', change_position, x, y)

            lbl = ConfigLabel(_("_Position:"), grid)
            hb.pack_start(lbl, False, True, 0)
            hb.pack_start(grid, False, True, 0)
            vb2.pack_start(hb, False, True, 6)

            hb = Gtk.HBox(spacing=6)
            coversize = Gtk.SpinButton(
                adjustment=Gtk.Adjustment.new(
                    self.Conf.coversize, 1, 600, 1, 10, 0),
                climb_rate=1, digits=0)
            coversize.set_numeric(True)
            coversize.connect('value-changed', change_coversize)
            l1 = ConfigLabel(_("_Cover size:"), coversize)
            hb.pack_start(l1, False, True, 0)
            hb.pack_start(coversize, False, True, 0)
            vb2.pack_start(hb, False, True, 0)
            return vb2

        frame = qltk.Frame(label=_("Display"), child=build_display_widget())
        frame.set_border_width(6)
        self.pack_start(frame, False, True, 0)

        def build_text_widget():
            t = Gtk.Table(n_rows=2, n_columns=2)
            t.props.expand = False
            t.set_col_spacings(6)
            t.set_row_spacings(3)

            font = Gtk.FontButton(show_style=True)
            font.set_font_name(self.Conf.font)
            font.connect('font-set', set_font)
            lbl = ConfigLabel(_("_Font:"), font)
            t.attach(lbl, 0, 1, 0, 1, xoptions=Gtk.AttachOptions.FILL)
            t.attach(font, 1, 2, 0, 1)

            align = Gtk.ComboBoxText()
            align.append_text(_("Left"))
            align.append_text(_("Center"))
            align.append_text(_("Right"))
            align.set_active(self.Conf.align)
            align.connect('changed', change_align)
            lbl = ConfigLabel(_("_Align text:"), align)

            t.attach(lbl, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL)
            t.attach(align, 1, 2, 1, 2)
            return t

        frame = qltk.Frame(label=_("Text"), child=build_text_widget())
        frame.set_border_width(6)
        self.pack_start(frame, False, True, 0)

        def build_colors_widget():
            t = Gtk.Table(n_rows=2, n_columns=2)
            t.props.expand = False
            t.set_col_spacings(6)
            t.set_row_spacings(3)
            b = Gtk.ColorButton(
                rgba=Gdk.RGBA(*map(__floattocol, self.Conf.text)))
            l = ConfigLabel(_("_Text:"), b)

            t.attach(l, 0, 1, 0, 1, xoptions=Gtk.AttachOptions.FILL)
            t.attach(b, 1, 2, 0, 1)
            b.connect('color-set', set_text)
            b = Gtk.ColorButton(color=Gdk.Color(*map(__floattocol,
                                self.Conf.fill[0:3])))
            b.set_use_alpha(True)
            b.set_alpha(__floattocol(self.Conf.fill[3]))
            b.connect('color-set', set_fill)
            l = ConfigLabel(_("_Fill:"), b)
            t.attach(l, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL)
            t.attach(b, 1, 2, 1, 2)
            return t

        f = qltk.Frame(label=_("Colors"), child=build_colors_widget())
        f.set_border_width(6)
        self.pack_start(f, False, False, 0)

        def build_effects_widget():
            vb2 = Gtk.VBox(spacing=3)
            hb = Gtk.HBox(spacing=6)
            toggles = [
                (_("_Shadows"), self.Conf.shadow[0], change_shadow),
                (_("_Outline"), self.Conf.outline[0], change_outline),
                (_("Rou_nded Corners"), self.Conf.corners - 1, change_rounded)]

            for (label, current, callback) in toggles:
                checkb = Gtk.CheckButton(label=label, use_underline=True)
                checkb.set_active(current != -1)
                checkb.connect("toggled", callback)
                hb.pack_start(checkb, True, True, 0)
            vb2.pack_start(hb, True, True, 0)

            hb = Gtk.HBox(spacing=6)
            timeout = Gtk.SpinButton(
                adjustment=Gtk.Adjustment.new(
                    self.Conf.delay / 1000.0, 0, 60, 0.1, 1.0, 0),
                climb_rate=0.1, digits=1)
            timeout.set_numeric(True)
            timeout.connect('value-changed', change_delay)
            l1 = ConfigLabel(_("_Delay:"), timeout)
            hb.pack_start(l1, False, True, 0)
            hb.pack_start(timeout, False, True, 0)
            vb2.pack_start(hb, False, True, 0)
            return vb2

        frame = qltk.Frame(label=_("Effects"), child=build_effects_widget())
        frame.set_border_width(6)
        self.pack_start(frame, False, True, 0)

        def build_buttons_widget():
            hb = Gtk.HBox(spacing=6)
            edit_button = qltk.Button(_(u"Ed_it Display Pattern…"),
                                      Icons.EDIT)
            edit_button.connect('clicked', edit_pattern)
            hb.pack_start(edit_button, False, True, 0)
            preview_button = Gtk.Button(label=_("Preview"), use_underline=True)
            preview_button.connect("button-press-event", on_button_pressed)
            hb.pack_start(preview_button, False, True, 0)
            return hb

        self.pack_start(build_buttons_widget(), False, True, 0)
