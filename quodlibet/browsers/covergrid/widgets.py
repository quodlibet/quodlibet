# Copyright 2022 Thomas Leberbauer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from gi.repository import GObject, Gio, GdkPixbuf, Gtk, Gdk, Pango
from .models import AlbumListItem

from quodlibet.qltk.cover import get_no_cover_pixbuf
from quodlibet.qltk.image import add_border_widget


def _no_cover(size) -> GdkPixbuf.Pixbuf | None:
    old_size, pixbuf = getattr(_no_cover, "cache", (None, None))
    if old_size != size or pixbuf is None:
        pixbuf = get_no_cover_pixbuf(size, size)
        _no_cover.cache = size, pixbuf  # type: ignore
    return pixbuf


class AlbumWidget(Gtk.FlowBoxChild):
    """An AlbumWidget displays an album with a cover and a label.

    The cover initially holds a placeholder. When the widget is realized the
    real cover loads and the label is shown.
    """

    __gsignals__ = {"songs-menu": (GObject.SignalFlags.RUN_LAST, None, ())}

    padding = GObject.Property(type=int, default=0)
    cover_size = GObject.Property(type=int, default=48)
    text_visible = GObject.Property(type=bool, default=True)
    display_pattern = GObject.Property()

    def __init__(
        self, model: AlbumListItem, cancelable: Gio.Cancellable | None = None, **kwargs
    ):
        super().__init__(has_tooltip=True, **kwargs)

        self.model = model
        self._cancelable = cancelable
        self.__realize_handler_id = None

        self._box = box = Gtk.Box(vexpand=False, orientation=Gtk.Orientation.VERTICAL)

        image_size = self.__get_image_size()
        self._image = Gtk.Image(width_request=image_size, height_request=image_size)
        self._label = label = Gtk.Label(
            ellipsize=Pango.EllipsizeMode.END, justify=Gtk.Justification.CENTER
        )

        box.append(self._image)
        box.append(self._label)

        eb = Gtk.Box()
        eb.connect("popup-menu", lambda _: self.emit("songs-menu"))
        # GTK4: use GestureClick instead of button-press-event
        gesture = Gtk.GestureClick()
        gesture.set_button(0)
        gesture.connect("pressed", self.__rightclick)
        eb.add_controller(gesture)
        eb.append(box)

        self.set_child(eb)

        # GTK4: "margin" property removed; bind each side individually
        for margin_prop in (
            "margin-top",
            "margin-bottom",
            "margin-start",
            "margin-end",
        ):
            self.bind_property(
                "padding", box, margin_prop, GObject.BindingFlags.SYNC_CREATE
            )
        self.bind_property("padding", box, "spacing", GObject.BindingFlags.SYNC_CREATE)
        self.bind_property(
            "text-visible", label, "visible", GObject.BindingFlags.SYNC_CREATE
        )

        model.connect("notify::album", lambda *a: self._populate())
        model.connect("notify::label", lambda *a: self._set_text(model.label))
        model.connect("notify::cover", lambda *a: self._set_cover(model.cover))

        self.connect("query-tooltip", self.__tooltip)
        self.connect("notify::cover-size", self.__cover_size)
        self.connect("notify::display-pattern", self.__display_pattern)

        self._set_cover(self.model.cover)
        self._set_text(self.model.label)
        self._populate_on_realize()

    def do_measure(self, orientation, for_size):
        image_size = self.__get_image_size()
        width = image_size + 4 * self.props.padding
        if orientation == Gtk.Orientation.HORIZONTAL:
            return (width, width, -1, -1)
        return Gtk.FlowBoxChild.do_measure(self, orientation, for_size)

    def __get_image_size(self) -> int:
        return self.props.cover_size + 2

    def populate(self):
        self._populate_on_realize()

    def _populate_on_realize(self):
        if self.get_realized():
            self._populate()
        else:
            if self.__realize_handler_id is not None:
                self.disconnect(self.__realize_handler_id)
            self.__realize_handler_id = self.connect("realize", self.__on_realize)

    def __on_realize(self, widget):
        if self.__realize_handler_id is not None:
            self.disconnect(self.__realize_handler_id)
            self.__realize_handler_id = None
        self._populate()

    def _populate(self):
        size = self.props.scale_factor * self.props.cover_size
        self.model.load_cover(size, self._cancelable)
        self.model.format_label(self.props.display_pattern)

    def _set_cover(self, cover: GdkPixbuf.Pixbuf | None = None):
        if cover:
            pb = add_border_widget(cover, self)
        else:
            size = self.props.scale_factor * self.props.cover_size
            pb = _no_cover(size)
        self._image.set_from_pixbuf(pb)

    def _set_text(self, label: str | None = None):
        if label:
            self._label.set_markup(label)

    def __cover_size(self, _, prop):
        size = self.__get_image_size()
        self._image.props.width_request = size
        self._image.props.height_request = size
        self._set_cover()
        self._populate_on_realize()

    def __display_pattern(self, _, prop):
        self.model.format_label(self.props.display_pattern)

    def __rightclick(self, gesture, n_press, x, y):
        if gesture.get_current_button() == Gdk.BUTTON_SECONDARY:
            self.emit("songs-menu")

    def __tooltip(self, widget, x, y, keyboard_tip, tooltip):
        label = self.model.label
        if label:
            tooltip.set_markup(label)
        return True
