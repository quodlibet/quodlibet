# -*- coding: utf-8 -*-
# Copyright 2004-2012 Joe Wreschnig, Michael Urman, Iñigo Serna, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

import gtk
import pango

from quodlibet import qltk

from quodlibet import config
from quodlibet import formats
from quodlibet import util

from quodlibet.util import massagers

from quodlibet.qltk.completion import LibraryValueCompletion
from quodlibet.qltk.tagscombobox import TagsComboBox, TagsComboBoxEntry
from quodlibet.qltk.views import RCMHintedTreeView, TreeViewColumn
from quodlibet.qltk.wlw import WritingWindow
from quodlibet.qltk._editpane import EditingPluginHandler
from quodlibet.plugins import PluginManager

class AudioFileGroup(dict):

    class Comment(unicode):
        complete = True
        def __repr__(self):
            return '%s %s' % (str(self), self.paren())

        def __str__(self):
            return util.escape(self)

        def paren(self):
            if self.shared:
                return ngettext('missing from %d song',
                                'missing from %d songs',
                                self.missing) % self.missing
            elif self.complete:
                return ngettext('different across %d song',
                                'different across %d songs',
                                self.total) % self.total
            else:
                d = ngettext('different across %d song',
                              'different across %d songs',
                              self.have) % self.have
                m = ngettext('missing from %d song',
                              'missing from %d songs',
                              self.missing) % self.missing
                return ", ".join([d, m])

        def safenicestr(self):
            if self.shared and self.complete: return str(self)
            elif self.shared:
                return "\n".join(['%s<i> (%s)</i>' % (s, self.paren())
                                  for s in str(self).split("\n")])
            else: return '<i>(%s)</i>' % self.paren()

    class SharedComment(Comment): shared = True
    class UnsharedComment(Comment): shared = False
    class PartialSharedComment(SharedComment): complete = False
    class PartialUnsharedComment(UnsharedComment): complete = False

    def realkeys(self):
        return filter(lambda s: s and "~" not in s and "=" not in s, self)

    is_file = True
    multiple_values = True

    def __init__(self, songs):
        keys = {}
        first = {}
        all = {}
        total = len(songs)
        self.songs = songs

        for song in songs:
            self.is_file &= song.is_file
            self.multiple_values &= song.multiple_values
            for comment, val in song.iteritems():
                keys[comment] = keys.get(comment, 0) + 1
                first.setdefault(comment, val)
                all[comment] = all.get(comment, True) and first[comment] == val

        # collect comment representations
        for comment, count in keys.iteritems():
            if count < total:
                if all[comment]:
                    value = self.PartialSharedComment(first[comment])
                else:
                    value = self.PartialUnsharedComment(first[comment])
            else:
                decoded = first[comment]
                if isinstance(decoded, str): decoded = util.decode(decoded)
                if all[comment]: value = self.SharedComment(decoded)
                else: value = self.UnsharedComment(decoded)
            value.have = count
            value.total = total
            value.missing = total - count

            self[comment] = value

    def can_change(self, k=None):
        if k is None:
            can = True
            for song in self.songs:
                cantoo = song.can_change()
                if can is True: can = cantoo
                elif cantoo is True: pass
                else: can = set(can) | set(cantoo)
        else:
            if not self.songs: return False
            can = min([song.can_change(k) for song in self.songs])
        return can

class SplitValues(gtk.ImageMenuItem):
    tags = False
    needs = []
    _order = 0.0

    def __init__(self, tag, value):
        super(SplitValues, self).__init__(_("Split into _Multiple Values"))
        self.set_image(gtk.image_new_from_stock(
            gtk.STOCK_FIND_AND_REPLACE, gtk.ICON_SIZE_MENU))
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        self.set_sensitive(len(util.split_value(value, spls)) > 1)

    def activated(self, tag, value):
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        return [(tag, value) for value in util.split_value(value, spls)]

class SplitDisc(gtk.ImageMenuItem):
    tags = ["album"]
    needs = ["discnumber"]
    _order = 0.5

    def __init__(self, tag, value):
        super(SplitDisc, self).__init__(_("Split Disc out of _Album"))
        self.set_image(gtk.image_new_from_stock(
            gtk.STOCK_FIND_AND_REPLACE, gtk.ICON_SIZE_MENU))
        self.set_sensitive(util.split_album(value)[1] is not None)

    def activated(self, tag, value):
        album, disc = util.split_album(value)
        return [(tag, album), ("discnumber", disc)]

class SplitTitle(gtk.ImageMenuItem):
    tags = ["title"]
    needs = ["version"]
    _order = 0.5

    def __init__(self, tag, value):
        super(SplitTitle, self).__init__(_("Split _Version out of Title"))
        self.set_image(gtk.image_new_from_stock(
            gtk.STOCK_FIND_AND_REPLACE, gtk.ICON_SIZE_MENU))
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        self.set_sensitive(bool(util.split_title(value, spls)[1]))

    def activated(self, tag, value):
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        title, versions = util.split_title(value, spls)
        return [(tag, title)] + [("version", v) for v in versions]

class SplitPerson(gtk.ImageMenuItem):
    tags = ["artist"]
    _order = 0.5

    def __init__(self, tag, value):
        super(SplitPerson, self).__init__(self.title)
        self.set_image(gtk.image_new_from_stock(
            gtk.STOCK_FIND_AND_REPLACE, gtk.ICON_SIZE_MENU))
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        self.set_sensitive(bool(util.split_people(value, spls)[1]))

    def activated(self, tag, value):
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        artist, others = util.split_people(value, spls)
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


class AddTagDialog(gtk.Dialog):

    def __init__(self, parent, can_change, library):
        super(AddTagDialog, self).__init__(
            _("Add a Tag"), qltk.get_top_parent(parent))
        self.set_border_width(6)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        add = self.add_button(gtk.STOCK_ADD, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)
        table = gtk.Table(2, 2)
        table.set_row_spacings(12)
        table.set_col_spacings(6)
        table.set_border_width(6)

        self.__tag = (TagsComboBoxEntry() if can_change == True
                      else TagsComboBox(can_change))

        label = gtk.Label()
        label.set_alignment(0.0, 0.5)
        label.set_text(_("_Tag:"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.__tag)
        table.attach(label, 0, 1, 0, 1)
        table.attach(self.__tag, 1, 2, 0, 1)

        self.__val = gtk.Entry()
        self.__val.set_completion(LibraryValueCompletion("", library))
        label = gtk.Label()
        label.set_text(_("_Value:"))
        label.set_alignment(0.0, 0.5)
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.__val)
        valuebox = gtk.EventBox()
        table.attach(label, 0, 1, 1, 2)
        table.attach(valuebox, 1, 2, 1, 2)
        hbox = gtk.HBox()
        valuebox.add(hbox)
        hbox.pack_start(self.__val)
        hbox.set_spacing(6)
        invalid = gtk.image_new_from_stock(
            gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_SMALL_TOOLBAR)
        hbox.pack_start(invalid)

        self.vbox.pack_start(table)
        self.child.show_all()
        invalid.hide()

        for entry in [self.__tag, self.__val]:
            entry.connect(
                'changed', self.__validate, add, invalid, valuebox)
        self.__tag.connect('changed', self.__set_value_completion, library)
        self.__set_value_completion(self.__tag, library)

        if can_change == True:
            self.__tag.child.connect_object(
                'activate', gtk.Entry.grab_focus, self.__val)

    def __set_value_completion(self, tag, library):
        completion = self.__val.get_completion()
        if completion:
            completion.set_tag(self.__tag.tag, library)

    def get_tag(self):
        try: return self.__tag.tag
        except AttributeError:
            return self.__tag.tag

    def get_value(self):
        return self.__val.get_text().decode("utf-8")

    def __validate(self, editable, add, invalid, box):
        tag = self.get_tag()
        value = self.get_value()
        fmt = massagers.tags.get(tag)
        if fmt: valid = fmt.is_valid(value)
        else: valid = True
        add.set_sensitive(valid)
        if valid:
            invalid.hide()
            box.set_tooltip_text(None)
        else:
            invalid.show()
            box.set_tooltip_text(fmt.error)

    def run(self):
        self.show()
        self.__val.set_activates_default(True)
        self.__tag.grab_focus()
        return super(AddTagDialog, self).run()

TAG, VALUE, EDITED, CANEDIT, DELETED, ORIGVALUE, RENAMED, ORIGTAG = range(8)

def is_special(string):
    return string.endswith("</i>")

def is_different(string):
    return is_special(string) and string.startswith("<i>")

def is_missing(string):
    return is_special(string) and not string.startswith("<i>")

def strip_missing(string):
    try: return string[:string.index(" <i>")]
    except ValueError: return string

class EditTagsPluginHandler(EditingPluginHandler):
    from quodlibet.plugins.editing import EditTagsPlugin
    Kind = EditTagsPlugin

class EditTags(gtk.VBox):
    _SAVE_BUTTON_KEY = 'ql-save'
    _REVERT_BUTTON_KEY = 'ql-revert'
    # Translators: translate only to override the text for the tag "save" button
    _SAVE_BUTTON_TEXT = _('ql-save')
    # Translators: translate only to override the  for the tag "revert" button
    _REVERT_BUTTON_TEXT = _('ql-revert')
    handler = EditTagsPluginHandler()

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.handler)

    def __init__(self, parent, library):
        super(EditTags, self).__init__(spacing=12)
        self.title = _("Edit Tags")
        self.set_border_width(12)

        model = gtk.ListStore(str, str, bool, bool, bool, str, bool, str)
        view = RCMHintedTreeView(model)
        selection = view.get_selection()
        render = gtk.CellRendererPixbuf()
        column = TreeViewColumn(_("Write"), render)

        style = view.get_style()
        pixbufs = [ style.lookup_icon_set(stock)
                    .render_icon(style, gtk.TEXT_DIR_NONE, state,
                        gtk.ICON_SIZE_MENU, view, None)
                    for state in (gtk.STATE_INSENSITIVE, gtk.STATE_NORMAL)
                        for stock in (gtk.STOCK_EDIT, gtk.STOCK_DELETE) ]
        def cdf_write(col, rend, model, iter, (write, delete)):
            row = model[iter]
            if row[CANEDIT]:
                rend.set_property('stock-id', None)
                rend.set_property('pixbuf', pixbufs[2*row[EDITED]+row[DELETED]])
            else:
                rend.set_property('stock-id', gtk.STOCK_DIALOG_AUTHENTICATION)
        column.set_cell_data_func(render, cdf_write, (2, 4))
        view.append_column(column)

        render = gtk.CellRendererText()
        column = TreeViewColumn(
            _('Tag'), render, text=0, editable=3, strikethrough=4)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        render.set_property('editable', True)
        render.connect('edited', self.__edit_tag_name, model)
        render.connect(
            'editing-started', self.__tag_editing_started, model, library)
        view.append_column(column)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        render.set_property('editable', True)
        render.connect('edited', self.__edit_tag, model)
        render.connect(
            'editing-started', self.__value_editing_started, model, library)
        render.markup = 1
        column = TreeViewColumn(
            _('Value'), render, markup=1, editable=3, strikethrough=4)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(column)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        self.pack_start(sw)

        # Add and Remove [tags] buttons
        buttonbox = gtk.HBox(spacing=18)
        bbox1 = gtk.HButtonBox()
        bbox1.set_spacing(6)
        bbox1.set_layout(gtk.BUTTONBOX_START)
        add = gtk.Button(stock=gtk.STOCK_ADD)
        add.set_focus_on_click(False)
        add.connect('clicked', self.__add_tag, model, library)
        bbox1.pack_start(add)
        # Remove button
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)
        remove.set_focus_on_click(False)
        remove.connect('clicked', self.__remove_tag, view)
        remove.set_sensitive(False)

        bbox1.pack_start(remove)

        # Revert and save buttons
        # Both can have customised translated text (and thus accels)
        bbox2 = gtk.HButtonBox()
        bbox2.set_spacing(6)
        bbox2.set_layout(gtk.BUTTONBOX_END)
        revert = (gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)
                  if self._REVERT_BUTTON_KEY == self._REVERT_BUTTON_TEXT
                  else gtk.Button(label=self._REVERT_BUTTON_TEXT))
        revert.set_sensitive(False)
        # Save button.
        save = (gtk.Button(stock=gtk.STOCK_SAVE)
                if self._SAVE_BUTTON_TEXT == self._SAVE_BUTTON_KEY
                else gtk.Button(label=self._SAVE_BUTTON_TEXT))
        save.set_sensitive(False)
        self.save = save
        bbox2.pack_start(revert)
        bbox2.pack_start(save)

        buttonbox.pack_start(bbox1)
        buttonbox.pack_start(bbox2)
        self.pack_start(buttonbox, expand=False)

        UPDATE_ARGS = [
            view, buttonbox, model, add, [save, revert, remove]]
        parent.connect_object(
            'changed', self.__class__.__update, self, *UPDATE_ARGS)
        revert.connect_object(
            'clicked', self.__update, None, *UPDATE_ARGS)
        revert.connect_object('clicked', parent.set_pending, None)

        save.connect('clicked', self.__save_files, revert, model, library)
        save.connect_object('clicked', parent.set_pending, None)
        for sig in ['row-inserted', 'row-deleted', 'row-changed']:
            model.connect(sig, self.__enable_save, [save, revert])
            model.connect_object(sig, parent.set_pending, save)

        view.connect('popup-menu', self.__popup_menu, parent)
        view.connect('button-press-event', self.__button_press)
        view.connect('key-press-event', self.__view_key_press_event)
        selection.connect('changed', self.__tag_select, remove)
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.show_all()

    def __view_key_press_event(self, view, event):
        # We can't use a real accelerator to this because it would
        # interfere with typeahead and row editing.
        ctrl = event.state & gtk.gdk.CONTROL_MASK
        keyval_name = gtk.gdk.keyval_name(event.keyval)
        if event.keyval == gtk.accelerator_parse("Delete")[0]:
            self.__remove_tag(view, view)
        elif ctrl and keyval_name == 's':
            # Issue 697: allow Ctrl-s to save.
            self.save.emit('clicked')

    def __enable_save(self, *args):
        buttons = args[-1]
        for b in buttons: b.set_sensitive(True)

    def __paste(self, clip, text, (rend, path)):
        if text: rend.emit('edited', path, text.strip())

    def __menu_activate(self, activator, view):
        model, (iter,) = view.get_selection().get_selected_rows()
        row = model[iter]
        tag = row[TAG]
        value = util.unescape(row[VALUE].decode('utf-8'))
        vals = activator.activated(tag, value)
        replaced = False
        if vals and (len(vals) != 1 or vals[0][1] != value):
            for atag, aval in vals:
                if atag == tag and not replaced:
                    replaced = True
                    row[VALUE] = util.escape(aval)
                    row[EDITED] = True
                else: self.__add_new_tag(model, atag, aval)
        elif vals: replaced = True
        if not replaced: row[EDITED] = row[DELETED] = True

    def __popup_menu(self, view, parent):
        menu = gtk.Menu()

        view.ensure_popup_selection()
        model, rows = view.get_selection().get_selected_rows()
        can_change = min([model[path][CANEDIT] for path in rows])

        items = [SplitDisc, SplitTitle, SplitPerformer, SplitArranger,
                 SplitValues, SplitPerformerFromTitle,
                 SplitOriginalArtistFromTitle]
        items.extend(self.handler.plugins)
        items.sort(key=lambda item: (item._order, item.__name__))

        if len(rows) == 1:
            row = model[rows[0]]

            value = row[VALUE].decode('utf-8')
            text = util.unescape(value)
            multi = (value.split("<")[0] != value)

            for Item in items:
                if Item.tags and row[TAG] not in Item.tags: continue

                try: b = Item(row[TAG], text)
                except:
                    util.print_exc()
                else:
                    b.connect('activate', self.__menu_activate, view)

                    if not min(map(self.__songinfo.can_change, b.needs)+[1]) \
                        or multi:
                        b.set_sensitive(False)

                    menu.append(b)

            if menu.get_children(): menu.append(gtk.SeparatorMenuItem())

        b = gtk.ImageMenuItem(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        b.connect('activate', self.__remove_tag, view)
        keyval, mod = gtk.accelerator_parse("Delete")
        menu.__accels = gtk.AccelGroup()
        b.add_accelerator(
            'activate', menu.__accels, keyval, mod, gtk.ACCEL_VISIBLE)
        menu.append(b)

        menu.show_all()
        # Setting the menu itself to be insensitive causes it to not
        # be dismissed; see #473.
        for c in menu.get_children():
            c.set_sensitive(can_change and c.get_property('sensitive'))
        menu.connect('selection-done', lambda m: m.destroy())
        return view.popup_menu(menu, 3, gtk.get_current_event_time())

    def __tag_select(self, selection, remove):
        model, rows = selection.get_selected_rows()
        remove.set_sensitive(
            bool(rows and min([model[row][CANEDIT] for row in rows])))

    def __add_new_tag(self, model, tag, value):
        if (tag in self.__songinfo and not self.__songinfo.multiple_values):
            title = _("Unable to add tag")
            msg = _("Unable to add <b>%s</b>\n\nThe files currently"
                    " selected do not support multiple values."
                    ) % util.escape(tag)
            qltk.ErrorMessage(self, title, msg).run()
            return

        iters = [row.iter for row in model if row[TAG] == tag]
        row = [tag, util.escape(value), True, True, False, None, False, None]
        if len(iters): model.insert_after(iters[-1], row=row)
        else: model.append(row=row)

    def __add_tag(self, activator, model, library):
        add = AddTagDialog(self, self.__songinfo.can_change(), library)

        while True:
            resp = add.run()
            if resp != gtk.RESPONSE_OK: break
            tag = add.get_tag()
            value = add.get_value()
            if tag in massagers.tags:
                value = massagers.tags[tag].validate(value)
            if not self.__songinfo.can_change(tag):
                title = _("Invalid tag")
                msg = _("Invalid tag <b>%s</b>\n\nThe files currently"
                        " selected do not support editing this tag."
                        ) % util.escape(tag)
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
            if row[ORIGVALUE] is not None:
                row[EDITED] = row[DELETED] = True
            else: model.remove(row.iter)

    def __save_files(self, save, revert, model, library):
        updated = {}
        deleted = {}
        added = {}
        renamed = {}
        for row in model:
            if row[EDITED] and not (row[DELETED] or row[RENAMED]):
                if row[ORIGVALUE] is not None:
                    updated.setdefault(row[TAG], [])
                    updated[row[TAG]].append((util.decode(row[VALUE]),
                                              util.decode(row[ORIGVALUE])))
                else:
                    added.setdefault(row[TAG], [])
                    added[row[TAG]].append(util.decode(row[VALUE]))
            if row[EDITED] and row[DELETED]:
                if row[ORIGVALUE] is not None:
                    deleted.setdefault(row[TAG], [])
                    deleted[row[TAG]].append(util.decode(row[ORIGVALUE]))

            if row[EDITED] and row[RENAMED] and not row[DELETED]:
                renamed.setdefault(row[TAG], [])
                renamed[row[TAG]].append((util.decode(row[ORIGTAG]),
                                          util.decode(row[VALUE]),
                                          util.decode(row[ORIGVALUE])))

        was_changed = []
        songs = self.__songinfo.songs
        win = WritingWindow(self, len(songs))
        for song in songs:
            if not song.valid() and not qltk.ConfirmAction(
                self, _("Tag may not be accurate"),
                _("<b>%s</b> changed while the program was running. "
                  "Saving without refreshing your library may "
                  "overwrite other changes to the song.\n\n"
                  "Save this song anyway?") % util.escape(util.fsdecode(
                song("~basename")))
                ).run():
                break

            changed = False
            for key, values in updated.iteritems():
                for (new_value, old_value) in values:
                    new_value = util.unescape(new_value)
                    if song.can_change(key):
                        if old_value is None: song.add(key, new_value)
                        else: song.change(key, old_value, new_value)
                        changed = True
            for key, values in added.iteritems():
                for value in values:
                    value = util.unescape(value)
                    if song.can_change(key):
                        song.add(key, value)
                        changed = True
            for key, values in deleted.iteritems():
                for value in values:
                    value = util.unescape(value)
                    if song.can_change(key) and key in song:
                        song.remove(key, value)
                        changed = True
            save_rename = []
            for new_tag, values in renamed.iteritems():
                for old_tag, new_value, old_value in values:
                    old_tag = util.unescape(old_tag)
                    old_value = util.unescape(old_value)
                    new_value = util.unescape(new_value)
                    if (song.can_change(new_tag) and
                        song.can_change(old_tag) and old_tag in song):
                        if not is_special(new_value):
                            song.remove(old_tag, old_value)
                            save_rename.append((new_tag, new_value))
                        elif is_missing(new_value):
                            value = strip_missing(old_value)
                            song.remove(old_tag, old_value)
                            save_rename.append((new_tag, new_value))
                        else:
                            save_rename.append((new_tag, song[old_tag]))
                            song.remove(old_tag, None)
                        changed = True
            for tag, value in save_rename:
                song.add(tag, value)

            if changed:
                try: song.write()
                except:
                    util.print_exc()
                    qltk.ErrorMessage(
                        self, _("Unable to save song"),
                        _("Saving <b>%s</b> failed. The file "
                          "may be read-only, corrupted, or you "
                          "do not have permission to edit it.")%(
                        util.escape(util.fsdecode(
                        song('~basename'))))).run()
                    library.reload(song, changed=was_changed)
                    break
                was_changed.append(song)

            if win.step(): break

        win.destroy()
        library.changed(was_changed)
        for b in [save, revert]: b.set_sensitive(False)

    def __edit_tag(self, renderer, path, new_value, model):
        new_value = ', '.join(new_value.splitlines())
        row = model[path]
        if row[TAG] in massagers.tags:
            fmt = massagers.tags[row[TAG]]
            if not fmt.is_valid(new_value):
                qltk.WarningMessage(
                    self, _("Invalid value"),
                    _("Invalid value: <b>%(value)s</b>\n\n%(error)s") %{
                    "value": new_value, "error": fmt.error}).run()
                return
            else: new_value = fmt.validate(new_value)
        tag = self.__songinfo.get(row[TAG], None)
        if row[VALUE].split('<')[0] != new_value or (
                tag and tag.shared and not tag.complete):
            row[VALUE] = util.escape(new_value)
            row[EDITED] = True
            row[DELETED] = False

    def __edit_tag_name(self, renderer, path, new_tag, model):
        new_tag = ' '.join(new_tag.splitlines()).lower()
        row = model[path]
        if new_tag == row[TAG]:
            return
        elif not self.__songinfo.can_change(row[TAG]):
            # Can't remove the old tag.
            title = _("Invalid tag")
            msg = _("Invalid tag <b>%s</b>\n\nThe files currently"
                    " selected do not support editing this tag."
                    ) % util.escape(row[TAG])
            qltk.ErrorMessage(self, title, msg).run()
        elif not self.__songinfo.can_change(new_tag):
            # Can't add the new tag.
            title = _("Invalid tag")
            msg = _("Invalid tag <b>%s</b>\n\nThe files currently"
                    " selected do not support editing this tag."
                    ) % util.escape(new_tag)
            qltk.ErrorMessage(self, title, msg).run()
        else:
            if new_tag in massagers.tags:
                fmt = massagers.tags[new_tag]
                v = util.unescape(row[VALUE])
                if not fmt.is_valid(v):
                    qltk.WarningMessage(
                        self, _("Invalid value"),
                        _("Invalid value: <b>%(value)s</b>\n\n%(error)s") %{
                        "value": row[VALUE], "error": fmt.error}).run()
                    return
                value = fmt.validate(v)
            else:
                value = row[VALUE]
                value = util.unescape(value)

            if row[ORIGVALUE] is None:
                # The tag hasn't been saved yet, so we can just update
                # the name in the model, and the value, since it
                # may have been re-validated.
                row[TAG] = new_tag
                row[VALUE] = value
            else:
                # The tag has been saved, so delete the old tag and
                # add a new one with the old (or sanitized) value.
                row[RENAMED] = row[EDITED] = True
                row[ORIGTAG] = row[TAG]
                row[TAG] = new_tag

    def __button_press(self, view, event):
        if event.button not in [1, 2]: return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return False

        if event.button == 1 and col is view.get_columns()[0]:
            row = view.get_model()[path]
            row[EDITED] = not row[EDITED]
            if row[EDITED]:
                idx = row[VALUE].find('<i>')
                if idx >= 0: row[VALUE] = row[VALUE][:idx].strip()
            return True
        elif event.button == 2 and col == view.get_columns()[2]:
            display = gtk.gdk.display_manager_get().get_default_display()
            clipboardname = ["PRIMARY", "CLIPBOARD"][sys.platform == "win32"]
            clipboard = gtk.Clipboard(display, clipboardname)
            for rend in col.get_cell_renderers():
                if rend.get_property('editable'):
                    clipboard.request_text(self.__paste, (rend, path[0]))
                    return True
            else: return False
        else: return False

    def __update(self, songs, view, buttonbox, model, add, buttons):
        if songs is None:
            songs = self.__songinfo.songs

        self.__songinfo = songinfo = AudioFileGroup(songs)
        view.set_model(None)
        model.clear()
        view.set_model(model)

        keys = sorted(songinfo.realkeys())

        if not config.getboolean("editing", "alltags"):
            keys = filter(lambda k: k not in formats.MACHINE_TAGS, keys)

        # reverse order here so insertion puts them in proper order.
        for tag in ['album', 'artist', 'title']:
            try: keys.remove(tag)
            except ValueError: pass
            else: keys.insert(0, tag)

        for tag in keys:
            # Handle with care.
            orig_value = songinfo[tag].split("\n")
            value = songinfo[tag].safenicestr()
            edited = False
            edit = songinfo.can_change(tag)
            deleted = False
            renamed = False
            newtag = ""
            if value[0:1] == "<": # "different etc."
                model.append(row=[tag, value, edited, edit, deleted,
                                  "\n".join(orig_value), renamed,
                                  newtag])
            else:
                for i, v in enumerate(value.split("\n")):
                    model.append(row=[tag, v, edited, edit, deleted,
                                      orig_value[i], renamed, newtag])

        buttonbox.set_sensitive(bool(songinfo.can_change()))
        for b in buttons: b.set_sensitive(False)
        add.set_sensitive(bool(songs))

    def __value_editing_started(self, render, editable, path, model, library):
        try:
            if not editable.get_completion():
                tag = model[path][TAG]
                completion = LibraryValueCompletion(tag, library)
                editable.set_completion(completion)
        except AttributeError:
            pass
        if isinstance(editable, gtk.Entry):
            editable.set_text(util.unescape(model[path][VALUE].split('<')[0]))

    def __tag_editing_started(self, render, editable, path, model, library):
        try:
            if not editable.get_completion():
                tags = self.__songinfo.can_change()
                if tags == True:
                    from quodlibet.formats import USEFUL_TAGS as tags
                completion = qltk.EntryCompletion(tags)
                editable.set_completion(completion)
        except AttributeError:
            pass
