# Copyright 2015 Anton Shestakov
#           2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests.helper import ListWithUnused
from tests.plugin import PluginTestCase
from quodlibet.util.string.titlecase import human_title


class TPluginStyle(PluginTestCase):
    def conclude(self, fails):
        if not fails:
            return
        grouped = {}
        for f in fails:
            grouped.setdefault(f[2], []).append(f)
        lines = []
        for reason in grouped:
            lines.append("== " + reason + " ==")
            for f in grouped[reason]:
                plugin, string = f[:2]
                pclass = plugin.cls.__name__
                ppath = plugin.cls.__module__.rpartition(".plugins.")[2]
                lines.append(f"{ppath}.{pclass}: {string!r}")
        self.fail("One or more plugins did not pass:\n" + "\n".join(lines))

    def test_plugin_name(self):
        reason_absent = "plugin should have PLUGIN_NAME"
        reason_case = "PLUGIN_NAME should be in Title Case"

        ok_names = ListWithUnused(
            "Last.fm Cover Source", "Last.fm Sync", "Send to iFP",
            "This is a test")
        fails = []

        for _pid, plugin in self.plugins.items():
            if not hasattr(plugin.cls, "PLUGIN_NAME"):
                fails.append((plugin, None, reason_absent))
                continue
            name = plugin.cls.PLUGIN_NAME
            if name != human_title(name):
                if name not in ok_names:
                    fails.append((plugin, name, reason_case))

        ok_names.check_unused()
        self.conclude(fails)

    def test_plugin_desc(self):
        reason_absent = "plugin should have PLUGIN_DESC or PLUGIN_DESC_MARKUP"
        reason_dot = ("PLUGIN_DESC / PLUGIN_DESC_MARKUP "
                      "should be a full sentence and end with a '.'")

        skip_plugins = ListWithUnused("pickle_plugin")
        fails = []

        for pid, plugin in self.plugins.items():
            cls = plugin.cls
            if pid in skip_plugins:
                continue
            got = 0
            if hasattr(cls, "PLUGIN_DESC"):
                got += 1
                desc = cls.PLUGIN_DESC
                if not desc.endswith("."):
                    fails.append((plugin, desc, reason_dot))
                    continue
            if hasattr(cls, "PLUGIN_DESC_MARKUP"):
                got += 1
                desc = cls.PLUGIN_DESC_MARKUP
                if not desc.endswith("."):
                    fails.append((plugin, desc, reason_dot))
                    continue
            if not got:
                fails.append((plugin, None, reason_absent))
        skip_plugins.check_unused()
        self.conclude(fails)
