# Copyright 2005-2006 Sergey Fedoseev <fedoseev.sergey@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from string import join
import gtk, config
import dbus

from plugins.events import EventPlugin
from parse import Pattern
from qltk import Frame

class GajimStatusMessage(EventPlugin):
    PLUGIN_ID = 'Gajim status message'
    PLUGIN_NAME = _('Gajim Status Message')
    PLUGIN_DESC = _("Change Gajim status message according to what "
                    "you are listening now.")
    PLUGIN_VERSION = '0.7.2'

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
            self.statuses = config.get('plugins', self.c_statuses)
        except:
            self.statuses = 'online chat'
            config.set('plugins', self.c_statuses, self.statuses)

        try:
            self.pattern = config.get('plugins', self.c_pattern)
        except:
            self.pattern = '<artist> - <title>'
            config.set('plugins', self.c_pattern, self.pattern)

        gtk.quit_add(0, self.quit)

        self.interface = dbus.Interface(
        dbus.SessionBus().get_object('org.gajim.dbus',
            '/org/gajim/dbus/RemoteObject'),
            'org.gajim.dbus.RemoteInterface')
    
        self.current = ''

    def quit(self):
        try: self.change_status(self.accounts, '')
        except dbus.DBusException: pass

    def change_status(self, accounts, status_message):
        if accounts == []:
            accounts = ['']
        for account in accounts:
            status = self.interface.get_status(account)
            if status in self.statuses:
                self.interface.change_status(status, status_message, account)

    def plugin_on_song_started(self, song):
        if song:
            self.current = Pattern(self.pattern) % song
        else:
            self.current = ''
        self.change_status(self.accounts, self.current)

    def plugin_on_paused(self):
        if self.paused and self.current != '':
            self.change_status(self.accounts, self.current+" [paused]")

    def plugin_on_unpaused(self):
        self.change_status(self.accounts, self.current)

    def accounts_e_changed(self, e):
        self.accounts = e.get_text().split()
        config.set('plugins', self.c_accounts, e.get_text())

    def pattern_e_changed(self, e):
        self.pattern = e.get_text()
        config.set('plugins', self.c_pattern, self.pattern)

    def c_changed(self, c):
        config.set('plugins', self.c_paused, str(c.get_active()))

    def b_changed(self, b):
        self.statuses = ''
        for b in self.list:
            if b.get_active():
                self.statuses = self.statuses + b.get_name()
        config.set('plugins', self.c_statuses, self.statuses)

    def PluginPreferences(self, parent):
        vb = gtk.VBox(spacing=3)
        tooltips = gtk.Tooltips().set_tip

        pattern_e = gtk.Entry()
        pattern_e.set_text(self.pattern)
        pattern_e.connect('changed', self.pattern_e_changed)

        hb = gtk.HBox(spacing=3)
        hb.set_border_width(6)
        accounts_e = gtk.Entry()
        accounts_e.set_text(join(self.accounts))
        accounts_e.connect('changed', self.accounts_e_changed)
        tooltips(accounts_e, "List accounts, separated by spaces, for "
                             "changing status message. If none is specified "
                             "status message of all accounts will be changed.")
        hb.pack_start(gtk.Label("Accounts:"), expand=False)
        hb.pack_start(accounts_e)

        c = gtk.CheckButton(label="Add '[paused]'")
        c.set_active(self.paused)
        c.connect('toggled', self.c_changed)
        tooltips(c, "If checked, '[paused]' will be added to "
                    "status message on pause.")

        table = gtk.Table()
        self.list = []
        i = 0
        j = 0
        for a in ['online', 'offline', 'chat', 'away', 'xa', 'invisible']:
            b = gtk.CheckButton(label=a)
            b.set_name(a)
            b.connect('toggled', self.b_changed)
            self.list.append(b)
            if a in self.statuses:
                b.set_active(True)
            table.attach(b, i, i+1, j, j+1)
            if i == 2:
                i = 0
                j += 1
            else:
                i += 1

        vb.pack_start(pattern_e)
        vb.pack_start(hb)
        vb.pack_start(c)
        vb.pack_start(Frame(label="Statuses for which status message\n"
                                  "will be changed"))
        vb.pack_start(table)

        return vb
