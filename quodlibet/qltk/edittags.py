# Copyright 2004-2012 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2011-2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
from collections.abc import Sequence

from gi.repository import Gtk, Pango, Gdk

from quodlibet import C_, _, ngettext, print_e, print_d
from quodlibet import app
from quodlibet import config
from quodlibet import qltk
from quodlibet import util
from quodlibet.formats import AudioFileError
from quodlibet.plugins import PluginManager
from quodlibet.plugins.editing import EditTagsPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk._editutils import EditingPluginHandler, OverwriteWarning
from quodlibet.qltk._editutils import WriteFailedError
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.completion import LibraryValueCompletion
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.tagscombobox import TagsComboBox, TagsComboBoxEntry
from quodlibet.qltk.views import RCMHintedTreeView, TreeViewColumn, BaseView
from quodlibet.qltk.window import Dialog
from quodlibet.qltk.wlw import WritingWindow
from quodlibet.qltk.x import SeparatorMenuItem, Button, MenuItem
from quodlibet.util import connect_obj
from quodlibet.util import massagers
from quodlibet.util.i18n import numeric_phrase
from quodlibet.util.string.splitters import (
    split_value,
    split_title,
    split_people,
    split_album,
)
from quodlibet.util.tags import USER_TAGS, MACHINE_TAGS, sortkey as tagsortkey


class Comment:
    """A summary of a collection of values for one tag"""

    def __init__(self, text, have=1, total=1, shared=True):
        """
        Args:
            text: the first or only text value
            have: amount of songs that have a value
            total: total amount of songs
            shared: if all songs that have a value, have the same one
        """

        self.complete = have == total
        self.shared = shared
        self.total = total
        self.missing = total - have
        self.have = have
        self.text = text

    def _paren(self):
        if self.shared:
            return numeric_phrase(
                "missing from %d song", "missing from %d songs", self.missing
            )
        if self.complete:
            return numeric_phrase(
                "different across %d song", "different across %d songs", self.total
            )
        d = numeric_phrase(
            "different across %d song", "different across %d songs", self.have
        )
        m = numeric_phrase(
            "missing from %d song", "missing from %d songs", self.missing
        )
        return f"{d}, {m}"

    def is_special(self):
        return not self.shared or not self.complete

    def is_missing(self):
        return not self.complete

    def get_shared_text(self):
        if self.shared:
            return util.escape(self.text)
        return ""

    def get_markup(self):
        """Returns pango markup for displaying"""

        if self.shared and self.complete:
            return util.escape(self.text)
        if self.shared:
            return "\n".join(
                [
                    f"{util.escape(s)}{util.italic(' ' + self._paren())}"
                    for s in self.text.split("\n")
                ]
            )
        return util.italic(self._paren())


def get_default_tags():
    """Returns a list of tags that should be displayed even if not present
    in the file.
    """

    text = config.get("editing", "default_tags").strip()
    if not text:
        return []
    return text.split(",")


class AudioFileGroup(dict):
    """Values are a list of Comment instances"""

    def __init__(self, songs, real_keys_only=True):
        keys = {}
        first = {}
        all = {}
        total = len(songs)
        self.songs = songs
        self.is_file = True
        can_multi = True
        can_change = True

        for song in songs:
            self.is_file &= song.is_file

            if real_keys_only:
                iter_func = song.iterrealitems
            else:
                iter_func = song.items

            for comment, val in iter_func():
                keys[comment] = keys.get(comment, 0) + 1
                first.setdefault(comment, val)
                all[comment] = all.get(comment, True) and first[comment] == val

            song_can_multi = song.can_multiple_values()
            if song_can_multi is not True:
                if can_multi is True:
                    can_multi = set(song_can_multi)
                else:
                    can_multi.intersection_update(song_can_multi)

            song_can_change = song.can_change()
            if song_can_change is not True:
                if can_change is True:
                    can_change = set(song_can_change)
                else:
                    can_change.intersection_update(song_can_change)

        self._can_multi = can_multi
        self._can_change = can_change

        # collect comment representations
        for tag, count in keys.items():
            first_value = first[tag]
            if not isinstance(first_value, str):
                first_value = str(first_value)
            shared = all[tag]
            complete = count == total
            if shared and complete:
                values = first_value.split("\n")
            else:
                values = [first_value]
            for v in values:
                self.setdefault(tag, []).append(Comment(v, count, total, shared))

    def can_multiple_values(self, key=None):
        """If no arguments passed returns a set of tags that have multi
        value support for all contained songs. If key is given returns
        if all songs support multi value tags for that key.
        """

        if key is None:
            return self._can_multi
        return all(song.can_multiple_values(key) for song in self.songs)

    def can_change(self, key=None):
        """See can_multiple_values()"""

        if key is None:
            return self._can_change
        return all(song.can_change(key) for song in self.songs)


class TagSplitter(EditTagsPlugin):
    """Splits tag values into other tags"""


class SplitValues(TagSplitter):
    def __init__(self, tag, value):
        super().__init__(label=_("Split into _Multiple Values"), use_underline=True)
        self.set_image(
            Gtk.Image.new_from_icon_name(Icons.EDIT_FIND_REPLACE, Gtk.IconSize.MENU)
        )
        spls = config.gettext("editing", "split_on").split()
        vals = [
            val if len(val) <= 64 else val[:64] + "…"
            for val in split_value(value, spls)
        ]
        string = ", ".join([f"{tag}={val}" for val in vals])
        self.set_label(string)
        self.set_sensitive(len(vals) > 1)

    def activated(self, tag, value):
        spls = config.gettext("editing", "split_on").split()
        return [(tag, v) for v in split_value(value, spls)]


class SplitDisc(TagSplitter):
    tags = ["album"]
    needs = ["discnumber"]
    _order = 0.5

    def __init__(self, tag, value):
        super().__init__(label=_("Split Disc out of _Album"), use_underline=True)
        self.set_image(
            Gtk.Image.new_from_icon_name(Icons.EDIT_FIND_REPLACE, Gtk.IconSize.MENU)
        )

        album, disc = split_album(value)
        if disc is not None:
            album = album if len(album) <= 64 else album[:64] + "…"
            self.set_label(f"{tag}={album}, {self.needs[0]}={disc}")

        self.set_sensitive(disc is not None)

    def activated(self, tag, value):
        album, disc = split_album(value)
        return [(tag, album), ("discnumber", disc)]


class SplitTitle(TagSplitter):
    tags = ["title"]
    needs = ["version"]
    _order = 0.5

    def __init__(self, tag, value):
        super().__init__(label=_("Split _Version out of Title"), use_underline=True)
        self.set_image(
            Gtk.Image.new_from_icon_name(Icons.EDIT_FIND_REPLACE, Gtk.IconSize.MENU)
        )
        tag_spls = config.gettext("editing", "split_on").split()
        sub_spls = config.gettext("editing", "sub_split_on").split()

        title, versions = split_title(value, tag_spls, sub_spls)
        if versions:
            title = title if len(title) <= 64 else title[:64] + "…"
            versions = [ver if len(ver) <= 64 else ver[:64] + "…" for ver in versions]
            string = ", ".join(
                [f"{tag}={title}"] + [f"{self.needs[0]}={ver}" for ver in versions]
            )
            self.set_label(string)

        self.set_sensitive(bool(versions))

    def activated(self, tag, value):
        tag_spls = config.gettext("editing", "split_on").split()
        sub_spls = config.gettext("editing", "sub_split_on").split()
        title, versions = split_title(value, tag_spls, sub_spls)
        return [(tag, title)] + [("version", v) for v in versions]


class SplitPerson(TagSplitter):
    tags = ["artist"]
    _order = 0.5

    def __init__(self, tag, value):
        super().__init__(label=self.title, use_underline=True)
        self.set_image(
            Gtk.Image.new_from_icon_name(Icons.EDIT_FIND_REPLACE, Gtk.IconSize.MENU)
        )
        tag_spls = config.gettext("editing", "split_on").split()
        sub_spls = config.gettext("editing", "sub_split_on").split()

        artist, others = split_people(value, tag_spls, sub_spls)
        if others:
            artist = artist if len(artist) <= 64 else artist[:64] + "…"
            others = [
                other if len(other) <= 64 else other[:64] + "…" for other in others
            ]
            string = ", ".join(
                [f"{tag}={artist}"] + [f"{self.needs[0]}={o}" for o in others]
            )
            self.set_label(string)

        self.set_sensitive(bool(others))

    def activated(self, tag, value):
        tag_spls = config.gettext("editing", "split_on").split()
        sub_spls = config.gettext("editing", "sub_split_on").split()
        artist, others = split_people(value, tag_spls, sub_spls)
        return [(tag, artist)] + [(self.needs[0], o) for o in others]


class SplitArranger(SplitPerson):
    needs = ["arranger"]
    title = _("Split Arranger out of Ar_tist")


class SplitPerformer(SplitPerson):
    needs = ["performer"]
    title = _("Split _Performer out of Artist")


class SplitPerformerFromTitle(SplitPerson):
    tags = ["title"]
    needs = ["performer"]
    title = _("Split _Performer out of Title")


class SplitOriginalArtistFromTitle(SplitPerson):
    tags = ["title"]
    needs = ["originalartist"]
    title = _("Split _Originalartist out of Title")


class AddTagDialog(Dialog):
    def __init__(self, parent, can_change, library):
        super().__init__(
            title=_("Add a Tag"),
            transient_for=qltk.get_top_parent(parent),
            use_header_bar=True,
        )
        self.set_border_width(6)
        self.set_resizable(False)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        add = self.add_icon_button(_("_Add"), Icons.LIST_ADD, Gtk.ResponseType.OK)
        self.vbox.set_spacing(6)
        self.set_default_response(Gtk.ResponseType.OK)
        table = Gtk.Table(n_rows=2, n_columns=2)
        table.set_row_spacings(12)
        table.set_col_spacings(6)
        table.set_border_width(6)

        self.__tag = (
            TagsComboBoxEntry() if can_change is True else TagsComboBox(can_change)
        )

        label = Gtk.Label()
        label.set_alignment(0.0, 0.5)
        label.set_text(_("_Tag:"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.__tag)
        table.attach(label, 0, 1, 0, 1)
        table.attach(self.__tag, 1, 2, 0, 1)

        self.__val = Gtk.Entry()
        self.__val.set_completion(LibraryValueCompletion("", library))
        label = Gtk.Label()
        label.set_text(_("_Value:"))
        label.set_alignment(0.0, 0.5)
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.__val)
        valuebox = Gtk.EventBox()
        table.attach(label, 0, 1, 1, 2)
        table.attach(valuebox, 1, 2, 1, 2)
        hbox = Gtk.HBox()
        valuebox.add(hbox)
        hbox.pack_start(self.__val, True, True, 0)
        hbox.set_spacing(6)
        invalid = Gtk.Image.new_from_icon_name(
            Icons.DIALOG_WARNING, Gtk.IconSize.SMALL_TOOLBAR
        )
        hbox.pack_start(invalid, True, True, 0)

        self.vbox.pack_start(table, True, True, 0)
        self.get_child().show_all()
        invalid.hide()

        for entry in [self.__tag, self.__val]:
            entry.connect("changed", self.__validate, add, invalid, valuebox)
        self.__tag.connect("changed", self.__set_value_completion, library)
        self.__set_value_completion(self.__tag, library)

        if can_change is True:
            connect_obj(
                self.__tag.get_child(), "activate", Gtk.Entry.grab_focus, self.__val
            )

    def __set_value_completion(self, tag, library):
        completion = self.__val.get_completion()
        if completion:
            completion.set_tag(self.__tag.tag, library)

    def get_tag(self):
        try:
            return self.__tag.tag
        except AttributeError:
            return self.__tag.tag

    def get_value(self):
        return self.__val.get_text()

    def __validate(self, editable, add, invalid, box):
        tag = self.get_tag()
        value = self.get_value()
        valid = massagers.is_valid(tag, value)
        add.set_sensitive(valid)
        if valid:
            invalid.hide()
            box.set_tooltip_text("")
        else:
            invalid.show()
            box.set_tooltip_text(massagers.error_message(tag, value))

    def run(self):
        self.show()
        self.__val.set_activates_default(True)
        self.__tag.grab_focus()
        return super().run()


class EditTagsPluginHandler(EditingPluginHandler):
    from quodlibet.plugins.editing import EditTagsPlugin

    Kind = EditTagsPlugin


class ListEntry:
    """Holds a Comment and some state for the editing process"""

    tag = None
    value = None
    edited = False
    canedit = True
    deleted = False
    origvalue = None
    renamed = False
    origtag = None

    def __init__(self, tag, value):
        self.tag = tag
        self.value = value


class EditTags(Gtk.VBox):
    handler = EditTagsPluginHandler()

    _SPLITTERS: Sequence[type[TagSplitter]] = sorted(
        [
            SplitDisc,
            SplitTitle,
            SplitPerformer,
            SplitArranger,
            SplitValues,
            SplitPerformerFromTitle,
            SplitOriginalArtistFromTitle,
        ],
        key=lambda item: (item._order, item.__name__),
    )

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.handler)

    def __init__(self, parent, library):
        super().__init__(spacing=12)
        self.title = _("Edit Tags")
        self.set_border_width(12)
        self._group_info = None

        model = ObjectStore()
        view = RCMHintedTreeView(model=model)
        self._view = view
        selection = view.get_selection()
        render = Gtk.CellRendererPixbuf()
        column = TreeViewColumn()
        column.pack_start(render, True)
        column.set_fixed_width(24)
        column.set_expand(False)

        def cdf_write(col, rend, model, iter_, *args):
            entry = model.get_value(iter_)
            rend.set_property("sensitive", entry.edited or entry.deleted)
            if entry.canedit or entry.deleted:
                if entry.deleted:
                    rend.set_property("icon-name", Icons.EDIT_DELETE)
                else:
                    rend.set_property("icon-name", Icons.EDIT)
            else:
                rend.set_property("icon-name", Icons.CHANGES_PREVENT)

        column.set_cell_data_func(render, cdf_write)
        view.append_column(column)

        render = Gtk.CellRendererText()
        column = TreeViewColumn(title=_("Tag"))
        column.pack_start(render, True)

        def cell_data_tag(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("text", entry.tag)
            cell.set_property("strikethrough", entry.deleted)

        column.set_cell_data_func(render, cell_data_tag)

        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        render.set_property("editable", True)
        render.connect("edited", self.__edit_tag_name, model)
        render.connect("editing-started", self.__tag_editing_started, model, library)
        view.append_column(column)

        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)
        render.set_property("editable", True)
        render.connect("edited", self.__edit_tag, model)
        render.connect("editing-started", self.__value_editing_started, model, library)
        column = TreeViewColumn(title=_("Value"))
        column.pack_start(render, True)

        def cell_data_value(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            markup = entry.value.get_markup()
            cell.markup = markup
            cell.set_property("markup", markup)
            cell.set_property("editable", entry.canedit)
            cell.set_property("strikethrough", entry.deleted)

        column.set_cell_data_func(render, cell_data_value)

        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        view.append_column(column)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(view)
        self.pack_start(sw, True, True, 0)

        cb = ConfigCheckButton(
            _("Show _programmatic tags"),
            "editing",
            "alltags",
            populate=True,
            tooltip=_(
                "Access all tags, including machine-generated "
                "ones e.g. MusicBrainz or Replay Gain tags"
            ),
        )
        cb.connect("toggled", self.__checkbox_toggled)
        hb = Gtk.HBox()
        hb.pack_start(cb, False, True, 0)

        cb = ConfigCheckButton(
            _("Show _multi-line tags"),
            "editing",
            "show_multi_line_tags",
            populate=True,
            tooltip=_("Show potentially multi-line tags (e.g 'lyrics') here too"),
        )
        cb.connect("toggled", self.__checkbox_toggled)
        hb.pack_start(cb, False, True, 12)
        self.pack_start(hb, False, True, 0)

        # Add and Remove [tags] buttons
        buttonbox = Gtk.HBox(spacing=18)
        bbox1 = Gtk.HButtonBox()
        bbox1.set_spacing(9)
        bbox1.set_layout(Gtk.ButtonBoxStyle.START)
        add = qltk.Button(_("_Add…"), Icons.LIST_ADD)
        add.set_focus_on_click(False)
        self._add = add
        add.connect("clicked", self.__add_tag, model, library)
        bbox1.pack_start(add, True, True, 0)
        # Remove button
        remove = qltk.Button(_("_Remove"), Icons.LIST_REMOVE)
        remove.set_focus_on_click(False)
        remove.connect("clicked", self.__remove_tag, view)
        remove.set_sensitive(False)
        self._remove = remove

        bbox1.pack_start(remove, True, True, 0)

        # Revert and save buttons
        # Both can have customised translated text (and thus accels)
        bbox2 = Gtk.HButtonBox()
        bbox2.set_spacing(9)
        bbox2.set_layout(Gtk.ButtonBoxStyle.END)
        # Translators: Revert button in the tag editor
        revert = Button(C_("edittags", "_Revert"), Icons.DOCUMENT_REVERT)

        self._revert = revert
        revert.set_sensitive(False)
        # Translators: Save button in the tag editor
        save = Button(C_("edittags", "_Save"), Icons.DOCUMENT_SAVE)
        save.set_sensitive(False)
        self._save = save
        bbox2.pack_start(revert, True, True, 0)
        bbox2.pack_start(save, True, True, 0)

        buttonbox.pack_start(bbox1, True, True, 0)
        buttonbox.pack_start(bbox2, True, True, 0)
        self.pack_start(buttonbox, False, True, 0)
        self._buttonbox = buttonbox

        parent.connect("changed", self.__parent_changed)
        revert.connect("clicked", lambda *x: self._update())
        connect_obj(revert, "clicked", parent.set_pending, None)

        save.connect("clicked", self.__save_files, revert, model, library)
        connect_obj(save, "clicked", parent.set_pending, None)
        for sig in ["row-inserted", "row-deleted", "row-changed"]:
            model.connect(sig, self.__enable_save, [save, revert])
            connect_obj(model, sig, parent.set_pending, save)

        view.connect("popup-menu", self._popup_menu, parent)
        view.connect("button-press-event", self.__button_press)
        view.connect("key-press-event", self.__view_key_press_event)
        selection.connect("changed", self.__tag_select, remove)
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        self._parent = parent

        for child in self.get_children():
            child.show_all()

    def __checkbox_toggled(self, *args):
        self._update()

    def __view_key_press_event(self, view, event):
        if qltk.is_accel(event, "Delete"):
            self.__remove_tag(view, view)
            return Gdk.EVENT_STOP
        if qltk.is_accel(event, "<Primary>s"):
            # Issue 697: allow Ctrl-s to save.
            self._save.emit("clicked")
            return Gdk.EVENT_STOP
        if qltk.is_accel(event, "<Primary>c"):
            self.__copy_tag_value(event, view)
            return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    def __enable_save(self, *args):
        buttons = args[-1]
        for b in buttons:
            b.set_sensitive(True)

    def __paste(self, clip, text, args):
        rend, path = args
        if text:
            rend.emit("edited", path, text.strip())

    def __menu_activate(self, activator, view):
        model, (path,) = view.get_selection().get_selected_rows()
        entry = model[path][0]

        tag = entry.tag
        comment = entry.value
        value = comment.text
        vals = activator.activated(tag, value)
        replaced = False
        if vals and (len(vals) != 1 or vals[0][1] != value):
            for atag, aval in vals:
                if atag == tag and not replaced:
                    replaced = True
                    entry.value = Comment(aval)
                    entry.edited = True
                    model.path_changed(path)
                else:
                    self.__add_new_tag(model, atag, aval)
        elif vals:
            replaced = True

        if not replaced:
            entry.edited = entry.deleted = True
            model.path_changed(path)

    def __item_for(
        self, view: BaseView, item_cls: type[EditTagsPlugin], tag: str, text: str
    ) -> EditTagsPlugin | None:
        try:
            item = item_cls(tag, text)
        except Exception as e:
            print_e(f"Couldn't create menu item from {item_cls} ({e})")
            return None
        else:
            item.connect("activate", self.__menu_activate, view)
            return item

    def _popup_menu(self, view: BaseView, _parent):
        menu = Gtk.Menu()

        view.ensure_popup_selection()
        model, rows = view.get_selection().get_selected_rows()
        can_change = all(model[path][0].canedit for path in rows)

        if len(rows) == 1:
            row = model[rows[0]]
            entry = row[0]

            comment = entry.value
            text = comment.text

            split_menu = Gtk.Menu()

            for Item in self._SPLITTERS:
                if Item.tags and entry.tag not in Item.tags:
                    continue
                item = self.__item_for(view, Item, entry.tag, text)
                if not item:
                    continue
                vals = item.activated(entry.tag, text)
                changeable = any(not self._group_info.can_change(k) for k in item.needs)
                fixed = changeable or comment.is_special()
                if fixed:
                    item.set_sensitive(False)
                if len(vals) > 1 and vals[1][1]:
                    split_menu.append(item)
            if split_menu.get_children():
                split_menu.append(SeparatorMenuItem())

            plugins = self.handler.plugins
            print_d(
                f"Adding {len(plugins)} plugin(s) to menu: "
                f"{', '.join(p.__name__ for p in plugins)}"
            )
            for p_cls in plugins:
                item = self.__item_for(view, p_cls, entry.tag, text)
                if not item:
                    continue
                results = item.activated(entry.tag, text)
                # Only enable for the user if the plugin would do something
                item.set_sensitive(results != [(entry.tag, text)])
                menu.append(item)
            pref_item = MenuItem(_("_Configure"), Icons.PREFERENCES_SYSTEM)
            split_menu.append(pref_item)

            def show_prefs(parent):
                from quodlibet.qltk.exfalsowindow import ExFalsoWindow

                if isinstance(app.window, ExFalsoWindow):
                    from quodlibet.qltk.exfalsowindow import PreferencesWindow

                    window = PreferencesWindow(parent)
                else:
                    from quodlibet.qltk.prefs import PreferencesWindow

                    window = PreferencesWindow(parent, open_page="tagging")
                window.show()

            connect_obj(pref_item, "activate", show_prefs, self)

            split_item = MenuItem(_("_Split Tag"), Icons.EDIT_FIND_REPLACE)

            if split_menu.get_children():
                split_item.set_submenu(split_menu)
            else:
                split_item.set_sensitive(False)

            menu.append(split_item)

        copy_b = MenuItem(_("_Copy Value(s)"), Icons.EDIT_COPY)
        copy_b.connect("activate", self.__copy_tag_value, view)
        qltk.add_fake_accel(copy_b, "<Primary>c")
        menu.append(copy_b)

        remove_b = MenuItem(_("_Remove"), Icons.LIST_REMOVE)
        remove_b.connect("activate", self.__remove_tag, view)
        qltk.add_fake_accel(remove_b, "Delete")
        menu.append(remove_b)

        menu.show_all()
        # Setting the menu itself to be insensitive causes it to not
        # be dismissed; see #473.
        for c in menu.get_children():
            c.set_sensitive(can_change and c.get_property("sensitive"))
        copy_b.set_sensitive(True)
        remove_b.set_sensitive(True)
        menu.connect("selection-done", lambda m: m.destroy())

        # XXX: Keep reference
        self.__menu = menu
        return view.popup_menu(menu, 3, Gtk.get_current_event_time())

    def __tag_select(self, selection, remove):
        model, rows = selection.get_selected_rows()
        remove.set_sensitive(bool(rows))

    def __add_new_tag(self, model, tag, value):
        assert isinstance(value, str)
        iters = [i for (i, v) in model.iterrows() if v.tag == tag]
        if iters and not self._group_info.can_multiple_values(tag):
            title = _("Unable to add tag")
            msg = _("Unable to add %s") % util.bold(tag)
            msg += "\n\n"
            msg += _(
                "The files currently selected do not support multiple values for %s."
            ) % util.bold(tag)
            qltk.ErrorMessage(self, title, msg, escape_desc=False).run()
            return

        entry = ListEntry(tag, Comment(value))
        entry.edited = True

        if len(iters):
            model.insert_after(iters[-1], row=[entry])
        else:
            model.append(row=[entry])

    def __add_tag(self, activator, model, library):
        add = AddTagDialog(self, self._group_info.can_change(), library)

        while True:
            resp = add.run()
            if resp != Gtk.ResponseType.OK:
                break
            tag = add.get_tag()
            value = add.get_value()
            assert isinstance(value, str)
            value = massagers.validate(tag, value)
            assert isinstance(value, str)
            if not self._group_info.can_change(tag):
                title = ngettext("Invalid tag", "Invalid tags", 1)
                msg = ngettext(
                    "Invalid tag %s\n\nThe files currently "
                    "selected do not support editing this tag.",
                    "Invalid tags %s\n\nThe files currently "
                    "selected do not support editing these tags.",
                    1,
                ) % util.bold(tag)
                qltk.ErrorMessage(self, title, msg).run()
            else:
                self.__add_new_tag(model, tag, value)
                break

        add.destroy()

    def __remove_tag(self, activator, view):
        model, paths = view.get_selection().get_selected_rows()
        # Since the iteration can modify path numbers, we need accurate
        # rows (= iters) before we start.
        rows = [model[path] for path in paths]
        for row in rows:
            entry = row[0]
            if entry.origvalue is not None:
                entry.edited = entry.deleted = True
                model.row_changed(row.path, row.iter)
            else:
                model.remove(row.iter)

    def __copy_tag_value(self, activator, view):
        model, paths = view.get_selection().get_selected_rows()
        rows = [model[path] for path in paths]
        values = []
        for row in rows:
            entry_text = row[0].value.get_shared_text()
            if entry_text:
                values.append(entry_text)
        text = "\n".join(values)
        if len(text) > 0:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text, -1)

    def __save_files(self, save, revert, model, library):
        updated = {}
        deleted = {}
        added = {}
        renamed = {}

        for entry in model.values():
            if entry.edited and not (entry.deleted or entry.renamed):
                if entry.origvalue is not None:
                    l = updated.setdefault(entry.tag, [])
                    l.append((entry.value, entry.origvalue))
                else:
                    l = added.setdefault(entry.tag, [])
                    l.append(entry.value)

            if entry.edited and entry.deleted:
                if entry.origvalue is not None:
                    l = deleted.setdefault(entry.tag, [])
                    l.append(entry.origvalue)

            if entry.edited and entry.renamed and not entry.deleted:
                l = renamed.setdefault(entry.tag, [])
                l.append((entry.origtag, entry.value, entry.origvalue))

        was_changed = set()
        songs = self._group_info.songs
        win = WritingWindow(self, len(songs))
        win.show()
        all_done = False
        for song in songs:
            if not song.valid():
                win.hide()
                dialog = OverwriteWarning(self, song)
                resp = dialog.run()
                win.show()
                if resp != OverwriteWarning.RESPONSE_SAVE:
                    break

            changed = False
            for key, values in updated.items():
                for new_value, old_value in values:
                    if song.can_change(key):
                        if old_value is None:
                            song.add(key, new_value.text)
                        else:
                            song.change(key, old_value.text, new_value.text)
                        changed = True

            for key, values in added.items():
                for value in values:
                    if song.can_change(key):
                        song.add(key, value.text)
                        changed = True

            for key, values in deleted.items():
                for value in values:
                    if not value.shared:
                        # In case it isn't shared we don't know the actual
                        # values to remove. But we know that in that case
                        # we merge all values into one Comment so just removing
                        # everything for that key is OK.
                        song.remove(key, None)
                        changed = True
                    elif key in song:
                        song.remove(key, value.text)
                        changed = True

            save_rename = []
            for new_tag, values in renamed.items():
                for old_tag, new_value, old_value in values:
                    if song.can_change(new_tag) and old_tag in song:
                        if not new_value.is_special():
                            song.remove(old_tag, old_value.text)
                            save_rename.append((new_tag, new_value))
                        elif new_value.is_missing():
                            song.remove(old_tag, old_value)
                            save_rename.append((new_tag, new_value))
                        else:
                            save_rename.append((new_tag, Comment(song[old_tag])))
                            song.remove(old_tag, None)
                        changed = True

            for tag, value in save_rename:
                song.add(tag, value.text)

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
        for b in [save, revert]:
            b.set_sensitive(not all_done)

    def __edit_tag(self, renderer, path, new_value, model):
        path = Gtk.TreePath.new_from_string(path)
        entry = model[path][0]
        error_dialog = None

        if not massagers.is_valid(entry.tag, new_value):
            error_dialog = qltk.WarningMessage(
                self,
                _("Invalid value"),
                _("Invalid value: %(value)s\n\n%(error)s")
                % {
                    "value": util.bold(new_value),
                    "error": massagers.error_message(entry.tag, new_value),
                },
            )
        else:
            new_value = massagers.validate(entry.tag, new_value)

        comment = entry.value
        changed = comment.text != new_value
        identical = comment.shared and comment.complete
        if (changed and (identical or new_value)) or (new_value and not identical):
            # only give an error if we would have applied the value
            if error_dialog is not None:
                error_dialog.run()
                return
            entry.value = Comment(new_value)
            entry.edited = True
            entry.deleted = False
            model.path_changed(path)

    def __edit_tag_name(self, renderer, path, new_tag, model):
        new_tag = " ".join(new_tag.splitlines()).lower()
        path = Gtk.TreePath.new_from_string(path)
        entry = model[path][0]
        if new_tag == entry.tag:
            return
        if not self._group_info.can_change(new_tag):
            # Can't add the new tag.
            title = ngettext("Invalid tag", "Invalid tags", 1)
            msg = ngettext(
                "Invalid tag %s\n\nThe files currently "
                "selected do not support editing this tag.",
                "Invalid tags %s\n\nThe files currently "
                "selected do not support editing these tags.",
                1,
            ) % util.bold(new_tag)
            qltk.ErrorMessage(self, title, msg, escape_desc=False).run()
        else:
            # FIXME: In case this is a special one we only
            # validate one value and never write it back..

            text = entry.value.text
            if not massagers.is_valid(new_tag, text):
                qltk.WarningMessage(
                    self,
                    _("Invalid value"),
                    _("Invalid value: %(value)s\n\n%(error)s")
                    % {
                        "value": util.bold(text),
                        "error": massagers.error_message(new_tag, text),
                    },
                ).run()
                return
            text = massagers.validate(new_tag, text)

            if entry.origvalue is None:
                # The tag hasn't been saved yet, so we can just update
                # the name in the model, and the value, since it
                # may have been re-validated.
                entry.tag = new_tag
                entry.value = Comment(text)
            else:
                # The tag has been saved, so delete the old tag and
                # add a new one with the old (or sanitized) value.
                entry.renamed = entry.edited = True
                entry.origtag = entry.tag
                entry.tag = new_tag
                if not entry.value.is_special():
                    entry.value = Comment(text)

            entry.canedit = True

            model.row_changed(path, model.get_iter(path))

    def __button_press(self, view, event):
        if event.button not in [Gdk.BUTTON_PRIMARY, Gdk.BUTTON_MIDDLE]:
            return Gdk.EVENT_PROPAGATE

        x, y = map(int, [event.x, event.y])
        try:
            path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError:
            return Gdk.EVENT_PROPAGATE

        if event.button == Gdk.BUTTON_MIDDLE and col == view.get_columns()[2]:
            display = Gdk.DisplayManager.get().get_default_display()
            selection = Gdk.SELECTION_PRIMARY
            if sys.platform == "win32":
                selection = Gdk.SELECTION_CLIPBOARD

            clipboard = Gtk.Clipboard.get_for_display(display, selection)
            for rend in col.get_cells():
                if rend.get_property("editable"):
                    clipboard.request_text(self.__paste, (rend, path.get_indices()[0]))
                    return Gdk.EVENT_STOP
            else:
                return Gdk.EVENT_PROPAGATE
        else:
            return Gdk.EVENT_PROPAGATE

    def _update(self, songs=None):
        if songs is None:
            songs = self._group_info.songs
        else:
            self._group_info = AudioFileGroup(songs)
        info = self._group_info

        keys = list(info.keys())
        default_tags = get_default_tags()
        keys = set(keys + default_tags)

        def custom_sort(key):
            try:
                prio = default_tags.index(key)
            except ValueError:
                prio = len(default_tags)
            return (prio, tagsortkey(key))

        if not config.getboolean("editing", "alltags"):
            keys = filter(lambda k: k not in MACHINE_TAGS, keys)

        if not config.getboolean("editing", "show_multi_line_tags"):
            tags = config.getstringlist("editing", "multi_line_tags")
            keys = filter(lambda k: k not in tags, keys)

        if not songs:
            keys = []

        with self._view.without_model() as model:
            model.clear()

            for tag in sorted(keys, key=custom_sort):
                canedit = info.can_change(tag)

                # default tags
                if tag not in info:
                    entry = ListEntry(tag, Comment(""))
                    entry.canedit = canedit
                    model.append(row=[entry])
                    continue

                for value in info[tag]:
                    entry = ListEntry(tag, value)
                    entry.origvalue = value
                    entry.edited = False
                    entry.canedit = canedit
                    entry.deleted = False
                    entry.renamed = False
                    entry.origtag = ""
                    model.append(row=[entry])

        self._buttonbox.set_sensitive(bool(info.can_change()))
        self._revert.set_sensitive(False)
        self._remove.set_sensitive(False)
        self._save.set_sensitive(False)
        self._add.set_sensitive(bool(songs))
        self._parent.set_pending(None)

    def __parent_changed(self, parent, songs):
        self._update(songs)

    def __value_editing_started(self, render, editable, path, model, library):
        if not editable.get_completion():
            tag = model[path][0].tag
            completion = LibraryValueCompletion(tag, library)
            editable.set_completion(completion)

        if isinstance(editable, Gtk.Entry):
            comment = model[path][0].value
            if comment.shared:
                editable.set_text(comment.text)
            else:
                editable.set_text("")

    def __tag_editing_started(self, render, editable, path, model, library):
        if not editable.get_completion():
            tags = self._group_info.can_change()
            if tags is True:
                tags = USER_TAGS
            completion = qltk.EntryCompletion(tags)
            editable.set_completion(completion)
