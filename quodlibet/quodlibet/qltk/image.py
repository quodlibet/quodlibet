# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Some helper function for loading and converting image data."""

import math

from gi.repository import GdkPixbuf, Gtk, Gdk, GLib
import cairo


def get_surface_for_pixbuf(widget, pixbuf):
    """Returns a cairo surface"""

    scale_factor = widget.get_scale_factor()
    return Gdk.cairo_surface_create_from_pixbuf(
            pixbuf, scale_factor, widget.get_window())


def get_surface_extents(surface):
    """Gives (x, y, width, height) for a surface, scale independent"""

    ctx = cairo.Context(surface)
    x1, y1, x2, y2 = ctx.clip_extents()
    x1 = int(math.floor(x1))
    y1 = int(math.floor(y1))
    x2 = int(math.ceil(x2))
    y2 = int(math.ceil(y2))
    x2 -= x1
    y2 -= y1

    return (x1, y1, x2, y2)


def get_border_radius(_widgets=[]):
    """Returns the border radius commonly used in the current theme.
    If there are no rounded corners 0 will be returned.
    """

    if not _widgets:
        b = Gtk.Button()
        b.show()
        e = Gtk.Entry()
        e.show()
        _widgets += [b, e]

    radii = []
    for widget in _widgets:
        style_context = widget.get_style_context()
        radii.append(style_context.get_property(
            Gtk.STYLE_PROPERTY_BORDER_RADIUS, style_context.get_state()))
    radius = max(radii)

    # Doesn't work on the default Ubuntu theme.
    # Not sure why, so fix manually for now
    theme_name = Gtk.Settings.get_default().props.gtk_theme_name
    if theme_name in ("Ambiance", "Radiance"):
        radius = int(radius / 1.5)

    return radius


def add_border(pixbuf, color, width=1, radius=0):
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
    r = min(radius, min(w, h) / 2)
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


def add_border_widget(pixbuf, widget):
    """Like add_border() but uses the widget to get a border color and a
    border width.
    """

    context = widget.get_style_context()
    color = context.get_color(context.get_state())
    scale_factor = widget.get_scale_factor()
    border_radius = get_border_radius() * scale_factor

    return add_border(pixbuf, color, width=scale_factor, radius=border_radius)


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

    return scale(pixbuf, (w, h), scale_up=True)
