# Copyright 2005 Joe Wreschnig, Michael Urman
#        2020-22 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Things that are more or less direct wrappers around GTK widgets to
ease constructors.
"""

from urllib.request import urlopen

from gi.repository import Gtk, GObject, GLib, Gio, GdkPixbuf, Gdk

from quodlibet.util.dprint import print_d

from quodlibet import util
from quodlibet.util import print_w
from quodlibet.util.thread import call_async, Cancellable
from quodlibet.qltk import add_css, is_accel, gtk_version

from .paned import (
    Paned,
    RPaned,
    RHPaned,
    RVPaned,
    ConfigRPaned,
    ConfigRHPaned,
    ConfigRVPaned,
)


Paned, RPaned, RHPaned, RVPaned, ConfigRPaned, ConfigRHPaned, ConfigRVPaned  # noqa


class ScrolledWindow(Gtk.ScrolledWindow):
    """Draws a border around all edges that don't touch the parent window"""

    def do_size_allocate(self, alloc):
        if self.get_shadow_type() == Gtk.ShadowType.NONE:
            return Gtk.ScrolledWindow.do_size_allocate(self, alloc)

        toplevel = self.get_toplevel()
        # try to get the child so we ignore the CSD
        toplevel = toplevel.get_child() or toplevel

        try:
            dx, dy = self.translate_coordinates(toplevel, 0, 0)
        except TypeError:
            GLib.idle_add(self.queue_resize)
            return Gtk.ScrolledWindow.do_size_allocate(self, alloc)

        ctx = self.get_style_context()
        border = ctx.get_border(ctx.get_state())

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
            pass
        else:
            top_ctx = top_bar.get_style_context()
            b = top_ctx.get_border(top_ctx.get_state())
            if b.bottom:
                dy_bar = self.translate_coordinates(top_bar, 0, 0)[1]
                dy_bar -= top_bar.get_allocation().height
                dy = min(dy, dy_bar)

        # since 3.15 the gdkwindow moves to dx==-1 with the allocation
        # so ignore anything < 0 (I guess something passes the adjusted alloc
        # to us a second time)
        # https://git.gnome.org/browse/gtk+/commit/?id=fdf367e8689cb
        dx = max(0, dx)
        dy = max(0, dy)

        # Don't remove the border if the border is drawn inside
        # and the scrollbar on that edge is visible
        bottom = left = right = top = False

        if gtk_version < (3, 19):
            value = GObject.Value()
            value.init(GObject.TYPE_BOOLEAN)
            # default to True:
            #    https://bugzilla.gnome.org/show_bug.cgi?id=701058
            value.set_boolean(True)
            ctx.get_style_property("scrollbars-within-bevel", value)
            scroll_within = value.get_boolean()
            value.unset()
        else:
            # was deprecated in gtk 3.20
            # https://git.gnome.org/browse/gtk+/commit/?id=
            #   7c0f0e882ae60911e39aaf7b42fb2d94108f3474
            scroll_within = True

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

        top_alloc = toplevel.get_allocation()
        width, height = top_alloc.width, top_alloc.height
        if alloc.height + dy == height and not bottom:
            alloc.height += border.bottom

        if alloc.width + dx == width and not right:
            alloc.width += border.right

        if dy == 0 and not top:
            alloc.y -= border.top
            alloc.height += border.top

        if dx == 0 and not left:
            alloc.x -= border.left
            alloc.width += border.left

        return Gtk.ScrolledWindow.do_size_allocate(self, alloc)


MT = Gdk.ModifierType


class Notebook(Gtk.Notebook):
    """A regular gtk.Notebook, except when appending a page, if no
    label is given, the page's 'title' attribute (either a string or
    a widget) is used."""

    _KEY_MODS = MT.SHIFT_MASK | MT.CONTROL_MASK | MT.ALT_MASK | MT.SUPER_MASK
    """Keyboard modifiers of interest"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event_controller = Gtk.EventControllerKey()
        event_controller.connect("key-pressed", self.__key_pressed)
        self.add_controller(event_controller)

    def __key_pressed(self, _widget: Gtk.Widget, event: Gdk.Event):
        # alt+X switches to page X
        for i in range(self.get_n_pages()):
            if is_accel(event, "<alt>%d" % (i + 1)):
                self.set_current_page(i)
                return Gdk.EVENT_STOP

        state = event.state & self._KEY_MODS
        # Use hardware, as Gtk+ seems to special-case tab for itself
        if event.hardware_keycode == 23:
            total = self.get_n_pages()
            current = self.get_current_page()
            if state == (MT.SHIFT_MASK | MT.CONTROL_MASK | MT.SUPER_MASK):
                self.set_current_page((current + total - 1) % total)
                return Gdk.EVENT_STOP
            if state == (MT.CONTROL_MASK | MT.SUPER_MASK):
                self.set_current_page((current + 1) % total)
                return Gdk.EVENT_STOP
            print_d(f"Unhandled tab key combo: {event.state}")
        return Gdk.EVENT_PROPAGATE

    def do_size_allocate(self, alloc):
        ctx = self.get_style_context()
        border = ctx.get_border(ctx.get_state())

        toplevel = self.get_toplevel()
        # try to get the child so we ignore the CSD
        toplevel = toplevel.get_child() or toplevel

        try:
            dx, dy = self.translate_coordinates(toplevel, 0, 0)
        except TypeError:
            GLib.idle_add(self.queue_resize)
            return Gtk.Notebook.do_size_allocate(self, alloc)

        dx = max(0, dx)
        dy = max(0, dy)

        # all 0 since gtk+ 3.12..
        border.left = border.top = border.right = border.bottom = 1

        top_alloc = toplevel.get_allocation()
        width, height = top_alloc.width, top_alloc.height
        if alloc.height + dy == height:
            alloc.height += border.bottom

        if alloc.width + dx == width:
            alloc.width += border.right

        if dy == 0:
            alloc.y -= border.top
            alloc.height += border.top

        if dx == 0:
            alloc.x -= border.left
            alloc.width += border.left

        return Gtk.Notebook.do_size_allocate(self, alloc)

    def append_page(self, page, label=None):
        if label is None:
            try:
                label = page.title
            except AttributeError as e:
                raise TypeError("no page.title and no label given") from e

        if not isinstance(label, Gtk.Widget):
            label = Gtk.Label(label=label)
        super().append_page(page, label)


def Frame(label, child=None):
    """A Gtk.Frame with no shadow, 12px left padding, and 6px top padding."""
    frame = Gtk.Frame()
    label_w = Gtk.Label()
    label_w.set_markup(util.bold(label))
    align = Align(left=12, top=6)
    frame.add(align)
    frame.set_shadow_type(Gtk.ShadowType.NONE)
    frame.set_label_widget(label_w)
    if child:
        align.add(child)
        label_w.set_mnemonic_widget(child)
        label_w.set_use_underline(True)
    return frame


class Align(Gtk.Box):
    """GTK4: Replaced Gtk.Alignment with Box + margin/align properties"""

    def __init__(
        self,
        child=None,
        top=0,
        right=0,
        bottom=0,
        left=0,
        border=0,
        halign=Gtk.Align.FILL,
        valign=Gtk.Align.FILL,
    ):
        super().__init__()

        # Set alignment and margins
        self.set_halign(halign)
        self.set_valign(valign)
        self.set_margin_top(border + top)
        self.set_margin_bottom(border + bottom)
        self.set_margin_start(border + left)
        self.set_margin_end(border + right)

        # Store for compatibility methods
        self._margins = {
            "top": border + top,
            "bottom": border + bottom,
            "left": border + left,
            "right": border + right,
        }

        if child is not None:
            self.append(child)

    def get_margin_top(self):
        return self._margins["top"]

    def get_margin_bottom(self):
        return self._margins["bottom"]

    def get_margin_left(self):
        return self._margins["left"]

    def get_margin_right(self):
        return self._margins["right"]

    def add(self, child):
        """GTK4 compatibility: add() → append()"""
        self.append(child)


def MenuItem(label, icon_name: str | None = None, tooltip: str | None = None):
    """A GTK4 menu item using Button.

    Note: In GTK4, menus should use Gio.Menu with actions, but for compatibility
    we provide a widget-based fallback using Button."""

    # Create a box to hold icon and label if needed
    if icon_name:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        image = Gtk.Image.new_from_icon_name(icon_name)
        box.append(image)
        label_widget = Gtk.Label(label=label, use_underline=True)
        box.append(label_widget)

        item = Gtk.Button()
        item.set_child(box)
    else:
        item = Gtk.Button(label=label, use_underline=True)

    if tooltip:
        item.set_tooltip_text(tooltip)

    # Remove default button styling for menu-like appearance
    item.add_css_class("flat")

    return item


def _Button(type_, label, icon_name, size):
    if icon_name is None:
        return type_.new_with_mnemonic(label)

    align = Align(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
    hbox = Gtk.Box(spacing=6)
    image = Gtk.Image.new_from_icon_name(icon_name, size)
    hbox.prepend(image, True, True, 0)
    label = Gtk.Label(label=label)
    label.set_use_underline(True)
    hbox.prepend(label, True, True, 0)
    align.add(hbox)
    align.show_all()
    button = type_()
    button.add(align)
    return button


def Button(label, icon_name=None, size=Gtk.IconSize.LARGE):
    """A Button with a custom label and stock image. It should pack
    exactly like a stock button.
    """

    return _Button(Gtk.Button, label, icon_name, size)


def ToggleButton(label, icon_name=None, size=Gtk.IconSize.LARGE):
    """A ToggleButton with a custom label and stock image. It should pack
    exactly like a stock button.
    """

    return _Button(Gtk.ToggleButton, label, icon_name, size)


class _SmallImageButton:
    """A button for images with less padding"""

    def __init__(self, **kwargs):
        # GTK4: Extract image from kwargs and set it as child
        image = kwargs.pop("image", None)
        super().__init__(**kwargs)

        if image is not None:
            self.set_child(image)

        self.set_size_request(26, 26)
        add_css(
            self,
            """
            * {
                padding: 0px;
            }
        """,
        )


class SmallImageButton(_SmallImageButton, Gtk.Button):
    pass


class SmallImageToggleButton(_SmallImageButton, Gtk.ToggleButton):
    pass


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
    """GTK4 RadioMenuItem replacement using ModelButton with radio mode.

    In GTK4, radio menu items should ideally use Gio.Menu with radio actions,
    but for compatibility we use ModelButton which can act as a radio button."""

    label = kwargs.pop("label", None)
    if args and not label:
        label = args[0]

    tooltip_text = kwargs.pop("tooltip_text", None)
    group = kwargs.pop("group", None)

    item = Gtk.CheckButton()
    if label:
        item.set_label(label)

    if tooltip_text:
        item.set_tooltip_text(tooltip_text)

    if group is not None:
        item.set_group(group)

    # Store the group reference for later use
    if not hasattr(item, "_radio_group"):
        item._radio_group = group

    return item


def SeparatorMenuItem(*args, **kwargs):
    """GTK4 SeparatorMenuItem replacement using Separator.

    In GTK4, menu separators are typically handled by Gio.Menu,
    but for widget-based menus we use a regular Separator."""

    return Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)


def SymbolicIconImage(name, size, fallbacks=None):
    """Gtk.Image that displays a symbolic version of 'name' and falls
    back to the non-symbolic one.
    """

    symbolic_name = name + "-symbolic"
    gicon = Gio.ThemedIcon.new_from_names([symbolic_name, name])
    return Gtk.Image.new_from_gicon(gicon)


class CellRendererPixbuf(Gtk.CellRendererPixbuf):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Action(Gio.SimpleAction):
    def __init__(self, *args, **kwargs):
        # GTK4: SimpleAction doesn't have label/icon_name properties
        # Store them as instance attributes for compatibility
        self.label = kwargs.pop("label", None)
        self.icon_name = kwargs.pop("icon_name", None)
        super().__init__(*args, **kwargs)


class ToggleAction(Gio.SimpleAction):
    def __init__(self, *args, **kwargs):
        # GTK4: SimpleAction doesn't have label property
        self.label = kwargs.pop("label", None)
        self.icon_name = kwargs.pop("icon_name", None)
        # TODO GTK4: Toggle behaviour - may need state_type parameter
        super().__init__(*args, **kwargs)


class RadioAction(Gio.SimpleAction):
    def __init__(self, *args, **kwargs):
        # GTK4: SimpleAction doesn't have label/value properties
        self.label = kwargs.pop("label", None)
        self._value = kwargs.pop("value", 0)
        self._group = []
        # TODO GTK4: Radio behaviour - needs state and parameter_type
        super().__init__(*args, **kwargs)

    def join_group(self, group_source):
        """GTK4: Stub for RadioAction group compatibility"""
        if group_source is not None:
            if not hasattr(group_source, "_group"):
                group_source._group = []
            group_source._group.append(self)
            self._group = group_source._group
        return self

    def get_group(self):
        """GTK4: Return radio group"""
        return self._group if self._group else [self]

    def get_current_value(self):
        """GTK4: Return current value"""
        return self._value

    def set_active(self, active):
        """GTK4: Set action as active"""
        # TODO: Implement proper radio behavior
        pass


class WebImage(Gtk.Image):
    """A Gtk.Image which loads the image over HTTP in the background
    and displays it when available.
    """

    def __init__(self, url, width=-1, height=-1):
        """
        Args:
            url (str): an HTTP URL
            width (int): a width to reserve for the image or -1
            height (int): a height to reserve for the image or -1
        """

        super().__init__()

        self._cancel = Cancellable()
        call_async(self._fetch_image, self._cancel, self._finished, (url,))
        self.connect("destroy", self._on_destroy)
        self.set_size_request(width, height)
        self.set_from_icon_name("image-loading", Gtk.IconSize.LARGE)

    def _on_destroy(self, *args):
        self._cancel.cancel()

    def _fetch_image(self, url):
        try:
            data = urlopen(url).read()
        except Exception as e:
            print_w(f"Couldn't read web image from {url} ({e})")
            return None
        try:
            loader = GdkPixbuf.PixbufLoader()
        except GLib.GError as e:
            print_w(f"Couldn't create GdkPixbuf ({e})")
        else:
            loader.write(data)
            loader.close()
            print_d(f"Got web image from {url}")
            return loader.get_pixbuf()

    def _finished(self, pixbuf):
        if pixbuf is None:
            self.set_from_icon_name("image-missing", Gtk.IconSize.LARGE)
        else:
            self.set_from_pixbuf(pixbuf)


class HighlightToggleButton(Gtk.ToggleButton):
    """A ToggleButton which changes the foreground color when active"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._provider = None
        self._color = ""
        self._dummy = Gtk.ToggleButton()

    def _update_provider(self):
        # not active, reset everything
        if not self.get_active():
            if self._provider is not None:
                style_context = self.get_style_context()
                style_context.remove_provider(self._provider)
                self._provider = None
                self._color = ""
            return

        # in case the foreground changes between normal and checked
        # state assume that the theme does some highlighting and stop.
        style_context = self._dummy.get_style_context()
        style_context.save()
        style_context.set_state(Gtk.StateFlags.NORMAL)
        a = style_context.get_color(style_context.get_state())
        style_context.set_state(Gtk.StateFlags.CHECKED)
        b = style_context.get_color(style_context.get_state())
        same_color = a.to_string() == b.to_string()
        style_context.restore()
        if not same_color:
            style_context = self.get_style_context()
            if self._provider is not None:
                style_context.remove_provider(self._provider)
                self._provider = None
                self._color = ""
            return

        # force a color
        style_context = self.get_style_context()
        style_context.save()
        style_context.set_state(Gtk.StateFlags.VISITED)
        color = style_context.get_color(style_context.get_state())
        style_context.restore()
        if self._color != color.to_string():
            self._color = color.to_string()
            style_context = self.get_style_context()
            if self._provider is not None:
                style_context.remove_provider(self._provider)

            provider = Gtk.CssProvider()
            provider.load_from_data((f"* {{color: {self._color}}}").encode("ascii"))
            style_context.add_provider(
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self._provider = provider

    def do_draw(self, context):
        self._update_provider()
        return Gtk.ToggleButton.do_draw(self, context)
