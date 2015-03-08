# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Things that are more or less direct wrappers around GTK widgets to
# ease constructors.

from gi.repository import Gtk, GObject, GLib, Gio

from quodlibet import util
from quodlibet import config
from quodlibet.qltk import add_css, is_accel
from quodlibet.util import connect_obj


class ScrolledWindow(Gtk.ScrolledWindow):
    """Draws a border around all edges that don't touch the parent window"""

    def do_size_allocate(self, alloc):
        if self.get_shadow_type() == Gtk.ShadowType.NONE:
            return Gtk.ScrolledWindow.do_size_allocate(self, alloc)

        toplevel = self.get_toplevel()

        try:
            dx, dy = self.translate_coordinates(toplevel, 0, 0)
        except TypeError:
            GLib.idle_add(self.queue_resize)
            return Gtk.ScrolledWindow.do_size_allocate(self, alloc)

        # since 3.15 the gdkwindow moves to dx==-1 with the allocation
        # so ignore anything < 0 (I guess something passes the adjusted alloc
        # to us a second time)
        # https://git.gnome.org/browse/gtk+/commit/?id=fdf367e8689cb
        if dx < 0:
            dx = 0
            alloc.width += dx
        if dy < 0:
            dy = 0
            alloc.height += dy

        ctx = self.get_style_context()
        border = ctx.get_border(self.get_state_flags())

        # https://bugzilla.gnome.org/show_bug.cgi?id=694844
        border.left = border.top = border.right = border.bottom = 1

        # XXX: ugly, ugly hack
        # Pretend the main window toolbar is the top of the window.
        # This removes the top border in case the ScrolledWindow
        # is drawn right below the toolbar.
        try:
            top_bar = toplevel.top_bar
            if not isinstance(top_bar, Gtk.Widget):
                raise TypeError
        except (AttributeError, TypeError):
            # In case the window border is at the top, we expect the menubar
            # there, so draw the normal border
            border.top = 0
        else:
            top_alloc = top_bar.get_allocation()
            top_ctx = top_bar.get_style_context()
            b = top_ctx.get_border(top_bar.get_state_flags())
            # only if the toolbar has a border we hide our own.
            # seems to work, even tough it doesn't for getting the
            # Notebook/ScrolledWindow border :/
            if b.bottom:
                dy -= top_alloc.y + top_alloc.height

        # Don't remove the border if the border is drawn inside
        # and the scrollbar on that edge is visible
        bottom = left = right = top = False

        value = GObject.Value()
        value.init(GObject.TYPE_BOOLEAN)
        # default to True: https://bugzilla.gnome.org/show_bug.cgi?id=701058
        value.set_boolean(True)
        ctx.get_style_property("scrollbars-within-bevel", value)
        scroll_within = value.get_boolean()
        value.unset()

        if not scroll_within:
            h, v = self.get_hscrollbar(), self.get_vscrollbar()
            hscroll = vscroll = False
            if h.get_visible():
                req = h.size_request()
                hscroll = bool(req.width + req.height)

            if v.get_visible():
                req = v.size_request()
                vscroll = bool(req.width + req.height)

            placement = self.get_placement()
            if placement == Gtk.CornerType.TOP_LEFT:
                bottom = hscroll
                right = vscroll
            elif placement == Gtk.CornerType.BOTTOM_LEFT:
                right = vscroll
                top = hscroll
            elif placement == Gtk.CornerType.TOP_RIGHT:
                bottom = hscroll
                left = vscroll
            elif placement == Gtk.CornerType.BOTTOM_RIGHT:
                left = vscroll
                top = hscroll

        width, height = toplevel.get_size()
        if alloc.y + alloc.height + dy >= height and not bottom:
            alloc.height += border.bottom

        if alloc.x + alloc.width + dx >= width and not right:
            alloc.width += border.right

        if alloc.y + dy <= 0 and not top:
            alloc.y -= border.top
            alloc.height += border.top

        if alloc.x + dx <= 0 and not left:
            alloc.x -= border.left
            alloc.width += border.left

        return Gtk.ScrolledWindow.do_size_allocate(self, alloc)


class Notebook(Gtk.Notebook):
    """A regular gtk.Notebook, except when appending a page, if no
    label is given, the page's 'title' attribute (either a string or
    a widget) is used."""

    def __init__(self, *args, **kwargs):
        super(Notebook, self).__init__(*args, **kwargs)
        self.connect("key-press-event", self.__key_pressed)

    def __key_pressed(self, widget, event):
        # alt+X switches to page X
        for i in xrange(self.get_n_pages()):
            if is_accel(event, "<alt>%d" % (i + 1)):
                self.set_current_page(i)
                return True
        return False

    def do_size_allocate(self, alloc):
        ctx = self.get_style_context()
        border = ctx.get_border(self.get_state_flags())

        toplevel = self.get_toplevel()
        top_window = toplevel.get_window()
        window = self.get_window()

        if not window:
            GLib.idle_add(self.queue_resize)
            return Gtk.Notebook.do_size_allocate(self, alloc)

        dummy, x1, y1 = top_window.get_origin()
        dummy, x2, y2 = window.get_origin()
        dx = x2 - x1
        dy = y2 - y1

        # all 0 since gtk+ 3.12..
        border.left = border.top = border.right = border.bottom = 1

        width, height = toplevel.get_size()
        if alloc.y + alloc.height + dy == height:
            alloc.height += border.bottom

        if alloc.x + alloc.width + dx == width:
            alloc.width += border.right

        if alloc.x + dx == 0:
            alloc.x -= border.left
            alloc.width += border.left

        return Gtk.Notebook.do_size_allocate(self, alloc)

    def append_page(self, page, label=None):
        if label is None:
            try:
                label = page.title
            except AttributeError:
                raise TypeError("no page.title and no label given")

        if not isinstance(label, Gtk.Widget):
            label = Gtk.Label(label=label)
        super(Notebook, self).append_page(page, label)


def Frame(label, child=None):
    """A Gtk.Frame with no shadow, 12px left padding, and 6px top padding."""
    frame = Gtk.Frame()
    label_w = Gtk.Label()
    label_w.set_markup("<b>%s</b>" % util.escape(label))
    align = Align(left=12, top=6)
    frame.add(align)
    frame.set_shadow_type(Gtk.ShadowType.NONE)
    frame.set_label_widget(label_w)
    if child:
        align.add(child)
        label_w.set_mnemonic_widget(child)
        label_w.set_use_underline(True)
    return frame


class Align(Gtk.Frame):
    """A Gtk.Alignment replacement which is responsible for
    the positioning/allocation of its child widget.

    XXX: Subclasses Gtk.Frame instead of Gtk.Bin because the later
    fails with Gtk+ 3.4.
    """

    def __init__(self, child=None,
                 top=0, right=0, bottom=0, left=0, border=0,
                 halign=Gtk.Align.FILL, valign=Gtk.Align.FILL):

        kwargs = dict(
            shadow_type=Gtk.ShadowType.NONE,
            halign=halign, valign=valign,
            margin_top=border + top, margin_bottom=border + bottom,
            margin_start=border + left, margin_end=border + right,
        )

        # < Gtk+ 3.12
        if not hasattr(Gtk.Widget.props, "margin_start"):
            kwargs["margin_left"] = kwargs.pop("margin_start")
            kwargs["margin_right"] = kwargs.pop("margin_end")

        super(Align, self).__init__(**kwargs)

        if child is not None:
            self.add(child)


def MenuItem(label, stock_id):
    """An ImageMenuItem with a custom label and stock image."""

    item = Gtk.ImageMenuItem.new_with_mnemonic(label)
    item.set_always_show_image(True)
    if Gtk.stock_lookup(stock_id):
        image = Gtk.Image.new_from_stock(stock_id, Gtk.IconSize.MENU)
    else:
        image = Gtk.Image.new_from_icon_name(stock_id, Gtk.IconSize.MENU)
    image.show()
    item.set_image(image)
    return item


def Button(label, stock_id, size=Gtk.IconSize.BUTTON):
    """A Button with a custom label and stock image. It should pack
    exactly like a stock button."""

    align = Align(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
    hbox = Gtk.HBox(spacing=2)
    if Gtk.stock_lookup(stock_id):
        image = Gtk.Image.new_from_stock(stock_id, size)
    else:
        image = Gtk.Image.new_from_icon_name(stock_id, size)
    hbox.pack_start(image, True, True, 0)
    label = Gtk.Label(label=label)
    label.set_use_underline(True)
    hbox.pack_start(label, True, True, 0)
    align.add(hbox)
    align.show_all()
    button = Gtk.Button()
    button.add(align)
    return button


class Paned(Gtk.Paned):

    def __init__(self, *args, **kwargs):
        super(Paned, self).__init__(*args, **kwargs)
        self.ensure_wide_handle()

    def ensure_wide_handle(self):
        if hasattr(self.props, "wide_handle"):
            # gtk 3.16
            self.props.wide_handle = True
            add_css(self, """
                GtkPaned {
                    border-width: 0;
                }
            """)
            return

        # gtk 3.14
        add_css(self, """
            GtkPaned {
                -GtkPaned-handle-size: 6;
                background-image: none;
                margin: 0;
                border-width: 0;
            }
        """)


class RPaned(Paned):
    """A Paned that supports relative (percentage) width/height setting."""

    ORIENTATION = None

    def __init__(self, *args, **kwargs):
        if self.ORIENTATION is not None:
            kwargs["orientation"] = self.ORIENTATION
        super(RPaned, self).__init__(*args, **kwargs)
        # before first alloc: save value in relative and set on the first alloc
        # after the first alloc: use the normal properties
        self.__alloced = False
        self.__relative = None

    def set_relative(self, v):
        """Set the relative position of the separator, [0..1]."""

        if self.__alloced:
            max_pos = self.get_property('max-position')
            if not max_pos:
                # no children
                self.__relative = v
                return
            self.set_position(int(v * max_pos))
        else:
            self.__relative = v

    def get_relative(self):
        """Return the relative position of the separator, [0..1]."""

        if self.__alloced:
            max_pos = self.get_property('max-position')
            if not max_pos:
                # no children
                return self.__relative
            return (float(self.get_position()) / max_pos)
        elif self.__relative is not None:
            return self.__relative
        else:
            # before first alloc and set_relative not called
            return 0.5

    def do_size_allocate(self, *args):
        ret = Gtk.HPaned.do_size_allocate(self, *args)
        if not self.__alloced and self.__relative is not None:
            self.__alloced = True
            self.set_relative(self.__relative)
            # call again so the children get alloced
            ret = Gtk.HPaned.do_size_allocate(self, *args)
        self.__alloced = True
        return ret


class RHPaned(RPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class RVPaned(RPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL


class ConfigRPaned(RPaned):
    def __init__(self, section, option, default, *args, **kwargs):
        super(ConfigRPaned, self).__init__(*args, **kwargs)
        self.set_relative(config.getfloat(section, option, default))
        self.connect('notify::position', self.__changed, section, option)

    def __changed(self, widget, event, section, option):
        if self.get_property('position-set'):
            config.set(section, option, str(self.get_relative()))


class ConfigRHPaned(ConfigRPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class ConfigRVPaned(ConfigRPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL


class _SmallImageButton(object):
    """A button for images with less padding"""

    def __init__(self, **kwargs):
        super(_SmallImageButton, self).__init__(**kwargs)

        self.set_size_request(26, 26)
        add_css(self, """
            * {
                padding: 0px;
            }
        """)


class SmallImageButton(_SmallImageButton, Gtk.Button):
    pass


class SmallImageToggleButton(_SmallImageButton, Gtk.ToggleButton):
    pass


def ClearButton(entry=None):
    clear = Gtk.Button()
    clear.add(Gtk.Image.new_from_stock(Gtk.STOCK_CLEAR, Gtk.IconSize.MENU))
    clear.set_tooltip_text(_("Clear search"))
    if entry is not None:
        connect_obj(clear, 'clicked', entry.set_text, '')
    return clear


def EntryCompletion(words):
    """Simple string completion."""
    model = Gtk.ListStore(str)
    for word in sorted(words):
        model.append(row=[word])
    comp = Gtk.EntryCompletion()
    comp.set_model(model)
    comp.set_text_column(0)
    return comp


def RadioMenuItem(*args, **kwargs):
    """RadioMenuItem that allows None for group"""

    if kwargs.get("group", None) is None:
        kwargs.pop("group", None)
    return Gtk.RadioMenuItem(*args, **kwargs)


def SeparatorMenuItem(*args, **kwargs):
    # https://bugzilla.gnome.org/show_bug.cgi?id=670575
    # PyGObject 3.2 always sets a label in __init__
    if not args and not kwargs:
        return Gtk.SeparatorMenuItem.new()
    return Gtk.SeparatorMenuItem(*args, **kwargs)


def SymbolicIconImage(name, size, fallbacks=None):
    """Gtk.Image that displays a symbolic version of 'name' and falls
    back to the non-symbolic one.
    """

    symbolic_name = name + "-symbolic"
    gicon = Gio.ThemedIcon.new_from_names([symbolic_name, name])
    return Gtk.Image.new_from_gicon(gicon, size)
