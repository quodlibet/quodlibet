# Copyright 2005 Joe Wreschnig, Michael Urman
#        2012-22 Nick Boultbee
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
        super().__init__(label=label, use_underline=True)

        if default is None:
            default = config._config.defaults.getboolean(section, option, True)

        if populate:
            self.set_active(config.getboolean(section, option, default))
        if tooltip:
            self.set_tooltip_text(tooltip)
        self.connect('toggled', ConfigCheckButton.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())


class ConfigSwitch(Gtk.Box):
    """A Switch that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is initialised to the current config value if `populate` is set True."""

    def __init__(self, label, section, option, populate=False, tooltip=None,
                 default=None):
        super().__init__()
        self.label = Gtk.Label(label, use_underline=True)
        self.switch = Gtk.Switch()
        self.label.set_mnemonic_widget(self.switch)
        eb = Gtk.EventBox()
        eb.add(self.label)
        self.pack_start(eb, False, True, 0)
        self.pack_end(self.switch, False, True, 0)
        if default is None:
            default = config._config.defaults.getboolean(section, option, True)

        if populate:
            self.set_active(config.getboolean(section, option, default))
        if tooltip:
            self.label.set_tooltip_text(tooltip)
        self.switch.connect('notify::active', self.__activated, section, option)
        eb.connect('button_press_event',
                   lambda *_: self.switch.set_state(not self.switch.get_state()))

    def set_active(self, value: bool):
        self.switch.set_active(value)

    def get_active(self) -> bool:
        return self.switch.get_active()

    def connect(self, *args, **kwargs):
        self.switch.connect(*args, **kwargs)

    def __activated(self, switch, state, section, option):
        config.set(section, option, str(switch.get_active()).lower())


class ConfigCheckMenuItem(Gtk.CheckMenuItem):
    """A CheckMenuItem that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is initialised to the current config value if `populate` is set True."""

    def __init__(self, label, section, option, populate=False, default=False):
        super().__init__(
            label=label, use_underline=True)
        if populate:
            self.set_active(config.getboolean(section, option, default))
        self.connect('toggled', ConfigCheckMenuItem.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())
