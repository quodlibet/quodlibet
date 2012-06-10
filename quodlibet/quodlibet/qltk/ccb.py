# Copyright 2005 Joe Wreschnig, Michael Urman
#           2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet import config

class ConfigCheckButton(gtk.CheckButton):
    """A CheckButton that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is initialised to the current config value if `populate` is set True."""

    def __init__(self, label, section, option, populate=False):
        super(ConfigCheckButton, self).__init__(label)
        if populate: self.set_active(config.getboolean(section, option))
        self.connect('toggled', ConfigCheckButton.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())

class ConfigCheckMenuItem(gtk.CheckMenuItem):
    """A CheckMenuItem that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is initialised to the current config value if `populate` is set True."""

    def __init__(self, label, section, option, populate=False):
        super(ConfigCheckMenuItem, self).__init__(label)
        if populate: self.set_active(config.getboolean(section, option))
        self.connect('toggled', ConfigCheckMenuItem.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())

