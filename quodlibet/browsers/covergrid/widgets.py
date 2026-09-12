# Copyright 2022 Thomas Leberbauer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from gi.repository import GObject, Gio, GdkPixbuf, Gtk, Gdk, Pango
from .models import AlbumListItem

from quodlibet.qltk import is_accel_pressed
from quodlibet.qltk.cover import get_no_cover_pixbuf
from quodlibet.qltk.image import add_border_widget


def _no_cover(size) -> GdkPixbuf.Pixbuf | None:
    old_size, pixbuf = getattr(_no_cover, "cache", (None, None))
    if old_size != size or pixbuf is None:
        pixbuf = get_no_cover_pixbuf(size, size)
        _no_cover.cache = size, pixbuf  # type: ignore
    return pixbuf


class AlbumWidget(Gtk.Box):
    """Displays an album with a cover and a label.

    Designed to be recycled by a ``Gtk.GridView`` factory:
    the widget is built once and an :class:`AlbumListItem` is attached/detached
    via :meth:`bind` and :meth:`unbind` as it scrolls into and out of view.
    """

    __gsignals__ = {"songs-menu": (GObject.SignalFlags.RUN_LAST, None, ())}

    padding = GObject.Property(type=int, default=0)
    cover_size = GObject.Property(type=int, default=48)
    text_visible = GObject.Property(type=bool, default=True)
    display_pattern = GObject.Property()

    def __init__(self, cancelable: Gio.Cancellable | None = None, **kwargs):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            vexpand=False,
            has_tooltip=True,
            **kwargs,
        )

        self.model: AlbumListItem | None = None
        self._cancelable = cancelable
        self.__model_sigs: list[int] = []

        image_size = self.__get_image_size()
        # GTK4: Gtk.Image only renders at icon size and downscales arbitrary pixbufs;
        # Gtk.Picture renders covers at their natural size.
        self._image = Gtk.Picture(
            content_fit=Gtk.ContentFit.CONTAIN, hexpand=True, vexpand=True
        )
        # GridView stretches each column to fill the width, so keep the cover
        # square and filling the cell instead of floating at a fixed size.
        self._frame = frame = Gtk.AspectFrame(ratio=1.0, obey_child=False)
        frame.set_child(self._image)
        frame.set_size_request(image_size, image_size)

        self._label = label = Gtk.Label(
            ellipsize=Pango.EllipsizeMode.END,
            justify=Gtk.Justification.CENTER,
            max_width_chars=1,
        )

        self.append(frame)
        self.append(self._label)

        gesture = Gtk.GestureClick()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", lambda *_: self.emit("songs-menu"))
        self.add_controller(gesture)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self.__on_menu_key)
        self.add_controller(key_ctrl)

        self.bind_property("padding", self, "spacing", GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "text-visible", label, "visible", GObject.BindingFlags.SYNC_CREATE
        )

        self.connect("query-tooltip", self.__tooltip)
        self.connect("notify::cover-size", self.__cover_size)
        self.connect("notify::display-pattern", self.__display_pattern)

    def bind(self, model: AlbumListItem):
        self.model = model
        self.__model_sigs = [
            model.connect("notify::album", lambda *a: self.populate()),
            model.connect("notify::label", lambda *a: self._set_text(model.label)),
            model.connect("notify::cover", lambda *a: self._set_cover(model.cover)),
        ]
        self._set_cover(model.cover)
        self._set_text(model.label)
        # Only the visible items are bound,
        # so loading on demand here is what makes the grid cheap.
        # The model caches the cover/label,
        # so a recycled widget re-binding to the same item won't refetch.
        if model.cover is None:
            model.load_cover(
                self.props.scale_factor * self.props.cover_size, self._cancelable
            )
        if model.label is None:
            model.format_label(self.props.display_pattern)

    def unbind(self):
        if self.model is None:
            return
        for sig in self.__model_sigs:
            self.model.disconnect(sig)
        self.__model_sigs = []
        self.model = None
        self._set_cover(None)

    def do_measure(self, orientation, for_size):
        image_size = self.__get_image_size()
        width = image_size + 4 * self.props.padding
        if orientation == Gtk.Orientation.HORIZONTAL:
            return (width, width, -1, -1)
        return Gtk.Box.do_measure(self, orientation, for_size)

    def __get_image_size(self) -> int:
        return self.props.cover_size + 2

    def populate(self):
        """Force a cover/label (re)load for the bound item."""
        if self.model is None:
            return
        size = self.props.scale_factor * self.props.cover_size
        self.model.load_cover(size, self._cancelable)
        self.model.format_label(self.props.display_pattern)

    def _set_cover(self, cover: GdkPixbuf.Pixbuf | None = None):
        if cover:
            pb = add_border_widget(cover, self)
        else:
            size = self.props.scale_factor * self.props.cover_size
            pb = _no_cover(size)
        self._image.set_paintable(Gdk.Texture.new_for_pixbuf(pb))

    def _set_text(self, label: str | None = None):
        if label:
            self._label.set_markup(label)

    def __cover_size(self, _, prop):
        size = self.__get_image_size()
        self._frame.set_size_request(size, size)
        self._set_cover(self.model.cover if self.model else None)
        self.populate()

    def __display_pattern(self, _, prop):
        if self.model is not None:
            self.model.format_label(self.props.display_pattern)

    def __on_menu_key(self, _controller, keyval, _keycode, state):
        if is_accel_pressed(keyval, state, "Menu", "<Shift>F10"):
            self.emit("songs-menu")
            return True
        return False

    def __tooltip(self, widget, x, y, keyboard_tip, tooltip):
        label = self.model.label if self.model else None
        if label:
            tooltip.set_markup(label)
            return True
        return False
