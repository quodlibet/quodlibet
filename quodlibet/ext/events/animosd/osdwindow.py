# Copyright (C) 2012-13 Thomas Vogt
# Copyright (C) 2012-17 Nick Boultbee
# Copyright (C) 2008 Andreas Bombe
# Copyright (C) 2005  Michael Urman
# Based on osd.py (C) 2005 Ton van den Heuvel, Joe Wreshnig
#                 (C) 2004 Gustavo J. A. M. Carneiro
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections import namedtuple
from math import pi

import gi

gi.require_version("PangoCairo", "1.0")

from gi.repository import Gtk, GObject, GLib
from gi.repository import Gdk, Graphene
from gi.repository import Pango, PangoCairo
import cairo

from quodlibet.qltk.image import get_surface_for_pixbuf, get_surface_extents
from quodlibet import qltk
from quodlibet import app
from quodlibet import pattern


def _monitor_geometry(index):
    """The geometry of monitor `index`, or of the first one."""

    monitors = Gdk.Display.get_default().get_monitors()
    count = monitors.get_n_items()
    if not count:
        raise ValueError("no monitors")
    return monitors.get_item(min(index, count - 1)).get_geometry()


class OSDWindow(Gtk.Window):
    __gsignals__ = {
        "fade-finished": (GObject.SignalFlags.RUN_LAST, None, (bool,)),
    }

    MARGIN = 50
    """never any closer to the screen edge than this"""

    BORDER = 20
    """text/cover this far apart, from edge"""

    FADETIME = 0.3
    """take this many seconds to fade in or out"""

    MS = 40
    """wait this many milliseconds between steps"""

    def __init__(self, conf, song):
        Gtk.Window.__init__(self)
        # GTK4 has no window type hints; surfaces are RGBA-capable already
        self.set_decorated(False)
        self.set_name("osd_bubble")
        qltk.add_css(self, "#osd_bubble { background-color: rgba(0,0,0,0); }")

        self.conf = conf
        self.iteration_source = None
        self.fading_in = False
        self.fade_start_time = 0

        mgeo = _monitor_geometry(conf.monitor)
        textwidth = mgeo.width - 2 * (self.BORDER + self.MARGIN)

        scale_factor = self.get_scale_factor()
        cover_pixbuf = app.cover_manager.get_pixbuf(
            song, conf.coversize * scale_factor, conf.coversize * scale_factor
        )
        coverheight = 0
        coverwidth = 0
        if cover_pixbuf:
            self.cover_surface = get_surface_for_pixbuf(self, cover_pixbuf)
            coverwidth = cover_pixbuf.get_width() // scale_factor
            coverheight = cover_pixbuf.get_height() // scale_factor
            textwidth -= coverwidth + self.BORDER
        else:
            self.cover_surface = None

        layout = self.create_pango_layout("")
        layout.set_alignment(
            (Pango.Alignment.LEFT, Pango.Alignment.CENTER, Pango.Alignment.RIGHT)[
                conf.align
            ]
        )
        layout.set_spacing(Pango.SCALE * 7)
        layout.set_font_description(Pango.FontDescription(conf.font))
        try:
            layout.set_markup(pattern.XMLFromMarkupPattern(conf.string) % song)
        except pattern.Error:
            layout.set_markup("")
        layout.set_width(Pango.SCALE * textwidth)
        layoutsize = layout.get_pixel_size()
        if layoutsize[0] < textwidth:
            layout.set_width(Pango.SCALE * layoutsize[0])
            layoutsize = layout.get_pixel_size()
        self.title_layout = layout

        winw = layoutsize[0] + 2 * self.BORDER
        if coverwidth:
            winw += coverwidth + self.BORDER
        winh = max(coverheight, layoutsize[1]) + 2 * self.BORDER
        self.set_default_size(winw, winh)

        rect = namedtuple("Rect", ["x", "y", "width", "height"])
        rect.x = self.BORDER
        rect.y = (winh - coverheight) // 2
        rect.width = coverwidth
        rect.height = coverheight

        self.cover_rectangle = rect

        # TODO GTK4: a client can no longer place its own toplevel, so the
        # position preferences have nowhere to go. Needs a layer-shell surface
        # (wlr-layer-shell / gtk4-layer-shell) to honour them again.

    def do_snapshot(self, snapshot):
        width, height = self.get_width(), self.get_height()
        rect = Graphene.Rect().init(0, 0, width, height)
        self.draw_title_info(snapshot.append_cairo(rect))

    @staticmethod
    def rounded_rectangle(cr, x, y, radius, width, height):
        cr.move_to(x + radius, y)
        cr.line_to(x + width - radius, y)
        cr.arc(
            x + width - radius, y + radius, radius, -90.0 * pi / 180.0, 0.0 * pi / 180.0
        )
        cr.line_to(x + width, y + height - radius)
        cr.arc(
            x + width - radius,
            y + height - radius,
            radius,
            0.0 * pi / 180.0,
            90.0 * pi / 180.0,
        )
        cr.line_to(x + radius, y + height)
        cr.arc(
            x + radius,
            y + height - radius,
            radius,
            90.0 * pi / 180.0,
            180.0 * pi / 180.0,
        )
        cr.line_to(x, y + radius)
        cr.arc(x + radius, y + radius, radius, 180.0 * pi / 180.0, 270.0 * pi / 180.0)
        cr.close_path()

    @property
    def corners_factor(self):
        if self.conf.corners != 0:
            return 0.14
        return 0.0

    def draw_conf_rect(self, cr, x, y, width, height, radius):
        if self.conf.corners != 0:
            self.rounded_rectangle(cr, x, y, radius, width, height)
        else:
            cr.rectangle(x, y, width, height)

    def draw_title_info(self, cr):
        cr.save()
        do_shadow = self.conf.shadow[0] != -1.0
        do_outline = self.conf.outline[0] != -1.0

        win_width, win_height = self.get_width(), self.get_height()

        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(*self.conf.fill)
        radius = min(25, self.corners_factor * min(win_width, win_height))
        self.draw_conf_rect(cr, 0, 0, win_width, win_height, radius)
        cr.fill()

        # draw border
        if do_outline:
            # Make border darker and more translucent than the fill
            f = self.conf.fill
            rgba = (f[0] / 1.25, f[1] / 1.25, f[2] / 1.25, f[3] / 2.0)
            cr.set_source_rgba(*rgba)
            self.draw_conf_rect(cr, 1, 1, win_width - 2, win_height - 2, radius)
            cr.set_line_width(2.0)
            cr.stroke()

        textx = self.BORDER

        if self.cover_surface is not None:
            rect = self.cover_rectangle
            textx += rect.width + self.BORDER
            surface = self.cover_surface
            transmat = cairo.Matrix()

            if do_shadow:
                cr.set_source_rgba(*self.conf.shadow)
                self.draw_conf_rect(
                    cr,
                    rect.x + 2,
                    rect.y + 2,
                    rect.width,
                    rect.height,
                    0.6 * self.corners_factor * rect.width,
                )
                cr.fill()

            if do_outline:
                cr.set_source_rgba(*self.conf.outline)
                self.draw_conf_rect(
                    cr,
                    rect.x,
                    rect.y,
                    rect.width,
                    rect.height,
                    0.6 * self.corners_factor * rect.width,
                )
                cr.stroke()

            cr.set_source_surface(surface, 0, 0)
            width, height = get_surface_extents(surface)[2:]

            transmat.scale(width / float(rect.width), height / float(rect.height))
            transmat.translate(-rect.x, -rect.y)
            cr.get_source().set_matrix(transmat)
            self.draw_conf_rect(
                cr,
                rect.x,
                rect.y,
                rect.width,
                rect.height,
                0.6 * self.corners_factor * rect.width,
            )
            cr.fill()

        PangoCairo.update_layout(cr, self.title_layout)
        texty = (win_height - self.title_layout.get_pixel_size()[1]) // 2

        if do_shadow:
            cr.set_source_rgba(*self.conf.shadow)
            cr.move_to(textx + 2, texty + 2)
            PangoCairo.show_layout(cr, self.title_layout)
        if do_outline:
            cr.set_source_rgba(*self.conf.outline)
            cr.move_to(textx, texty)
            PangoCairo.layout_path(cr, self.title_layout)
            cr.stroke()
        cr.set_source_rgb(*self.conf.text[:3])
        cr.move_to(textx, texty)
        PangoCairo.show_layout(cr, self.title_layout)
        cr.restore()

    def fade_in(self):
        self.do_fade_inout(True)

    def fade_out(self):
        self.do_fade_inout(False)

    def do_fade_inout(self, fadein):
        fadein = bool(fadein)
        self.fading_in = fadein
        now = GLib.get_real_time()

        fraction = self.get_opacity()
        if not fadein:
            fraction = 1.0 - fraction
        self.fade_start_time = now - fraction * self.FADETIME

        if self.iteration_source is None:
            self.iteration_source = GLib.timeout_add(
                self.MS, self.fade_iteration_callback
            )

    def fade_iteration_callback(self):
        delta = GLib.get_real_time() - self.fade_start_time
        fraction = delta / self.FADETIME

        if self.fading_in:
            self.set_opacity(fraction)
        else:
            self.set_opacity(1.0 - fraction)

        if fraction >= 1.0:
            self.iteration_source = None
            self.emit("fade-finished", self.fading_in)
            return False
        return True
