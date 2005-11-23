# Copyright (C) 2005  Michael Urman
# Based on osd.py (C) 2005 Ton van den Heuvel, Joe Wreshnig
#                 (C) 2004 Gustavo J. A. M. Carneiro
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#

import gtk, gobject, pango, pattern

class AnimOsd(object):
    PLUGIN_NAME = "Animated On-Screen Display"
    PLUGIN_DESC = "Display song information on your screen when it changes."
    PLUGIN_VERSION = "0.14.1"

    # mu's default settings - this needs to be configurable
    class conf(object):
        pos = 0.5, 0.0 # position of window 0--1 horizontal, 0--1 vertical
        margin = 16 # never any closer to the screen edge than this
        border = 4 # text/cover this far apart, from edge
        step = 32 # of 256, how far to jump each step of animation
        ms = 80 # wait this many milliseconds between steps
        delay = 2500 # wait this many milliseconds before hiding
        font = "Sans 22"
        text = "#ffd096" # main font color
        outline = "#202020" # color or None - surrounds text and cover
        shadow = "#000000" # color or None - shadows outline or text and cover
        fill = "#40404080" # color+alpha or None - fills rectangular area
        bcolor = "#000000" # color or None - borders rectangular area
        # song information to use - like in main window
        string = r'''<album|\<b\><album>\</b\><discnumber| - Disc <discnumber>><part| - \<b\><part>\</b\>><tracknumber| - <tracknumber>>
>\<span weight='bold' size='large'\><title>\</span\> - <~length><version|
\<small\>\<i\><version>\</i\>\</small\>><~people|
by <~people>>'''

    def __init__(self):
        window = self.__window = gtk.Window(gtk.WINDOW_POPUP)
        window.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        window.connect('button-press-event', self.__buttonpress)
        darea = self.__darea = gtk.DrawingArea()
        window.add(self.__darea)
        darea.show()
        darea.realize()
        layout = self.__layout = window.create_pango_layout("")
        layout.set_justify(False)
        layout.set_alignment(pango.ALIGN_CENTER)
        layout.set_font_description(pango.FontDescription(self.conf.font))
        layout.set_wrap(pango.WRAP_WORD)
        self.__step = 0 # 0=invisible; 255=fully visible
        self.__stepby = 0
        self.__song = None
        self.__next = None
        self.__screen = gtk.gdk.screen_get_default()
        geom = gtk.gdk.Screen.get_monitor_geometry(self.__screen, 0)
        self.__screenwidth = geom.width
        self.__screenheight = geom.height
        self.__coverwidth = min(120, self.__screenwidth // 8)
        self.__width = self.__height = self.__coverwidth + 2 * self.conf.border
        self.__delayhide = None

    # for rapid debugging
    def plugin_single_song(self, song): self.plugin_on_song_started(song)

    def plugin_on_song_started(self, song):
        self.__next = song
        gobject.idle_add(self.show)

    def wait_until_hidden(self):
        while self.__stepby < 0:
            gtk.main_iteration()

    def hide(self):
        if self.__step <= 0:
            return

        # cancel any pending hides.
        if self.__delayhide is not None:
            gobject.source_remove(self.__delayhide)
            self.__delayhide = None

        if self.__stepby == 0:
            self.__stepby = -self.conf.step
            gobject.timeout_add(self.conf.ms, self.render)

    def show(self):
        if self.__step > 0:
            self.hide()
            return

        if self.__next is not None:
            self.__song = self.__next
            self.__next = None
        if self.__song is None:
            return

        if self.__step >= 255:
            return

        self.render_setup(self.__song)

        if self.__stepby == 0:
            self.__stepby = self.conf.step
            gobject.timeout_add(self.conf.ms, self.render)

    def render_setup(self, song):
        # size cover
        cover = self.__cover = song.find_cover()
        if cover is not None:
            try:
                self.__cover = gtk.gdk.pixbuf_new_from_file_at_size(
                    cover.name, self.__coverwidth, self.__coverwidth)
                cw = self.__cover.get_width()
                ch = self.__cover.get_height()
                self.__coverx = self.conf.border + (self.__coverwidth - cw) // 2
                self.__covery = self.conf.border + (self.__coverwidth - ch) // 2
            except:
                from traceback import print_exc; print_exc()
                self.__cover = None

        # size text
        tw = (self.__screenwidth - 2 * (self.conf.border + self.conf.margin))
        if self.__cover is not None:
            tw -= self.__coverwidth + self.conf.border
        layout = self.__layout
        layout.set_markup(pattern.XMLFromPattern(self.conf.string) % song)
        layout.set_width(pango.SCALE * tw)
        self.__textsize = layout.get_pixel_size()
        layout.set_width(pango.SCALE * min(self.__textsize[0], tw))
        self.__textsize = layout.get_pixel_size()

        # size window to text + cover
        w = self.__textsize[0] + 2 * self.conf.border
        h = max(self.__cover and self.__coverwidth or 0,
                self.__textsize[1]) + 2 * self.conf.border
        if self.__cover is not None:
            w += self.__coverwidth + self.conf.border
            self.__covery = (h - ch) // 2
        darea = self.__darea
        darea.set_size_request(w, h)
        self.__width = w
        self.__height = h

        # figure positions
        sw, sh = self.__screenwidth, self.__screenheight
        m = self.conf.margin
        x = int((sw - w) * self.conf.pos[0])
        x = self.__winx = max(m, min(sw - m - w, x))
        y = int((sh - h) * self.conf.pos[1])
        y = self.__winy = max(m, min(sh - m - h, y))

        self.__textx = self.conf.border
        if self.__cover is not None:
            self.__textx += self.__coverwidth + self.conf.border
        self.__texty = (h - self.__textsize[1]) // 2

        # scrape root for pseudo transparancy
        root = gtk.gdk.Screen.get_root_window(self.__screen)
        self.__bg = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 0, 8, w, h)
        self.__bg.get_from_drawable(root, root.get_colormap(),
                x, y, 0, 0, w, h)

        # iter 1: prerender the whole thing, including composite; then
        # recomposite for alpha effect

        mask = gtk.gdk.Pixmap(darea.window, w, h, 1)
        maskoff = gtk.gdk.GC(mask)
        maskoff.set_colormap(darea.window.get_colormap())
        maskoff.set_foreground(gtk.gdk.Color(pixel=0))
        mask.draw_rectangle(maskoff, True, 0, 0, w, h)
        maskon = maskoff
        del maskoff
        maskon.set_foreground(gtk.gdk.Color(pixel=-1))

        # panel background overlay
        dareacmap = darea.get_colormap()
        img = gtk.gdk.Pixmap(darea.window, w, h)
        bg_gc = gtk.gdk.GC(img)
        bg_gc.copy(darea.style.fg_gc[gtk.STATE_NORMAL])
        bg_gc.set_colormap(darea.window.get_colormap())
        if self.conf.fill is not None:
            bg_gc.set_foreground(dareacmap.alloc_color(self.conf.fill[:7]))
            img.draw_rectangle(bg_gc, True, 0, 0, w, h)
            mask.draw_rectangle(maskon, True, 0, 0, w, h)

        # composite with root
        try: alpha = int(self.conf.fill[7:], 16)
        except (ValueError,TypeError): alpha = 0
        buf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 0, 8, w, h)
        buf.get_from_drawable(img, img.get_colormap(), 0, 0, 0, 0, w, h)
        if self.conf.fill is not None: # else just use pure background
            self.__bg.composite(buf, 0, 0, w, h, 0, 0, 1, 1,
                    gtk.gdk.INTERP_NEAREST, 255-alpha)
        img.draw_pixbuf(darea.style.fg_gc[gtk.STATE_NORMAL], buf, 0, 0, 0, 0)

        # border
        if self.conf.bcolor is not None:
            bg_gc.set_foreground(dareacmap.alloc_color(self.conf.bcolor))
            img.draw_rectangle(bg_gc, False, 0, 0, w - 1, h - 1)
            mask.draw_rectangle(maskon, False, 0, 0, w - 1, h - 1)

        # text
        fg_gc = gtk.gdk.GC(img)
        fg_gc.copy(darea.style.fg_gc[gtk.STATE_NORMAL])
        fg_gc.set_colormap(dareacmap)
        tx = self.__textx
        ty = self.__texty

        if self.conf.shadow is not None:
            fg_gc.set_foreground(dareacmap.alloc_color(self.conf.shadow))
            img.draw_layout(fg_gc, tx + 2, ty + 2, layout)
            if self.conf.fill is None:
                mask.draw_layout(maskon, tx + 2, ty + 2, layout)

        if self.conf.outline is not None:
            fg_gc.set_foreground(dareacmap.alloc_color(self.conf.outline))
            for dx,dy in [(-1,-1), (-1, 0), (-1, 1),
                          ( 0,-1),          ( 0, 1),
                          ( 1,-1), ( 1, 0), ( 1, 1)]:
                    img.draw_layout(fg_gc, tx + dx, ty + dy, layout)
                    if self.conf.fill is None:
                        mask.draw_layout(maskon, tx + dx, ty + dy, layout)

        fg_gc.set_foreground(dareacmap.alloc_color(self.conf.text))
        img.draw_layout(fg_gc, tx, ty, layout)
        if self.conf.fill is None:
            mask.draw_layout(maskon, tx, ty, layout)

        # cover
        if self.__cover is not None:
            if self.conf.shadow is not None:
                fg_gc.set_foreground(dareacmap.alloc_color(self.conf.shadow))
                img.draw_rectangle(bg_gc, True,
                        self.__coverx + 2, self.__covery + 2, cw, ch)
                mask.draw_rectangle(maskon, True,
                        self.__coverx + 2, self.__covery + 2, cw, ch)

            if self.conf.outline is not None:
                fg_gc.set_foreground(dareacmap.alloc_color(self.conf.outline))
                img.draw_rectangle(bg_gc, False,
                        self.__coverx - 1, self.__covery - 1, cw + 1, ch + 1)
                mask.draw_rectangle(maskon, False,
                        self.__coverx - 1, self.__covery - 1, cw + 1, ch + 1)

            img.draw_pixbuf(darea.style.fg_gc[gtk.STATE_NORMAL],
                    self.__cover, 0, 0, self.__coverx, self.__covery)
            mask.draw_rectangle(maskon, True,
                    0, 0, self.__coverx, self.__covery)

        self.__img = img
        self.__window.shape_combine_mask(mask, 0, 0)
        self.__window.move(x, y)
        self.__window.resize(w, h)

    def render(self):
        w = self.__width
        h = self.__height
        x = self.__winx
        y = self.__winy
        darea = self.__darea
        self.__step = max(0, min(255, self.__step + self.__stepby))

        if 0 < self.__step < 255:
            # recomposite
            buf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 0, 8, w, h)
            buf.get_from_drawable(self.__img, self.__img.get_colormap(),
                    0, 0, 0, 0, w, h)
            self.__bg.composite(buf, 0, 0, w, h,
                    0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, 255-self.__step)
            img = gtk.gdk.Pixmap(darea.window, w, h)
            img.draw_pixbuf(darea.style.fg_gc[gtk.STATE_NORMAL],
                    buf, 0, 0, 0, 0)
        else:
            img = self.__img

        darea.window.set_back_pixmap(img, False)
        darea.queue_draw_area(0, 0, w, h)

        # has it finished hiding?
        if self.__step <= 0:
            del self.__bg
            self.__window.hide()
            self.__stepby = 0
            self.__step = 0
            self.__song = None
            if self.__next is not None:
                gobject.timeout_add(self.conf.ms, self.show)
            return

        gobject.idle_add(self.__window.show)

        # has it finished showing?
        if self.__step >= 255:
            self.__stepby = 0
            self.__step = 255
            self.__delayhide = gobject.timeout_add(self.conf.delay, self.hide)
            return

        # or is it just a normal update? (keep updates coming)
        return True

    def __buttonpress(self, *args):
        self.__stepby = self.__step = 0
        self.__window.hide()
