import os

import gtk

from quodlibet import util
from quodlibet.qltk import ErrorMessage
from quodlibet.plugins.songsmenu import SongsMenuPlugin

class Command(object):
    FILES, URIS, FOLDERS = range(3)
    def __init__(self, title, command, type):
        self.title = title
        self.command = command
        self.type = type

    def exists(self):
        return util.iscommand(self.command.split()[0])

    def run(self, songs):
        if self.type == self.FOLDERS:
            files = [song("~dirname") for song in songs]
        elif self.type == self.FILES:
            files = [song("~filename") for song in songs]
        elif self.type == self.URIS:
            files = [song("~uri") for song in songs]
        files = dict.fromkeys(files).keys()
        util.spawn(self.command.split() + files)

class SendTo(SongsMenuPlugin):
    PLUGIN_ID = 'SendTo'
    PLUGIN_NAME = _('Send To...')
    PLUGIN_DESC = _("Generic file-opening plugin.")
    PLUGIN_ICON = gtk.STOCK_EXECUTE
    PLUGIN_VERSION = '1'

    commands = [
        Command("K3B", "k3b --audiocd", Command.FILES),
        Command("Thunar", "thunar", Command.FOLDERS),
        ]

    def __init__(self, *args, **kwargs):
        super(SendTo, self).__init__(*args, **kwargs)
        self.command = None
        submenu = gtk.Menu()
        for command in self.commands:
            item = gtk.MenuItem(command.title)
            if not command.exists():
                item.set_sensitive(False)
            else:
                item.connect_object('activate', self.__set, command)
            submenu.append(item)
        if submenu.get_children():
            self.set_submenu(submenu)
        else:
            self.set_sensitive(False)

    def __set(self, command):
        self.command = command

    def plugin_songs(self, songs):
        if self.command:
            self.command.run(songs)
