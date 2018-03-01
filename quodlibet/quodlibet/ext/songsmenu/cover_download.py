# -*- coding: utf-8 -*-
# Copyright 2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gio, GLib, Soup, GdkPixbuf

from quodlibet import _, app, print_d, print_w
from quodlibet import qltk
from quodlibet.plugins.songshelpers import any_song, is_a_file
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons, Button
from quodlibet.qltk.paned import ConfigRVPaned
from quodlibet.util.http import session


class ResizeWebImage(Gtk.Image):

    def __init__(self, url, size=500, cancellable=None):
        super().__init__()
        self.size = size
        self.url = url
        self.cancellable = cancellable
        self.message = msg = Soup.Message.new('GET', self.url)
        session.send_async(msg, self.cancellable, self._sent, None)

        self.set_size_request(size, size)

    def _sent(self, session, task, data):
        try:
            status = int(self.message.get_property('status-code'))
            if status >= 400:
                msg = 'HTTP {0} error in {1} request to {2}'.format(
                    status, self.message.method, self.url)
                print_w(msg)
                return
            istream = session.send_finish(task)
            GdkPixbuf.Pixbuf.new_from_stream_at_scale_async(
                istream, self.size, self.size, True, None, self._finished)
            print_d('Got HTTP {code} on {method} request to {uri}.'.format(
                uri=self.url, code=status, method=self.message.method))
        except GLib.GError as e:
            print_w('Failed sending {method} request to {uri} ({err})'.format(
                method=self.message.method, uri=self.url, err=e))

    def _finished(self, istream, result):
        self._pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        self.set_from_pixbuf(self._pixbuf)
        istream.close()
        props = self._pixbuf.props
        print_d("Got web image pixbuf from %s (%d x %d)" %
                (self.url, props.width, props.height))
        self.queue_draw()


class CoverArtWindow(qltk.Window):
    def __init__(self, songs):
        super().__init__(title="Cover Art Download")
        self.set_default_size(1000, 800)
        self.flow_box = box = Gtk.FlowBox()
        self.model = model = Gio.ListStore()

        def create_widget(item, data=None):
            img = ResizeWebImage(item.url)
            text = "Image from %s (%s)" % (item.source, item.dimensions)
            frame = Gtk.Frame.new(text)
            frame.add(img)
            return frame

        box.bind_model(model, create_widget, None)
        box.set_valign(Gtk.Align.START)
        box.set_max_children_per_line(4)
        paned = ConfigRVPaned("plugins", "cover_art_pane_pos", 0.5)
        paned.ensure_wide_handle()
        self.add(paned)
        sw = Gtk.ScrolledWindow()
        sw.add(self.flow_box)
        vbox = Gtk.VBox()
        frame = Gtk.Frame(label=_("Options"))
        vbox.pack_start(frame, True, True, 6)
        self.button = Button(_("_Save"), Icons.DOCUMENT_SAVE_AS)
        self.button.set_sensitive(False)
        self.button.connect('clicked', self.__save)
        vbox.pack_start(self.button, True, False, 6)

        paned.pack1(sw, True, False)
        paned.pack2(vbox, True, False)

        manager = app.cover_manager

        def on_success(source, results, cancel=None):
            if not results:
                print_d("No results from %s" % source)
                return
            for result in results:
                self.model.append(result)
            self.show_all()
        cancellable = self.__cancellable = Gio.Cancellable()
        manager.search_cover(on_success, cancellable, songs)

    def __save(self):
        print_d("Saving...")
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
