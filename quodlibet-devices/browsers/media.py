# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import sys
import cPickle as pickle
from ConfigParser import RawConfigParser

import gtk
import gtk.gdk as gdk
import pango

import config
import const
import qltk
import util
import devices

from browsers._base import Browser
from formats._audio import AudioFile
from qltk.views import AllTreeView
from qltk.songsmenu import SongsMenu
from qltk.wlw import WaitLoadWindow
from qltk.browser import LibraryBrowser

DEVICES = os.path.join(const.USERDIR, "devices")

class DeviceProperties(gtk.Dialog):
    def __init__(self, parent, device):
        self.__device = device

        super(DeviceProperties, self).__init__(
            _("Device Properties"), qltk.get_top_parent(parent),
            buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.set_default_size(400, -1)
        self.connect('response', self.__close)

        table = gtk.Table()
        table.set_border_width(8)
        table.set_row_spacings(8)
        table.set_col_spacings(8)
        self.vbox.pack_start(table, expand=False)

        props = []
        props.append((_("Device Type:"), device.__class__.name, None))

        entry = gtk.Entry()
        entry.set_text(device.name)
        props.append((_("_Name:"), entry, 'name'))

        y = 0
        for title, value, attr in props + device.Properties():
            if title == None:
                self.__table.attach(gtk.HSeparator(), 0, 2, y, y + 1)
            else:
                if attr and isinstance(value, gtk.CheckButton):
                    value.set_label(title)
                    value.set_use_underline(True)
                    value.connect('toggled', self.__changed, attr)
                    table.attach(value, 0, 2, y, y + 1, xoptions=gtk.FILL)
                else:
                    label = gtk.Label()
                    label.set_markup("<b>%s</b>" % util.escape(title))
                    label.set_alignment(0.0, 0.5)
                    table.attach(label, 0, 1, y, y + 1, xoptions=gtk.FILL)
                    if attr and isinstance(value, gtk.Widget):
                        widget = value
                        label.set_mnemonic_widget(widget)
                        label.set_use_underline(True)
                        widget.connect('changed', self.__changed, attr)
                    else:
                        widget = gtk.Label(value)
                        widget.set_selectable(True)
                        widget.set_alignment(0.0, 0.5)
                    table.attach(widget, 1, 2, y, y + 1)
            y += 1
        self.show_all()

    def __changed(self, widget, attr):
        if isinstance(widget, gtk.Entry):
            value = widget.get_text()
        elif isinstance(widget, gtk.SpinButton):
            value = widget.get_value()
        elif isinstance(widget, gtk.CheckButton):
            value = widget.get_active()
        else:
            raise NotImplementedError
        setattr(self.__device, attr, value)

    def __close(self, dialog, response):
        dialog.destroy()
        MediaDevices.write()

class AddDeviceDialog(gtk.Dialog):
    def __init__(self, parent):
        super(AddDeviceDialog, self).__init__(
            _("Add Device"), qltk.get_top_parent(parent),
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_ADD, gtk.RESPONSE_OK))
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_default_size(400, 200)

        model = gtk.ListStore(object, gdk.Pixbuf)
        for device in devices.devices:
            pixbuf = gdk.pixbuf_new_from_file_at_size(
                device.icon, 24, 24)
            model.append(row=[device, pixbuf])

        swin = gtk.ScrolledWindow()
        swin.set_border_width(8)
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.vbox.pack_start(swin)

        self.__view = view = AllTreeView(model)
        view.set_rules_hint(True)
        view.set_headers_visible(False)
        view.connect('row-activated', self.__select)
        swin.add(view)

        col = gtk.TreeViewColumn("Devices")
        view.append_column(col)

        render = gtk.CellRendererPixbuf()
        col.pack_start(render, expand=False)
        col.add_attribute(render, 'pixbuf', 1)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        col.pack_start(render)
        col.set_cell_data_func(render, AddDeviceDialog.cell_data)

        self.show_all()

    def __select(self, view, path, col):
        self.response(gtk.RESPONSE_OK)

    def cell_data(col, render, model, iter):
        device = model[iter][0]
        render.markup = "<b>%s</b>\n%s" % (util.escape(device.name),
                                           util.escape(device.description))
        render.set_property('markup', render.markup)
    cell_data = staticmethod(cell_data)

    def run(self):
        response = super(AddDeviceDialog, self).run()
        model, iter = self.__view.get_selection().get_selected()
        self.destroy()
        if response == gtk.RESPONSE_OK and iter:
            return model[iter][0]
        else: return None

# A delete dialog for devices which implement a custom delete method.
# Adapted from qltk.DeleteDialog, which only works with files.
class DeleteDialog(gtk.Dialog):
    def __init__(self, parent, songs):
        super(DeleteDialog, self).__init__(
            _("Delete Songs"), qltk.get_top_parent(parent),
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                     gtk.STOCK_DELETE, gtk.RESPONSE_OK))
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_border_width(6)
        self.vbox.set_spacing(6)
        self.set_has_separator(False)
        self.action_area.set_border_width(0)
        self.set_resizable(False)

        hbox = gtk.HBox()
        hbox.set_border_width(6)
        i = gtk.Image()
        i.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        i.set_padding(12, 0)
        i.set_alignment(0.5, 0.0)
        hbox.pack_start(i, expand=False)
        vbox = gtk.VBox(spacing=6)

        base = "<b>%s</b>" % util.escape(songs[0]["title"])
        l = ngettext("Permanently delete this song?",
                     "Permanently delete these songs?", len(songs))
        exp = gtk.Expander()
        exp.set_use_markup(True)
        if len(songs) == 1:
            exp.set_label(base)
        else:
            exp.set_label(ngettext(
                "%(title)s and %(count)d more...",
                "%(title)s and %(count)d more...", len(songs)-1) %
                {'title': base, 'count': len(songs) - 1})

        lab = gtk.Label()
        lab.set_markup("<big><b>%s</b></big>" % l)
        lab.set_alignment(0.0, 0.5)
        vbox.pack_start(lab, expand=False)

        lab = gtk.Label("\n".join(
            [util.escape(song["title"]) for song in songs]))
        lab.set_alignment(0.1, 0.0)
        exp.add(gtk.ScrolledWindow())
        exp.child.add_with_viewport(lab)
        exp.child.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        exp.child.child.set_shadow_type(gtk.SHADOW_NONE)
        vbox.pack_start(exp)
        hbox.pack_start(vbox)
        self.vbox.pack_start(hbox)
        self.vbox.show_all()

    def run(self):
        response = super(DeleteDialog, self).run()
        self.destroy()
        if response == gtk.RESPONSE_OK: return True
        else: return False

# This will be included in SongsMenu
class Menu(gtk.Menu):
    def __init__(self, songs, watcher):
        super(Menu, self).__init__()
        for device, pixbuf in MediaDevices.devices():
            x, y = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)
            pixbuf = pixbuf.scale_simple(x, y, gtk.gdk.INTERP_BILINEAR)
            i = gtk.ImageMenuItem(device.name)
            i.set_sensitive(device.is_connected())
            i.get_image().set_from_pixbuf(pixbuf)
            i.connect_object(
                'activate', self.__copy_to_device, device, songs, watcher)
            self.append(i)

    def __copy_to_device(device, songs, watcher):
        win = LibraryBrowser(MediaDevices, watcher)
        win.browser.select(device)
        win.browser.dropped(win.songlist, songs)
    __copy_to_device = staticmethod(__copy_to_device)

# A custom paned to allow a browser-controlled widget above the songlist.
class CustomPaned(qltk.RHPaned):
    def pack2(self, child, resize=True, shrink=True):
        self.__songpane = child
        self.__vbox = vbox = gtk.VBox(spacing=8)
        super(CustomPaned, self).pack2(vbox)

        browser = self.get_children()[0]
        vbox.pack_start(browser.header, expand=False)
        vbox.pack_start(child)
        vbox.show()

    def remove(self, child):
        if child == self.__songpane:
            child = self.__vbox
            for i in child.get_children():
                child.remove(i)
        super(CustomPaned, self).remove(child)

class MediaDevices(Browser, gtk.VBox):
    __gsignals__ = Browser.__gsignals__

    __devices = gtk.ListStore(object, gdk.Pixbuf)

    expand = CustomPaned

    name = _("Media Devices")
    accelerated_name = _("_Media Devices")
    priority = 25

    def cell_data(col, render, model, iter):
        device = model[iter][0]
        if device.is_connected():
            render.markup = "<b>%s</b>" % util.escape(device.name)
        else:
            render.markup = util.escape(device.name)
        render.set_property('markup', render.markup)
    cell_data = staticmethod(cell_data)

    def init(klass, watcher):
        try:
            # Use a custom unpickler to avoid losing all devices
            # when one of them isn't importable anymore.
            def find_global(module, name):
                if module.split('.')[0] == 'devices': return devices.get(name)
                else:
                    # This is the find_class function from pickle.Unpickler
                    __import__(module)
                    mod = sys.modules[module]
                    klass = getattr(mod, name)
                    return klass
            pickler = pickle.Unpickler(file(DEVICES, "rb"))
            pickler.find_global = find_global
            devs = pickler.load()
        except IOError: pass
        else:
            for device in devs:
                if type(device) == devices._base.Device: continue
                pixbuf = gdk.pixbuf_new_from_file_at_size(
                    device.icon, 24, 24)
                klass.__devices.append(row=[device, pixbuf])
    init = classmethod(init)

    def devices(klass):
        return [(row[0], row[1]) for row in klass.__devices]
    devices = classmethod(devices)

    def write(klass):
        devices = [row[0] for row in klass.__devices]
        f = file(DEVICES, "wb")
        pickle.dump(devices, f, pickle.HIGHEST_PROTOCOL)
        f.close()
    write = classmethod(write)

    def __init__(self, watcher, player):
        super(MediaDevices, self).__init__(spacing=6)
        self.__main = bool(player)

        # Device list on the left pane
        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.pack_start(swin)

        self.__view = view = AllTreeView()
        view.set_reorderable(True)
        view.set_model(self.__devices)
        view.set_rules_hint(True)
        view.set_headers_visible(False)
        view.get_selection().set_mode(gtk.SELECTION_BROWSE)
        view.get_selection().connect('changed', self.__changed)
        view.connect('popup-menu', self.__popup_menu, watcher)
        if player: view.connect('row-activated', self.__play, player)
        swin.add(view)
        self.connect('destroy', lambda w: MediaDevices.write())

        col = gtk.TreeViewColumn("Devices")
        view.append_column(col)

        render = gtk.CellRendererPixbuf()
        col.pack_start(render, expand=False)
        col.add_attribute(render, 'pixbuf', 1)

        self.__render = render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        render.connect('edited', self.__edited)
        col.pack_start(render)
        col.set_cell_data_func(render, MediaDevices.cell_data)

        add = qltk.Button(_("_Add Device"), gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        add.connect('clicked', self.__add_device)
        self.pack_start(add, expand=False)

        self.__eject_button = eject = qltk.Button(
            _("_Eject"), gtk.STOCK_DISCONNECT, gtk.ICON_SIZE_MENU)
        eject.connect('clicked', self.__eject)
        eject.set_sensitive(False)
        self.pack_start(eject, expand=False)

        # Device info on the right pane
        self.header = table = gtk.Table()
        table.set_col_spacings(8)

        self.__device_icon = icon = gtk.Image()
        icon.set_size_request(48, 48)
        table.attach(icon, 0, 1, 0, 2, 0)

        self.__device_name = label = gtk.Label()
        label.set_alignment(0, 0)
        table.attach(label, 1, 3, 0, 1)

        self.__device_space = label = gtk.Label()
        label.set_alignment(0, 0.5)
        table.attach(label, 1, 2, 1, 2)

        self.__progress = progress = gtk.ProgressBar()
        progress.set_size_request(200, -1)
        table.attach(progress, 2, 3, 1, 2, xoptions=0, yoptions=0)

        self.accelerators = gtk.AccelGroup()
        keyval, mod = gtk.accelerator_parse('F2')
        self.accelerators.connect_group(keyval, mod, 0, self.__rename)

        self.show_all()

    def Menu(self, songs, songlist):
        items = []
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            device = model[iter][0]
            if device.delete:
                delete = gtk.ImageMenuItem(gtk.STOCK_DELETE)
                delete.connect_object('activate',
                    self.__delete, songlist, songs)
                items.append(delete)
        return items

    def __play(self, view, path, column, player):
        player.reset()

    def __add_device(self, button):
        device = AddDeviceDialog(self).run()
        if device is not None:
            device = device()
            pixbuf = gdk.pixbuf_new_from_file_at_size(
                device.icon, 24, 24)
            self.__devices.append(row=[device, pixbuf])
            self.__properties(device)
            MediaDevices.write()

    def __eject(self, button):
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            device = model[iter][0]
            status = device.eject()
            if status == True:
                self.__refresh(device)
            else:
                qltk.ErrorMessage(
                    self, _("Unable to eject device"),
                    _("Ejecting <b>%s</b> failed with the following error:\n\n"
                      + status) % device.name).run()

    def __properties(self, device):
        DeviceProperties(self, device).run()
        self.select(device)

    def __rename(self, group, acceleratable, keyval, modifier):
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            self.__render.set_property('editable', True)
            self.__view.set_cursor(model.get_path(iter),
                                   self.__view.get_columns()[0],
                                   start_editing=True)

    def __edited(self, render, path, newname):
        self.__devices[path][0].name = newname
        self.__set_name(newname)
        render.set_property('editable', False)

    def __popup_menu(self, view, watcher):
        model, iter = view.get_selection().get_selected()
        device = model[iter][0]

        if device.is_connected(): songs = device.list(self)
        else: songs = []
        menu = SongsMenu(watcher, songs, playlists=False,
                         devices=False, remove=False)

        menu.preseparate()

        delete = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        delete.connect_object('activate', model.remove, iter)
        menu.prepend(delete)

        ren = qltk.MenuItem(_("_Rename"), gtk.STOCK_EDIT)
        keyval, mod = gtk.accelerator_parse("F2")
        ren.add_accelerator(
            'activate', self.accelerators, keyval, mod, gtk.ACCEL_VISIBLE)
        def rename(path):
            self.__render.set_property('editable', True)
            view.set_cursor(path, view.get_columns()[0], start_editing=True)
        ren.connect_object('activate', rename, model.get_path(iter))
        menu.prepend(ren)

        menu.preseparate()

        eject = qltk.MenuItem(_("_Eject"), gtk.STOCK_DISCONNECT)
        eject.set_sensitive(device.eject and device.is_connected())
        eject.connect_object('activate', self.__eject, None)
        menu.prepend(eject)

        refresh = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        refresh.set_sensitive(device.is_connected())
        refresh.connect_object('activate', self.__refresh, device, True)
        menu.prepend(refresh)

        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        props.connect_object( 'activate', self.__properties, model[iter][0])
        menu.append(props)

        menu.show_all()
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True

    def select(self, device):
        for row in self.__devices:
            if row[0] == device: break
        else: return
        selection = self.__view.get_selection()
        selection.unselect_all()
        selection.select_iter(row.iter)

    def __set_name(self, name):
        self.__device_name.set_markup(
            '<span size="x-large"><b>%s</b></span>' % util.escape(name))

    def __changed(self, selection):
        model, iter = selection.get_selected()
        if iter:
            device = model[iter][0]
            if device: self.__refresh(device, rescan=True)

    def __refresh(self, device, rescan=False):
        self.__device_icon.set_from_file(device.icon)
        self.__set_name(device.name)

        songs = []
        if device.is_connected():
            self.header.show_all()
            self.__eject_button.set_sensitive(bool(device.eject))
            try: space, free = device.get_space()
            except NotImplementedError:
                self.__device_space.set_text("")
                self.__progress.hide()
            else:
                used = space - free
                fraction = float(used) / space

                self.__device_space.set_markup(
                    _("<b>%s</b> used, <b>%s</b> available") %
                        (util.format_size(used), util.format_size(free)))
                self.__progress.set_fraction(fraction)
                self.__progress.set_text("%.f%%" % round(fraction * 100))
                self.__progress.show()

            try: songs = device.list(self, rescan)
            except NotImplementedError: pass
        else:
            self.header.hide()
        self.emit('songs-selected', songs, True)

    def activate(self):
        self.__changed(self.__view.get_selection())

    def save(self):
        selection = self.__view.get_selection()
        model, iter = selection.get_selected()
        config.set('browsers', 'media', model[iter][0].name)

    def restore(self):
        try: name = config.get('browsers', 'media')
        except: pass
        else:
            for row in self.__devices:
                if row[0].name == name: break
            else: return
            selection = self.__view.get_selection()
            selection.unselect_all()
            selection.select_iter(row.iter)

    def __check_device(self, device, message):
        if not device.writable:
            qltk.WarningMessage(
                self, message,
                _("The device <b>%s</b> is read-only.")
                    % util.escape(device.name)
            ).run()
            return False

        if not device.is_connected():
            qltk.WarningMessage(
                self, message,
                _("The device <b>%s</b> is not connected.")
                    % util.escape(device.name)
            ).run()
            return False

        return True

    def dropped(self, songlist, songs):
        model, iter = self.__view.get_selection().get_selected()
        if not iter: return False

        device = model[iter][0]
        if not self.__check_device(device, _("Unable to copy songs")):
            return False

        wlw = WaitLoadWindow(
            self, len(songs),
            _("Copying %d songs to device <b>%s</b>\n\n"
              "Copying <b>%%s</b>") % (len(songs), util.escape(device.name)),
            "", 0)

        model = songlist.get_model()
        for song in songs:
            if wlw.step(util.escape(song["title"])):
                wlw.destroy()
                break
            while gtk.events_pending(): gtk.main_iteration()

            space, free = device.get_space()
            if free < os.path.getsize(song["~filename"]):
                wlw.destroy()
                qltk.WarningMessage(
                    self, _("Unable to copy song"),
                    _("The device has not enough free space for this song.")
                ).run()
                break

            status = device.copy(songlist, song)
            if isinstance(status, AudioFile):
                model.append([status])
            else:
                msg = _("The song <b>%s</b> could not be copied.")
                if type(status) == str:
                    msg += "\n\n"
                    msg += _("<b>Error:</b> %s") % util.escape(status)
                qltk.WarningMessage(
                    self, _("Unable to copy song"),
                    msg % util.escape(song["title"])).run()

        if device.cleanup: device.cleanup(wlw, 'copy')
        wlw.destroy()
        return True

    def __delete(self, songlist, songs):
        model, iter = self.__view.get_selection().get_selected()
        if not iter: return False

        device = model[iter][0]
        if not self.__check_device(device, _("Unable to delete songs")):
            return False

        if not DeleteDialog(self, songs).run(): return False

        wlw = WaitLoadWindow(
            self, len(songs),
            _("Deleting %d songs from device <b>%s</b>\n\n"
              "Deleting <b>%%s</b>") % (len(songs), util.escape(device.name)),
            "", 0)

        model = songlist.get_model()
        for song in songs:
            if wlw.step(util.escape(song["title"])):
                wlw.destroy()
                break

            status = device.delete(songlist, song)
            if status:
                model.remove(model.find(song))
            else:
                msg = _("The song <b>%s</b> could not be deleted.")
                if type(status) == str:
                    msg += "\n\n"
                    msg += _("<b>Error:</b> %s") % status
                qltk.WarningMessage(
                    self, _("Unable to delete song"),
                    msg % song["title"]).run()

        if device.cleanup: device.cleanup(wlw, 'delete')
        wlw.destroy()

browsers = [MediaDevices]
