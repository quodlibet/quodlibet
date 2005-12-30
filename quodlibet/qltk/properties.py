# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import sre
import gtk, pango, gobject

import stock
import qltk
from qltk.wlw import WritingWindow
from qltk.views import HintedTreeView
from qltk.cbes import ComboBoxEntrySave
from qltk.renamefiles import RenameFiles
from qltk.tracknumbers import TrackNumbers
from qltk.edittags import EditTags

import const
import config
import util

import __builtin__; __builtin__.__dict__.setdefault("_", lambda a: a)

class TagByFilename(gtk.VBox):
    def __init__(self, prop, watcher):
        gtk.VBox.__init__(self, spacing=6)
        self.title = _("Tag by Filename")
        self.set_border_width(12)
        hbox = gtk.HBox(spacing=12)

        # Main buttons
        preview = gtk.Button(stock=stock.PREVIEW)
        save = gtk.Button(stock=gtk.STOCK_SAVE)

        # Text entry and preview button
        combo = ComboBoxEntrySave(
            const.TBP, const.TBP_EXAMPLES.split("\n"))
        hbox.pack_start(combo)
        entry = combo.child
        hbox.pack_start(preview, expand=False)
        self.pack_start(hbox, expand=False)

        # Header preview display
        view = gtk.TreeView()
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        self.pack_start(sw)

        # Options
        vbox = gtk.VBox()
        space = gtk.CheckButton(_("Replace _underscores with spaces"))
        space.set_active(config.state("tbp_space"))
        titlecase = gtk.CheckButton(_("_Title-case resulting values"))
        titlecase.set_active(config.state("titlecase"))
        split = gtk.CheckButton(_("Split into _multiple values"))
        split.set_active(config.state("splitval"))
        addreplace = gtk.combo_box_new_text()
        addreplace.append_text(_("Tags replace existing ones"))
        addreplace.append_text(_("Tags are added to existing ones"))
        addreplace.set_active(config.getint("settings", "addreplace"))
        for i in [space, titlecase, split]:
            vbox.pack_start(i)
        vbox.pack_start(addreplace)
        self.pack_start(vbox, expand=False)

        # Save button
        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.pack_start(save)
        self.pack_start(bbox, expand=False)

        tips = qltk.Tooltips(self)
        tips.set_tip(
            titlecase,
            _("The first letter of each word will be capitalized"))

        # Changing things -> need to preview again
        kw = { "titlecase": titlecase,
               "splitval": split, "tbp_space": space }
        for i in [space, titlecase, split]:
            i.connect('toggled', self.__changed, preview, save, kw)
        entry.connect('changed', self.__changed, preview, save, kw)

        UPDATE_ARGS = [prop, view, combo, entry, preview, save,
                       space, titlecase, split]

        # Song selection changed, preview clicked
        preview.connect('clicked', self.__preview_tags, *UPDATE_ARGS)
        prop.connect_object(
            'changed', self.__class__.__update, self, *UPDATE_ARGS)

        # Save changes
        save.connect('clicked', self.__save_files, prop, view, entry,
                     addreplace, watcher)

        self.show_all()

    def __update(self, songs, parent, view, combo, entry, preview, save,
                 space, titlecase, split):
        from library import AudioFileGroup
        self.__songs = songs

        songinfo = AudioFileGroup(songs)
        if songs: pattern_text = entry.get_text().decode("utf-8")
        else: pattern_text = ""
        try: pattern = util.PatternFromFile(pattern_text)
        except sre.error:
            qltk.ErrorMessage(
                parent, _("Invalid pattern"),
                _("The pattern\n\t<b>%s</b>\nis invalid. "
                  "Possibly it contains the same tag twice or "
                  "it has unbalanced brackets (&lt; / &gt;).")%(
                util.escape(pattern_text))).run()
            return
        else:
            if pattern_text:
                combo.prepend_text(pattern_text)
                combo.write(const.TBP)

        invalid = []

        for header in pattern.headers:
            if not songinfo.can_change(header):
                invalid.append(header)
        if len(invalid) and songs:
            if len(invalid) == 1:
                title = _("Invalid tag")
                msg = _("Invalid tag <b>%s</b>\n\nThe files currently"
                        " selected do not support editing this tag.")
            else:
                title = _("Invalid tags")
                msg = _("Invalid tags <b>%s</b>\n\nThe files currently"
                        " selected do not support editing these tags.")
            qltk.ErrorMessage(
                parent, title, msg % ", ".join(invalid)).run()
            pattern = util.PatternFromFile("")

        view.set_model(None)
        rep = space.get_active()
        title = titlecase.get_active()
        split = split.get_active()
        model = gtk.ListStore(object, str,
                             *([str] * len(pattern.headers)))
        for col in view.get_columns():
            view.remove_column(col)

        col = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                 text=1)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(col)
        for i, header in enumerate(pattern.headers):
            render = gtk.CellRendererText()
            render.set_property('editable', True)
            render.connect(
                'edited', self.__row_edited, model, i + 2, preview)
            col = gtk.TreeViewColumn(header, render, text=i + 2)
            col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            view.append_column(col)
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()

        for song in songs:
            basename = song("~basename")
            basename = basename.decode(util.fscoding, "replace")
            row = [song, basename]
            match = pattern.match(song)
            for h in pattern.headers:
                text = match.get(h, '')
                if rep: text = text.replace("_", " ")
                if title: text = util.title(text)
                if split: text = "\n".join(util.split_value(text, spls))
                row.append(text)
            model.append(row=row)

        # save for last to potentially save time
        if songs: view.set_model(model)
        preview.set_sensitive(False)
        save.set_sensitive(len(pattern.headers) > 0)

    def __save_files(self, save, parent, view, entry, addreplace, watcher):
        pattern_text = entry.get_text().decode('utf-8')
        pattern = util.PatternFromFile(pattern_text)
        add = (addreplace.get_active() == 1)
        config.set("settings", "addreplace", str(addreplace.get_active()))
        win = WritingWindow(parent, len(self.__songs))

        was_changed = []

        for row in view.get_model():
            song = row[0]
            changed = False
            if not song.valid() and not qltk.ConfirmAction(
                parent, _("Tag may not be accurate"),
                _("<b>%s</b> changed while the program was running. "
                  "Saving without refreshing your library may "
                  "overwrite other changes to the song.\n\n"
                  "Save this song anyway?") %(
                util.escape(util.fsdecode(song("~basename"))))
                ).run():
                break

            for i, h in enumerate(pattern.headers):
                if row[i + 2]:
                    if not add or h not in song:
                        song[h] = row[i + 2].decode("utf-8")
                        changed = True
                    else:
                        vals = row[i + 2].decode("utf-8")
                        for val in vals.split("\n"):
                            if val not in song.list(h):
                                song.add(h, val)
                                changed = True

            if changed:
                try: song.write()
                except:
                    qltk.ErrorMessage(
                        parent, _("Unable to edit song"),
                        _("Saving <b>%s</b> failed. The file "
                          "may be read-only, corrupted, or you "
                          "do not have permission to edit it.")%(
                        util.escape(util.fsdecode(song('~basename'))))
                        ).run()
                    watcher.reload(song)
                    break
                was_changed.append(song)

            if win.step(): break

        win.destroy()
        watcher.changed(was_changed)
        watcher.refresh()
        save.set_sensitive(False)

    def __row_edited(self, renderer, path, new, model, colnum, preview):
        row = model[path]
        if row[colnum] != new:
            row[colnum] = new
            preview.set_sensitive(True)

    def __preview_tags(self, activator, *args):
        self.__update(self.__songs, *args)

    def __changed(self, activator, preview, save, kw):
        for key, widget in kw.items():
            config.set("settings", key, str(widget.get_active()))
        preview.set_sensitive(True)
        save.set_sensitive(False)

class SongProperties(qltk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    def __init__(self, watcher, songs):
        super(SongProperties, self).__init__()
        if len(songs) > 1: self.set_default_size(600, 400)
        else: self.set_default_size(400, 400)
        paned = gtk.HPaned()
        notebook = qltk.Notebook()
        pages = []
        pages.extend([Ctr(self, watcher) for Ctr in
                      [EditTags, TagByFilename, RenameFiles]])
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

        # Although connecting 'changed' would be a better idea, it results
        # in segfaults as the model is updated while songs are being saved
        # as the sorted model goes nuts.
        s1 = watcher.connect('refresh', self.__refresh, fbasemodel, selection)
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
        to_remove = [row.iter for row in model if row[0] in songs]
        if to_remove:
            selection.handler_block(sig)
            map(model.remove, to_remove)
            selection.handler_unblock(sig)
            self.__refill(model)
            selection.emit('changed')

    def __set_title(self, songs):
        if songs:
            if len(songs) == 1: title = songs[0].comma("title")
            else: title = _("%(title)s and %(count)d more") % (
                    {'title':songs[0].comma("title"), 'count':len(songs) - 1})
            self.set_title("%s - %s" % (title, _("Properties")))
        else: self.set_title(_("Properties"))

    def __refresh(self, watcher, model, selection):
        self.__refill(model)
        selection.emit('changed')

    def __refill(self, model):
        for row in model:
            song = row[0]
            row[1] = song("~basename")
            row[2] = song("~dirname")
            row[3] = song["~filename"]

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

gobject.type_register(SongProperties)
