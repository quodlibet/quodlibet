# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import sre
import gtk

import stock
import qltk
from qltk.wlw import WritingWindow
from qltk.cbes import ComboBoxEntrySave
from qltk.ccb import ConfigCheckButton

import const
import config
import util

import __builtin__; __builtin__.__dict__.setdefault("_", lambda a: a)

class TagsFromPattern(object):
    def __init__(self, pattern):
        self.compile(pattern)

    def compile(self, pattern):
        self.headers = []
        self.slashes = len(pattern) - len(pattern.replace(os.path.sep,'')) + 1
        self.pattern = None
        # patterns look like <tagname> non regexy stuff <tagname> ...
        pieces = sre.split(r'(<[A-Za-z0-9_]+>)', pattern)
        override = { '<tracknumber>': r'\d\d?', '<discnumber>': r'\d\d??' }
        for i, piece in enumerate(pieces):
            if not piece: continue
            if piece[0]+piece[-1] == '<>' and piece[1:-1].isalnum():
                piece = piece.lower()   # canonicalize to lowercase tag names
                pieces[i] = '(?P%s%s)' % (piece, override.get(piece, '.+'))
                self.headers.append(piece[1:-1].encode("ascii", "replace"))
            else:
                pieces[i] = sre.escape(piece)

        # some slight magic to anchor searches "nicely"
        # nicely means if it starts with a <tag>, anchor with a /
        # if it ends with a <tag>, anchor with .xxx$
        # but if it's a <tagnumber>, don't bother as \d+ is sufficient
        # and if it's not a tag, trust the user
        if pattern.startswith('<') and not pattern.startswith('<tracknumber>')\
                and not pattern.startswith('<discnumber>'):
            pieces.insert(0, os.path.sep)
        if pattern.endswith('>') and not pattern.endswith('<tracknumber>')\
                and not pattern.endswith('<discnumber>'):
            pieces.append(r'(?:\.\w+)$')

        self.pattern = sre.compile(''.join(pieces))

    def match(self, song):
        if isinstance(song, dict):
            song = song['~filename'].decode(fscoding, "replace")
        # only match on the last n pieces of a filename, dictated by pattern
        # this means no pattern may effectively cross a /, despite .* doing so
        sep = os.path.sep
        matchon = sep+sep.join(song.split(sep)[-self.slashes:])
        match = self.pattern.search(matchon)

        # dicts for all!
        if match is None: return {}
        else: return match.groupdict()

class FilterCheckButton(ConfigCheckButton):
    def __init__(self):
        super(FilterCheckButton, self).__init__(
            self._label, "tagsfrompath", self._key)
        try: self.set_active(config.getboolean("tagsfrompath", self._key))
        except: pass
    active = property(lambda s: s.get_active())

    def filter(self, filename): raise NotImplementedError

class UnderscoresToSpaces(FilterCheckButton):
    _label = _("Replace _underscores with spaces")
    _key = "underscores"
    def filter(self, tag): return tag.replace("_", " ")

class TitleCase(FilterCheckButton):
    _label = _("_Title-case tags")
    _key = "titlecase"
    def filter(self, tag): return util.title(tag)

class SplitTag(FilterCheckButton):
    _label = _("Split into _multiple values")
    _key = "split"
    def filter(self, tag):
        spls = config.get("editing", "split_on").decode('utf-8', 'replace')
        spls = spls.split()
        return "\n".join(util.split_value(tag, spls))

class TagsFromPath(gtk.VBox):
    def __init__(self, prop, watcher):
        gtk.VBox.__init__(self, spacing=6)
        self.title = _("Tags From Path")
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
        space = UnderscoresToSpaces()
        titlecase = TitleCase()
        split = SplitTag()
        addreplace = gtk.combo_box_new_text()
        addreplace.append_text(_("Tags replace existing ones"))
        addreplace.append_text(_("Tags are added to existing ones"))
        addreplace.set_active(config.getboolean("tagsfrompath", "add"))
        addreplace.connect('changed', self.__add_changed)
        vbox.pack_start(addreplace)
        self.__filters = [space, titlecase, split]
        map(vbox.pack_start, self.__filters)
        self.pack_start(vbox, expand=False)

        # Save button
        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.pack_start(save)
        self.pack_start(bbox, expand=False)

        entry.connect_object('changed', preview.set_sensitive, True)
        entry.connect_object('changed', save.set_sensitive, False)

        UPDATE_ARGS = [view, combo, entry, preview, save]

        for f in self.__filters:
            f.connect('clicked', self.__preview_tags, *UPDATE_ARGS)
        preview.connect('clicked', self.__preview_tags, *UPDATE_ARGS)
        prop.connect_object(
            'changed', self.__class__.__update, self, *UPDATE_ARGS)

        # Save changes
        save.connect('clicked', self.__save_files, view, entry,
                     addreplace, watcher)

        self.show_all()

    def __add_changed(self, combo):
        config.set("tagsfrompath", "add", str(bool(combo.get_active())))

    def __update(self, songs, view, combo, entry, preview, save):
        from library import AudioFileGroup
        self.__songs = songs

        songinfo = AudioFileGroup(songs)
        if songs: pattern_text = entry.get_text().decode("utf-8")
        else: pattern_text = ""
        try: pattern = TagsFromPattern(pattern_text)
        except sre.error:
            qltk.ErrorMessage(
                self, _("Invalid pattern"),
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
                self, title, msg % ", ".join(invalid)).run()
            pattern = TagsFromPattern("")

        view.set_model(None)
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

        for song in songs:
            basename = song("~basename")
            basename = basename.decode(util.fscoding, "replace")
            row = [song, basename]
            match = pattern.match(song)
            for h in pattern.headers:
                text = match.get(h, '')
                for f in self.__filters:
                    if f.active: text = f.filter(text)
                row.append(text)
            model.append(row=row)

        # save for last to potentially save time
        if songs: view.set_model(model)
        preview.set_sensitive(False)
        save.set_sensitive(len(pattern.headers) > 0)

    def __save_files(self, save, view, entry, addreplace, watcher):
        pattern_text = entry.get_text().decode('utf-8')
        pattern = TagsFromPattern(pattern_text)
        add = bool(addreplace.get_active())
        win = WritingWindow(self, len(self.__songs))

        was_changed = []

        for row in view.get_model():
            song = row[0]
            changed = False
            if not song.valid() and not qltk.ConfirmAction(
                self, _("Tag may not be accurate"),
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
                        self, _("Unable to edit song"),
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

    def __changed(self, activator, preview, save):
        preview.set_sensitive(True)
        save.set_sensitive(False)
