# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#                2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gobject
import gtk
import pango

from quodlibet import qltk
from quodlibet import util
from quodlibet import config

from quodlibet.qltk.edittags import EditTags
from quodlibet.qltk.renamefiles import RenameFiles
from quodlibet.qltk.tagsfrompath import TagsFromPath
from quodlibet.qltk.tracknumbers import TrackNumbers
from quodlibet.qltk.views import HintedTreeView
from quodlibet.qltk.window import PersistentWindowMixin


class SongProperties(qltk.Window, PersistentWindowMixin):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    def __init__(self, library, songs, parent=None):
        super(SongProperties, self).__init__(dialog=False)
        self.set_transient_for(qltk.get_top_parent(parent))

        default_width = 600
        config_suffix = ""
        if len(songs) <= 1:
            default_width -= 200
            config_suffix += "single"
        self.set_default_size(default_width, 400)

        self.enable_window_tracking("quodlibet_properties",
                                    size_suffix=config_suffix)

        self.auto_save_on_change = config.getboolean(
                'editing', 'auto_save_changes', False)

        paned = gtk.HPaned()
        notebook = qltk.Notebook()
        pages = []
        pages.extend([Ctr(self, library) for Ctr in
                      [EditTags, TagsFromPath, RenameFiles]])
        if len(songs) > 1:
            pages.append(TrackNumbers(self, library))
        for page in pages: notebook.append_page(page)
        self.set_border_width(12)

        fbasemodel = gtk.ListStore(object, str)
        fmodel = gtk.TreeModelSort(fbasemodel)
        fview = HintedTreeView(fmodel)
        fview.connect('button-press-event', self.__pre_selection_changed)
        fview.set_rules_hint(True)
        selection = fview.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
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

        # Invisible selections behave a little strangely. So, when
        # handling this selection, there's a lot of if len(model) == 1
        # checks that "hardcode" the first row being selected.

        for song in songs:
            fbasemodel.append(row=[song, util.fsdecode(song("~basename"))])

        self.connect_object('changed', SongProperties.__set_title, self)

        selection.select_all()
        paned.pack2(notebook, shrink=False, resize=True)

        csig = selection.connect('changed', self.__selection_changed)
        s1 = library.connect(
            'changed', self.__refresh, fbasemodel, fview)
        s2 = library.connect(
            'removed', self.__remove, fbasemodel, selection, csig)
        self.connect_object('destroy', library.disconnect, s1)
        self.connect_object('destroy', library.disconnect, s2)
        self.connect_object('changed', self.set_pending, None)

        self.emit('changed', songs)
        self.add(paned)
        paned.set_position(175)
        notebook.show()
        paned.show()
        self.show()

    def __remove(self, library, songs, model, selection, sig):
        # If the handler is unblocked, then the selection gets updated
        # with some half-gone rows and we get a null-type error. So,
        # block the changed handler. Instead, track changes manually.
        # We can't just unconditionally emit a changed signal on the
        # selection or we risk voiding edits on a selection that
        # doesn't include the removed songs.
        selection.handler_block(sig)
        if len(model) == 1: rows = [(0,)]
        else: rows = selection.get_selected_rows()[1]
        to_remove = []
        changed = False
        for row in model:
            if row[0] in songs:
                to_remove.append(row.iter)
                changed = changed or (row.path in rows)
        map(model.remove, to_remove)
        selection.handler_unblock(sig)
        if changed:
            selection.emit('changed')

    def __set_title(self, songs):
        if songs:
            if len(songs) == 1: title = songs[0].comma("title")
            else:
                title = ngettext(
                    "%(title)s and %(count)d more",
                    "%(title)s and %(count)d more",
                    len(songs) - 1) % (
                    {'title': songs[0].comma("title"), 'count': len(songs) - 1})
            self.set_title("%s - %s" % (title, _("Properties")))
        else: self.set_title(_("Properties"))

    def __refresh(self, library, songs, model, view):
        view.freeze_notify()
        if len(model) == 1: rows = [(0,)]
        else: rows = view.get_selection().get_selected_rows()[1]
        changed = False
        for row in model:
            song = row[0]
            if song in songs:
                row[1] = song("~basename")
                changed = changed or (row.path in rows)
        view.thaw_notify()
        if changed:
            view.get_selection().emit('changed')

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event):
        if self.__save:
            if self.auto_save_on_change:
                self.__save.clicked()
                return
            resp = qltk.CancelRevertSave(self).run()
            if resp == gtk.RESPONSE_YES:
                self.__save.clicked()
            elif resp == gtk.RESPONSE_NO:
                return False
            else:
                return True # cancel or closed

    def __selection_changed(self, selection):
        model = selection.get_tree_view().get_model()
        if len(model) == 1:
            self.emit('changed', [model[(0,)][0]])
        else:
            model, rows = selection.get_selected_rows()
            songs = [model[row][0] for row in rows]
            self.emit('changed', songs)
