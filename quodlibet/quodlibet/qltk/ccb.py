# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#           2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import config


class ConfigCheckButton(Gtk.CheckButton):
    """A CheckButton that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is initialised to the current config value if `populate` is set True."""

    def __init__(self, label, section, option, populate=False, tooltip=None,
                 default=None):
        super(ConfigCheckButton, self).__init__(label=label,
                                                use_underline=True)

        if default is None:
            default = config._config.defaults.getboolean(section, option, True)

        if populate:
            self.set_active(config.getboolean(section, option, default))
        if tooltip:
            self.set_tooltip_text(tooltip)
        self.connect('toggled', ConfigCheckButton.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())


class ConfigCheckMenuItem(Gtk.CheckMenuItem):
    """A CheckMenuItem that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is initialised to the current config value if `populate` is set True."""

    def __init__(self, label, section, option, populate=False, default=False):
        super(ConfigCheckMenuItem, self).__init__(
            label=label, use_underline=True)
        if populate:
            self.set_active(config.getboolean(section, option, default))
        self.connect('toggled', ConfigCheckMenuItem.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())
