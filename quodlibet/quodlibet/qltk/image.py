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

from gi.repository import GdkPixbuf, Gtk, Gdk, GLib

from quodlibet.util import thumbnails


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


def pbosf_render(style_context, cairo_context, pbosf, x, y):
    """Draws the PixbufOrSurface to the cairo context at (x, y)"""

    if isinstance(pbosf, GdkPixbuf.Pixbuf):
        Gtk.render_icon(style_context, cairo_context, pbosf, x, y)
    else:
        Gtk.render_icon_surface(style_context, cairo_context, pbosf, x, y)


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

    return thumbnails.scale(pixbuf, (w, h), scale_up=False)
