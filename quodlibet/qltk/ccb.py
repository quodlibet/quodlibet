# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
import config

class ConfigCheckButton(gtk.CheckButton):
    """A CheckButton that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is *not* set to the current config value initially."""

    def __init__(self, label, section, option):
        gtk.CheckButton.__init__(self, label)
        self.connect('toggled', ConfigCheckButton.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())
