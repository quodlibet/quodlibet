#!/usr/bin/env python

## On Screen Display
## (C) 2004 Gustavo J. A. M. Carneiro <gustavo@users.sf.net>

## Hacked up extensively and stripped of features by Joe Wreschnig
## <piman@sacredchao.net>, from gnome-osd 0.6.0.

## This library is free software; you can redistribute it and/or
## modify it under the terms of the GNU Lesser General Public
## License as published by the Free Software Foundation; either
## version 2 of the License, or (at your option) any later version.

# $Id$

import pygtk
pygtk.require('2.0')

import pango
import gtk
import gtk.gdk as gdk

BORDER_WIDTH=4

def osd(text, bgcolor, fgcolor, fontdesc, use_markup = True,
        alignment = pango.ALIGN_CENTER):
    if isinstance(fontdesc, str):
        fontdesc = pango.FontDescription(fontdesc)
    assert isinstance(fontdesc, pango.FontDescription)

    win = gtk.Window(gtk.WINDOW_POPUP)
    win.add_events(gtk.gdk.POINTER_MOTION_MASK)
    darea = gtk.DrawingArea()
    win.add(darea)
    darea.show()

    if use_markup:
        layout = win.create_pango_layout('')
        layout.set_markup(text)
    else:
        layout = win.create_pango_layout(text)

    layout.set_justify(False)
    layout.set_alignment(alignment)
    layout.set_font_description(fontdesc)

    MAX_WIDTH = gdk.screen_width() - 8
    layout.set_width(pango.SCALE*MAX_WIDTH)
    layout.set_wrap(pango.WRAP_WORD)
    width, height = layout.get_pixel_size()
    off_x = BORDER_WIDTH*2
    off_y = BORDER_WIDTH*2

    if alignment == pango.ALIGN_CENTER:
        off_x -= MAX_WIDTH/2 - width/2
    elif alignment == pango.ALIGN_RIGHT:
        off_x -= MAX_WIDTH - width
    
    width += BORDER_WIDTH*4
    height += BORDER_WIDTH*4
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
    for dx in range(-BORDER_WIDTH, BORDER_WIDTH+1):
        for dy in range(-BORDER_WIDTH, BORDER_WIDTH+1):
            if dx*dx + dy*dy >= BORDER_WIDTH*BORDER_WIDTH: continue
            bitmap.draw_layout(fg_gc, off_x + dx, off_y + dy, layout)

    darea.window.set_back_pixmap(pixmap, False)
    win.window.shape_combine_mask(bitmap, 0, 0)
    win.width = width
    win.height = height
    return win

if __name__ == '__main__':
    w = osd("<i>Hello</i> <span size='larger' weight='bold'>World</span>"
            "<span foreground='red'>!</span>", "#000000", "#80ff80",
            pango.FontDescription("sans serif 20"),  use_markup=True)
    w.move(gdk.screen_width()/2 - w.width/2, gdk.screen_height() - w.height - 10)
    w.show()
    gtk.main()
