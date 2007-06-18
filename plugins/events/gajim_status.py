# Copyright 2005-2006 Sergey Fedoseev <fedoseev.sergey@gmail.com>
# Copyright 2007 Simon Morgan <zen84964@zen.co.uk>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from string import join
import gtk
import dbus

from plugins.events import EventPlugin
from parse import Pattern
from qltk import Frame
import config

class GajimStatusMessage(EventPlugin):
    PLUGIN_ID = 'Gajim status message'
    PLUGIN_NAME = _('Gajim Status Message')
    PLUGIN_DESC = _("Change Gajim status message according to what "
                    "you are currently listening to.")
    PLUGIN_VERSION = '0.7.4'

    c_accounts = __name__+'_accounts'
    c_paused = __name__+'_paused'
    c_statuses = __name__+'_statuses'
    c_pattern = __name__+'_pattern'

    def __init__(self):
        try:
            self.accounts = config.get('plugins', self.c_accounts).split()
        except:
            self.accounts = []
            config.set('plugins', self.c_accounts, '')

        try:
            self.paused = config.getboolean('plugins', self.c_paused)
        except:
            self.paused = True
            config.set('plugins', self.c_paused, 'True')

        try:
            self.statuses = config.get('plugins', self.c_statuses).split()
        except:
            self.statuses = ['online', 'chat']
            config.set('plugins', self.c_statuses, join(self.statuses))

        try:
            self.pattern = config.get('plugins', self.c_pattern)
        except:
            self.pattern = '<artist> - <title>'
            config.set('plugins', self.c_pattern, self.pattern)

        gtk.quit_add(0, self.quit)

        self.interface = None
        self.current = ''

    def quit(self):
        if self.current != '':
            self.change_status(self.accounts, '')

    def change_status(self, enabled_accounts, status_message):
        if not self.interface:
            try:
                bus = dbus.SessionBus()
                obj = bus.get_object(
                    'org.gajim.dbus', '/org/gajim/dbus/RemoteObject')
                self.interface = dbus.Interface(
                obj, 'org.gajim.dbus.RemoteInterface')
            except dbus.DBusException:
                self.interface = None

        if self.interface:
            try:
                for account in self.interface.list_accounts():
                    status = self.interface.get_status(account)
                    if enabled_accounts != [] and account not in enabled_accounts:
                        continue
                    if status in self.statuses:
                        self.interface.change_status(status, status_message, account)
            except dbus.DBusException:
                self.interface = None

    def plugin_on_song_started(self, song):
        if song:
            self.current = Pattern(self.pattern) % song
        else:
            self.current = ''
        self.change_status(self.accounts, self.current)

    def plugin_on_paused(self):
        if self.paused and self.current != '':
            self.change_status(self.accounts, self.current + " [paused]")

    def plugin_on_unpaused(self):
        self.change_status(self.accounts, self.current)

    def accounts_changed(self, entry):
        self.accounts = entry.get_text().split()
        config.set('plugins', self.c_accounts, entry.get_text())

    def pattern_changed(self, entry):
        self.pattern = entry.get_text()
        config.set('plugins', self.c_pattern, self.pattern)

    def paused_changed(self, c):
        config.set('plugins', self.c_paused, str(c.get_active()))

    def statuses_changed(self, b):
        if b.get_active() and b.get_name() not in self.statuses:
            self.statuses.append(b.get_name())
        elif b.get_active() == False and b.get_name() in self.statuses:
            self.statuses.remove(b.get_name())
        config.set('plugins', self.c_statuses, join(self.statuses))

    def PluginPreferences(self, parent):
        vb = gtk.VBox(spacing = 3)
        tooltips = gtk.Tooltips().set_tip

        pattern_box = gtk.HBox(spacing = 3)
        pattern_box.set_border_width(3)
        pattern = gtk.Entry()
        pattern.set_text(self.pattern)
        pattern.connect('changed', self.pattern_changed)
        pattern_box.pack_start(gtk.Label("Pattern:"), expand = False)
        pattern_box.pack_start(pattern)

        accounts_box = gtk.HBox(spacing = 3)
        accounts_box.set_border_width(3)
        accounts = gtk.Entry()
        accounts.set_text(join(self.accounts))
        accounts.connect('changed', self.accounts_changed)
        tooltips(accounts, "List accounts, separated by spaces, for "
                             "changing status message. If none are specified, "
                             "status message of all accounts will be changed.")
        accounts_box.pack_start(gtk.Label("Accounts:"), expand = False)
        accounts_box.pack_start(accounts)

        c = gtk.CheckButton(label="Add '[paused]'")
        c.set_active(self.paused)
        c.connect('toggled', self.paused_changed)
        tooltips(c, "If checked, '[paused]' will be added to "
                    "status message on pause.")

        table = gtk.Table()
        self.list = []
        i = 0
        j = 0
        for status in ['online', 'offline', 'chat', 'away', 'xa', 'invisible']:
            button = gtk.CheckButton(label=status)
            button.set_name(status)
            if status in self.statuses:
                button.set_active(True)
            button.connect('toggled', self.statuses_changed)
            self.list.append(button)
            table.attach(button, i, i+1, j, j+1)
            if i == 2:
                i = 0
                j += 1
            else:
                i += 1

        vb.pack_start(pattern_box)
        vb.pack_start(accounts_box)
        vb.pack_start(c)
        vb.pack_start(Frame(label="Statuses for which status message\n"
                                  "will be changed"))
        vb.pack_start(table)

        return vb
