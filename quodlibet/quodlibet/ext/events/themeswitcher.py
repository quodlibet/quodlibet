# -*- coding: utf-8 -*-
# Copyright 2011,2013 Christoph Reiter
#                2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import warnings
import os

from gi.repository import Gtk

from quodlibet import qltk
from quodlibet import config
from quodlibet.qltk import Icons
from quodlibet.util.path import get_home_dir
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.plugins.events import EventPlugin


def has_header_bar_prop():
    """if gtk is recent enough to have the property"""

    settings = Gtk.Settings.get_default()
    return hasattr(settings.props, "gtk_dialogs_use_header")


def set_header_bar(value):
    if not has_header_bar_prop():
        return
    settings = Gtk.Settings.get_default()
    settings.set_property('gtk-dialogs-use-header', value)


def get_header_bar():
    if not has_header_bar_prop():
        return False
    settings = Gtk.Settings.get_default()
    return settings.get_property('gtk-dialogs-use-header')


class ThemeSwitcher(EventPlugin):
    PLUGIN_ID = "Theme Switcher"
    PLUGIN_NAME = _("Theme Switcher")
    PLUGIN_DESC = _("Changes the active GTK+ theme.")
    PLUGIN_ICON = Icons.PREFERENCES_DESKTOP_THEME

    __enabled = False
    __defaults = False

    CONFIG_THEME = PLUGIN_ID + "_theme"
    CONFIG_DARK = PLUGIN_ID + "_prefer_dark"
    CONFIG_HEADER_BAR = PLUGIN_ID + "_prefer_header_bar"

    def __init_defaults(self):
        if self.__defaults:
            return
        self.__defaults = True

        settings = Gtk.Settings.get_default()
        self.__default_theme = settings.get_property('gtk-theme-name')
        self.__default_dark = settings.get_property(
            'gtk-application-prefer-dark-theme')
        self.__default_header_bar = get_header_bar()

    def PluginPreferences(self, *args):
        self.__init_defaults()

        hb = Gtk.HBox(spacing=6)
        label = Gtk.Label(label=_("_Theme:"))
        combo = Gtk.ComboBoxText()

        theme = config.get("plugins", self.CONFIG_THEME, None)

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
            "plugins", self.CONFIG_DARK,
            populate=True, default=self.__get_dark())

        def dark_cb(button):
            self.__set_dark(button.get_active())

        dark_button.connect('toggled', dark_cb)

        hb_button = ConfigCheckButton(
            _("Use header bars"),
            "plugins", self.CONFIG_HEADER_BAR,
            populate=True, default=self.__get_header_bar())

        def hb_cb(button):
            self.__set_header_bar(button.get_active())

        hb_button.connect('toggled', hb_cb)

        label.set_mnemonic_widget(combo)
        label.set_use_underline(True)
        hb.pack_start(label, False, True, 0)
        hb.pack_start(combo, False, True, 0)

        vbox = Gtk.VBox(spacing=6)
        vbox.pack_start(hb, False, True, 0)
        vbox.pack_start(dark_button, False, True, 0)
        vbox.pack_start(hb_button, False, True, 0)

        return qltk.Frame(_("Preferences"), child=vbox)

    def __changed(self, combo):
        index = combo.get_active()
        name = (index and combo.get_active_text()) or ""
        config.set("plugins", self.CONFIG_THEME, name)
        self.__set_theme(name)

    def __get_themes(self):
        # deprecated, but there is no public replacement
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            theme_dir = Gtk.rc_get_theme_dir()

        theme_dirs = [theme_dir, os.path.join(get_home_dir(), ".themes")]

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

    def __set_header_bar(self, value):
        if not self.__enabled:
            return
        if value is None:
            value = self.__default_header_bar
        set_header_bar(value)

    def __get_header_bar(self):
        return config.getboolean(
            "plugins", self.CONFIG_HEADER_BAR, self.__default_header_bar)

    def __get_dark(self):
        return config.getboolean(
            "plugins", self.CONFIG_DARK, self.__default_dark)

    def enabled(self):
        self.__enabled = True
        self.__init_defaults()

        theme = config.get("plugins", self.CONFIG_THEME, None)
        self.__set_theme(theme)

        self.__set_dark(self.__get_dark())
        self.__set_header_bar(self.__get_header_bar())

    def disabled(self):
        self.__set_theme(None)
        self.__set_dark(None)
        self.__set_header_bar(None)
        self.__enabled = False
