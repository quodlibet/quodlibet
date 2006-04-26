# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject
import gtk
import pango

import qltk
import util

from qltk.edittags import EditTags
from qltk.renamefiles import RenameFiles
from qltk.tagsfrompath import TagsFromPath
from qltk.tracknumbers import TrackNumbers
from qltk.views import HintedTreeView

class SongProperties(qltk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    def __init__(self, watcher, songs):
        super(SongProperties, self).__init__()
        if len(songs) > 1: self.set_default_size(600, 400)
        else: self.set_default_size(400, 400)
        self.plugins.rescan()

        paned = gtk.HPaned()
        notebook = qltk.Notebook()
        pages = []
        pages.extend([Ctr(self, watcher) for Ctr in
                      [EditTags, TagsFromPath, RenameFiles]])
        if len(songs) > 1:
            pages.append(TrackNumbers(self, watcher))
        for page in pages: notebook.append_page(page)
        self.set_border_width(12)

        fbasemodel = gtk.ListStore(object, str, str, str)
        fmodel = gtk.TreeModelSort(fbasemodel)
        fview = HintedTreeView(fmodel)
        fview.connect('button-press-event', self.__pre_selection_changed)
        fview.set_rules_hint(True)
        selection = fview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        csig = selection.connect('changed', self.__selection_changed)
        self.__save = None

        if len(songs) > 1:
            render = gtk.CellRendererText()
            c1 = gtk.TreeViewColumn(_('File'), render, text=1)
            render.set_property('ellipsize', pango.ELLIPSIZE_END)
            c1.set_sort_column_id(1)
            fview.append_column(c1)
            sw = gtk.ScrolledWindow()
            sw.add(fview)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
            sw.show_all()
            paned.pack1(sw, shrink=True, resize=True)

        for song in songs:
            fbasemodel.append(
                row = [song,
                       util.fsdecode(song("~basename")),
                       util.fsdecode(song("~dirname")),
                       song["~filename"]])

        self.connect_object('changed', SongProperties.__set_title, self)

        selection.select_all()
        paned.pack2(notebook, shrink=False, resize=True)
        self.connect_object('destroy', fview.set_model, None)
        self.connect_object('destroy', gtk.ListStore.clear, fbasemodel)

        s1 = watcher.connect(
            'changed', self.__refresh, fbasemodel, fview)
        s2 = watcher.connect(
            'removed', self.__remove, fbasemodel, selection, csig)
        self.connect_object('destroy', watcher.disconnect, s1)
        self.connect_object('destroy', watcher.disconnect, s2)
        self.connect_object('changed', self.set_pending, None)

        self.emit('changed', songs)
        self.add(paned)
        paned.set_position(175)
        notebook.show()
        paned.show()
        self.show()

    def __remove(self, watcher, songs, model, selection, sig):
        map(model.remove, [row.iter for row in model if row[0] in songs])

    def __set_title(self, songs):
        if songs:
            if len(songs) == 1: title = songs[0].comma("title")
            else: title = _("%(title)s and %(count)d more") % (
                    {'title':songs[0].comma("title"), 'count':len(songs) - 1})
            self.set_title("%s - %s" % (title, _("Properties")))
        else: self.set_title(_("Properties"))

    def __refresh(self, watcher, songs, model, view):
        view.freeze_notify()
        rows = view.get_selection().get_selected_rows()[1]
        is_one_song = len(model) == 1
        changed = False
        for row in model:
            song = row[0]
            if song in songs:
                model.set(row.iter, 1, song("~basename"),
                          2, song("~dirname"), 3, song["~filename"])
                changed = changed or (row.path in rows) or is_one_song
        view.thaw_notify()
        if changed:
            view.get_selection().emit('changed')

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event):
        if self.__save:
            resp = qltk.CancelRevertSave(self).run()
            if resp == gtk.RESPONSE_YES: self.__save.clicked()
            elif resp == gtk.RESPONSE_NO: return False
            else: return True # cancel or closed

    def __selection_changed(self, selection):
        model = selection.get_tree_view().get_model()
        if model and len(model) == 1: self.emit('changed', [model[(0,)][0]])
        else:
            model, rows = selection.get_selected_rows()
            songs = [model[row][0] for row in rows]
            self.emit('changed', songs)
