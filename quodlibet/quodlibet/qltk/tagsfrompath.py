# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re

import gtk

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.qltk._editpane import EditPane, FilterCheckButton
from quodlibet.qltk._editpane import EditingPluginHandler
from quodlibet.qltk.wlw import WritingWindow

class TagsFromPattern(object):
    def __init__(self, pattern):
        self.compile(pattern)

    def compile(self, pattern):
        self.headers = []
        self.slashes = len(pattern) - len(pattern.replace(os.path.sep,'')) + 1
        self.pattern = None
        # patterns look like <tagname> non regexy stuff <tagname> ...
        pieces = re.split(r'(<[A-Za-z0-9~_]+>)', pattern)
        override = { '<tracknumber>': r'\d\d?', '<discnumber>': r'\d\d??' }
        dummies_found = 0
        for i, piece in enumerate(pieces):
            if not piece:
                continue
            if piece[0]+piece[-1] == '<>':
                piece = piece.lower()   # canonicalize to lowercase tag names
                if "~" in piece:
                    dummies_found += 1
                    piece = "<QUOD_LIBET_DUMMY_%d>" % dummies_found
                pieces[i] = '(?P%s%s)' % (piece, override.get(piece, '.+?'))
                if "QUOD_LIBET" not in piece:
                    self.headers.append(piece[1:-1].encode("ascii", "replace"))
            else:
                pieces[i] = re.escape(piece)

        # some slight magic to anchor searches "nicely"
        # nicely means if it starts with a <tag>, anchor with a /
        # if it ends with a <tag>, anchor with .xxx$
        # but if it's a <tagnumber>, don't bother as \d+ is sufficient
        # and if it's not a tag, trust the user
        if pattern.startswith('<') and not pattern.startswith('<tracknumber>')\
                and not pattern.startswith('<discnumber>'):
            pieces.insert(0, re.escape(os.path.sep))
        if pattern.endswith('>') and not pattern.endswith('<tracknumber>')\
                and not pattern.endswith('<discnumber>'):
            pieces.append(r'(?:\.[A-Za-z0-9_+]+)$')

        self.pattern = re.compile(''.join(pieces))

    def match(self, song):
        if isinstance(song, dict):
            song = util.fsdecode(song['~filename'])
        # only match on the last n pieces of a filename, dictated by pattern
        # this means no pattern may effectively cross a /, despite .* doing so
        sep = os.path.sep
        matchon = sep+sep.join(song.split(sep)[-self.slashes:])
        match = self.pattern.search(matchon)

        # dicts for all!
        if match is None: return {}
        else: return match.groupdict()

class UnderscoresToSpaces(FilterCheckButton):
    _label = _("Replace _underscores with spaces")
    _section = "tagsfrompath"
    _key = "underscores"
    _order = 1.0
    def filter(self, tag, value): return value.replace("_", " ")

class TitleCase(FilterCheckButton):
    _label = _("_Title-case tags")
    _section = "tagsfrompath"
    _key = "titlecase"
    _order = 1.1
    def filter(self, tag, value): return util.title(value)

class SplitTag(FilterCheckButton):
    _label = _("Split into multiple _values")
    _section = "tagsfrompath"
    _key = "split"
    _order = 1.2
    def filter(self, tag, value):
        spls = config.get("editing", "split_on").decode('utf-8', 'replace')
        spls = spls.split()
        return "\n".join(util.split_value(value, spls))


class TagsFromPathPluginHandler(EditingPluginHandler):
    from quodlibet.plugins.editing import TagsFromPathPlugin
    Kind = TagsFromPathPlugin


class TagsFromPath(EditPane):
    title = _("Tags From Path")
    FILTERS = [UnderscoresToSpaces, TitleCase, SplitTag]
    handler = TagsFromPathPluginHandler()

    def __init__(self, parent, library):
        super(TagsFromPath, self).__init__(
            const.TBP, const.TBP_EXAMPLES.split("\n"))

        vbox = self.get_children()[2]
        addreplace = gtk.combo_box_new_text()
        addreplace.append_text(_("Tags replace existing ones"))
        addreplace.append_text(_("Tags are added to existing ones"))
        addreplace.set_active(config.getboolean("tagsfrompath", "add"))
        addreplace.connect('changed', self.__add_changed)
        vbox.pack_start(addreplace)
        addreplace.show()

        self.preview.connect_object('clicked', self.__preview, None)
        parent.connect_object('changed', self.__class__.__preview, self)

        # Save changes
        self.save.connect_object('clicked', self.__save, addreplace, library)

    def __add_changed(self, combo):
        config.set("tagsfrompath", "add", str(bool(combo.get_active())))

    def __preview(self, songs):
        if songs is None:
            songs = [row[0] for row in (self.view.get_model() or [])]

        if songs: pattern_text = self.combo.child.get_text().decode("utf-8")
        else: pattern_text = ""
        try: pattern = TagsFromPattern(pattern_text)
        except re.error:
            qltk.ErrorMessage(
                self, _("Invalid pattern"),
                _("The pattern\n\t<b>%s</b>\nis invalid. "
                  "Possibly it contains the same tag twice or "
                  "it has unbalanced brackets (&lt; / &gt;).")%(
                util.escape(pattern_text))).run()
            return
        else:
            if pattern_text:
                self.combo.prepend_text(pattern_text)
                self.combo.write(const.TBP)

        invalid = []

        for header in pattern.headers:
            if not min([song.can_change(header) for song in songs]):
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

        self.view.set_model(None)
        model = gtk.ListStore(
            object, str, *([str] * len(pattern.headers)))
        for col in self.view.get_columns():
            self.view.remove_column(col)

        col = gtk.TreeViewColumn(_('File'), gtk.CellRendererText(),
                                 text=1)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.view.append_column(col)
        for i, header in enumerate(pattern.headers):
            render = gtk.CellRendererText()
            render.set_property('editable', True)
            render.connect('edited', self.__row_edited, model, i + 2)
            escaped_title = header.replace("_", "__")
            col = gtk.TreeViewColumn(escaped_title, render, text=i + 2)
            col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            self.view.append_column(col)

        for song in songs:
            basename = util.fsdecode(song("~basename"))
            row = [song, basename]
            match = pattern.match(song)
            for h in pattern.headers:
                text = match.get(h, '')
                for f in self.filters:
                    if f.active: text = f.filter(h, text)
                if not song.multiple_values:
                    text = u", ".join(text.split("\n"))
                row.append(text)
            model.append(row=row)

        # save for last to potentially save time
        if songs: self.view.set_model(model)
        self.preview.set_sensitive(False)
        self.save.set_sensitive(len(pattern.headers) > 0)

    def __save(self, addreplace, library):
        pattern_text = self.combo.child.get_text().decode('utf-8')
        pattern = TagsFromPattern(pattern_text)
        model = self.view.get_model()
        add = bool(addreplace.get_active())
        win = WritingWindow(self, len(model))

        was_changed = []

        for row in (model or []):
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
                    text = row[i + 2].decode("utf-8")
                    if not add or h not in song or not song.multiple_values:
                        song[h] = text
                        changed = True
                    else:
                        for val in text.split("\n"):
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
                    library.reload(song, changed=was_changed)
                    break
                was_changed.append(song)

            if win.step(): break

        win.destroy()
        library.changed(was_changed)
        self.save.set_sensitive(False)

    def __row_edited(self, renderer, path, new, model, colnum):
        row = model[path]
        if row[colnum] != new:
            row[colnum] = new
            self.preview.set_sensitive(True)
