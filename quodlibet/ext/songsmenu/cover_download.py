# Copyright 2018-2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import operator
import os
import shutil
from functools import reduce
from typing import Iterable

from gi.repository import GObject, Gtk, Gdk, Gio, GLib, Soup, GdkPixbuf

from quodlibet import _, app, print_d, print_w
from quodlibet import qltk
from quodlibet.formats import AudioFile
from senf import path2fsn
from quodlibet.pattern import ArbitraryExtensionFileFromPattern, Pattern
from quodlibet.plugins import (PluginConfig, ConfProp, IntConfProp,
                               BoolConfProp)
from quodlibet.plugins.songshelpers import any_song, is_a_file
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.paned import Paned
from quodlibet.qltk.window import PersistentWindowMixin
from quodlibet.util import connect_destroy, format_size, escape
from quodlibet.util.cover import CoverManager
from quodlibet.util.cover.manager import CoverData
from quodlibet.util.http import download

_FULL_PAT = "<albumartist|<albumartist>|<artist>><album| - <album>| - <title>>"
SAVE_PATTERNS = [
    "folder",
    "cover",
    _FULL_PAT,
    f"{_FULL_PAT} - front",
    f"{_FULL_PAT} - back"
]

IMAGE_EXTENSIONS = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
}


class DownloadCoverArt(SongsMenuPlugin):
    """Download and save album (cover) art from a variety of sources"""

    PLUGIN_ID = 'Download Cover Art'
    PLUGIN_NAME = _('Download Cover Art')
    PLUGIN_DESC = _('Downloads high-quality album covers using cover plugins.')
    PLUGIN_ICON = Icons.INSERT_IMAGE
    REQUIRES_ACTION = True

    plugin_handles = any_song(lambda song: song("album") and is_a_file(song))

    def plugin_album(self, songs):
        manager = app.cover_manager
        if not (songs and songs[0]("album")):
            return
        dialog = CoverArtWindow(songs, manager, Config())
        ret = dialog.run()
        if ret == Gtk.ResponseType.APPLY:
            manager.cover_changed(songs)
        dialog.destroy()


class Config:
    plugin_config = PluginConfig(DownloadCoverArt.PLUGIN_ID.replace(" ", "_"))
    preview_size = IntConfProp(plugin_config, "preview_size", 500)
    save_pattern = ConfProp(plugin_config, "save_pattern", "folder.%(ext)")
    over_scale = BoolConfProp(plugin_config, "preview_over_scale", True)
    re_encode = BoolConfProp(plugin_config, "re_encode", False)
    jpg_quality = IntConfProp(plugin_config, "jpeg_quality", 95)


class ResizeWebImage(Gtk.Image):
    """A resizeable widget that can receive loaded images, and save them"""

    __gsignals__ = {
        # The content-type, size (in bytes) and properties of a cover
        # once discovered
        'info-known': (GObject.SignalFlags.RUN_LAST, None, (str, int, object)),
        'failed': (GObject.SignalFlags.RUN_LAST, None, (str,))
    }

    def __init__(self, url, config: Config, cancellable=None):
        super().__init__()
        self.config = config
        self.url = url
        self.cancellable = cancellable
        self.message = msg = Soup.Message.new('GET', self.url)
        self._content_type = None
        self._original = None
        download(msg, cancellable, self._sent, None,
                 failure_callback=lambda *args: self.emit("failed", self.url))
        self.set_size_request(config.preview_size, config.preview_size)
        self._pixbuf = None

    @property
    def extension(self):
        return ("jpg" if self.config.re_encode else
                IMAGE_EXTENSIONS.get(self._content_type, "jpg"))

    def _sent(self, msg, result, data):
        headers = self.message.get_property('response-headers')
        self.size = int(headers.get('content-length'))
        self._content_type = headers.get('content-type')
        print_d("Loading %d KB (of %s)"
                % (len(result) / 1024, self._content_type))
        self._original = result
        try:
            loader = GdkPixbuf.PixbufLoader()
        except GLib.GError as e:
            print_w("Couldn't create GdkPixbuf (%s)" % e)
        else:
            loader.write(result)
            loader.close()
            self._pixbuf = loader.get_pixbuf()
            self.emit("info-known", self._content_type, self.size,
                      self._pixbuf.props)
            self.resize()
            self.queue_draw()

    def resize(self, new_size=None):
        if not self._pixbuf:
            return
        if new_size:
            self.config.preview_size = new_size
        else:
            new_size = self.config.preview_size
        props = self._pixbuf.props
        if not self.config.over_scale:
            new_size = min(props.width, props.height, new_size)
        resized = self._pixbuf.scale_simple(new_size, new_size,
                                            GdkPixbuf.InterpType.BILINEAR)
        self.set_from_pixbuf(resized)
        self.set_size_request(new_size, new_size)

    def save_image(self, fsn):
        fsn = path2fsn(fsn)
        if self.config.re_encode:
            quality = str(self.config.jpg_quality)
            print_d(f"Converting image to JPEG @ {quality}%")
            ret = self._pixbuf.savev(fsn, "jpeg", ["quality"], [quality])
            if not ret:
                raise IOError("Couldn't save to %s" % fsn)
        else:
            print_d("Saving original image to %s" % fsn)
            with open(fsn, "wb") as f:
                f.write(self._original)


class CoverArtWindow(qltk.Dialog, PersistentWindowMixin):
    SIZES = {
        300: _("Small"),
        500: _("Classic"),
        600: _("Large"),
        720: _("HD"),
        1080: _("Full HD"),
        1600: _("WQXGA"),
        2160: _("4K UHD")
    }
    DEFAULT_SIZE = list(SIZES.keys())[0]

    def __init__(self, songs: Iterable[AudioFile], manager: CoverManager,
                 config: Config, headless: bool = False, **kwargs):
        super().__init__(title=_("Cover Art Download"), use_header_bar=True,
                         **kwargs)
        self.set_default_size(1400, 720)
        id_ = DownloadCoverArt.PLUGIN_ID.lower().replace(" ", "_")
        self.enable_window_tracking(id_)
        self.config = config
        self.headless = headless
        self.flow_box = box = Gtk.FlowBox()
        self.model = Gio.ListStore()
        self.songs = songs
        self._groups = {}
        self.button = None

        def selected(fb):
            children = fb.get_selected_children()
            if children:
                cover = self.model.get_item(children[0].get_index())
                if cover:
                    self.button.set_sensitive(True)

        # Only supported on GTK >= 3.18 (not Ubuntu 16.04)
        # Re-enable some day perhaps...
        # box.bind_model(self.model, self.create_widget, None)
        box.set_valign(Gtk.Align.START)
        box.set_max_children_per_line(4)
        box.connect("selected-children-changed", selected)

        paned = Paned(orientation=Gtk.Orientation.VERTICAL)
        paned.ensure_wide_handle()
        sw = Gtk.ScrolledWindow()
        sw.add(self.flow_box)

        paned.pack1(sw, True, True)
        paned.pack2(self.create_options(), False, False)
        self.vbox.pack_start(paned, True, True, 0)

        connect_destroy(manager, "covers-found", self._covers_found)
        connect_destroy(manager, "searches-complete", self._finished)
        cancellable = self.__cancellable = Gio.Cancellable()
        self.show_all()

        # Do the search
        self._groups = manager.search_cover(cancellable, songs)

    def _image_failed(self, _view, message: str, widget: Gtk.Widget):
        print_d(f"Failed downloading image ({message}), removing result.")
        # FlowBox creates a hidden child on addition
        self.flow_box.remove(widget.get_parent())

    def _create_item_widget(self, item):
        def update(img, content_type, size, props, item, frame):
            format = IMAGE_EXTENSIONS.get(content_type, content_type).upper()
            source = escape(item.source)
            text = (f"{source} - {format}, "
                    f"{props.width} x {props.height}, "
                    f"<b>{format_size(size)}</b>")
            frame.get_label_widget().set_markup(text)
            frame.get_child().set_reveal_child(True)

        img = ResizeWebImage(item.url, config=self.config)
        text = (_("Loading %(source)s - %(dimensions)s…")
                % {'source': item.source, 'dimensions': item.dimensions})
        frame = Gtk.Frame.new(text)
        img.set_padding(12, 12)
        frame.set_shadow_type(Gtk.ShadowType.NONE)
        frame.set_border_width(12)
        img.connect("info-known", update, item, frame)
        img.connect("failed", self._image_failed, frame)
        reveal = Gtk.Revealer()
        reveal.set_reveal_child(False)
        reveal.props.transition_duration = 800
        reveal.props.transition_type = Gtk.RevealerTransitionType.CROSSFADE

        eb = Gtk.EventBox()
        eb.add(img)
        reveal.add(eb)
        frame.add(reveal)
        frame.set_label_align(0.5, 1.0)
        reveal.connect("button-press-event", self._on_click)
        return frame

    def _on_click(self, view, event):
        # TODO: less hacky way to detect double-click
        if (event.button == Gdk.BUTTON_PRIMARY and
                event.type != Gdk.EventType.BUTTON_PRESS):
            self.__save(None)
            self.destroy()

    def _filenames(self, pat_text, ext, full_path=False):
        def fn_for(song):
            pat = ArbitraryExtensionFileFromPattern(f"{pat_text}.{ext}")
            fn = pat.format(song)
            return os.path.join(song('~dirname'), fn) if full_path else fn

        return sorted({fn_for(song) for song in self.songs})

    def _covers_found(self, manager, provider, results):
        if not results:
            print_d(f"No results from {provider}")
            return
        for result in results:
            self.model.append(result)
            self.flow_box.insert(self._create_item_widget(result), 0)
        self.show_all()

    def _finished(self, manager, results):
        self.__cancellable.cancel()
        if not any(results.values()):
            print_w(f"Nothing found from {len(self._groups)} provider(s)")

            self.button.set_sensitive(False)
            if not self.headless:
                self._quit(results)

    def _quit(self, results):
        pat = Pattern("<albumartist|<albumartist>|<artist>> - <album>")
        group_songs = [songs
                       for group in self._groups.values()
                       for songs in group.values()]
        texts = {pat.format(s) for s in
                 reduce(operator.concat, group_songs, [])}
        albums = "\n".join(texts)
        providers = ", ".join({manager.name for manager in results.keys()})
        data = {'albums': escape(albums), 'providers': escape(providers)}
        text = _("Nothing found for albums:\n<i>%(albums)s</i>.\n\n"
                 "Providers used:\n<tt>%(providers)s</tt>") % data
        dialog = qltk.Message(Gtk.MessageType.INFO, parent=self,
                              title=_("No covers found"), description=text)
        dialog.run()
        self.destroy()

    @staticmethod
    def __image_from_child(child):
        # Ugh, horrible
        return child.get_child().get_child().get_child().get_child()

    def create_options(self):
        frame = Gtk.Frame(label=_("Options"))
        hbox = Gtk.HBox()
        sizes = self.SIZES.keys()
        slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,
                                          min(sizes), max(sizes), 100)
        for size, name in self.SIZES.items():
            slider.add_mark(size, Gtk.PositionType.BOTTOM, name)
        slider.set_show_fill_level(False)
        slider.set_value(self.config.preview_size)

        def format_dims(_slider, value):
            size = int(value)
            return _(f"{size} ✕ {size} px")

        def slider_changed(_slider):
            new_size = slider.get_value()
            try:
                for child in self.flow_box.get_children():
                    img = self.__image_from_child(child)
                    img.resize(new_size)
            except AttributeError as e:
                print_w(f"Couldn't set picture size(s) ({e})")

        slider.connect("format-value", format_dims)
        slider.connect("value-changed", slider_changed)
        label = Gtk.Label(_("Preview size"))
        label.set_mnemonic_widget(slider)
        hbox.pack_start(label, False, False, 6)
        hbox.pack_start(slider, True, True, 6)
        vbox = Gtk.VBox()
        vbox.pack_start(hbox, False, False, 6)

        def create_save_box():
            hbox = Gtk.HBox()
            label = Gtk.Label(_("Save destination"))
            hbox.pack_start(label, False, False, 6)
            model = Gtk.ListStore(str)
            for val in SAVE_PATTERNS:
                model.append(row=[val])
            save_filename = Gtk.ComboBox(model=model)
            label.set_mnemonic_widget(save_filename)
            cell = Gtk.CellRendererText()
            save_filename.pack_start(cell, True)

            def draw_save_type(column, cell, model, it, data):
                pat_text = model[it][0]
                ext = "jpg" if self.config.re_encode else "*"
                text = list(self._filenames(pat_text, ext))[0]
                cell.set_property("markup", f"<tt>{escape(text)}</tt>")

            save_filename.set_cell_data_func(cell, draw_save_type, None)

            def changed(combo):
                value = model.get_value(combo.get_active_iter(), 0)
                self.config.save_pattern = value

            def select_value(combo, value):
                for i, item in enumerate(model):
                    if value == item[0]:
                        combo.set_active(i)

            save_filename.connect("changed", changed)
            select_value(save_filename, self.config.save_pattern)
            hbox.pack_start(save_filename, False, False, 6)
            create_ccb = self.config.plugin_config.ConfigCheckButton
            tooltip = _("If not already a JPEG, convert the image to "
                        "a high-quality JPEG of the same size")
            re_encode = create_ccb(_("Save as JPEG"), "re_encode",
                                   tooltip=tooltip, populate=True)
            re_encode.connect("toggled", lambda _: hbox.queue_draw())
            hbox.pack_start(re_encode, False, False, 6)
            return hbox

        vbox.pack_start(create_save_box(), False, False, 6)
        frame.add(vbox)

        self.button = self.add_icon_button(_("_Save"), Icons.DOCUMENT_SAVE,
                                           Gtk.ResponseType.APPLY)
        self.button.set_sensitive(False)
        self.button.connect("clicked", self.__save)
        return frame

    def __save(self, button):
        child = self.flow_box.get_selected_children()[0]
        data = self.model.get_item(child.get_index())
        img = self.__image_from_child(child)
        self._save_images(data, img)

    def _save_images(self, data: CoverData, img: Gtk.Image):
        paths = self._filenames(self.config.save_pattern, img.extension,
                                full_path=True)
        first_path = paths.pop()
        print_d(f"Saving {data} to {first_path}")
        img.save_image(first_path)
        # Copying faster than potentially resizing
        for path in paths:
            shutil.copy(first_path, path)
