# Copyright (C) 2012-13 Nick Boultbee, Thomas Vogt
# Copyright (C) 2008 Andreas Bombe
# Copyright (C) 2005  Michael Urman
# Based on osd.py (C) 2005 Ton van den Heuvel, Joe Wreshnig
#                 (C) 2004 Gustavo J. A. M. Carneiro
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#

from collections import namedtuple

import gi
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gtk, GObject, GLib
from gi.repository import Gdk, GdkPixbuf
from gi.repository import Pango, PangoCairo
import cairo

from math import pi

from quodlibet import config, qltk, app
from quodlibet.qltk.textedit import PatternEdit
from quodlibet.formats import DUMMY_SONG
from quodlibet import parse
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins import PluginConfigMixin
from quodlibet.util.dprint import print_d, print_w


class ConfigLabel(Gtk.Label):
    """Customised Label for configuration, tied to a widget"""

    def __init__(self, text, widget):
        super(Gtk.Label, self).__init__(label=text, use_underline=True)
        self.set_mnemonic_widget(widget)
        self.set_alignment(0.0, 0.5)


class OSDWindow(Gtk.Window):
    __gsignals__ = {
        'fade-finished': (GObject.SignalFlags.RUN_LAST, None, (bool,)),
    }

    def __init__(self, conf, song):
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)
        self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)

        screen = self.get_screen()
        rgba = Gdk.Screen.get_rgba_visual(screen)
        self.set_visual(rgba)

        self.conf = conf
        self.iteration_source = None
        self.fading_in = False
        self.fade_start_time = 0

        cover = song.find_cover()
        try:
            if cover is not None:
                cover = GdkPixbuf.Pixbuf.new_from_file(cover.name)
        except GLib.GError, gerror:
            print_w('GDK error while loading cover image: %s'
                    % gerror.message)
        except:
            from traceback import format_exc
            print_w("Error loading cover image: %s" % format_exc())

        # now calculate size of window
        mgeo = screen.get_monitor_geometry(conf.monitor)
        coverwidth = min(120, mgeo.width // 8)
        textwidth = mgeo.width - 2 * (conf.border + conf.margin)
        if cover is not None:
            textwidth -= coverwidth + conf.border
            coverheight = int(cover.get_height() * float(coverwidth)
                              / cover.get_width())
        else:
            coverheight = 0
        self.cover_pixbuf = cover

        layout = self.create_pango_layout('')
        layout.set_alignment((Pango.Alignment.LEFT, Pango.Alignment.CENTER,
                              Pango.Alignment.RIGHT)[conf.align])
        layout.set_spacing(Pango.SCALE * 7)
        layout.set_font_description(Pango.FontDescription(conf.font))
        try:
            layout.set_markup(parse.XMLFromMarkupPattern(conf.string) % song)
        except parse.error:
            layout.set_markup("")
        layout.set_width(Pango.SCALE * textwidth)
        layoutsize = layout.get_pixel_size()
        if layoutsize[0] < textwidth:
            layout.set_width(Pango.SCALE * layoutsize[0])
            layoutsize = layout.get_pixel_size()
        self.title_layout = layout

        winw = layoutsize[0] + 2 * conf.border
        if cover is not None:
            winw += coverwidth + conf.border
        winh = max(coverheight, layoutsize[1]) + 2 * conf.border
        self.set_default_size(winw, winh)

        rect = namedtuple("Rect", ["x", "y", "width", "height"])
        rect.x = conf.border
        rect.y = (winh - coverheight) // 2
        rect.width = coverwidth
        rect.height = coverheight

        self.cover_rectangle = rect

        winx = int((mgeo.width - winw) * conf.pos_x)
        winx = max(conf.margin, min(mgeo.width - conf.margin - winw, winx))
        winy = int((mgeo.height - winh) * conf.pos_y)
        winy = max(conf.margin, min(mgeo.height - conf.margin - winh, winy))
        self.move(winx + mgeo.x, winy + mgeo.y)

    def do_draw(self, cr):
        if self.is_composited():
            self.draw_title_info(cr)
        else:
            # manual transparency rendering follows
            walloc = self.get_allocation()
            wpos = self.get_position()

            if not getattr(self, "_bg_sf", None):
                # copy the root surface into a temp image surface
                root_win = self.get_root_window()
                bg_sf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                           walloc.width, walloc.height)
                pb = Gdk.pixbuf_get_from_window(
                    root_win, wpos[0], wpos[1], walloc.width, walloc.height)
                bg_cr = cairo.Context(bg_sf)
                Gdk.cairo_set_source_pixbuf(bg_cr, pb, 0, 0)
                bg_cr.paint()
                self._bg_sf = bg_sf

            if not getattr(self, "_fg_sf", None):
                # draw the window content in another temp surface
                fg_sf = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                           walloc.width, walloc.height)
                fg_cr = cairo.Context(fg_sf)
                fg_cr.set_source_surface(fg_sf)
                self.draw_title_info(fg_cr)
                self._fg_sf = fg_sf

            # first draw the background so we have 'transparancy'
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.set_source_surface(self._bg_sf)
            cr.paint()

            # then draw the window content with the right opacity
            cr.set_operator(cairo.OPERATOR_OVER)
            cr.set_source_surface(self._fg_sf)
            cr.paint_with_alpha(self.get_opacity())

    @staticmethod
    def rounded_rectangle(cr, x, y, radius, width, height):
        cr.move_to(x + radius, y)
        cr.line_to(x + width - radius, y)
        cr.arc(x + width - radius, y + radius, radius,
               - 90.0 * pi / 180.0, 0.0 * pi / 180.0)
        cr.line_to(x + width, y + height - radius)
        cr.arc(x + width - radius, y + height - radius, radius,
               0.0 * pi / 180.0, 90.0 * pi / 180.0)
        cr.line_to(x + radius, y + height)
        cr.arc(x + radius, y + height - radius, radius,
               90.0 * pi / 180.0, 180.0 * pi / 180.0)
        cr.line_to(x, y + radius)
        cr.arc(x + radius, y + radius, radius,
               180.0 * pi / 180.0, 270.0 * pi / 180.0)
        cr.close_path()

    def draw_conf_rect(self, cr, x, y, width, height, radius):
        if self.conf.corners != 0:
            self.rounded_rectangle(cr, x, y, radius, width, height)
        else:
            cr.rectangle(x, y, width, height)

    def draw_title_info(self, cr):
        cr.save()
        do_shadow = (self.conf.shadow[0] != -1.0)
        do_outline = (self.conf.outline[0] != -1.0)

        self.set_name("osd_bubble")
        style_provider = Gtk.CssProvider()
        css = """
            #osd_bubble {
                background-color:rgba(0,0,0,0);
            }
        """
        style_provider.load_from_data(css.encode("utf8"))
        style_context = self.get_style_context()
        style_context.add_provider(
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgba(*self.conf.fill)
        radius = min(25, self.conf.corners * min(*self.get_size()))
        self.draw_conf_rect(cr, 0, 0, self.get_size()[0],
                            self.get_size()[1], radius)
        cr.fill()

        # draw border
        if do_outline:
            # Make border darker and more translucent than the fill
            f = self.conf.fill
            rgba = (f[0] / 1.25, f[1] / 1.25, f[2] / 1.25, f[3] / 2.0)
            cr.set_source_rgba(*rgba)
            self.draw_conf_rect(cr,
                                1, 1,
                                self.get_size()[0] - 2, self.get_size()[1] - 2,
                                radius)
            cr.set_line_width(2.0)
            cr.stroke()

        textx = self.conf.border

        if self.cover_pixbuf is not None:
            rect = self.cover_rectangle
            textx += rect.width + self.conf.border
            pbuf = self.cover_pixbuf
            transmat = cairo.Matrix()

            if do_shadow:
                cr.set_source_rgba(*self.conf.shadow)
                self.draw_conf_rect(cr,
                                    rect.x + 2, rect.y + 2,
                                    rect.width, rect.height,
                                    0.6 * self.conf.corners * rect.width)
                cr.fill()

            if do_outline:
                cr.set_source_rgba(*self.conf.outline)
                self.draw_conf_rect(cr,
                                    rect.x, rect.y,
                                    rect.width, rect.height,
                                    0.6 * self.conf.corners * rect.width)
                cr.stroke()

            Gdk.cairo_set_source_pixbuf(cr, pbuf, 0, 0)
            transmat.scale(pbuf.get_width() / float(rect.width),
                           pbuf.get_height() / float(rect.height))
            transmat.translate(-rect.x, -rect.y)
            cr.get_source().set_matrix(transmat)
            self.draw_conf_rect(cr,
                                rect.x, rect.y,
                                rect.width, rect.height,
                                0.6 * self.conf.corners * rect.width)
            cr.fill()

        PangoCairo.update_layout(cr, self.title_layout)
        height = self.title_layout.get_pixel_size()[1]
        texty = (self.get_size()[1] - height) // 2

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
        now = GObject.get_current_time()

        fraction = self.get_opacity()
        if not fadein:
            fraction = 1.0 - fraction
        self.fade_start_time = now - fraction * self.conf.fadetime

        if self.iteration_source is None:
            self.iteration_source = GLib.timeout_add(self.conf.ms,
                    self.fade_iteration_callback)

    def fade_iteration_callback(self):
        delta = GObject.get_current_time() - self.fade_start_time
        fraction = delta / self.conf.fadetime

        if self.fading_in:
            self.set_opacity(fraction)
        else:
            self.set_opacity(1.0 - fraction)

        if not self.is_composited():
            self.queue_draw()

        if fraction >= 1.0:
            self.iteration_source = None
            self.emit('fade-finished', self.fading_in)
            return False
        return True


class AnimOsd(EventPlugin, PluginConfigMixin):
    PLUGIN_ID = "Animated On-Screen Display"
    PLUGIN_NAME = _("Animated On-Screen Display")
    PLUGIN_DESC = _("Display song information on your screen when it changes.")
    PLUGIN_VERSION = "1.3"
    # Retain compatibility with old configuration
    CONFIG_SECTION = 'animosd'

    def PluginPreferences(self, parent):
        def __coltofloat(x):
            return x / 65535.0

        def __floattocol(x):
            return int(x * 65535)

        def cfg_set_tuple(name, t):
            s = " ".join(map(str, t))
            self.config_set("%s" % name, s)

        def show_preview():
            preview_song = (app.player.song if app.player.song else DUMMY_SONG)
            self.plugin_on_song_started(preview_song)

        def on_button_pressed(x=None, y=None):
            show_preview()

        def set_text(button):
            color = button.get_color()
            color = map(__coltofloat,
                        (color.red, color.green, color.blue, 0.0))
            self.Conf.text = tuple(color)
            cfg_set_tuple("text", self.Conf.text)
            show_preview()

        def set_fill(button):
            color = button.get_color()
            color = map(__coltofloat, (color.red, color.green, color.blue,
                button.get_alpha()))
            self.Conf.fill = tuple(color)
            cfg_set_tuple("fill", self.Conf.fill)
            show_preview()

        def set_font(button):
            font = button.get_font_name()
            self.config_set("font", font)
            self.Conf.font = font
            show_preview()

        def change_delay(button):
            value = int(button.get_value() * 1000)
            self.config_set("delay", str(value))
            self.Conf.delay = value

        def change_monitor(button):
            """Monitor number config change handler"""
            value = int(button.get_value())
            self.config_set("monitor", str(value))
            self.Conf.monitor = value
            show_preview()

        def change_position(button):
            value = button.get_active() / 2.0
            self.config_set("pos_y", str(value))
            self.Conf.pos_y = value
            show_preview()

        def change_align(button):
            value = button.get_active()
            self.config_set("align", str(value))
            self.Conf.align = value
            show_preview()

        def change_shadow(button):
            if button.get_active():
                self.Conf.shadow = (0.0, 0.0, 0.0, self.Conf.fill[3])
            else:
                self.Conf.shadow = (-1.0, 0.0, 0.0, 0.0)
            cfg_set_tuple("shadow", self.Conf.shadow)
            show_preview()

        def change_outline(button):
            if button.get_active():
                # Vary with fill alpha to create a smoother outline edge
                alpha = (min(1.0, self.Conf.fill[3] * 1.25))
                self.Conf.outline = (0.1, 0.1, 0.1, alpha)
            else:
                self.Conf.outline = (-1.0, 0.0, 0.0)
            cfg_set_tuple("outline", self.Conf.outline)
            show_preview()

        def change_rounded(button):
            if button.get_active():
                self.Conf.corners = 0.14
            else:
                self.Conf.corners = 0
            self.config_set("corners", str(self.Conf.corners))
            show_preview()

        def edit_pattern(button):
            w = PatternEdit(button, AnimOsd.ConfDef.string)
            w.set_default_size(520, 260)
            w.text = self.Conf.string
            w.apply.connect_object_after('clicked', set_string, w)
            w.show()

        def set_string(window):
            value = window.text
            self.config_set("string", value)
            self.Conf.string = value
            show_preview()

        # Main VBox to return
        vb = Gtk.VBox(spacing=6)

        def build_display_widget():
            vb2 = Gtk.VBox(spacing=3)
            hb = Gtk.HBox(spacing=6)
            # Set monitor to display OSD on if there's more than one
            monitor_cnt = Gdk.Screen.get_default().get_n_monitors()
            if monitor_cnt > 1:
                adj = Gtk.Adjustment(value=self.Conf.monitor, lower=0,
                                     upper=monitor_cnt - 1, step_incr=1)
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
            cb = Gtk.ComboBoxText()
            cb.append_text(_("Top of screen"))
            cb.append_text(_("Middle of screen"))
            cb.append_text(_("Bottom of screen"))
            cb.set_active(int(self.Conf.pos_y * 2.0))
            cb.connect('changed', change_position)
            lbl = ConfigLabel(_("_Position:"), cb)

            hb.pack_start(lbl, False, True, 0)
            hb.pack_start(cb, False, True, 0)
            vb2.pack_start(hb, False, True, 0)
            return vb2

        frame = qltk.Frame(label=_("Display"), child=build_display_widget())
        frame.set_border_width(6)
        vb.pack_start(frame, False, True, 0)

        def build_text_widget():
            t = Gtk.Table(2, 2)
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
        vb.pack_start(frame, False, True, 0)

        def build_colors_widget():
            t = Gtk.Table(2, 2)
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
        vb.pack_start(f, False, False, 0)

        def build_effects_widget():
            vb2 = Gtk.VBox(spacing=3)
            hb = Gtk.HBox(spacing=6)
            toggles = [
                ("_Shadows", self.Conf.shadow[0], change_shadow),
                ("_Outline", self.Conf.outline[0], change_outline),
                ("Rou_nded Corners", self.Conf.corners - 1, change_rounded)]

            for (label, current, callback) in toggles:
                checkb = Gtk.CheckButton(label, use_underline=True)
                checkb.set_active(current != -1)
                checkb.connect("toggled", callback)
                hb.pack_start(checkb, True, True, 0)
            vb2.pack_start(hb, True, True, 0)

            hb = Gtk.HBox(spacing=6)
            timeout = Gtk.SpinButton(
                adjustment=Gtk.Adjustment(
                    self.Conf.delay / 1000.0, 0, 60, 0.1, 1.0, 0),
                climb_rate=0.1, digits=1)
            timeout.set_numeric(True)
            timeout.connect('value-changed', change_delay)
            l1 = ConfigLabel("_Delay:", timeout)
            hb.pack_start(l1, False, True, 0)
            hb.pack_start(timeout, False, True, 0)
            vb2.pack_start(hb, False, True, 0)
            return vb2

        frame = qltk.Frame(label=_("Effects"), child=build_effects_widget())
        frame.set_border_width(6)
        vb.pack_start(frame, False, True, 0)

        def build_buttons_widget():
            hb = Gtk.HBox(spacing=6)
            edit_button = qltk.Button(_("Ed_it Display Pattern..."),
                                      Gtk.STOCK_EDIT)
            edit_button.connect('clicked', edit_pattern)
            hb.pack_start(edit_button, False, True, 0)
            preview_button = Gtk.Button(_("Preview"))
            preview_button.connect("button-press-event", on_button_pressed)
            hb.pack_start(preview_button, False, True, 0)
            return hb

        vb.pack_start(build_buttons_widget(), False, True, 0)
        return vb

    class ConfDef(object):
        # position of window 0--1 horizontal
        pos_x = 0.5
        # position of window 0--1 vertical
        pos_y = 0.0
        # never any closer to the screen edge than this
        margin = 50
        # text/cover this far apart, from edge
        border = 20
        # take this many seconds to fade in or out
        fadetime = 0.3
        # wait this many milliseconds between steps
        ms = 40
        # wait this many milliseconds before hiding
        delay = 2500
        # monitor to display OSD on
        monitor = 0
        # Font
        font = "Sans 22"
        # main font color. Alpha is ignored.
        text = (0.9, 0.9, 0.9, 0.0)
        # align text: 0 (left), 1 (center), 2 (right)
        align = 1
        # rounded corner radius, 0 for angled corners
        corners = 0
        # color,alpha or (-1.0,0.0,0.0,0.0) - surrounds text and cover
        outline = (-1.0, 0.0, 0.0, 0.2)
        # color,alpha or (-1.0,0.0,0.0) - shadows outline for text and cover
        shadow = (-1.0, 0.0, 0.0, 0.1)
        # color,alpha or None - fills rectangular area
        fill = (0.25, 0.25, 0.25, 0.5)
        # color,alpha or (-1.0,0.0,0.0,0.5) - borders the whole OSD
        bcolor = (0.0, 0.0, 0.0, 0.2)
        # song information to use - like in main window
        string = (r"<album|[b]<album>[/b]<discnumber| - Disc "
"""<discnumber>><part| - [b]<part>[/b]><tracknumber| - <tracknumber>>
>[span weight='bold' size='large']<title>[/span] - <~length><version|
[small][i]<version>[/i][/small]><~people|
by <~people>>""")

    Conf = ConfDef()

    def __init__(self):
        self.__current_window = None

        def str_to_tuple(s):
            lst = map(float, s.split())
            while len(lst) < 4:
                lst.append(0.0)
            return tuple(lst)

        config_map = [
            ('text', str_to_tuple),
            ('fill', str_to_tuple),
            ('shadow', str_to_tuple),
            ('outline', str_to_tuple),
            ('bcolor', str_to_tuple),
            ('corners', float),
            ('font', None),
            ('align', int),
            ('delay', int),
            ('monitor', int),
            ('pos_y', float),
            ('string', None),
            ]
        for key, getconv in config_map:
            try:
                default = getattr(self.Conf, key)
            except AttributeError:
                print_d("Unknown config item '%s'" % key)
            try:
                value = self.config_get(key, default)
                # This should never happen now that we default, but still..
                if value is None:
                    continue
            except (config.Error, ValueError):
                print_d("Couldn't find config item %s" % key)
                continue

            try:
                if getconv is not None:
                    value = getconv(value)
            except Exception as err:
                print_d("Error parsing config for %s (%s) - defaulting to %r"
                        % (key, err, default))
                # Replace the invalid value
                if default is not None:
                    self.config_set(key, default)
            else:
                setattr(self.Conf, key, value)

    def plugin_on_song_started(self, song):
        if self.__current_window is not None:
            if self.__current_window.is_composited():
                self.__current_window.fade_out()
            else:
                self.__current_window.hide()
                self.__current_window.destroy()

        if song is None:
            self.__current_window = None
            return

        window = OSDWindow(self.Conf, song)
        window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        window.connect('button-press-event', self.__buttonpress)
        window.connect('fade-finished', self.__fade_finished)
        self.__current_window = window

        window.set_opacity(0.0)
        window.show()
        window.fade_in()

    @staticmethod
    def start_fade_out(window):
        window.fade_out()
        return False

    def __buttonpress(self, window, event):
        window.hide()
        if self.__current_window is window:
            self.__current_window = None
        window.destroy()

    def __fade_finished(self, window, fade_in):
        if fade_in:
            GLib.timeout_add(self.Conf.delay, self.start_fade_out, window)
        else:
            window.hide()
            if self.__current_window is window:
                self.__current_window = None
            # Delay destroy - apparently the hide does not quite register if
            # the destroy is done immediately.  The compiz animation plugin
            # then sometimes triggers and causes undesirable effects while the
            # popup should already be invisible.
            GLib.timeout_add(1000, window.destroy)
