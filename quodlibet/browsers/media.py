# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import cPickle as pickle
import os

import gtk
import gtk.gdk as gdk
import pango

import config
import const
import qltk
import util
import devices

from browsers._base import Browser
from qltk.views import AllTreeView
from qltk.songsmenu import SongsMenu

DEVICES = os.path.join(const.USERDIR, "devices")

# I guess this will break pretty fast...
class CustomPaned(qltk.RHPaned):
    def pack2(self, child, resize=True, shrink=True):
        self.__songpane = child
        self.__vbox = vbox = gtk.VBox(spacing=8)
        super(CustomPaned, self).pack2(vbox)

        browser = self.get_children()[0]
        vbox.pack_start(browser.header, expand=False)
        vbox.pack_start(child)
        vbox.show_all()

    def remove(self, child):
        if child == self.__songpane:
            child = self.__vbox
            for i in child.get_children():
                child.remove(i)
        super(CustomPaned, self).remove(child)

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

class DeviceProperties(gtk.Dialog):
    __pos = 0

    def __init__(self, parent, device):
        self.__device = device

        super(DeviceProperties, self).__init__(
            _("Device Properties"), qltk.get_top_parent(parent),
            buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.set_default_size(400, -1)
        self.connect('response', lambda d, r: d.destroy())

        self.__table = table = gtk.Table()
        table.set_border_width(8)
        table.set_row_spacings(8)
        table.set_col_spacings(8)
        self.vbox.pack_start(table, expand=False)

        label = gtk.Label(device.__class__.name)
        label.set_alignment(0.0, 0.5)
        self.add_property(_("Device Type"), label)

        entry = gtk.Entry()
        entry.set_text(device.name)
        self.add_property(_("Name"), entry, 'name')

        device.Properties(self)
        self.show_all()

    def add_property(self, title, value, attr=None):
        label = gtk.Label()
        label.set_markup("<b>%s:</b>" % title)
        label.set_alignment(0.0, 0.5)
        self.__table.attach(
            label, 0, 1, self.__pos, self.__pos + 1, xoptions=gtk.FILL)

        if isinstance(value, gtk.Widget):
            widget = value
            if attr: widget.connect('changed', self.__changed, attr)
        else:
            widget = gtk.Label(value)
            widget.set_alignment(0.0, 0.5)
        self.__table.attach(widget, 1, 2, self.__pos, self.__pos + 1)
        self.__table.show_all()

        self.__pos += 1

    def add_separator(self):
        sep = gtk.HSeparator()
        self.__table.attach(sep, 0, 2, self.__pos, self.__pos + 1)
        self.__pos += 1

    def __changed(self, widget, attr):
        if isinstance(widget, gtk.Entry):
            value = widget.get_text()
        elif isinstance(widget, gtk.SpinButton):
            value = widget.get_value()
        else:
            raise NotImplementedError
        setattr(self.__device, attr, value)

class MediaDevices(Browser, gtk.VBox):
    __gsignals__ = Browser.__gsignals__

    __devices = gtk.ListStore(object, gdk.Pixbuf)

    expand = CustomPaned

    def cell_data(col, render, model, iter):
        device = model[iter][0]
        if device.is_connected():
            render.markup = "<b>%s</b>" % util.escape(device.name)
        else:
            render.markup = util.escape(device.name)
        render.set_property('markup', render.markup)
    cell_data = staticmethod(cell_data)

    def init(klass, watcher):
        try: devices = pickle.load(file(DEVICES, "rb"))
        except (AttributeError, EnvironmentError, EOFError): pass
        else:
            for device in devices:
                pixbuf = gdk.pixbuf_new_from_file_at_size(
                    device.icon, 24, 24)
                klass.__devices.append(row=[device, pixbuf])
    init = classmethod(init)

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
                self.__changed(self.__view.get_selection())
            else:
                qltk.ErrorMessage(
                    qltk.get_top_parent(self), _("Unable to eject device"),
                    _("Ejecting <b>%s</b> failed with the following error:\n\n"
                      + status)
                    % device.name).run()

    def __properties(self, device):
        DeviceProperties(self, device).run()
        self.__changed(self.__view.get_selection())

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
        menu = SongsMenu(watcher, songs, playlists=False, remove=False)
        menu.preseparate()

        delete = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        delete.connect_object( 'activate', model.remove, iter)
        menu.prepend(delete)

        if device.ejectable:
            eject = qltk.MenuItem(_("_Eject"), gtk.STOCK_DISCONNECT)
            eject.connect_object('activate', self.__eject, None)
            menu.prepend(eject)

        ren = qltk.MenuItem(_("_Rename"), gtk.STOCK_EDIT)
        keyval, mod = gtk.accelerator_parse("F2")
        ren.add_accelerator(
            'activate', self.accelerators, keyval, mod, gtk.ACCEL_VISIBLE)
        def rename(path):
            self.__render.set_property('editable', True)
            view.set_cursor(path, view.get_columns()[0], start_editing=True)
        ren.connect_object('activate', rename, model.get_path(iter))
        menu.prepend(ren)

        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        props.connect_object( 'activate', self.__properties, model[iter][0])
        menu.append(props)

        menu.show_all()
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True

    def __set_name(self, name):
        self.__device_name.set_markup(
            '<span size="x-large"><b>%s</b></span>' % name)

    def __changed(self, selection):
        model, iter = selection.get_selected()
        if iter:
            device = model[iter][0]
            self.__device_icon.set_from_file(device.icon)
            self.__set_name(device.name)

            songs = []
            if device.is_connected():
                self.__device_icon.set_sensitive(True)
                self.__eject_button.set_sensitive(device.ejectable)
                try: space, free = device.get_space()
                except NotImplementedError:
                    self.__device_space.set_text("")
                    self.__progress.hide()
                else:
                    used = space - free
                    fraction = float(used) / space

                    self.__device_space.set_markup(
                        "<b>%s</b> used, <b>%s</b> available" %
                            (util.format_size(used), util.format_size(free)))
                    self.__progress.set_fraction(fraction)
                    self.__progress.set_text("%.f%%" % round(fraction * 100))
                    self.__progress.show()

                try: songs = device.list(self, rescan=True)
                except NotImplementedError: pass
            else:
                self.__device_icon.set_sensitive(False)
                self.__device_name.set_markup(
                    self.__device_name.get_label() +
                    " (%s)" % _("Disconnected"))
                self.__device_space.set_text("")
                self.__progress.hide()
            self.emit('songs-selected', songs, True)

    def activate(self):
        self.__changed(self.__view.get_selection())

    def save(self):
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

    #def drop(self, songlist):
        #model, iter = self.__view.get_selection().get_selected()
        #if not iter:
            #songlist.set_songs([], True)
            #return

        #device = model[iter][0]
        #if not device.is_connected():
            #qltk.WarningMessage(
                #qltk.get_top_parent(self), _("Unable to copy songs"),
                #_("The device <b>%s</b> is not connected.") % device.name
            #).run()
            #songlist.set_songs([], True)
            #return

        #if not device.writable:
            #qltk.WarningMessage(
                #qltk.get_top_parent(self), _("Unable to copy songs"),
                #_("The device <b>%s</b> is read-only.") % device.name
            #).run()
            #songlist.set_songs([], True)
            #return

browsers = [(25, _("_Media Devices"), MediaDevices, True)]
