# -*- coding: utf-8 -*-
# Copyright 2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
import json
import pango
from quodlibet.qltk.data_editors import JSONBasedEditor

from quodlibet.util.dprint import print_w, print_d, print_e
from quodlibet import qltk
from quodlibet.const import USERDIR
from quodlibet.parse._pattern import Pattern
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import ErrorMessage
from quodlibet import util

import gtk
import os
from quodlibet.qltk.entry import UndoEntry, ValidatingEntry
from quodlibet.qltk.views import RCMHintedTreeView
import re
from quodlibet.util.json_data import JSONObject, JSONObjectDict


class Command(JSONObject):
    """
    Wraps an arbitrary shell command and its argument pattern.
    Serialises as JSON for some editability
    """

    @property
    def data(self):
        return JSONObject._data(self,
                ["name", "command", "pattern", "unique", "max_args"])

    def __init__(self, name=None, command=None, pattern="<~filename>",
                 unique=False, max_args=10000, warn_threshold=100):
        JSONObject.__init__(self, name)
        self.command = str(command or "")
        self.pattern = str(pattern)
        self.unique = bool(unique)
        self.max_args = max_args
        self.__pat = Pattern(self.pattern)
        self.warn_threshold = warn_threshold

    def run(self, songs):
        """
        Runs this command on `songs`,
        splitting into multiple calls if necessary
        """
        args = []
        for song in songs:
            arg = str(self.__pat.format(song))
            if not arg:
                print_w("Couldn't build shell command using \"%s\"."
                        "Check your pattern?" % self.pattern)
                break
            if not self.unique:
                args.append(arg)
            elif arg not in args:
                args.append(arg)
        max = int((self.max_args or 10000))
        com_words = self.command.split(" ")
        while args:
            print_d("Running %s with %d substituted arg(s) (of %d%s total)..."
                    % (self.command, min(max, len(args)), len(args),
                       " unique" if self.unique else ""))
            util.spawn(com_words + args[:max])
            args = args[max:]

    def __str__(self):
        return "Command= {command} {pattern}".format(**dict(self.data))


class CustomCommands(SongsMenuPlugin, PluginConfigMixin):

    PLUGIN_ICON = gtk.STOCK_OPEN
    PLUGIN_ID = "CustomCommands"
    PLUGIN_NAME = _("Custom Commands")
    PLUGIN_DESC = _("Runs custom commands (in batches if required) on songs "
                    "using any of their tags.")
    PLUGIN_VERSION = '1.0'

    _TUPLE_DEF = "\s*\('([^']*)'%s\)" % ("(?:,\s*'([^']*)')?" * 5)
    _TUPLE_REGEX = re.compile(_TUPLE_DEF)

    # Here are some starters...
    DEFAULT_COMS = [
        Command("Compress files", "file-roller -d", "<~filename>"),

        Command("K3B", "k3b --audiocd", "<~filename>"),

        Command("Browse folders (Thunar)", "thunar", "<~dirname>", unique=True,
            max_args=50, warn_threshold=20),

        Command(name="Flash notification",
            command="notify-send"
                    " -i /usr/share/icons/hicolor/scalable/apps/quodlibet.svg",
            pattern="<~rating> \"<title><version| (<version>)>\""
                    "<~people| by <~people>>"
                    "<album|, from <album><discnumber| : disk <discnumber>>"
                    "<~length| (<~length>)>",
            unique=False,
            max_args=1,
            warn_threshold=10),

        Command("Fix MP3 VBR with mp3val", "mp3val -f", "<~filename>",
                unique=True, max_args=1),
        ]
    COMS_FILE = os.path.join(USERDIR, 'lists', 'customcommands.json')

    def __set_pat(self, name):
        self.com_index = name

    def get_data(self, key):
        """Gets the pattern for a given key"""
        try:
            return self.commands[key]
        except (KeyError, TypeError):
            print_d("Invalid key %s" % key)
            return None

    @classmethod
    def edit_patterns(cls, button):
        cls.commands = cls._get_saved_searches()
        win = JSONBasedEditor(Command, cls.commands, filename=cls.COMS_FILE,
                              title=_("Edit Custom Commands"))
        win.show()


    @classmethod
    def PluginPreferences(cls, parent):
        hb = gtk.HBox(spacing=3)
        hb.set_border_width(0)

        button = qltk.Button(_("Edit Custom Commands") + "...", gtk.STOCK_EDIT)
        button.set_tooltip_markup(util.escape(_("Supports QL patterns\neg "
                                    "<tt>stat <~filename></tt>")))
        button.connect("clicked", cls.edit_patterns)
        hb.pack_start(button, expand=True)
        hb.show_all()
        return hb

    @classmethod
    def _get_saved_searches(cls):
        filename = cls.COMS_FILE
        print_d("Loading saved commands from '%s'..." % filename)
        coms = None
        try:
            with open(filename) as f:
                coms = JSONObjectDict.from_json(Command, f.read())
        except (IOError,ValueError), e:
            print_w("Couldn't open saved commands (%s)" % e)

        # Failing all else...
        if not coms:
            print_d("No commands found in %s. Using defaults." % filename)
            coms = dict([(c.name,c) for c in cls.DEFAULT_COMS])
        print_d("Commands = %s" % coms)
        return coms

    def __init__(self, *args, **kwargs):
        super(CustomCommands, self).__init__(*args, **kwargs)
        self.com_index = None
        self.unique_only = False
        self.commands = {}
        submenu = gtk.Menu()
        self.commands = self._get_saved_searches()
        for (name,c) in self.commands.items():
            item = gtk.MenuItem(name)
            item.connect_object('activate', self.__set_pat, name)
            submenu.append(item)
            # Add link to editor
        config = gtk.MenuItem(_("Edit Custom Commands") + "...")
        config.connect_object('activate', self.edit_patterns, config)
        submenu.append(gtk.SeparatorMenuItem())
        submenu.append(config)
        if submenu.get_children():
            self.set_submenu(submenu)
        else:
            self.set_sensitive(False)

    def plugin_songs(self, songs):
        # Check this is a launch, not a configure
        if self.com_index:
            com = self.get_data(self.com_index)
            print_d("Running %s" % com)
            try:
                com.run(songs)
            except Exception, err:
                print_e("Couldn't run command %s: %s %s at"
                        % (com.name, type(err), err))
                ErrorMessage(
                    self.plugin_window,
                    _("Unable to run custom command %s" %
                      util.escape(self.com_index)),
                    util.escape(str(err))).run()
