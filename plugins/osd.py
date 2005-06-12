# Copyright 2004 Gustavo J. A. M. Carneiro
#           2005 Joe Wreschnig, Ton van den Heuvel
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
    PLUGIN_VERSION = "0.11.2"

    BORDER = 4
    __sid = None
    __window = None
    __level = 0

    def PluginPreferences(self, parent):
        w = gtk.Window()
        w.set_title("OSD Preferences")
        w.set_resizable(False)
        w.set_border_width(12)
        w.add(gtk.HBox(spacing=12))

        def Label(t): l = gtk.Label(t); l.set_alignment(0.0, 0.5); return l

        t = gtk.Table(2, 3)
        t.set_col_spacings(6)
        t.set_row_spacings(6)
        t.attach(Label("Text color #1:"), 0, 1, 0, 1)
        t.attach(Label("Text color #2:"), 0, 1, 1, 2)
        t.attach(Label("Background:"), 0, 1, 2, 3)
        c1, c2, c3 = config.get("plugins", "osd_colors").split()
        color1 = gtk.ColorButton(gtk.gdk.color_parse(c1))
        color2 = gtk.ColorButton(gtk.gdk.color_parse(c2))
        color3 = gtk.ColorButton(gtk.gdk.color_parse(c3))
        t.attach(color1, 1, 2, 0, 1)
        t.attach(color2, 1, 2, 1, 2)
        t.attach(color3, 1, 2, 2, 3)
        color1.connect('color-set', self.__color_set, color1, color2, color3)
        color2.connect('color-set', self.__color_set, color1, color2, color3)
        color3.connect('color-set', self.__color_set, color1, color2, color3)

        w.child.pack_start(t, expand=False)

        cb = gtk.combo_box_new_text()
        cb.append_text('Display OSD on the top')
        cb.append_text('Display OSD on the bottom')
        cb.set_active(config.getint('plugins', 'osd_position'))
        cb.connect('changed', self.__changed)
        box = gtk.VBox(spacing=6)
        box.pack_start(cb, expand=False)

        font = gtk.FontButton(config.get("plugins", "osd_font"))
        font.set_size_request(200, -1)
        font.connect('font-set', self.__font_set)
        box.pack_start(font, expand=False)

        hbox = gtk.HBox(spacing=6)
        hbox.pack_start(Label("Background Transparency:"))
        transparency = gtk.SpinButton(gtk.Adjustment(
            config.getint("plugins", "osd_transparency"), 0, 100, 1, 10, 10))
        transparency.connect('value-changed', self.__transparency_set)
        hbox.pack_start(transparency, expand=False)
        box.pack_start(hbox, expand=False)

        w.child.pack_start(box)
        w.child.show_all()

        w.set_transient_for(parent)
        w.connect('delete-event', self.__delete)
        return w

    def __delete(self, prefs, event):
        prefs.hide()
        return True

    def __font_set(self, font):
        config.set("plugins", "osd_font", font.get_font_name())

    def __color_set(self, color, c1, c2, c3):
        color = c1.get_color()
        ct1 = (color.red // 256, color.green // 256, color.blue // 256)
        color = c2.get_color()
        ct2 = (color.red // 256, color.green // 256, color.blue // 256)
        color = c3.get_color()
        ct3 = (color.red // 256, color.green // 256, color.blue // 256)
        config.set("plugins", "osd_colors",
                   "#%02x%02x%02x #%02x%02x%02x #%02x%02x%02x" % (ct1+ct2+ct3))

    def __transparency_set(self, transparency):
        config.set(
            "plugins", "osd_transparency",str(int(transparency.get_value())))

    def __changed(self, cb):
        config.set("plugins", "osd_position",  str(cb.get_active()))

    def __init__(self):
        for key, value in {
            "position": "0",
            "colors": "#ffbb00 #ff8800 #000000",
            "font": "Sans 22",
            "transparency": "75"}.items():
            try: config.get("plugins", "osd_" + key)
            except: config.set("plugins", "osd_" + key, value)
        if len(config.get("plugins", "osd_colors").split()) == 2:
            config.set("plugins", "osd_colors",
                config.get("plugins", "osd_colors") + " #000000")

    def plugin_on_song_started(self, song):
        if song is None: return

        self.__cover = song.find_cover()

        color1, color2 = config.get("plugins", "osd_colors").split()[:2]

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
                        "style='italic'>%s:</span> %s   "%(
                    (color2, tag(key), util.escape(song.comma(key)))))
        msg = msg.strip() + "</span>"
        if isinstance(msg, unicode):
            msg = msg.encode("utf-8")
        msg = "<message id='quodlibet'>%s</message>" % msg
        self.__sid = gobject.timeout_add(500, self.__display, msg)

    def plugin_on_song_ended(self, song, stopped):
        if self.__window:
            self.__window.destroy()
            self.__window = None
        if self.__sid:
            gobject.source_remove(self.__sid)
            self.__sid = None

    def __display(self, msg, bgcolor="black"):
        text = msg[msg.index(">")+1:msg.rindex("<")]

        fgcolor = config.get("plugins", "osd_colors").split()[0]
        border_color = config.get("plugins", "osd_colors").split()[2]

        if self.__window: self.__window.destroy()
        self.__level += 1

        try:
            fontdesc = pango.FontDescription(config.get("plugins", "osd_font"))
        except: fontdesc = pango.FontDescription("Sans 22")

        win = gtk.Window(gtk.WINDOW_POPUP)
        ev = gtk.EventBox()
        win.add(ev)
        win.connect('button-press-event', self.__unshow)

        darea = gtk.DrawingArea()
        ev.add(darea)
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

        # Initialize width and height with the size of the pango layout.
        width, height = layout.get_pixel_size()
        
        # Calculate final panel height by adding a border.
        height += self.BORDER * 4

        # Calculate the cover dimensions (if one is available)
        if not self.__cover is None:
            cover_dim = height - 2 * self.BORDER
        else:
            cover_dim = 0

        # Calculate text offsets.
        off_x = self.BORDER * 4 + cover_dim + width / 2 - MAX_WIDTH / 2
        off_y = self.BORDER * 2

        # Calculate panel width.
        width += self.BORDER * 6 + cover_dim

        darea.set_size_request(width, height)
        darea.realize()

        # Draw the surrounding panel.
        pixmap = gtk.gdk.Pixmap(darea.window, width, height)
        bg_gc = gdk.GC(pixmap)
        bg_gc.copy(darea.style.fg_gc[gtk.STATE_NORMAL])
        bg_gc.set_colormap(darea.window.get_colormap())

        win.width = width
        win.height = height

        at_bottom = config.getboolean("plugins", "osd_position")
        position = (at_bottom and gdk.screen_height() - win.height - 48) or 5

        x = monitor.x + monitor.width / 2 - win.width / 2
        y = monitor.y + position

        transparency = config.getint("plugins", "osd_transparency")
        if transparency < 100:
            # Draw contents.
            bg_color = (min(int(border_color[1:3], 16) + 30, 255),
                        min(int(border_color[3:5], 16) + 30, 255),
                        min(int(border_color[5:7], 16) + 30, 255))
            bg_color = '#%02x%02x%02x' % bg_color

            bg_gc.set_foreground(darea.get_colormap().alloc_color(bg_color))
            pixmap.draw_rectangle(bg_gc, True, 1, 1, width - 2, height - 2)

            # Get root window contents at panel position.
            root_win = gdk.Screen.get_root_window(gdk.screen_get_default())
            root_pb = gtk.gdk.Pixbuf(
                gtk.gdk.COLORSPACE_RGB, 0, 8, width, height)
            root_pb.get_from_drawable(
                root_win, root_win.get_colormap(), x, y, 0, 0, width, height)

            # Composite panel pixbuf with root pixbuf.
            composited = gtk.gdk.Pixbuf(
                gtk.gdk.COLORSPACE_RGB, 0, 8, width, height)
            composited.get_from_drawable(
                pixmap, pixmap.get_colormap(), 0, 0, 0, 0, width, height)

            alpha = 255 - int((transparency / 100.0) * 255)
            composited.composite(
                root_pb, 0, 0, width, height, 0, 0, 1, 1,
                gtk.gdk.INTERP_BILINEAR, alpha)
            pixmap.draw_pixbuf(
                darea.style.fg_gc[gtk.STATE_NORMAL], root_pb,
                0, 0, 0, 0, -1, -1)

            # Draw panel border.
            bg_gc.set_foreground(
                darea.get_colormap().alloc_color(border_color))
            pixmap.draw_rectangle(bg_gc, False, 0, 0, width - 1, height - 1)

        # Draw layout.
        fg_gc = gdk.GC(pixmap) 
        fg_gc.copy(darea.style.fg_gc[gtk.STATE_NORMAL])
        fg_gc.set_colormap(darea.window.get_colormap())
        fg_gc.set_foreground(darea.get_colormap().alloc_color(fgcolor))
        pixmap.draw_layout(fg_gc, off_x, off_y, layout)

        # Draw the cover image (if available).
        if not self.__cover is None:
            try:
                cover = gtk.gdk.pixbuf_new_from_file_at_size(
                    self.__cover.name, cover_dim, cover_dim)
            except: self.__cover = None
            else:
                left = self.BORDER + (cover_dim - coverPixmap.get_width())/2
                top = self.BORDER + (cover_dim - coverPixmap.get_height())/2
                pixmap.draw_pixbuf(darea.style.fg_gc[gtk.STATE_NORMAL],
                                   cover, 0, 0, left, top)
                # Draw a border around the cover image.
                bg_gc.set_foreground(darea.get_colormap().alloc_color("black"))
                pixmap.draw_rectangle(
                    bg_gc, False, left - 1, top - 1,
                    cover.get_width() + 1, cover.get_height() + 1)

        darea.window.set_back_pixmap(pixmap, False)
        if transparency == 100:
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

            win.window.shape_combine_mask(bitmap, 0, 0)
        gobject.idle_add(win.move, x, y)
        gobject.idle_add(win.show_all)
        self.__window = win
        gobject.timeout_add(7500, self.__unshow)

    def __unshow(self, *args):
        self.__level -= 1
        if self.__level == 0 and self.__window:
            gobject.idle_add(self.__window.destroy)
            self.__window = None
