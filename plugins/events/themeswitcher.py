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
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.plugins.events import EventPlugin


class ThemeSwitcher(EventPlugin):
    PLUGIN_ID = "Theme Switcher"
    PLUGIN_NAME = _("Theme Switcher")
    PLUGIN_DESC = ("Change the active GTK+ theme.")

    __enabled = False

    CONFIG_THEME = PLUGIN_ID + "_theme"
    CONFIG_DARK = PLUGIN_ID + "_prefer_dark"

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

        dark_button = ConfigCheckButton(
            _("Prefer dark theme version"),
            "plugins", self.CONFIG_DARK)
        dark_button.set_active(
            config.getboolean("plugins", self.CONFIG_DARK, False))

        def dark_cb(button):
            self.__set_dark(button.get_active())

        dark_button.connect('toggled', dark_cb)

        label.set_mnemonic_widget(combo)
        label.set_use_underline(True)
        hb.pack_start(label, False, True, 0)
        hb.pack_start(combo, False, True, 0)

        vbox = Gtk.VBox(spacing=6)
        vbox.pack_start(hb, False, True, 0)
        vbox.pack_start(dark_button, False, True, 0)

        return qltk.Frame(_("Preferences"), child=vbox)

    def __changed(self, combo):
        index = combo.get_active()
        name = (index and combo.get_active_text()) or ""
        config.set("plugins", self.CONFIG_THEME, name)
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

    def __set_dark(self, value):
        if not self.__enabled:
            return
        settings = Gtk.Settings.get_default()
        if value is None:
            value = self.__default_dark
        settings.set_property('gtk-application-prefer-dark-theme', value)

    def enabled(self):
        self.__enabled = True

        settings = Gtk.Settings.get_default()
        self.__default_theme = settings.get_property('gtk-theme-name')
        self.__default_dark = settings.get_property(
            'gtk-application-prefer-dark-theme')

        theme = config.get("plugins", self.CONFIG_THEME, None)
        self.__set_theme(theme)

        is_dark = config.getboolean("plugins", self.CONFIG_DARK, False)
        self.__set_dark(is_dark)

    def disabled(self):
        self.__set_theme(None)
        self.__set_dark(None)
        self.__enabled = False
