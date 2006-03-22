# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import gtk, pango

import qltk
from qltk.wlw import WritingWindow
from qltk.views import RCMHintedTreeView
from qltk.tagscombobox import TagsComboBox, TagsComboBoxEntry
from massagers import Massager

import const
import config
import util
import formats

from util import tag

import __builtin__; __builtin__.__dict__.setdefault("_", lambda a: a)

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

class AddTagDialog(gtk.Dialog):
    def __init__(self, parent, can_change):
        if can_change == True: can = formats.USEFUL_TAGS
        else: can = list(can_change)
        can.sort()

        gtk.Dialog.__init__(self, _("Add a Tag"), parent)
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

        if can_change == True: self.__tag = TagsComboBoxEntry()
        else: self.__tag = TagsComboBox(can_change)

        label = gtk.Label()
        label.set_alignment(0.0, 0.5)
        label.set_text(_("_Tag:"))
        label.set_use_underline(True)
        label.set_mnemonic_widget(self.__tag)
        table.attach(label, 0, 1, 0, 1)
        table.attach(self.__tag, 1, 2, 0, 1)

        self.__val = gtk.Entry()
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

        tips = qltk.Tooltips(self)
        tips.disable()
        for entry in [self.__tag, self.__val]:
            entry.connect(
                'changed', self.__validate, add, invalid, tips, valuebox)

        if can_change == True:
            self.__tag.child.connect_object(
                'activate', gtk.Entry.grab_focus, self.__val)

    def get_tag(self):
        try: return self.__tag.tag
        except AttributeError:
            return self.__tag.tag

    def get_value(self):
        return self.__val.get_text().decode("utf-8")

    def __validate(self, editable, add, invalid, tips, box):
        tag = self.get_tag()
        value = self.get_value()
        fmt = Massager.fmt.get(tag)
        if fmt: valid = bool(fmt.validate(value))
        else: valid = True
        add.set_sensitive(valid)
        if valid:
            invalid.hide()
            tips.disable()
        else:
            invalid.show()
            tips.set_tip(box, fmt.error)
            tips.enable()

    def run(self):
        self.show()
        self.__val.set_activates_default(True)
        self.__tag.grab_focus()
        return gtk.Dialog.run(self)

TAG, VALUE, EDITED, CANEDIT, DELETED, ORIGVALUE = range(6)

class EditTags(gtk.VBox):
    def __init__(self, parent, watcher):
        super(EditTags, self).__init__(spacing=12)
        self.title = _("Edit Tags")
        self.set_border_width(12)

        model = gtk.ListStore(str, str, bool, bool, bool, str)
        view = RCMHintedTreeView(model)
        selection = view.get_selection()
        render = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn(_("Write"), render)

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
        column = gtk.TreeViewColumn(
            _('Tag'), render, text=0, editable=3, strikethrough=4)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        render.set_property('editable', True)
        render.connect('edited', self.__edit_tag_name, model)
        view.append_column(column)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        render.set_property('editable', True)
        render.connect('edited', self.__edit_tag, model)
        render.markup = 1
        column = gtk.TreeViewColumn(
            _('Value'), render, markup=1, editable=3, strikethrough=4)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(column)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        self.pack_start(sw)

        buttonbox = gtk.HBox(spacing=18)
        bbox1 = gtk.HButtonBox()
        bbox1.set_spacing(6)
        bbox1.set_layout(gtk.BUTTONBOX_START)
        add = gtk.Button(stock=gtk.STOCK_ADD)
        add.set_focus_on_click(False)
        add.connect('clicked', self.__add_tag, model)
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)
        remove.set_focus_on_click(False)
        remove.connect('clicked', self.__remove_tag, view)
        remove.set_sensitive(False)
        bbox1.pack_start(add)
        bbox1.pack_start(remove)

        bbox2 = gtk.HButtonBox()
        bbox2.set_spacing(6)
        bbox2.set_layout(gtk.BUTTONBOX_END)
        revert = gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)
        save = gtk.Button(stock=gtk.STOCK_SAVE)
        revert.set_sensitive(False)
        save.set_sensitive(False)
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

        save.connect(
            'clicked', self.__save_files, revert, model, parent, watcher)
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
        if event.keyval == gtk.accelerator_parse("Delete")[0]:
            self.__remove_tag(view, view)

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
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()

        model, rows = view.get_selection().get_selected_rows()
        can_change = min([model[path][CANEDIT] for path in rows])

        items = [SplitDisc, SplitTitle, SplitPerformer, SplitArranger,
                 SplitValues]
        items.extend(parent.plugins.EditTagsPlugins())
        items.sort(lambda a, b:
                   (cmp(a._order, b._order) or cmp(a.__name__, b.__name__)))

        if len(rows) == 1:
            row = model[rows[0]]

            text = util.unescape(row[VALUE].decode('utf-8'))

            for Item in items:
                if Item.tags and row[TAG] not in Item.tags: continue

                try: b = Item(row[TAG], text)
                except:
                    import traceback; traceback.print_exc()
                else:
                    b.connect('activate', self.__menu_activate, view)

                    if not min(map(self.__songinfo.can_change, b.needs)+[1]):
                        b.set_sensitive(False)

                    menu.append(b)


            if menu.get_children(): menu.append(gtk.SeparatorMenuItem())

        b = gtk.ImageMenuItem(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        b.connect('activate', self.__remove_tag, view)
        keyval, mod = gtk.accelerator_parse("Delete")
        b.add_accelerator(
            'activate', gtk.AccelGroup(), keyval, mod, gtk.ACCEL_VISIBLE)
        menu.append(b)

        menu.show_all()
        # Setting the menu itself to be insensitive causes it to not
        # be dismissed; see #473.
        for c in menu.get_children():
            c.set_sensitive(can_change and c.get_property('sensitive'))
        menu.connect('selection-done', lambda m: m.destroy())
        menu.popup(None, None, None, 3, gtk.get_current_event_time())
        return True

    def __tag_select(self, selection, remove):
        model, rows = selection.get_selected_rows()
        remove.set_sensitive(
            bool(rows and min([model[row][CANEDIT] for row in rows])))

    def __add_new_tag(self, model, comment, value):
        if (comment in self.__songinfo and not self.__songinfo.multiple_values):
            title = _("Unable to add tag")
            msg = _("Unable to add <b>%s</b>\n\nThe files currently"
                    " selected do not support multiple values."
                    ) % util.escape(comment)
            qltk.ErrorMessage(None, title, msg).run()
            return

        edited = True
        edit = True
        orig = None
        deleted = False
        iters = [row.iter for row in model if row[TAG] == comment]
        row = [comment, util.escape(value), True, True, False, None]
        if len(iters): model.insert_after(iters[-1], row=row)
        else: model.append(row=row)

    def __add_tag(self, activator, model):
        add = AddTagDialog(None, self.__songinfo.can_change())

        while True:
            resp = add.run()
            if resp != gtk.RESPONSE_OK: break
            tag = add.get_tag()
            value = add.get_value()
            if tag in Massager.fmt:
                value = Massager.fmt[tag].validate(value)
            if not self.__songinfo.can_change(tag):
                title = _("Invalid tag")
                msg = _("Invalid tag <b>%s</b>\n\nThe files currently"
                        " selected do not support editing this tag."
                        ) % util.escape(tag)
                qltk.ErrorMessage(None, title, msg).run()
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

    def __save_files(self, save, revert, model, parent, watcher):
        updated = {}
        deleted = {}
        added = {}
        for row in model:
            if row[EDITED] and not row[DELETED]:
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

        was_changed = []
        win = WritingWindow(parent, len(self.__songs))
        for song in self.__songs:
            if not song.valid() and not qltk.ConfirmAction(
                None, _("Tag may not be accurate"),
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

            if changed:
                try: song.write()
                except:
                    qltk.ErrorMessage(
                        None, _("Unable to save song"),
                        _("Saving <b>%s</b> failed. The file "
                          "may be read-only, corrupted, or you "
                          "do not have permission to edit it.")%(
                        util.escape(util.fsdecode(
                        song('~basename'))))).run()
                    watcher.reload(song)
                    break
                was_changed.append(song)

            if win.step(): break

        win.destroy()
        watcher.changed(was_changed)
        for b in [save, revert]: b.set_sensitive(False)

    def __edit_tag_name(self, renderer, path, new, model):
        new = ' '.join(new.splitlines())
        row = model[path]
        if new == row[TAG]: return
        elif self.__songinfo.can_change(new):
            if new in Massager.fmt:
                fmt = Massager.fmt[new]
                value = fmt.validate(util.unescape(row[VALUE]))
                if not value:
                    qltk.WarningMessage(
                        None, _("Invalid value"), _("Invalid value") +
                        (": <b>%s</b>\n\n%s" % (row[VALUE], fmt.error))).run()
                return
            else:
                value = row[VALUE]
                idx = value.find('<i>')
                if idx == 0:
                    title = _("Unable to retag multiple values")
                    msg = _("Changing the name of a tag with multiple "
                            "values is not supported.")
                    qltk.ErrorMessage(None, title, msg).run()
                    return
                elif idx >= 0: value = value[:idx].strip()
                value = util.unescape(value)

            if row[ORIGVALUE] is None: row[0] = new
            else:
                row[DELETED] = row[EDITED] = True
                self.__add_new_tag(model, new, value)
        elif not self.__songinfo.can_change(row[TAG]):
            title = _("Invalid tag")
            msg = _("Invalid tag <b>%s</b>\n\nThe files currently"
                    " selected do not support editing this tag."
                    ) % util.escape(comment)
            qltk.ErrorMessage(None, title, msg).run()            

    def __edit_tag(self, renderer, path, new, model):
        new = ', '.join(new.splitlines())
        row = model[path]
        if row[TAG] in Massager.fmt:
            fmt = Massager.fmt[row[TAG]]
            newnew = fmt.validate(new)
            if not newnew:
                qltk.WarningMessage(
                    None, _("Invalid value"), _("Invalid value") +
                    (": <b>%s</b>\n\n%s" % (new, fmt.error))).run()
                return
            else: new = newnew
        if row[VALUE].replace('<i>','').replace('</i>','') != new:
            row[VALUE] = util.escape(new)
            row[EDITED] = True
            row[DELETED] = False

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
            clipboard = gtk.Clipboard(display, "PRIMARY")
            for rend in col.get_cell_renderers():
                if rend.get_property('editable'):
                    clipboard.request_text(self.__paste, (rend, path[0]))
                    return True
            else: return False
        else: return False

    def __update(self, songs, view, buttonbox, model, add, buttons):
        if songs is None: songs = self.__songs

        from library import AudioFileGroup
        self.__songinfo = songinfo = AudioFileGroup(songs)
        self.__songs = songs
        view.set_model(None)
        model.clear()
        view.set_model(model)

        keys = songinfo.realkeys()
        keys.sort()

        if not config.getboolean("editing", "alltags"):
            keys = filter(lambda k: k not in const.MACHINE_TAGS, keys)

        # reverse order here so insertion puts them in proper order.
        for comment in ['album', 'artist', 'title']:
            try: keys.remove(comment)
            except ValueError: pass
            else: keys.insert(0, comment)

        for comment in keys:
            # Handle with care.
            orig_value = songinfo[comment].split("\n")
            value = songinfo[comment].safenicestr()
            edited = False
            edit = songinfo.can_change(comment)
            deleted = False
            if value[0:1] == "<": # "different etc."
                model.append(row=[comment, value, edited, edit, deleted,
                                  "\n".join(orig_value)])
            else:
                for i, v in enumerate(value.split("\n")):
                    model.append(row=[comment, v, edited, edit, deleted,
                                      orig_value[i]])

        buttonbox.set_sensitive(bool(songinfo.can_change()))
        for b in buttons: b.set_sensitive(False)
        add.set_sensitive(bool(songs))
