# Copyright 2024 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from quodlibet import get_base_dir, config
from quodlibet.plugins import PluginManager, PluginHandler
from tests.plugin import PLUGIN_DIRS


class EverythingHandler(PluginHandler):
    def plugin_handle(self, plugin):
        return True

    def plugin_enable(self, plugin):
        pass


def test_default_plugins_from_config():
    # Not the easiest route to test here
    config.init()
    folders = [os.path.join(get_base_dir(), "ext", kind) for kind in PLUGIN_DIRS]
    pm = PluginManager(folders)
    pm.rescan()
    # Need an active handler, otherwise no plugins will be enabled at all
    pm.register_handler(EverythingHandler())
    active = {p for p in pm.plugins if pm.enabled(p)}
    assert len(active) >= 2, f"Was expecting enough default plugins here: {active}"
    assert "Shuffle Playlist" in {a.name for a in active}
