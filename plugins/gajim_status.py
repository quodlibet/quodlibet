# Copyright 2005 Sergey Fedoseev <fedoseev.sergey@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from os import system, popen
from string import join
from qltk import Frame
import gtk, config

class GajimStatusMessage(object):
    PLUGIN_NAME = 'Gajim status message'
    PLUGIN_DESC = 'Change Gajim status message according to what you are listening now.'
    PLUGIN_VERSION = '0.3'

    c_a = __name__+'_accounts'
    c_p = __name__+'_paused'
    c_s = __name__+'_statuses'

    def __init__(self):
        self.gajim_accounts = [x.strip() for x in popen("gajim-remote list_accounts").readlines()]
        try:
            self.accounts = self.check_accounts(config.get('plugins', self.c_a))
        except:
            self.accounts = []
        config.set('plugins', self.c_a, join(self.accounts))
        try:
            config.getboolean('plugins', self.c_p)
        except:
            config.set('plugins', self.c_p, 'True')
        try:
            config.get('plugins', self.c_s)
        except:
            config.set('plugins', self.c_s, 'online chat')

        gtk.quit_add(0, self.quit)

    def quit(self):
        self.change_status(self.accounts, '')

    def change_status(self, accounts, status):
        if accounts == []:
            accounts = self.gajim_accounts
        for account in accounts:
            t = popen("gajim-remote get_status "+account).readline().strip()
            if t in config.get('plugins', self.c_s):
                system("gajim-remote change_status "+t+" \'"+status+"\' "+account)

    def plugin_on_song_started(self, song):
        if song == None:
           self.change_status(self.accounts, '')
        else:
            try:
                self.current = "Listening: "+song.__getitem__('artist')+" - "+song.__getitem__('title')
            except KeyError:
                self.current = ''
            self.change_status(self.accounts, self.current)

    def plugin_on_paused(self):
        if config.getboolean('plugins', self.c_p) and self.current != '':
            self.change_status(self.accounts, self.current+" [paused]")

    def plugin_on_unpaused(self):
        self.change_status(self.accounts, self.current)

    def e_changed(self, e):
        self.accounts = self.check_accounts(e.get_text())
        config.set('plugins', self.c_a, join(self.accounts))

    def c_changed(self, c):
        config.set('plugins', self.c_p, str(c.get_active()))

    def b_changed(self, b):
        statuses = ''
        for b in self.list:
            if b.get_active():
                statuses = statuses + b.get_name()
        config.set('plugins', self.c_s, statuses)

    def check_accounts(self, accounts):
        if self.gajim_accounts == []:
            return accounts.split()
        else:
            checked = []
            for a in accounts.split():
                if a in self.gajim_accounts:
                    checked.append(a)
                else:
                    print("Gajim hasn't account "+a)
            return checked

    def PluginPreferences(self, parent):
        vb = gtk.VBox(spacing=3)
        tooltips = gtk.Tooltips().set_tip

        hb = gtk.HBox(spacing=3)
        hb.set_border_width(6)
        e = gtk.Entry()
        e.set_text(config.get('plugins', self.c_a))
        e.connect('changed', self.e_changed)
        tooltips(e, "List accounts, separated by spaces, for changing status message. If none is specified status message of all accounts will be changed.")
        hb.pack_start(gtk.Label("Accounts:"), expand=False)
        hb.pack_start(e)

        c = gtk.CheckButton(label="Add \'[paused]\'")
        c.set_active(config.getboolean('plugins', self.c_p))
        c.connect('toggled', self.c_changed)
        tooltips(c, "If checked, \'[paused]\' will be added to status message on pause.")

        table = gtk.Table()
        self.list = []
        i = 0
        j = 0
        for a in ['online', 'offline', 'chat', 'away', 'xa', 'invisible']:
            b = gtk.CheckButton(label=a)
            b.set_name(a)
            b.connect('toggled', self.b_changed)
            self.list.append(b)
            if a in config.get('plugins', self.c_s):
                b.set_active(True)
            table.attach(b, i, i+1, j, j+1)
            if i == 2:
                i = 0
                j += 1
            else:
                i += 1

        vb.pack_start(hb)
        vb.pack_start(c)
        vb.pack_start(Frame(label="Statuses for which status message\nwill be changed", bold=True))
        vb.pack_start(table)

        return vb
