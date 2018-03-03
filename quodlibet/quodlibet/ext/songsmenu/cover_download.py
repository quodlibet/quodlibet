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
from quodlibet.qltk import Icons, Button
from quodlibet.qltk.paned import ConfigRVPaned
from quodlibet.util import connect_destroy, format_size, escape
from quodlibet.util.http import session


class ResizeWebImage(Gtk.Image):
    __gsignals__ = {
        # The size (in bytes) and properties of a cover once known
        'info-known': (GObject.SignalFlags.RUN_LAST, None, (int, object))
    }

    def __init__(self, url, preview_size=400, cancellable=None):
        super().__init__()
        self.preview_size = preview_size
        self.url = url
        self.cancellable = cancellable
        self.message = msg = Soup.Message.new('GET', self.url)
        session.send_async(msg, self.cancellable, self._sent, None)

        self.set_size_request(preview_size + 24, preview_size + 24)

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

    def _finished(self, istream, result):
        self._pixbuf = pb = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        resized = pb.scale_simple(self.preview_size, self.preview_size,
                                  GdkPixbuf.InterpType.BILINEAR)
        self.set_from_pixbuf(resized)
        istream.close()
        self.emit('info-known', self.size, self._pixbuf.props)
        self.queue_draw()


class CoverArtWindow(qltk.Window):

    def __init__(self, songs):
        super().__init__(title="Cover Art Download")
        self.set_default_size(1000, 800)
        self.flow_box = box = Gtk.FlowBox()
        box.set_row_spacing(12)
        self.model = model = Gio.ListStore()

        def update(img, size, props, item, frame):
            text = ("{} - {}x{}, <b>{}</b>".format(escape(item.source),
                    props.width, props.height, format_size(size)))
            frame.get_label_widget().set_markup(text)

        def create_widget(item, data=None):
            img = ResizeWebImage(item.url)
            text = _("(Loading %s (%s)...)") % (item.source, item.dimensions)
            frame = Gtk.Frame.new(text)
            img.connect('info-known', update, item, frame)
            frame.add(img)
            frame.set_label_align(0.5, 0.5)
            return frame

        box.bind_model(model, create_widget, None)
        box.set_valign(Gtk.Align.START)
        box.set_max_children_per_line(4)
        paned = ConfigRVPaned("plugins", "cover_art_pane_pos", 0.5)
        paned.ensure_wide_handle()
        self.add(paned)
        sw = Gtk.ScrolledWindow()
        sw.add(self.flow_box)
        options_box = Gtk.VBox()
        frame = Gtk.Frame(label=_("Options"))
        options_box.pack_start(frame, True, False, 6)
        self.button = Button(_("_Save"), Icons.DOCUMENT_SAVE_AS)
        self.button.set_sensitive(False)
        self.button.connect('clicked', self.__save)
        options_box.pack_start(self.button, True, False, 6)

        paned.pack1(sw, True, False)
        paned.pack2(options_box, True, False)

        manager = app.cover_manager

        def covers_found(manager, provider, results):
            if not results:
                print_d("No results from %s" % provider)
                return
            for result in results:
                self.model.append(result)
            self.show_all()

        def finished(manager, songs):
            print_d("Finished all searches")
            if not self.model.get_n_items():
                print_w("Nothing found from any sources")

                self.button.set_sensitive(False)
            else:
                self.button.set_sensitive(True)

        cancellable = self.__cancellable = Gio.Cancellable()
        connect_destroy(manager, 'covers-found', covers_found)
        connect_destroy(manager, 'searches-complete', finished)

        manager.search_cover(cancellable, songs)

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
        return CoverArtWindow(songs).show()
