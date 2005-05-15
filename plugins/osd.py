# Copyright 2004 Gustavo J. A. M. Carneiro
#           2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import pango
import gtk
import gtk.gdk as gdk
import gobject

import config
import util
from widgets import tag
from qltk import ConfigCheckButton

class Osd(object):
    PLUGIN_NAME = "On-Screen Display"
    PLUGIN_DESC = "Display song information on your screen when it changes."
    PLUGIN_VERSION = "0.11"

    BORDER = 4

    def PluginPreferences(self, parent):
        w = gtk.Window()
        w.set_title("OSD")
        w.set_resizable(False)
        w.set_border_width(12)
        w.add(gtk.VBox(spacing=12))

        c = ConfigCheckButton("Use global GNOME OSD", "plugins", "osd_bonobo")
        c.set_sensitive(bool(self.__bonobo))
        w.child.pack_start(c, expand=False)

        cb = gtk.combo_box_new_text()
        cb.append_text('Display OSD on the top')
        cb.append_text('Display OSD on the bottom')
        cb.set_active(config.getint('plugins', 'osd_position'))
        cb.connect('changed', self.__changed)
        box = gtk.VBox(spacing=6)
        box.pack_start(cb, expand=False)

        hbox = gtk.HBox(spacing=6)
        c1, c2 = config.get("plugins", "osd_colors").split()
        color1 = gtk.ColorButton(gtk.gdk.color_parse(c1))
        color2 = gtk.ColorButton(gtk.gdk.color_parse(c2))
        tips = gtk.Tooltips()
        tips.set_tip(color1, "Select a color for the OSD")
        tips.set_tip(color2, "Select a second color for the OSD")
        color1.connect('color-set', self.__color_set, color1, color2)
        color2.connect('color-set', self.__color_set, color1, color2)
        font = gtk.FontButton(config.get("plugins", "osd_font"))
        font.set_size_request(200, -1)
        font.connect('font-set', self.__font_set)
        hbox.pack_start(color1, expand=False)
        hbox.pack_start(color2, expand=False)
        hbox.pack_start(font)
        box.pack_start(hbox, expand=False)

        w.child.pack_start(box)
        w.child.show_all()

        w.set_transient_for(parent)
        w.connect_object('destroy', gtk.Tooltips.destroy, tips)
        w.connect('delete-event', self.__delete)
        c.connect('toggled', self.__use_bonobo, cb, font, color1)
        c.set_active(
            config.getboolean("plugins", "osd_bonobo") and bool(self.__bonobo))
        return w

    def __delete(self, prefs, event):
        prefs.hide()
        return True

    def __use_bonobo(self, active, *other):
        if active.get_active(): self.__osd = self.__bonobo
        else: self.__osd = self
        for o in other: o.set_sensitive(self.__osd is self)

    def __font_set(self, font):
        config.set("plugins", "osd_font", font.get_font_name())

    def __color_set(self, color, c1, c2):
        color = c1.get_color()
        ct1 = (color.red // 256, color.green // 256, color.blue // 256)
        color = c2.get_color()
        ct2 = (color.red // 256, color.green // 256, color.blue // 256)
        config.set("plugins", "osd_colors",
                   "#%02x%02x%02x #%02x%02x%02x" % (ct1+ct2))

    def __changed(self, cb):
        config.set("plugins", "osd_position",  str(cb.get_active()))

    def __init__(self):
        for key, value in {
            "bonobo": "true",
            "position": "0",
            "colors": "#ffbb00 #ff8800",
            "font": "Sans 22"}.items():
            try: config.get("plugins", "osd_" + key)
            except: config.set("plugins", "osd_" + key, value)

        # Use the Bonobo interface if available, otherwise use our
        # internal implementation.
        try:
            import bonobo
            self.__bonobo = bonobo.get_object(
                "OAFIID:GNOME_OSD", "IDL:Bonobo/Application:1.0")
            if config.getboolean("osd_bonobo"): self.__osd = self.__bonobo
            else: self.__osd = self
        except:
            self.__bonobo = False
            self.__osd = self

        self.__window = None
        self.__level = 0

    def plugin_on_song_started(self, song):
        if song is None: return

        color1, color2 = config.get("plugins", "osd_colors").split()

        # \xe2\x99\xaa is a music note.
        msg = "\xe2\x99\xaa "

        msg += "<span foreground='%s' style='italic'>%s</span>" %(
            color2, util.escape(song("~title~version")))
        msg += " <span size='small'>(%s)</span> " % song("~length")
        msg += "\xe2\x99\xaa\n"

        msg += "<span size='x-small'>"
        for key in ["artist", "album", "tracknumber"]:
            if key in song:
                msg += ("<span foreground='%s' size='xx-small' "
                        "style='italic'>%s</span> %s   "%(
                    (color2, tag(key), util.escape(song.comma(key)))))
        msg = msg.strip() + "</span>"
        if isinstance(msg, unicode):
            msg = msg.encode("utf-8")
        msg = "<message id='quodlibet'>%s</message>" % msg
        self.__osd.msg_send('show', [msg])

    def msg_send(self, command, (msg,), bgcolor="black"):
        if command != "show": return
        text = msg[msg.index(">")+1:msg.rindex("<")]

        fgcolor = config.get("plugins", "osd_colors").split()[0]

        if self.__window: self.__window.destroy()
        self.__level += 1

        try:
            fontdesc = pango.FontDescription(config.get("plugins", "osd_font"))
        except: fontdesc = pango.FontDescription("Sans 22")

        win = gtk.Window(gtk.WINDOW_POPUP)
        win.add_events(gtk.gdk.POINTER_MOTION_MASK)
        darea = gtk.DrawingArea()
        win.add(darea)
        darea.show()
        layout = win.create_pango_layout('')
        layout.set_markup(text)
        layout.set_justify(False)
        layout.set_alignment(pango.ALIGN_CENTER)
        layout.set_font_description(fontdesc)

        monitor = gdk.Screen.get_monitor_geometry(gdk.screen_get_default(), 0)
        MAX_WIDTH = monitor.width - 8
        layout.set_width(pango.SCALE*MAX_WIDTH)
        layout.set_wrap(pango.WRAP_WORD)
        width, height = layout.get_pixel_size()
        off_x = self.BORDER * 2
        off_y = self.BORDER * 2

        off_x -= MAX_WIDTH / 2 - width / 2

        width += self.BORDER * 4
        height += self.BORDER * 4
        darea.set_size_request(width, height)
        darea.realize()
        pixmap = gtk.gdk.Pixmap(darea.window, width, height)

        fg_gc = gdk.GC(pixmap); fg_gc.copy(darea.style.fg_gc[gtk.STATE_NORMAL])
        bg_gc = gdk.GC(pixmap); bg_gc.copy(darea.style.fg_gc[gtk.STATE_NORMAL])
        fg_gc.set_colormap(darea.window.get_colormap())
        bg_gc.set_colormap(darea.window.get_colormap())
        fg_gc.set_foreground(darea.get_colormap().alloc_color(fgcolor))
        bg_gc.set_background(darea.get_colormap().alloc_color(bgcolor))
        pixmap.draw_rectangle(bg_gc, True, 0, 0, width, height)
        pixmap.draw_layout(fg_gc, off_x, off_y, layout)

        bitmap = gtk.gdk.Pixmap(None, width, height, 1)
        fg_gc = gdk.GC(bitmap)
        bg_gc = gdk.GC(bitmap)
        fg_gc.set_colormap(darea.window.get_colormap())
        bg_gc.set_colormap(darea.window.get_colormap())
        fg_gc.set_foreground(gdk.Color(pixel=-1))
        bg_gc.set_background(gdk.Color(pixel=0))
        bitmap.draw_rectangle(bg_gc, True, 0, 0, width, height)
        for dx in range(-self.BORDER, self.BORDER + 1):
            for dy in range(-self.BORDER, self.BORDER + 1):
                if dx*dx + dy*dy >= self.BORDER * self.BORDER: continue
                bitmap.draw_layout(fg_gc, off_x + dx, off_y + dy, layout)

        darea.window.set_back_pixmap(pixmap, False)
        win.window.shape_combine_mask(bitmap, 0, 0)
        win.width = width
        win.height = height

        at_bottom = config.getboolean("plugins", "osd_position")
        position = (at_bottom and gdk.screen_height() - win.height - 48) or 5
        gobject.idle_add(
            win.move, monitor.x + monitor.width / 2 - win.width / 2,
            monitor.y + position)
        gobject.idle_add(win.show_all)
        self.__window = win
        gobject.timeout_add(7500, self.__unshow)

    def __unshow(self):
        self.__level -= 1
        if self.__level == 0 and self.__window:
            gobject.idle_add(self.__window.destroy)
            self.__window = None
