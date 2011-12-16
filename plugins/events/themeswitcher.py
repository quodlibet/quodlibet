# Copyright 2011 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gtk

from quodlibet import qltk
from quodlibet import config
from quodlibet import const
from quodlibet.plugins.events import EventPlugin


class ThemeSwitcher(EventPlugin):
    PLUGIN_ID = "Theme Switcher"
    PLUGIN_NAME = _("Theme Switcher")
    PLUGIN_VERSION = "0.2"
    PLUGIN_DESC = ("Change the active GTK+ theme.")

    def PluginPreferences(self, *args):
        hb = gtk.HBox(spacing=6)
        label = gtk.Label(_("_Theme:"))
        combo = gtk.combo_box_new_text()

        try:
            theme = config.get("plugins", __name__)
        except config.error:
            theme = None

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
        hb.pack_start(label, expand=False)
        hb.pack_start(combo, expand=False)

        return qltk.Frame(_("Preferences"), child=hb)

    def __changed(self, combo):
        index = combo.get_active()
        name = (index and combo.get_active_text()) or ""
        config.set("plugins", __name__, name)
        self.__set_theme(name)

    def __get_themes(self):
        theme_dirs = [gtk.rc_get_theme_dir(),
                      os.path.join(const.HOME, ".themes")]

        themes = set()
        for theme_dir in theme_dirs:
            try:
                subdirs = os.listdir(theme_dir)
            except OSError:
                continue
            for dir_ in subdirs:
                rc = os.path.join(theme_dir, dir_, "gtk-2.0", "gtkrc")
                if os.path.isfile(rc):
                    themes.add(dir_)
        return themes

    def __set_theme(self, name):
        if not self.__enabled:
            return

        settings = gtk.settings_get_default()
        themes = self.__get_themes()
        name = ((name in themes) and name) or self.__default_theme

        settings.set_property('gtk-theme-name', name)

    def enabled(self):
        self.__enabled = True

        settings = gtk.settings_get_default()
        self.__default_theme = settings.get_property('gtk-theme-name')

        try: theme = config.get("plugins", __name__)
        except config.error: pass
        else: self.__set_theme(theme)

    def disabled(self):
        self.__set_theme(None)
        self.__enabled = False
