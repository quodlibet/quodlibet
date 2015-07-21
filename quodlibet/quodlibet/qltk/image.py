# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""
Some helper function for loading and converting image data.

A PixbufOrSurface is either a GdkPixbuf.Pixbuf or a cairo.Surface. Gtk+ 3.10
added HiDPI support and added APIs which take cairo surfaces. Since we still
want to support older GTK+  we provide some helpers to work on both data
types.

Rule of thumb: Every pixbuf which ends up in a surface before getting drawn
needs to be loaded at original_size * scale_factor.

To test HiDPI start QL with GDK_SCALE=2.
"""

import math

from gi.repository import GdkPixbuf, Gtk, Gdk, GLib
import cairo


def get_scale_factor(widget):
    """Returns the scale factor for a Gtk.Widget"""

    if hasattr(widget, "get_scale_factor"):
        return widget.get_scale_factor()
    else:
        return 1


def get_pbosf_for_pixbuf(widget, pixbuf):
    """Returns a cairo surface or the same pixbuf,
    let's call it PixbufOrSurface..
    """

    if hasattr(Gdk, "cairo_surface_create_from_pixbuf"):
        scale_factor = widget.get_scale_factor()
        # Don't create a surface if we don't have to
        if scale_factor == 1:
            return pixbuf
        return Gdk.cairo_surface_create_from_pixbuf(
                pixbuf, scale_factor, widget.get_window())
    else:
        return pixbuf


def pbosf_get_width(pbosf):
    """The scale independent width"""

    return pbosf_get_rect(pbosf)[2]


def pbosf_get_height(pbosf):
    """The scale independent height"""

    return pbosf_get_rect(pbosf)[3]


def pbosf_get_rect(pbosf):
    """Gives (x, y, width, height) for a pixbuf or a surface,
    scale independent
    """

    if isinstance(pbosf, GdkPixbuf.Pixbuf):
        return (0, 0, pbosf.get_width(), pbosf.get_height())
    else:
        ctx = cairo.Context(pbosf)
        x1, y1, x2, y2 = ctx.clip_extents()
        x1 = int(math.floor(x1))
        y1 = int(math.floor(y1))
        x2 = int(math.ceil(x2))
        y2 = int(math.ceil(y2))
        x2 -= x1
        y2 -= y1

        return (x1, y1, x2, y2)


def pbosf_get_property_name(pbosf):
    """Gives the property name to use for the PixbufOrSurface."""

    if pbosf is None or isinstance(pbosf, GdkPixbuf.Pixbuf):
        return "pixbuf"
    else:
        return "surface"


def set_renderer_from_pbosf(renderer, pbosf):
    """Set a Gtk.CellRendererPixbuf given a PixbufOrSurface or None"""

    name = pbosf_get_property_name(pbosf)
    renderer.set_property(name, pbosf)


def set_image_from_pbosf(image, pbosf):
    """Sets a Gtk.Image given a PixbufOrSurface"""

    if isinstance(pbosf, GdkPixbuf.Pixbuf):
        return image.set_from_pixbuf(pbosf)
    else:
        return image.set_from_surface(pbosf)


def set_ctx_source_from_pbosf(context, pbosf, x=0.0, y=0.0):
    """Sets the passed PixbufOrSurface as a source for the
    given cairo.Context
    """

    if isinstance(pbosf, GdkPixbuf.Pixbuf):
        Gdk.cairo_set_source_pixbuf(context, pbosf, x, y)
    else:
        context.set_source_surface(pbosf, x, y)


def pbosf_render(style_context, cairo_context, pbosf, x, y):
    """Draws the PixbufOrSurface to the cairo context at (x, y)"""

    if isinstance(pbosf, GdkPixbuf.Pixbuf):
        Gtk.render_icon(style_context, cairo_context, pbosf, x, y)
    else:
        Gtk.render_icon_surface(style_context, cairo_context, pbosf, x, y)


def add_border(pixbuf, color, round=False, width=1):
    """Add a border to the pixbuf and round of the edges.
    color is a Gdk.RGBA
    The resulting pixbuf will be width * 2px higher and wider.

    Can not fail.
    """

    w, h = pixbuf.get_width(), pixbuf.get_height()
    w += width * 2
    h += width * 2
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surface)

    pi = math.pi
    r = min(w, h) / 10.0 if round else 0
    ctx.new_path()
    ctx.arc(w - r, r, r, -pi / 2, 0)
    ctx.arc(w - r, h - r, r, 0, pi / 2)
    ctx.arc(r, h - r, r, pi / 2, pi)
    ctx.arc(r, r, r, pi, pi * 3 / 2)
    ctx.close_path()

    Gdk.cairo_set_source_pixbuf(ctx, pixbuf, width, width)
    ctx.clip_preserve()
    ctx.paint()

    ctx.set_source_rgba(color.red, color.green, color.blue, color.alpha)
    ctx.set_line_width(width * 2)
    ctx.stroke()

    return Gdk.pixbuf_get_from_surface(surface, 0, 0, w, h)


def add_border_widget(pixbuf, widget, cell=None, round=False):
    """Like add_border() but uses the widget to get a border color and a
    border width.
    """

    from quodlibet.qltk.image import get_scale_factor

    context = widget.get_style_context()
    if cell is not None:
        state = cell.get_state(widget, 0)
    else:
        state = widget.get_state_flags()
    color = context.get_color(state)
    scale_factor = get_scale_factor(widget)

    return add_border(pixbuf, color, round=round, width=scale_factor)


def scale(pixbuf, boundary, scale_up=True, force_copy=False):
    """Scale a pixbuf so it fits into the boundary.
    (preserves image aspect ratio)

    If `scale_up` is True, the resulting pixbuf can be larger than
    the original one.

    If `force_copy` is False the resulting pixbuf might be the passed one.

    Can not fail.
    """

    size = pixbuf.get_width(), pixbuf.get_height()

    scale_w, scale_h = calc_scale_size(boundary, size, scale_up)

    if (scale_w, scale_h) == size:
        if force_copy:
            return pixbuf.copy()
        return pixbuf

    return pixbuf.scale_simple(scale_w, scale_h, GdkPixbuf.InterpType.BILINEAR)


def calc_scale_size(boundary, size, scale_up=True):
    """Returns the biggest possible size to fit into the boundary,
    respecting the aspect ratio.

    If `scale_up` is True the result can be larger than size.

    All sizes have to be > 0.
    """

    bwidth, bheight = boundary
    iwidth, iheight = size

    if bwidth <= 0 or bheight <= 0 or iwidth <= 0 or iheight <= 0:
        raise ValueError

    scale_w, scale_h = iwidth, iheight

    if iwidth > bwidth or iheight > bheight or scale_up:
        bratio = float(bwidth) / bheight
        iratio = float(iwidth) / iheight

        if iratio > bratio:
            scale_w = bwidth
            scale_h = int(bwidth / iratio)
        else:
            scale_w = int(bheight * iratio)
            scale_h = bheight

    return scale_w, scale_h


def pixbuf_from_file(fileobj, boundary, scale_factor=1):
    """Returns a pixbuf with the maximum size defined by boundary.

    Can raise GLib.GError and return None
    """

    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(fileobj.name)
    except GLib.GError:
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.write(fileobj.read())
            loader.close()
            fileobj.seek(0, 0)
            pixbuf = loader.get_pixbuf()
        except EnvironmentError:
            return

    w, h = boundary
    w *= scale_factor
    h *= scale_factor

    return scale(pixbuf, (w, h), scale_up=False)
