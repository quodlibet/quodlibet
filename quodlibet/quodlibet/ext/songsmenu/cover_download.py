# -*- coding: utf-8 -*-
# Copyright 2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GObject, Gtk, Gio, GLib, Soup, GdkPixbuf

from quodlibet import _, app, print_d, print_w
from quodlibet import qltk
from quodlibet.plugins.songshelpers import any_song, is_a_file
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.paned import ConfigRVPaned
from quodlibet.util import connect_destroy, format_size, escape
from quodlibet.util.http import session


class ResizeWebImage(Gtk.Image):
    __gsignals__ = {
        # The size (in bytes) and properties of a cover once known
        'info-known': (GObject.SignalFlags.RUN_LAST, None, (int, object))
    }

    def __init__(self, url, preview_size, cancellable=None):
        super().__init__()
        self.preview_size = preview_size
        self.url = url
        self.cancellable = cancellable
        self.message = msg = Soup.Message.new('GET', self.url)
        session.send_async(msg, self.cancellable, self._sent, None)
        # TODO: drop this sizing hack
        self.set_size_request(preview_size, preview_size)
        self._pixbuf = None

    def _sent(self, session, task, data):
        try:
            status = int(self.message.get_property('status-code'))
            if status >= 400:
                msg = 'HTTP {0} error in {1} request to {2}'.format(
                    status, self.message.method, self.url)
                print_w(msg)
                return
            headers = self.message.get_property('response-headers')
            self.size = int(headers.get('content-length'))
            print_d('Got HTTP {code} from {uri} ({size} KB)'.format(
                uri=self.url, code=status, size=int(self.size / 1024)))
            istream = session.send_finish(task)
            GdkPixbuf.Pixbuf.new_from_stream_async(istream, self.cancellable,
                                                   self._finished)

        except GLib.GError as e:
            print_w('Failed sending {method} request to {uri} ({err})'.format(
                method=self.message.method, uri=self.url, err=e))

    def resize(self, new_size=None):
        if not self._pixbuf:
            return
        if new_size:
            self.preview_size = new_size
        pb = self._pixbuf
        resized = pb.scale_simple(self.preview_size, self.preview_size,
                                  GdkPixbuf.InterpType.BILINEAR)
        self.set_from_pixbuf(resized)
        self.queue_resize()

    def _finished(self, istream, result):
        self._pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        self.resize()
        istream.close()
        self.emit('info-known', self.size, self._pixbuf.props)
        self.queue_draw()


class CoverArtWindow(qltk.Dialog):
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

    def __init__(self, songs):
        super().__init__(title="Cover Art Download", use_header_bar=True)
        self.set_default_size(1200, 640)
        self.flow_box = box = Gtk.FlowBox()
        self.model = model = Gio.ListStore()

        def update(img, size, props, item, frame):
            text = ("{} - {}x{}, <b>{}</b>".format(escape(item.source),
                    props.width, props.height, format_size(size)))
            frame.get_label_widget().set_markup(text)
            frame.get_child().set_reveal_child(True)

        def create_widget(item, data=None):
            img = ResizeWebImage(item.url, preview_size=self.DEFAULT_SIZE)
            text = (_("(Loading %(source)s (%(dimensions)s)…")
                    % {'source': item.source, 'dimensions': item.dimensions})
            frame = Gtk.Frame.new(text)
            img.set_padding(12, 12)
            frame.set_shadow_type(Gtk.ShadowType.NONE)
            frame.set_border_width(12)
            img.connect('info-known', update, item, frame)
            reveal = Gtk.Revealer()
            reveal.set_reveal_child(False)
            reveal.props.transition_duration = 800
            reveal.props.transition_type = Gtk.RevealerTransitionType.CROSSFADE
            reveal.add(img)
            frame.add(reveal)

            frame.set_label_align(0.5, 1.0)
            return frame

        box.bind_model(model, create_widget, None)
        box.set_valign(Gtk.Align.START)
        box.set_max_children_per_line(4)
        paned = ConfigRVPaned("plugins", "cover_art_pane_pos", 0.25)
        paned.ensure_wide_handle()
        sw = Gtk.ScrolledWindow()
        sw.add(self.flow_box)

        paned.pack1(sw, True, True)
        paned.pack2(self.create_options(), True, False)
        self.vbox.pack_start(paned, True, True, 0)

        manager = app.cover_manager
        connect_destroy(manager, 'covers-found', self._covers_found)
        connect_destroy(manager, 'searches-complete', self._finished)
        cancellable = self.__cancellable = Gio.Cancellable()
        self.show_all()

        # Do the search
        manager.search_cover(cancellable, songs)

    def _covers_found(self, manager, provider, results):
        if not results:
            print_d("No results from %s" % provider)
            return
        for result in results:
            self.model.append(result)
        self.show_all()

    def _finished(self, manager, songs):
        print_d("Finished all searches")
        if not self.model.get_n_items():
            print_w("Nothing found from any sources")
            self.button.set_sensitive(False)
        else:
            self.button.set_sensitive(True)

    def create_options(self):
        frame = Gtk.Frame(label=_("Options"))
        hbox = Gtk.HBox()
        sizes = self.SIZES.keys()
        slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,
                                          min(sizes), max(sizes), 20)
        for size, name in self.SIZES.items():
            slider.add_mark(size, Gtk.PositionType.BOTTOM, name)
        slider.set_show_fill_level(False)
        slider.set_value(self.DEFAULT_SIZE)

        def format_size(slider, value):
            return _("%(size)d ✕ %(size)d px") % {'size': value}

        def slider_changed(slider):
            new_size = slider.get_value()
            try:
                for child in self.flow_box.get_children():
                    img = child.get_child().get_child().get_child()
                    img.resize(new_size)
            except AttributeError as e:
                print_w("Couldn't set picture size(s) (%s)" % e)

        slider.connect('format-value', format_size)
        slider.connect('value-changed', slider_changed)
        label = Gtk.Label(_("Preview size"))
        label.set_mnemonic_widget(slider)
        hbox.pack_start(label, False, False, 6)
        hbox.pack_start(slider, True, True, 6)
        frame.add(hbox)

        self.button = self.add_icon_button(_("_Save"), Icons.DOCUMENT_SAVE,
                                           Gtk.ResponseType.APPLY)
        self.button.set_sensitive(False)
        self.button.connect('clicked', self.__save)
        return frame

    def __save(self, button):
        children = self.flow_box.get_selected_children()
        cover = self.model.get_item(children[0].get_index())
        print_d("Would be saving... data of %s" % cover)
        pass


class DownloadCoverArt(SongsMenuPlugin):
    """Download and save album (cover) art from a variety of sources"""

    PLUGIN_ID = 'Download Cover Art'
    PLUGIN_NAME = _('Download Cover Art')
    PLUGIN_DESC = _('Downloads album covers using cover plugins.')
    PLUGIN_ICON = Icons.INSERT_IMAGE
    REQUIRES_ACTION = True

    plugin_handles = any_song(is_a_file)

    def plugin_album(self, songs):
        dialog = CoverArtWindow(songs)
        dialog.run()
        dialog.destroy()
