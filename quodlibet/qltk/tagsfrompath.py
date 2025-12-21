# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import os

from gi.repository import Gtk
from senf import fsn2text

import quodlibet

from quodlibet import _, ngettext
from quodlibet import config
from quodlibet import qltk
from quodlibet import util

from quodlibet.formats import AudioFileError
from quodlibet.plugins import PluginManager
from quodlibet.qltk._editutils import FilterPluginBox, FilterCheckButton
from quodlibet.qltk._editutils import EditingPluginHandler, OverwriteWarning
from quodlibet.qltk._editutils import WriteFailedError
from quodlibet.qltk.wlw import WritingWindow
from quodlibet.qltk.views import TreeViewColumn
from quodlibet.qltk.cbes import ComboBoxEntrySave
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk import Icons
from quodlibet.util.tagsfrompath import TagsFromPattern
from quodlibet.util.string.splitters import split_value
from quodlibet.util import connect_obj
from quodlibet.plugins.editing import TagsFromPathPlugin


TBP = os.path.join(quodlibet.get_user_dir(), "lists", "tagpatterns")
TBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
<artist> - <album>/<tracknumber>. <title>
<artist>/<album>/<tracknumber> - <title>"""


class UnderscoresToSpaces(FilterCheckButton):
    _label = _("Replace _underscores with spaces")
    _section = "tagsfrompath"
    _key = "underscores"
    _order = 1.0

    def filter(self, tag, value):
        return value.replace("_", " ")


class TitleCase(FilterCheckButton):
    _label = _("_Title-case tags")
    _section = "tagsfrompath"
    _key = "titlecase"
    _order = 1.1

    def filter(self, tag, value):
        return util.title(value)


class SplitTag(FilterCheckButton):
    _label = _("Split into multiple _values")
    _section = "tagsfrompath"
    _key = "split"
    _order = 1.2

    def filter(self, tag, value):
        spls = config.gettext("editing", "split_on")
        spls = spls.split()
        return "\n".join(split_value(value, spls))


class TagsFromPathPluginHandler(EditingPluginHandler):
    Kind = TagsFromPathPlugin


class ListEntry:
    def __init__(self, song):
        self.song = song
        self.matches = {}

    def get_match(self, key):
        return self.matches.get(key, "")

    def replace_match(self, key, value):
        self.matches[key] = value

    @property
    def name(self):
        return fsn2text(self.song("~basename"))


class TagsFromPath(Gtk.Box):
    title = _("Tags From Path")
    FILTERS = [UnderscoresToSpaces, TitleCase, SplitTag]
    handler = TagsFromPathPluginHandler()

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.handler)

    def __init__(self, parent, library):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self.set_border_width(12)
        hbox = Gtk.Box(spacing=6)
        cbes_defaults = TBP_EXAMPLES.split("\n")
        self.combo = ComboBoxEntrySave(
            TBP,
            cbes_defaults,
            title=_("Path Patterns"),
            edit_title=_("Edit saved patterns…"),
        )
        self.combo.show_all()
        hbox.prepend(self.combo, True, True, 0)
        self.preview = qltk.Button(_("_Preview"), Icons.VIEW_REFRESH)
        self.preview.show()
        hbox.prepend(self.preview, False, True, 0)
        self.prepend(hbox, False, True, 0)
        self.combo.get_child().connect("changed", self._changed)

        model = ObjectStore()
        self.view = Gtk.TreeView(model=model)
        self.view.show()

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.view)
        self.prepend(sw, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        addreplace = Gtk.ComboBoxText()
        addreplace.append_text(_("Tags replace existing ones"))
        addreplace.append_text(_("Tags are added to existing ones"))
        addreplace.set_active(config.getboolean("tagsfrompath", "add"))
        addreplace.connect("changed", self.__add_changed)
        vbox.prepend(addreplace, True, True, 0)
        addreplace.show()
        self.prepend(vbox, False, True, 0)

        filter_box = FilterPluginBox(self.handler, self.FILTERS)
        filter_box.connect("preview", self.__filter_preview)
        filter_box.connect("changed", self.__filter_changed)
        self.filter_box = filter_box
        self.prepend(filter_box, False, True, 0)

        # Save button
        self.save = qltk.Button(_("_Save"), Icons.DOCUMENT_SAVE)
        self.save.show()
        bbox = Gtk.HButtonBox()
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.prepend(self.save, True, True, 0)
        self.prepend(bbox, False, True, 0)

        connect_obj(self.preview, "clicked", self.__preview, None)
        connect_obj(parent, "changed", self.__class__.__preview, self)

        # Save changes
        connect_obj(self.save, "clicked", self.__save, addreplace, library)

        for child in self.get_children():
            child.show()

    def __filter_preview(self, *args):
        Gtk.Button.clicked(self.preview)

    def __filter_changed(self, *args):
        self._changed(self.combo.get_child())

    def _changed(self, entry):
        self.save.set_sensitive(False)
        self.preview.set_sensitive(bool(entry.get_text()))

    def __add_changed(self, combo):
        config.set("tagsfrompath", "add", str(bool(combo.get_active())))

    def __preview(self, songs):
        if songs is None:
            songs = [row[0].song for row in (self.view.get_model() or [])]

        if songs:
            pattern_text = self.combo.get_child().get_text()
        else:
            pattern_text = ""
        try:
            pattern = TagsFromPattern(pattern_text)
        except re.error:
            qltk.ErrorMessage(
                self,
                _("Invalid pattern"),
                _(
                    "The pattern\n\t%s\nis invalid. "
                    "Possibly it contains the same tag twice or "
                    "it has unbalanced brackets (&lt; / &gt;)."
                )
                % (util.bold(pattern_text)),
                escape_desc=False,
            ).run()
            return
        else:
            if pattern_text:
                self.combo.prepend_text(pattern_text)
                self.combo.write(TBP)

        invalid = []

        for header in pattern.headers:
            if not min([song.can_change(header) for song in songs]):
                invalid.append(header)
        total = len(invalid)
        if total and songs:
            title = ngettext("Invalid tag", "Invalid tags", total)
            msg = ngettext(
                "Invalid tag %s\n\nThe files currently "
                "selected do not support editing this tag.",
                "Invalid tags %s\n\nThe files currently "
                "selected do not support editing these tags.",
                total,
            )
            tags_str = util.bold(", ".join(invalid))
            qltk.ErrorMessage(self, title, msg % tags_str, escape_desc=False).run()
            pattern = TagsFromPattern("")

        self.view.set_model(None)
        model = ObjectStore()
        for col in self.view.get_columns():
            self.view.remove_column(col)

        render = Gtk.CellRendererText()
        col = TreeViewColumn(title=_("File"))
        col.prepend(render, True)
        col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        def cell_data_file(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("text", entry.name)

        col.set_cell_data_func(render, cell_data_file)

        def cell_data_header(column, cell, model, iter_, header):
            entry = model.get_value(iter_)
            cell.set_property("text", entry.get_match(header))

        self.view.append_column(col)
        for _i, header in enumerate(pattern.headers):
            render = Gtk.CellRendererText()
            render.set_property("editable", True)
            render.connect("edited", self.__row_edited, model, header)
            escaped_title = header.replace("_", "__")
            col = Gtk.TreeViewColumn(escaped_title, render)
            col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            col.set_cell_data_func(render, cell_data_header, header)
            self.view.append_column(col)

        for song in songs:
            entry = ListEntry(song)
            match = pattern.match(song)
            for h in pattern.headers:
                text = match.get(h, "")
                for f in self.filter_box.filters:
                    if f.active:
                        text = f.filter(h, text)
                if not song.can_multiple_values(h):
                    text = ", ".join(text.split("\n"))
                entry.matches[h] = text
            model.append([entry])

        # save for last to potentially save time
        if songs:
            self.view.set_model(model)
        self.preview.set_sensitive(False)
        self.save.set_sensitive(len(pattern.headers) > 0)

    def __save(self, addreplace, library):
        pattern_text = self.combo.get_child().get_text()
        pattern = TagsFromPattern(pattern_text)
        model = self.view.get_model()
        add = bool(addreplace.get_active())
        win = WritingWindow(self, len(model))
        win.show()

        was_changed = set()

        all_done = False
        for entry in (model and model.values()) or []:
            song = entry.song
            changed = False
            if not song.valid():
                win.hide()
                dialog = OverwriteWarning(self, song)
                resp = dialog.run()
                win.show()
                if resp != OverwriteWarning.RESPONSE_SAVE:
                    break

            for _i, h in enumerate(pattern.headers):
                text = entry.get_match(h)
                if text:
                    can_multiple = song.can_multiple_values(h)
                    if not add or h not in song or not can_multiple:
                        song[h] = text
                        changed = True
                    else:
                        for val in text.split("\n"):
                            if val not in song.list(h):
                                song.add(h, val)
                                changed = True

            if changed:
                try:
                    song.write()
                except AudioFileError:
                    util.print_exc()
                    WriteFailedError(self, song).run()
                    library.reload(song, changed=was_changed)
                    break
                was_changed.add(song)

            if win.step():
                break
        else:
            all_done = True

        win.destroy()
        library.changed(was_changed)
        self.save.set_sensitive(not all_done)

    def __row_edited(self, renderer, path, new, model, header):
        entry = model[path][0]
        if entry.get_match(header) != new:
            entry.replace_match(header, new)
            self.preview.set_sensitive(True)
            self.save.set_sensitive(True)
