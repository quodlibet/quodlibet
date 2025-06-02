# Copyright 2004-2017 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Nick Boultbee, Simonas Kazlauskas
#           2018-2019 Fredrik Strupe
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GLib, Gdk, GdkPixbuf, Gio, GObject
from senf import fsnative

from quodlibet import qltk
from quodlibet import app
from quodlibet.util import thumbnails, print_w
from quodlibet.qltk.image import (
    pixbuf_from_file,
    calc_scale_size,
    scale,
    add_border_widget,
    get_surface_for_pixbuf,
)


# TODO: neater way of managing dependency on this particular plugin
ALBUM_ART_PLUGIN_ID = "Download Album Art"


class BigCenteredImage(qltk.Window):
    """Load an image and display it, scaling it down to the parent window size."""

    def __init__(self, title, fileobj, parent, scale=0.5):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_type_hint(Gdk.WindowTypeHint.TOOLTIP)

        assert parent
        parent = qltk.get_top_parent(parent)
        self.set_transient_for(parent)

        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        # If image fails to set, abort construction.
        if not self.set_image(fileobj, parent, scale):
            self.destroy()
            return

        event_box = Gtk.Box()
        event_box.add(self.__image)

        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        frame.add(event_box)

        self.add(frame)

        event_box.connect("button-press-event", self.__destroy)
        event_box.connect("key-press-event", self.__destroy)

        self.get_child().show_all()

    def set_image(self, file, parent, scale=0.5):
        scale_factor = self.get_scale_factor()

        (width, height) = self.__calculate_screen_width(parent, scale)

        pixbuf = None
        try:
            pixbuf = pixbuf_from_file(file, (width, height), scale_factor)
        except GLib.GError:
            return False

        # failed to load, abort
        if not pixbuf:
            return False

        self.__image = Gtk.Image()
        self.__image.set_from_surface(get_surface_for_pixbuf(self, pixbuf))

        return True

    def __calculate_screen_width(self, parent, scale=0.5):
        width, height = parent.get_size()
        width = int(width * scale)
        height = int(height * scale)
        return (width, height)

    def __destroy(self, *args):
        self.destroy()


def get_no_cover_pixbuf(width, height, scale_factor=1):
    """A no-cover pixbuf at maximum width x height"""

    # win32 workaround: https://bugzilla.gnome.org/show_bug.cgi?id=721062

    width *= scale_factor
    height *= scale_factor

    size = max(width, height)
    theme = Gtk.IconTheme.get_default()
    icon_info = theme.lookup_icon("quodlibet-missing-cover", size, 0)
    if icon_info is None:
        return None

    filename = icon_info.get_filename()
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(filename, width, height)
    except GLib.GError:
        return None


class ResizeImage(Gtk.Widget):
    def __init__(self, resize=False, size=1):
        super().__init__()
        self._dirty = True
        self._path = None
        self._file = None
        self._pixbuf = None
        self._no_cover = None
        self._size = size
        self._resize = resize

    def set_file(self, fileobj):
        if fileobj is None:
            path = None
        else:
            path = fileobj.name
            assert isinstance(path, fsnative)

        # XXX: Don't reload if the file path is the same.
        # Could prevent updates if fileobj.name isn't defined
        if self._path == path:
            return

        self._file = fileobj
        self._path = path
        self._dirty = True
        self.queue_resize()

    def _get_pixbuf(self):
        if not self._dirty:
            return self._pixbuf
        self._dirty = False

        max_size = 256 * self.get_scale_factor()

        self._pixbuf = None
        if self._file:
            self._pixbuf = thumbnails.get_thumbnail_from_file(
                self._file, (max_size, max_size)
            )

        if not self._pixbuf:
            self._pixbuf = get_no_cover_pixbuf(max_size, max_size)

        return self._pixbuf

    def _get_size(self, max_width, max_height):
        pixbuf = self._get_pixbuf()
        if not pixbuf:
            return 0, 0
        width, height = pixbuf.get_width(), pixbuf.get_height()
        return calc_scale_size((max_width, max_height), (width, height))

    def do_get_request_mode(self):
        if self._resize:
            return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_get_preferred_width(self):
        if self._resize:
            return (0, 0)
        width, height = self._get_size(self._size, self._size)
        return (width, width)

    def do_get_preferred_height(self):
        if self._resize:
            return (0, 0)
        width, height = self._get_size(self._size, self._size)
        return (height, height)

    def do_get_preferred_width_for_height(self, req_height):
        width, height = self._get_size(300, req_height)

        if width > 256:
            width = width

        return (width, width)

    def do_draw(self, cairo_context):
        pixbuf = self._get_pixbuf()
        if not pixbuf:
            return

        alloc = self.get_allocation()
        width, height = alloc.width, alloc.height

        scale_factor = self.get_scale_factor()

        width *= scale_factor
        height *= scale_factor

        if self._path:
            if width < (2 * scale_factor) or height < (2 * scale_factor):
                return
            pixbuf = scale(
                pixbuf, (width - 2 * scale_factor, height - 2 * scale_factor)
            )
            pixbuf = add_border_widget(pixbuf, self)
        else:
            pixbuf = scale(pixbuf, (width, height))

        style_context = self.get_style_context()
        if not pixbuf:
            print_w(f"Failed to scale pixbuf for {self._path}")
            return
        surface = get_surface_for_pixbuf(self, pixbuf)
        Gtk.render_icon_surface(style_context, cairo_context, surface, 0, 0)


class CoverImage(Gtk.Box):
    __gsignals__ = {
        # We do not necessarily display cover at the same instant this widget
        # is created or set_song is called. This signal allows callers know
        # when the cover is visible for sure. The signal argument tells whether
        # cover shown is not the fallback image.
        "cover-visible": (GObject.SignalFlags.RUN_LAST, None, (bool,))
    }

    def __init__(self, resize=False, size=70, song=None):
        super().__init__()
        self.set_visible_window(False)
        self.__song = None
        self.__file = None
        self.__current_bci = None
        self.__cancellable = None
        self._scale = 0.9

        self.add(ResizeImage(resize, size))
        self.connect("button-press-event", self.__album_clicked)
        self.set_song(song)
        self.get_child().show_all()

    def set_image(self, _file):
        if _file is not None and not _file.name:
            print_w("Got file which is not in the filesystem!")
        self.__file = _file
        self.get_child().set_file(_file)

    def set_song(self, song):
        self.__song = song
        self.set_image(None)
        if self.__cancellable:
            self.__cancellable.cancel()
        cancellable = self.__cancellable = Gio.Cancellable()

        if song:

            def cb(success, result):
                if success:
                    try:
                        self.set_image(result)
                        self.emit("cover-visible", success)
                        self.update_bci(result)
                        # If this widget is already 'destroyed', we will get
                        # following error.
                    except AttributeError:
                        pass
                else:
                    self.update_bci(None)

            app.cover_manager.acquire_cover(cb, cancellable, song)

    def refresh(self):
        self.set_song(self.__song)

    def update_bci(self, albumfile):
        # If there's a big image displaying, it should update.
        if self.__current_bci is not None:
            self.__current_bci.destroy()
            if albumfile:
                if self._scale:
                    self.__show_cover(self.__song, self._scale)
                else:
                    self.__show_cover(self.__song)

    def __nonzero__(self):
        return bool(self.__file)

    def __reset_bci(self, bci):
        self.__current_bci = None

    def __album_clicked(self, box, event):
        song = self.__song
        if not song:
            return None

        if (
            event.type != Gdk.EventType.BUTTON_PRESS
            or event.button == Gdk.BUTTON_MIDDLE
        ):
            return False

        return self.__show_cover(song, scale=self._scale)

    def __show_cover(self, song, scale=0.5):
        """Show the cover as a detached BigCenteredImage.
        If one is already showing, destroy it instead
        If there is no image, run the AlbumArt plugin
        """
        if not self.__file and song.is_file:
            from quodlibet.qltk.songsmenu import SongsMenu
            from quodlibet import app

            SongsMenu.plugins.handle(
                ALBUM_ART_PLUGIN_ID, app.library, qltk.get_top_parent(self), [song]
            )

            return True

        if self.__current_bci is not None:
            # We're displaying it; destroy it.
            self.__current_bci.destroy()
            return True

        if not self.__file:
            return False

        try:
            self.__current_bci = BigCenteredImage(
                song.comma("album"), self.__file, parent=self, scale=scale
            )
        except GLib.GError:  # reload in case the image file is gone
            self.refresh()
        else:
            self.__current_bci.show()
            self.__current_bci.connect("destroy", self.__reset_bci)

        return True
