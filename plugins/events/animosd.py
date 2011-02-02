# Copyright (C) 2008 Andreas Bombe
# Copyright (C) 2005  Michael Urman
# Based on osd.py (C) 2005 Ton van den Heuvel, Joe Wreshnig
#                 (C) 2004 Gustavo J. A. M. Carneiro
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#

import gtk
import gobject
import pango
import cairo
import pangocairo

from quodlibet import config, qltk
from quodlibet.qltk.textedit import PatternEdit
from quodlibet.parse import XMLFromPattern
from quodlibet.plugins.events import EventPlugin

def Label(text):
    l = gtk.Label(text)
    l.set_alignment(0.0, 0.5)
    return l

class OSDWindow(gtk.Window):
    __gsignals__ = {
            'expose-event': 'override',
            'fade-finished': (gobject.SIGNAL_RUN_LAST, None, (bool,)),
            }

    def __init__(self, conf, song):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_NOTIFICATION)

        # for non-composite operation
        self.background_pixbuf = None
        self.titleinfo_surface = None

        screen = self.get_screen()
        cmap = screen.get_rgba_colormap()
        if cmap is None:
            cmap = screen.get_rgb_colormap()
        self.set_colormap(cmap)

        self.conf = conf
        self.iteration_source = None

        cover = song.find_cover()
        try:
            if cover is not None:
                cover = gtk.gdk.pixbuf_new_from_file(cover.name)
        except gobject.GError, gerror:
            print 'Error while loading cover image:', gerror.message
        except:
            from traceback import print_exc
            print_exc()

        # now calculate size of window
        mgeo = screen.get_monitor_geometry(0)
        coverwidth = min(120, mgeo.width // 8)
        textwidth = mgeo.width - 2 * (conf.border + conf.margin)
        if cover is not None:
            textwidth -= coverwidth + conf.border
            coverheight = int(cover.get_height() * (float(coverwidth) /
                cover.get_width()))
        else:
            coverheight = 0
        self.cover_pixbuf = cover
        self.cover_rectangle = gtk.gdk.Rectangle(conf.border, conf.border,
                coverwidth, coverheight)

        layout = self.create_pango_layout('')
        layout.set_alignment(pango.ALIGN_CENTER)
        layout.set_font_description(pango.FontDescription(conf.font))
        layout.set_markup(XMLFromPattern(conf.string) % song)
        layout.set_width(pango.SCALE * textwidth)
        layoutsize = layout.get_pixel_size()
        if layoutsize[0] < textwidth:
            layout.set_width(pango.SCALE * layoutsize[0])
            layoutsize = layout.get_pixel_size()
        self.title_layout = layout

        winw = layoutsize[0] + 2 * conf.border
        if cover is not None:
            winw += coverwidth + conf.border
        winh = max(coverheight, layoutsize[1]) + 2 * conf.border
        self.set_default_size(winw, winh)

        winx = int((mgeo.width - winw) * conf.pos_x)
        winx = max(conf.margin, min(mgeo.width - conf.margin - winw, winx))
        winy = int((mgeo.height - winh) * conf.pos_y)
        winy = max(conf.margin, min(mgeo.height - conf.margin - winh, winy))
        self.move(winx + mgeo.x, winy + mgeo.y)

    def do_expose_event(self, event):
        cr = self.window.cairo_create()

        if self.is_composited():
            # the simple case
            self.draw_title_info(cr)
            return

        # manual transparency rendering follows
        back_pbuf = self.background_pixbuf
        title_surface = self.titleinfo_surface
        walloc = self.allocation
        wpos = self.get_position()

        if back_pbuf is None:
            root = self.get_screen().get_root_window()
            back_pbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8,
                    walloc.width, walloc.height)
            back_pbuf.get_from_drawable(root, root.get_colormap(),
                    wpos[0], wpos[1], 0, 0, walloc.width, walloc.height)
            self.background_pixbuf = back_pbuf

        if title_surface is None:
            title_surface = gtk.gdk.Pixmap(self.window, walloc.width,
                    walloc.height)
            titlecr = title_surface.cairo_create()
            self.draw_title_info(titlecr)

        cr.set_operator(cairo.OPERATOR_SOURCE)
        if back_pbuf is not None:
            cr.set_source_pixbuf(back_pbuf, 0, 0)
        else:
            cr.set_source_rgb(0.3, 0.3, 0.3)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_pixmap(title_surface, 0, 0)
        cr.paint_with_alpha(self.get_opacity())

    def draw_title_info(self, cr):
        #cr.set_line_width(1.0)
        do_shadow = self.conf.shadow is not None
        do_outline = self.conf.outline is not None

        # clear with configured background fill
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(*self.conf.fill)
        cr.paint()

        cr.set_operator(cairo.OPERATOR_OVER)

        # draw border
        if self.conf.bcolor is not None:
            cr.set_source_rgb(*self.conf.bcolor)
            a = self.allocation
            cr.rectangle(a.x, a.y, a.width, a.height)
            cr.stroke()

        textx = self.conf.border

        if self.cover_pixbuf is not None:
            rect = self.cover_rectangle
            textx += rect.width + self.conf.border
            pbuf = self.cover_pixbuf
            transmat = cairo.Matrix()

            if do_shadow:
                cr.set_source_rgb(*self.conf.shadow)
                cr.rectangle(rect.x + 2, rect.y + 2, rect.width, rect.height)
                cr.fill()

            if do_outline:
                cr.set_source_rgb(*self.conf.outline)
                cr.rectangle(rect)
                cr.stroke()

            cr.set_source_pixbuf(pbuf, 0, 0)
            transmat.scale(pbuf.get_width() / float(rect.width),
                    pbuf.get_height() / float(rect.height))
            transmat.translate(-rect.x, -rect.y)
            cr.get_source().set_matrix(transmat)
            cr.rectangle(rect)
            cr.fill()

        pcc = pangocairo.CairoContext(cr)
        pcc.update_layout(self.title_layout)

        if do_shadow:
            cr.set_source_rgb(*self.conf.shadow)
            cr.move_to(textx + 2, self.conf.border + 2)
            pcc.show_layout(self.title_layout)
        if do_outline:
            cr.set_source_rgb(*self.conf.outline)
            cr.move_to(textx, self.conf.border)
            pcc.layout_path(self.title_layout)
            cr.stroke()
        cr.set_source_rgb(*self.conf.text)
        cr.move_to(textx, self.conf.border)
        pcc.show_layout(self.title_layout)

    def fade_in(self):
        self.do_fade_inout(True)

    def fade_out(self):
        self.do_fade_inout(False)

    def do_fade_inout(self, fadein):
        fadein = bool(fadein)

        self.fading_in = fadein
        now = gobject.get_current_time()

        fraction = self.get_opacity()
        if not fadein:
            fraction = 1.0 - fraction
        self.fade_start_time = now - fraction * self.conf.fadetime

        if self.iteration_source is None:
            self.iteration_source = gobject.timeout_add(self.conf.ms,
                    self.fade_iteration_callback)

    def fade_iteration_callback(self):
        delta = gobject.get_current_time() - self.fade_start_time
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

class AnimOsd(EventPlugin):
    PLUGIN_ID = "Animated On-Screen Display"
    PLUGIN_NAME = _("Animated On-Screen Display")
    PLUGIN_DESC = _("Display song information on your screen when it changes.")
    PLUGIN_VERSION = "1.0"

    def PluginPreferences(self, parent):
        def __coltofloat(x):
            return x / 65535.0
        def __floattocol(x):
            return int(x * 65535)

        def set_text(button):
            color = button.get_color()
            color = map(__coltofloat, (color.red, color.green, color.blue))
            config.set("plugins", "animosd_text",
                    "%f %f %f" % (color[0], color[1], color[2]))
            self.conf.text = tuple(color)

        def set_fill(button):
            color = button.get_color()
            color = map(__coltofloat, (color.red, color.green, color.blue,
                button.get_alpha()))
            config.set("plugins", "animosd_fill",
                    "%f %f %f %f" % (color[0], color[1], color[2], color[3]))
            self.conf.fill = tuple(color)

        def set_font(button):
            font = button.get_font_name()
            config.set("plugins", "animosd_font", font)
            self.conf.font = font

        def change_delay(button):
            value = int(button.get_value() * 1000)
            config.set("plugins", "animosd_delay", str(value))
            self.conf.delay = value

        def change_position(button):
            value = button.get_active() / 2.0
            config.set("plugins", "animosd_pos_y", str(value))
            self.conf.pos_y = value

        def edit_string(button):
            w = PatternEdit(button, AnimOsd.conf.string)
            w.child.text = self.conf.string
            w.apply.connect_object_after('clicked', set_string, w)

        def set_string(window):
            value = window.child.text
            config.set("plugins", "animosd_string", value)
            self.conf.string = value

        vb = gtk.VBox(spacing=6)

        cb = gtk.combo_box_new_text()
        cb.append_text(_("Display on top of screen"))
        cb.append_text(_("Display in middle of screen"))
        cb.append_text(_("Display on bottom of screen"))
        cb.set_active(int(self.conf.pos_y * 2.0))
        cb.connect('changed', change_position)
        vb.pack_start(cb, expand=False)

        font = gtk.FontButton()
        font.set_font_name(self.conf.font)
        font.connect('font-set', set_font)
        vb.pack_start(font, expand=False)

        hb = gtk.HBox(spacing=3)
        timeout = gtk.SpinButton(
            gtk.Adjustment(
            self.conf.delay/1000.0, 0, 60, 0.1, 1.0, 1.0), 0.1, 1)
        timeout.set_numeric(True)
        timeout.connect('value-changed', change_delay)

        hb.pack_start(Label("Display delay: "), expand=False)
        hb.pack_start(timeout, expand=False);
        hb.pack_start(Label("seconds"), expand=False)
        vb.pack_start(hb, expand=False)

        t = gtk.Table(2, 2)
        t.set_col_spacings(3)
        b = gtk.ColorButton(color=gtk.gdk.Color(*map(__floattocol,
            self.conf.text)))
        l = Label(_("_Text:"))
        l.set_mnemonic_widget(b); l.set_use_underline(True)
        t.attach(l, 0, 1, 0, 1, xoptions=gtk.FILL)
        t.attach(b, 1, 2, 0, 1)
        b.connect('color-set', set_text)
        b = gtk.ColorButton(color=gtk.gdk.Color(*map(__floattocol,
            self.conf.fill[0:3])))
        b.set_use_alpha(True)
        b.set_alpha(__floattocol(self.conf.fill[3]))
        b.connect('color-set', set_fill)
        l = Label(_("_Fill:"))
        l.set_mnemonic_widget(b); l.set_use_underline(True)
        t.attach(l, 0, 1, 1, 2, xoptions=gtk.FILL)
        t.attach(b, 1, 2, 1, 2)

        f = qltk.Frame(label=_("Colors"), child=t)
        f.set_border_width(12)
        vb.pack_start(f, expand=False, fill=False)

        string = qltk.Button(_("_Edit Display"), gtk.STOCK_EDIT)
        string.connect('clicked', edit_string)
        vb.pack_start(string, expand=False)
        return vb

    class conf(object):
        pos_x = 0.5 # position of window 0--1 horizontal
        pos_y = 0.0 # position of window 0--1 vertical
        margin = 16 # never any closer to the screen edge than this
        border = 8 # text/cover this far apart, from edge
        fadetime = 1.5 # take this many seconds to fade in or out
        ms = 40 # wait this many milliseconds between steps
        delay = 2500 # wait this many milliseconds before hiding
        font = "Sans 22"
        text = (1.0, 0.8125, 0.586) # main font color
        outline = (0.125, 0.125, 0.125) # color or None - surrounds text and cover
        shadow = (0.0, 0.0, 0.0) # color or None - shadows outline or text and cover
        fill = (0.25, 0.25, 0.25, 0.5) # color+alpha or None - fills rectangular area
        bcolor = (0.0, 0.0, 0.0) # color or None - borders rectangular area
        # song information to use - like in main window
        string = r'''<album|\<b\><album>\</b\><discnumber| - Disc <discnumber>><part| - \<b\><part>\</b\>><tracknumber| - <tracknumber>>
>\<span weight='bold' size='large'\><title>\</span\> - <~length><version|
\<small\>\<i\><version>\</i\>\</small\>><~people|
by <~people>>'''

    def __init__(self):
        self.__current_window = None

        # now load config, resetting values which had errors to their default
        def str_to_tuple(s):
            return tuple(map(float, s.split()))
        def tuple_to_str(t):
            return ' '.join(map(str, t))
        config_map = [
            ('text', config.get, str_to_tuple, tuple_to_str),
            ('fill', config.get, str_to_tuple, tuple_to_str),
            ('font', config.get, None, str),
            ('delay', config.getint, None, str),
            ('pos_y', config.getfloat, None, str),
            ('string', config.get, None, str),
            ]
        for key, cget, getconv, setconv in config_map:
            try: value = cget('plugins', 'animosd_' + key)
            except: continue
            try:
                if getconv is not None:
                    value = getconv(value)
            except:
                # auto-upgrade old hash-values to new tuple floats
                if (value is not None and value.startswith('#')) and \
                        ((key == 'text' and len(value) == 7) or \
                         (key == 'fill' and len(value) == 9)):
                    colors = [value[1:3], value[3:5], value[5:7]]
                    # fill has extra value for alpha
                    if key == 'fill':
                        colors.append(value[7:9])
                    colors = [int(c, 16) / 255.0 for c in colors]
                    config.set('plugins', 'animosd_' + key,
                            setconv(colors))
                else:
                    config.set('plugins', 'animosd_' + key,
                            setconv(getattr(self.conf, key)))
            else:
                setattr(self.conf, key, value)

    # for rapid debugging
    def plugin_single_song(self, song):
        self.plugin_on_song_started(song)

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

        window = OSDWindow(self.conf, song)
        window.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        window.connect('button-press-event', self.__buttonpress)
        window.connect('fade-finished', self.__fade_finished)
        self.__current_window = window

        window.set_opacity(0.0)
        window.show()
        window.fade_in()

    def start_fade_out(self, window):
        window.fade_out()
        return False

    def __buttonpress(self, window, event):
        window.hide()
        if self.__current_window is window:
            self.__current_window = None
        window.destroy()

    def __fade_finished(self, window, fade_in):
        if fade_in:
            gobject.timeout_add(self.conf.delay, self.start_fade_out, window)
        else:
            window.hide()
            if self.__current_window is window:
                self.__current_window = None
            # Delay destroy, apparantly the hide does not quite register if
            # the destroy is done immediately.  The compiz animation plugin
            # then sometimes triggers and causes undesirable effects while the
            # popup should already be invisible.
            gobject.timeout_add(1000, window.destroy)
