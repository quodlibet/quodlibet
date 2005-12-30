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
from qltk.views import HintedTreeView, RCMTreeView
from massagers import Massager

import const
import config
import util
import formats

from util import tag

import __builtin__; __builtin__.__dict__.setdefault("_", lambda a: a)

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

        if can_change == True:
            model = gtk.ListStore(str, str)
            self.__tag = gtk.ComboBoxEntry(model, column=0)
            self.__tag.clear()
            text = gtk.CellRendererText()
            self.__tag.pack_start(text)
            self.__tag.add_attribute(text, 'text', 1)
            for t in can:
                model.append(row=[t, "%s (%s)" % (tag(t), t)])
        else:
            self.__tag = gtk.combo_box_new_text()
            for t in can: self.__tag.append_text(t)
            self.__tag.set_active(0)

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

    def get_tag(self):
        try: return self.__tag.child.get_text().lower().strip()
        except AttributeError:
            return self.__tag.get_model()[self.__tag.get_active()][0]

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
        try: self.__tag.child.set_activates_default(True)
        except AttributeError: pass
        self.__val.set_activates_default(True)
        self.__tag.grab_focus()
        return gtk.Dialog.run(self)

class EditTags(gtk.VBox):
    class TV(HintedTreeView, RCMTreeView): pass

    def __init__(self, parent, watcher):
        gtk.VBox.__init__(self, spacing=12)
        self.title = _("Edit Tags")
        self.set_border_width(12)

        model = gtk.ListStore(str, str, bool, bool, bool, str)
        view = self.TV(model)
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
            if not self.__songinfo.can_change(row[0]):
                rend.set_property(
                    'stock-id', gtk.STOCK_DIALOG_AUTHENTICATION)
            else:
                rend.set_property('stock-id', None)
                rend.set_property(
                    'pixbuf', pixbufs[2*row[write]+row[delete]])
        column.set_cell_data_func(render, cdf_write, (2, 4))
        view.append_column(column)
        view.connect(
            'button-press-event', self.__write_toggle, (column, 1, 2))

        render = gtk.CellRendererText()
        column = gtk.TreeViewColumn(
            _('Tag'), render, text=0, strikethrough=4)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(column)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        render.set_property('editable', True)
        render.connect('edited', self.__edit_tag, model, 1)
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

        tips = qltk.Tooltips(self)
        for widget, tip in [
            (view, _("Double-click a tag value to change it, "
                     "right-click for other options")),
            (add, _("Add a new tag")),
            (remove, _("Remove selected tag"))]:
            tips.set_tip(widget, tip)

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

        view.connect('popup-menu', self.__popup_menu)
        view.connect('button-press-event', self.__button_press)
        selection.connect('changed', self.__tag_select, remove)
        self.show_all()

    def __enable_save(self, *args):
        buttons = args[-1]
        for b in buttons: b.set_sensitive(True)

    def __popup_menu(self, view):
        path, col = view.get_cursor()
        row = view.get_model()[path]
        self.__show_menu(row, 0, gtk.get_current_event_time(), view)
        return True

    def __button_press(self, view, event):
        if event.button != 2: return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        row = view.get_model()[path]

        if event.button == 2: # middle click paste
            if col != view.get_columns()[2]: return False
            display = gtk.gdk.display_manager_get().get_default_display()
            clipboard = gtk.Clipboard(display, "PRIMARY")
            for rend in col.get_cell_renderers():
                if rend.get_property('editable'):
                    clipboard.request_text(self.__paste, (rend, path[0]))
                    return True
            else: return False

    def __paste(self, clip, text, (rend, path)):
        if text: rend.emit('edited', path, text.strip())

    def __split_into_list(self, activator, view):
        model, iter = view.get_selection().get_selected()
        row = model[iter]
        string = row[1].decode('utf-8')
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        vals = util.split_value(util.unescape(string), spls)
        if vals[0] != util.unescape(string):
            row[1] = util.escape(vals[0])
            row[2] = True
            for val in vals[1:]:
                self.__add_new_tag(model, row[0], val)

    def __split_title(self, activator, view):
        model, iter = view.get_selection().get_selected()
        row = model[iter]
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        title, versions = util.split_title(util.unescape(row[1]), spls)
        if title != util.unescape(row[1]):
            row[1] = util.escape(title)
            row[2] = True
            for val in versions:
                self.__add_new_tag(model, "version", val)

    def __split_album(self, activator, view):
        model, iter = view.get_selection().get_selected()
        row = model[iter]
        album, disc = util.split_album(util.unescape(row[1]))
        if album != util.unescape(row[1]):
            row[1] = util.escape(album)
            row[2] = True
            self.__add_new_tag(model, "discnumber", disc)

    def __split_people(self, activator, tag, view):
        model, iter = view.get_selection().get_selected()
        row = model[iter]
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()
        person, others = util.split_people(util.unescape(row[1]), spls)
        if person != util.unescape(row[1]):
            row[1] = util.escape(person)
            row[2] = True
            for val in others:
                self.__add_new_tag(model, tag, val)

    def __show_menu(self, row, button, time, view):
        menu = gtk.Menu()        
        spls = config.get("editing", "split_on").decode(
            'utf-8', 'replace').split()

        can_change = self.__songinfo.can_change(row[0])

        text = row[1].decode('utf-8')
        b = qltk.MenuItem(
            _("Split into _Multiple Values"), gtk.STOCK_FIND_AND_REPLACE)
        b.set_sensitive(
            (len(util.split_value(text, spls)) > 1) and can_change)
        b.connect('activate', self.__split_into_list, view)
        menu.append(b)
        menu.append(gtk.SeparatorMenuItem())

        if row[0] == "album":
            b = qltk.MenuItem(
                _("Split Disc out of _Album"), gtk.STOCK_FIND_AND_REPLACE)
            b.connect('activate', self.__split_album, view)
            b.set_sensitive((util.split_album(text)[1] is not None) and
                            self.__songinfo.can_change("album"))
            menu.append(b)

        elif row[0] == "title":
            b = qltk.MenuItem(_("Split Version out of Title"),
                              gtk.STOCK_FIND_AND_REPLACE)
            b.connect('activate', self.__split_title, view)
            b.set_sensitive((util.split_title(text, spls)[1] != []) and
                            self.__songinfo.can_change("version"))
            menu.append(b)

        elif row[0] == "artist":
            ok = (util.split_people(text, spls)[1] != [])

            b = qltk.MenuItem(_("Split Arranger out of Ar_tist"),
                              gtk.STOCK_FIND_AND_REPLACE)
            b.connect('activate', self.__split_people, "arranger", view)
            b.set_sensitive(ok and self.__songinfo.can_change("arranger"))
            menu.append(b)

            b = qltk.MenuItem(_("Split _Performer out of Artist"),
                              gtk.STOCK_FIND_AND_REPLACE)
            b.connect('activate', self.__split_people, "performer", view)
            b.set_sensitive(ok and self.__songinfo.can_change("performer"))
            menu.append(b)

        if len(menu.get_children()) > 2:
            menu.append(gtk.SeparatorMenuItem())

        b = gtk.ImageMenuItem(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        b.connect('activate', self.__remove_tag, view)
        b.set_sensitive(can_change)
        menu.append(b)

        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        menu.popup(None, None, None, button, time)

    def __tag_select(self, selection, remove):
        model, iter = selection.get_selected()
        remove.set_sensitive(bool(iter and model[iter][3]))

    def __add_new_tag(self, model, comment, value):
        edited = True
        edit = True
        orig = None
        deleted = False
        iters = [row.iter for row in model if row[0] == comment]
        row = [comment, util.escape(value), edited, edit,deleted, orig]
        if len(iters): model.insert_after(iters[-1], row=row)
        else: model.append(row=row)

    def __add_tag(self, activator, model):
        add = AddTagDialog(None, self.__songinfo.can_change())

        while True:
            resp = add.run()
            if resp != gtk.RESPONSE_OK: break
            comment = add.get_tag()
            value = add.get_value()
            if comment in Massager.fmt:
                value = Massager.fmt[comment].validate(value)
            if not self.__songinfo.can_change(comment):
                title = _("Invalid tag")
                msg = _("Invalid tag <b>%s</b>\n\nThe files currently"
                        " selected do not support editing this tag."
                        ) % util.escape(comment)
                qltk.ErrorMessage(None, title, msg).run()
            else:
                self.__add_new_tag(model, comment, value)
                break

        add.destroy()

    def __remove_tag(self, activator, view):
        model, iter = view.get_selection().get_selected()
        row = model[iter]
        if row[0] in self.__songinfo:
            row[2] = True # Edited
            row[4] = True # Deleted
        else:
            model.remove(iter)

    def __save_files(self, save, revert, model, parent, watcher):
        updated = {}
        deleted = {}
        added = {}
        for row in model:
            # Edited, and or and not Deleted
            if row[2] and not row[4]:
                if row[5] is not None:
                    updated.setdefault(row[0], [])
                    updated[row[0]].append((util.decode(row[1]),
                                            util.decode(row[5])))
                else:
                    added.setdefault(row[0], [])
                    added[row[0]].append(util.decode(row[1]))
            if row[2] and row[4]:
                if row[5] is not None:
                    deleted.setdefault(row[0], [])
                    deleted[row[0]].append(util.decode(row[5]))

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
        watcher.refresh()
        for b in [save, revert]: b.set_sensitive(False)

    def __edit_tag(self, renderer, path, new, model, colnum):
        new = ', '.join(new.splitlines())
        row = model[path]
        if row[0] in Massager.fmt:
            fmt = Massager.fmt[row[0]]
            newnew = fmt.validate(new)
            if not newnew:
                qltk.WarningMessage(
                    None, _("Invalid value"), _("Invalid value") +
                    (": <b>%s</b>\n\n%s" % (new, fmt.error))).run()
                return
            else: new = newnew
        if row[colnum].replace('<i>','').replace('</i>','') != new:
            row[colnum] = util.escape(new)
            row[2] = True # Edited
            row[4] = False # not Deleted

    def __write_toggle(self, view, event, (writecol, textcol, edited)):
        if event.button != 1: return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return False

        if col is writecol:
            row = view.get_model()[path]
            row[edited] = not row[edited]
            if row[edited]:
                idx = row[textcol].find(' <i>')
                if idx >= 0: row[textcol] = row[textcol][:idx]
            return True

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
            # FIXME: This is really bad. It leads to problems removing
            # a tag from songs with different values since only the
            # first value gets noticed (since we safenicestr the displayed
            # value). However, without it, changing breaks from the
            # inverse problem: since the safenicestr'd orig_value isn't
            # in the file, the whole tag is changed, not just the one
            # value.
            orig_value = songinfo[comment].split("\n")
            value = songinfo[comment].safenicestr()
            edited = False
            edit = songinfo.can_change(comment)
            deleted = False
            for i, v in enumerate(value.split("\n")):
                model.append(row=[comment, v, edited, edit, deleted,
                                  orig_value[i]])

        buttonbox.set_sensitive(bool(songinfo.can_change()))
        for b in buttons: b.set_sensitive(False)
        add.set_sensitive(bool(songs))
