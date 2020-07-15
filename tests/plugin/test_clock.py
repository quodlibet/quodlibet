# Copyright 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from quodlibet.qltk.entry import ValidatingEntry
from tests.plugin import PluginTestCase
from quodlibet import config


class TClock(PluginTestCase):

    def setUp(self):
        config.init()
        self.mod = self.modules["Alarm Clock"]

    def tearDown(self):
        del self.mod
        config.quit()

    def test_alarm(self):
        def fake_entry(s):
            e = ValidatingEntry()
            e.set_text(str(s))
            return e
        plugin = self.mod.Alarm()
        plugin.enabled()
        entries = [fake_entry(s) for s in ['1', '3', '5'] + ['HH:MM'] * 4]
        plugin._entry_changed(entries)
        plugin._ready()

        self.failUnlessEqual(config.get('plugins', 'alarm_times'),
                             "1 3 5 HH:MM HH:MM HH:MM HH:MM")
        plugin.disabled()
