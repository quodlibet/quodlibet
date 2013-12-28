# -*- coding: utf-8 -*-
# Copyright 2004-2013 Joe Wreschnig, Michael Urman, Iñigo Serna,
# Christoph Reiter, Nick Boultbee, Simonas Kazlauskas
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GLib, Gdk, GdkPixbuf, Gio, GObject

from quodlibet import qltk
from quodlibet import config
from quodlibet.util import thumbnails
from quodlibet.util.cover.manager import cover_plugins


# TODO: neater way of managing dependency on this particular plugin
ALBUM_ART_PLUGIN_ID = "Download Album Art"


def pixbuf_from_file(fileobj, boundary):
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

    return thumbnails.scale(pixbuf, boundary, scale_up=False)


class BigCenteredImage(qltk.Window):
    """Load an image and display it, scaling down to 1/2 the screen's
    dimensions if necessary.

    This might leak memory, but it could just be Python's GC being dumb."""

    def __init__(self, title, fileobj, parent):
        super(BigCenteredImage, self).__init__(type=Gtk.WindowType.POPUP)

        assert parent
        parent = qltk.get_top_parent(parent)
        self.set_transient_for(parent)

        if qltk.is_wayland():
            # no screen size with wayland, the parent window is
            # the next best thing..
            width, height = parent.get_size()
            width = int(width / 1.1)
            height = int(height / 1.1)
        else:
            width = int(Gdk.Screen.width() / 1.75)
            height = int(Gdk.Screen.height() / 1.75)

        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        pixbuf = None
        try:
            pixbuf = pixbuf_from_file(fileobj, (width, height))
        except GLib.GError:
            pass

        # failed to load, abort
        if not pixbuf:
            self.destroy()
            return

        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)

        event_box = Gtk.EventBox()
        event_box.add(image)

        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        frame.add(event_box)

        self.add(frame)

        event_box.connect('button-press-event', self.__destroy)
        event_box.connect('key-press-event', self.__destroy)
        self.get_child().show_all()

    def __destroy(self, *args):
        self.destroy()


def get_no_cover_pixbuf(width, height):
    """A no cover pixbux at max width x height"""

    # win32 workaround: https://bugzilla.gnome.org/show_bug.cgi?id=721062

    size = max(width, height)
    theme = Gtk.IconTheme.get_default()
    icon_info = theme.lookup_icon("quodlibet-missing-cover", size, 0)
    if icon_info is None:
        return

    filename = icon_info.get_filename()
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(filename, width, height)
    except GLib.GError:
        return


class ResizeImage(Gtk.Bin):
    def __init__(self, resize=False, size=1):
        Gtk.Bin.__init__(self)
        self._dirty = True
        self._path = None
        self._file = None
        self._pixbuf = None
        self._no_cover = None
        self._size = size
        self._resize = resize

    def set_file(self, fileobj):
        path = fileobj and fileobj.name

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

        self._pixbuf = None
        if self._file:
            try:
                self._pixbuf = thumbnails.get_thumbnail_from_file(
                    self._file, (256, 256))
            except GLib.GError:
                pass

        if not self._pixbuf:
            self._pixbuf = get_no_cover_pixbuf(256, 256)

        return self._pixbuf

    def _get_size(self, max_width, max_height):
        pixbuf = self._get_pixbuf()
        if not pixbuf:
            return 0, 0
        width, height = pixbuf.get_width(), pixbuf.get_height()
        return thumbnails.calc_scale_size(
                (max_width, max_height),
                (width, height))

    def do_get_request_mode(self):
        if self._resize:
            return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_get_preferred_width(self):
        if self._resize:
            return (0, 0)
        else:
            width, height = self._get_size(self._size, self._size)
            return (width, width)

    def do_get_preferred_height(self):
        if self._resize:
            return (0, 0)
        else:
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
        if self._path:
            if width < 2 or height < 2:
                return
            round_thumbs = config.getboolean("albumart", "round")
            pixbuf = thumbnails.scale(pixbuf, (width - 2, height - 2))
            pixbuf = thumbnails.add_border(pixbuf, 80, round_thumbs)
        else:
            pixbuf = thumbnails.scale(pixbuf, (width, height))

        style_context = self.get_style_context()
        Gtk.render_icon(style_context, cairo_context, pixbuf, 0, 0)


class CoverImage(Gtk.EventBox):
    __gsignals__ = {
        # We do not necessarily display cover at the same instant this widget
        # is created or set_song is called. This signal allows callers know
        # when the cover is visible for sure. The signal argument tells whether
        # cover shown is not the fallback image.
        'cover-visible': (GObject.SignalFlags.RUN_LAST, None, (bool,))
    }

    def __init__(self, resize=False, size=70, song=None):
        super(CoverImage, self).__init__()
        self.set_visible_window(False)
        self.__song = None
        self.__file = None
        self.__current_bci = None
        self.__cancellable = None

        self.add(ResizeImage(resize, size))
        self.connect('button-press-event', self.__show_cover)
        self.set_song(song)
        self.get_child().show_all()

    def set_image(self, _file):
        if _file is not None and not _file.name:
            print_w('Got file which is not in the filesystem!')
        self.__file = _file
        self.get_child().set_file(_file)

    def set_song(self, song):
        self.__song = song
        self.set_image(None)
        if self.__cancellable:
            self.__cancellable.cancel()
        cancellable = self.__cancellable = Gio.Cancellable.new()

        if song:
            def cb(success, result):
                if success:
                    try:
                        self.set_image(result)
                        self.emit('cover-visible', success)
                        # If this widget is already 'destroyed', we will get
                        # following error.
                    except AttributeError:
                        pass
            cover_plugins.acquire_cover(cb, cancellable, song)

    def refresh(self):
        self.set_song(self.__song)

    def __nonzero__(self):
        return bool(self.__file)

    def __reset_bci(self, bci):
        self.__current_bci = None

    def __show_cover(self, box, event):
        """Show the cover as a detached BigCenteredImage.
        If one is already showing, destroy it instead
        If there is no image, run the AlbumArt plugin
        """

        song = self.__song
        if not song:
            return

        if event.button != Gdk.BUTTON_PRIMARY or \
                event.type != Gdk.EventType.BUTTON_PRESS:
            return

        if not self.__file:
            from quodlibet.qltk.songsmenu import SongsMenu
            from quodlibet import app

            SongsMenu.plugins.handle(ALBUM_ART_PLUGIN_ID, app.library,
                                     qltk.get_top_parent(self), [song])
            return True

        if self.__current_bci is not None:
            # We're displaying it; destroy it.
            self.__current_bci.destroy()
            return True

        try:
            self.__current_bci = BigCenteredImage(
                song.comma("album"), self.__file, parent=self)
        except GLib.GError: # reload in case the image file is gone
            self.refresh()
        else:
            self.__current_bci.show()
            self.__current_bci.connect('destroy', self.__reset_bci)

        return True
