# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import time

import gobject, gtk, pango
import const
import config
import qltk
import util

import cPickle as pickle

from browsers.base import Browser
from qltk.views import HintedTreeView
from qltk.getstring import GetStringDialog
from qltk.msg import ErrorMessage
from qltk.downloader import DownloadWindow
import formats; from formats.remote import RemoteFile
import config

FEEDS = os.path.join(const.DIR, "feeds")

if sys.version_info < (2, 4): from sets import Set as set

class InvalidFeed(ValueError): pass

class Feed(list):
    def __init__(self, uri):
        self.name = _("Unknown")
        self.uri = uri
        self.changed = False
        self.website = ""
        self.__lastgot = 0

    def get_age(self):
        return time.time() - self.__lastgot

    def __fill_af(feed, af):
        try: af["title"] = feed.title or _("Unknown")
        except: af["title"] = _("Unknown")
        try: af["date"] = "%04d-%02d-%02d" % feed.modified_parsed[:3]
        except AttributeError: pass

        for songkey, feedkey in [
            ("website", "link"),
            ("description", "tagline"),
            ("language", "language"),
            ("copyright", "copyright"),
            ("organization", "publisher"),
            ("license", "license")]:
            try: value = getattr(feed, feedkey)
            except: pass
            else:
                if value and value not in af.list(songkey):
                    af.add(songkey, value)

        try: author = feed.author_detail
        except AttributeError:
            try: author = feed.author
            except AttributeError: pass
            else:
                if author and author not in af.list("artist"):
                    af.add('artist', author)
        else:
            if author.email and author.email not in af.list("contact"):
                af.add("contact", author.email)
            if author.name and author.name not in af.list("artist"):
                af.add("artist", author.name)

        try: values = feed.contributors
        except AttributeError: pass
        else:
            for value in values:
                try: value = value.name
                except AttributeError: pass
                else:
                    if value and value not in af.list("performer"):
                        af.add("performer", value)

        try: values = dict(feed.categories).values()
        except AttributeError: pass
        else:
            for value in values:
                if value and value not in af.list("genre"):
                    af.add("genre", value)
    __fill_af = staticmethod(__fill_af)

    def parse(self):
        doc = feedparser.parse(self.uri)
        try: album = doc.channel.title
        except AttributeError: return False

        if album: self.name = album
        else: self.name = _("Unknown")

        from formats._audio import AudioFile
        defaults = AudioFile({"feed": self.uri})
        try: self.__fill_af(doc.channel, defaults)
        except: return False

        entries = []
        uris = set()
        for entry in doc.entries:
            try:
                for enclosure in entry.enclosures:
                    try:
                        if ("audio" in enclosure.type or
                            formats.filter(enclosure.url)):
                            uri = enclosure.url.encode('ascii', 'replace')
                            try: size = enclosure.length
                            except AttributeError: size = 0
                            entries.append((uri, entry, size))
                            uris.add(uri)
                            break
                    except AttributeError: pass
            except AttributeError: pass

        for entry in list(self):
            if entry["~uri"] not in uris: self.remove(entry)
            else: uris.remove(entry["~uri"])

        entries.reverse()
        for uri, entry, size in entries:
            if uri in uris:
                song = RemoteFile(uri)
                song["~#size"] = size
                song.fill_metadata = False
                song.update(defaults)
                song["album"] = self.name
                try: self.__fill_af(entry, song)
                except: pass
                else: self.insert(0, song)
        self.__lastgot = time.time()
        return bool(uris)

class AddFeedDialog(GetStringDialog):
    def __init__(self, parent):
        super(AddFeedDialog, self).__init__(
            qltk.get_top_parent(parent), _("New Feed"),
            _("Enter the location of an audio feed:"),
            okbutton=gtk.STOCK_ADD)

    def run(self):
        uri = super(AddFeedDialog, self).run()
        if uri: return Feed(uri.encode('ascii', 'replace'))
        else: return None

class AudioFeeds(Browser, gtk.VBox):
    __gsignals__ = Browser.__gsignals__

    __feeds = gtk.ListStore(object) # unread

    headers = "title date album website".split()

    expand = qltk.RHPaned

    def cell_data(col, render, model, iter):
        if model[iter][0].changed:
            render.markup = "<b>%s</b>" % util.escape(model[iter][0].name)
        else: render.markup = util.escape(model[iter][0].name)
        render.set_property('markup', render.markup)
    cell_data = staticmethod(cell_data)

    def changed(klass, feeds):
        for row in klass.__feeds:
            if row[0] in feeds:
                row[0].changed = True
                row[0] = row[0]
        AudioFeeds.write()
    changed = classmethod(changed)

    def write(klass):
        feeds = [row[0] for row in klass.__feeds]
        f = file(FEEDS, "wb")
        pickle.dump(feeds, f, pickle.HIGHEST_PROTOCOL)
        f.close()
    write = classmethod(write)

    def init(klass, watcher):
        try: feeds = pickle.load(file(FEEDS, "rb"))
        except EnvironmentError: pass
        else:
            for feed in feeds:
                klass.__feeds.append(row=[feed])
        gobject.idle_add(klass.__do_check)
    init = classmethod(init)

    def __do_check(klass):
        import threading
        thread = threading.Thread(target=klass.__check, args=())
        thread.setDaemon(True)
        thread.start()
    __do_check = classmethod(__do_check)

    def __check(klass):
        for row in klass.__feeds:
            feed = row[0]
            if feed.get_age() < 2*60*60: continue
            elif feed.parse():
                feed.changed = True
                row[0] = feed
        klass.write()
        gobject.timeout_add(60*60*1000, klass.__do_check)
    __check = classmethod(__check)

    def Menu(self, songs, songlist):
        if len(songs) == 1:
            item = qltk.MenuItem(_("Download..."), gtk.STOCK_CONNECT)
            item.connect('activate', self.__download, songs[0]("~uri"))
            item.set_sensitive(not songs[0].is_file)
            m = gtk.Menu()
            m.append(item)
            return m
        else:
            songs = filter(lambda s: not s.is_file, songs)
            uris = [song("~uri") for song in songs]
            item = qltk.MenuItem(_("Download..."), gtk.STOCK_CONNECT)
            item.connect('activate', self.__download_many, uris)
            item.set_sensitive(songs)
            m = gtk.Menu()
            m.append(item)
            return m

    def __download_many(self, activator, sources):
        chooser = gtk.FileChooserDialog(
            title=_("Download Files"), parent=qltk.get_top_parent(self),
            action=gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        resp = chooser.run()
        if resp == gtk.RESPONSE_OK:
            target = chooser.get_filename()
            if target:
                for i, source in enumerate(sources):
                    base = os.path.basename(source)
                    if not base:
                        base = ("file%d" % i) + (
                            os.path.splitext(source)[1] or ".audio")
                    fulltarget = os.path.join(target, base)
                    DownloadWindow.download(source, fulltarget)
        chooser.destroy()

    def __download(self, activator, source):
        chooser = gtk.FileChooserDialog(
            title=_("Download File"), parent=qltk.get_top_parent(self),
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        name = os.path.basename(source)
        if name: chooser.set_current_name(name)
        resp = chooser.run()
        if resp == gtk.RESPONSE_OK:
            target = chooser.get_filename()
            if target: DownloadWindow.download(source, target)
        chooser.destroy()

    def __init__(self, watcher, main):
        super(AudioFeeds, self).__init__(spacing=6)
        self.__main = bool(main)

        self.__view = view = HintedTreeView()
        self.__render = render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        col = gtk.TreeViewColumn("Audio Feeds", render)
        col.set_cell_data_func(render, AudioFeeds.cell_data)
        view.append_column(col)
        view.set_model(self.__feeds)
        view.set_rules_hint(True)
        view.set_headers_visible(False)
        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        swin.add(view)
        self.pack_start(swin)

        new = gtk.Button(stock=gtk.STOCK_NEW)
        new.connect('clicked', self.__new_feed)
        view.get_selection().connect('changed', self.__changed)
        view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        view.connect('popup-menu', self.__popup_menu)

        self.connect_object('destroy', self.__save, view)

        self.pack_start(new, expand=False)
        self.show_all()

    def __menu(self, view):
        model, paths = view.get_selection().get_selected_rows()
        menu = gtk.Menu()
        refresh = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        delete = gtk.ImageMenuItem(gtk.STOCK_DELETE)

        refresh.connect_object(
            'activate', self.__refresh, [model[p][0] for p in paths])
        delete.connect_object(
            'activate', map, model.remove, map(model.get_iter, paths))

        menu.append(refresh)
        menu.append(delete)
        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        return menu

    def __save(self, view):
        AudioFeeds.write()

    def __popup_menu(self, view):
        self.__menu(view).popup(
            None, None, None, 0, gtk.get_current_event_time())
        return True

    def __refresh(self, feeds):
        changed = filter(Feed.parse, feeds)
        AudioFeeds.changed(changed)

    def activate(self): self.__changed(self.__view.get_selection())

    def __changed(self, selection):
        model, paths = selection.get_selected_rows()
        if model and paths:
            songs = []
            for path in paths:
                model[path][0].changed = False
                songs.extend(model[path][0])
            self.emit('songs-selected', songs, True)
            config.set("browsers", "audiofeeds",
                         "\t".join([model[path][0].name for path in paths]))

    def __new_feed(self, activator):
        feed = AddFeedDialog(self).run()
        if feed is not None:
            feed.changed = feed.parse()
            if feed:
                self.__feeds.append(row=[feed])
                AudioFeeds.write()
            else:
                ErrorMessage(
                    self, _("Unable to add feed"),
                    _("<b>%s</b> could not be added. The server may be down, "
                      "or the location may not be an audio feed.") %(
                    util.escape(feed.uri))).run()

    def restore(self):
        try: names = config.get("browsers", "audiofeeds").split("\t")
        except: pass
        else:
            paths = [(i,) for i, row in enumerate(self.__feeds)
                     if row[0].name in names]
            if paths:
                selection = self.__view.get_selection()
                selection.unselect_all()
                map(selection.select_path, paths)

gobject.type_register(AudioFeeds)

try: import feedparser
except ImportError:
    try: import _feedparser as feedparser
    except ImportError: feedparser = None

import gst
if feedparser and gst.element_make_from_uri(gst.URI_SRC, "http://", ""):
    browsers = [(20, _("_Audio Feeds"), AudioFeeds, True)]
else: browsers = []
