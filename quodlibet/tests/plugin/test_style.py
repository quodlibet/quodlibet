# Copyright 2015 Anton Shestakov
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests.helper import ListWithUnused as L
from tests.plugin import PluginTestCase
from quodlibet.util.string.titlecase import human_title


class TPluginStyle(PluginTestCase):
    def conclude(self, fails):
        def format_msg(f):
            return "%s: '%s' plugin (%s)" % (f[1], f[0].name, f[0].cls)
        if not fails:
            return
        grouped = {}
        for f in fails:
            grouped.setdefault(f[2], []).append(f)
        lines = []
        for reason in grouped:
            lines.append('== ' + reason + ' ==')
            for f in grouped[reason]:
                plugin, string = f[:2]
                pclass = plugin.cls.__name__
                ppath = plugin.cls.__module__.rpartition('.plugins.')[2]
                lines.append("%s.%s: %r" % (ppath, pclass, string))
        self.fail("One or more plugins did not pass:\n" + '\n'.join(lines))

    def test_plugin_name(self):
        REASON_ABSENT = "plugin should have PLUGIN_NAME"
        REASON_CASE = "PLUGIN_NAME should be in Title Case"

        ok_names = L(
            'Last.fm Cover Source', 'Last.fm Sync', 'Send to iFP',
            'This is a test')
        fails = []

        for pid, plugin in self.plugins.items():
            if not hasattr(plugin.cls, 'PLUGIN_NAME'):
                fails.append((plugin, None, REASON_ABSENT))
                continue
            name = plugin.cls.PLUGIN_NAME
            if name != human_title(name):
                if name not in ok_names:
                    fails.append((plugin, name, REASON_CASE))

        ok_names.check_unused()
        self.conclude(fails)

    def test_plugin_desc(self):
        REASON_ABSENT = "plugin should have PLUGIN_DESC"
        REASON_DOT = "PLUGIN_DESC should be a full sentence and end with a '.'"

        skip_plugins = L('pickle_plugin')
        fails = []

        for pid, plugin in self.plugins.items():
            if pid in skip_plugins:
                continue
            if not hasattr(plugin.cls, 'PLUGIN_DESC'):
                fails.append((plugin, None, REASON_ABSENT))
                continue
            desc = plugin.cls.PLUGIN_DESC
            if not desc.endswith('.'):
                fails.append((plugin, desc, REASON_DOT))

        skip_plugins.check_unused()
        self.conclude(fails)
