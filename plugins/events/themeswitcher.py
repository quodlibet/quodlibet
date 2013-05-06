# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk

from quodlibet import qltk
from quodlibet import config
from quodlibet import const
from quodlibet.plugins.events import EventPlugin


class ThemeSwitcher(EventPlugin):
    PLUGIN_ID = "Theme Switcher"
    PLUGIN_NAME = _("Theme Switcher")
    PLUGIN_DESC = ("Change the active GTK+ theme.")

    __enabled = False

    def PluginPreferences(self, *args):
        hb = Gtk.HBox(spacing=6)
        label = Gtk.Label(label=_("_Theme:"))
        combo = Gtk.ComboBoxText()

        theme = config.get("plugins", __name__, None)

        combo.append_text(_("Default Theme"))
        themes = self.__get_themes()
        select = 0
        for i, name in enumerate(sorted(themes)):
            combo.append_text(name)
            if name == theme:
                select = i + 1

        combo.set_active(select)
        combo.connect('changed', self.__changed)

        label.set_mnemonic_widget(combo)
        label.set_use_underline(True)
        hb.pack_start(label, False, True, 0)
        hb.pack_start(combo, False, True, 0)

        return qltk.Frame(_("Preferences"), child=hb)

    def __changed(self, combo):
        index = combo.get_active()
        name = (index and combo.get_active_text()) or ""
        config.set("plugins", __name__, name)
        self.__set_theme(name)

    def __get_themes(self):
        theme_dirs = [Gtk.rc_get_theme_dir(),
                      os.path.join(const.HOME, ".themes")]

        themes = set()
        for theme_dir in theme_dirs:
            try:
                subdirs = os.listdir(theme_dir)
            except OSError:
                continue
            for dir_ in subdirs:
                gtk_dir = os.path.join(theme_dir, dir_, "gtk-3.0")
                if os.path.isdir(gtk_dir):
                    themes.add(dir_)
        return themes

    def __set_theme(self, name):
        if not self.__enabled:
            return

        settings = Gtk.Settings.get_default()
        themes = self.__get_themes()
        name = ((name in themes) and name) or self.__default_theme

        settings.set_property('gtk-theme-name', name)

    def enabled(self):
        self.__enabled = True

        settings = Gtk.Settings.get_default()
        self.__default_theme = settings.get_property('gtk-theme-name')

        theme = config.get("plugins", __name__, None)

        self.__set_theme(theme)

    def disabled(self):
        self.__set_theme(None)
        self.__enabled = False
