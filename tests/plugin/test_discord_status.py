# Copyright 2025 W. Connor Yates <self@wcyates.xyz>
#           2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from quodlibet.plugins import MissingModulePluginError
from tests.plugin import PluginTestCase


class TDiscordStatusMessage(PluginTestCase):
    def setUp(self):
        try:
            from quodlibet.ext.events.discord_status import (
                DiscordStatusMessage,
                DISCORD_RP_DETAILS_MAX_CODEUNITS,
                _utf16_cu_len,
            )
        except (ImportError, MissingModulePluginError):
            self.skipTest("Discord Status plugin (or dependencies) not installed")
        self.truncate_func = DiscordStatusMessage.truncate_unicode_text
        self.max_cu = DISCORD_RP_DETAILS_MAX_CODEUNITS
        self.len_func = _utf16_cu_len

    def test_unicode_truncation(self):
        # Truncation of simple strings to limit
        x_str = "x" * 145
        # Truncation of heterogeneous strings to limit
        het_str = ("f" * 30) + ("🇦🇶" * 30) + ("🏴‍☠️" * 30)

        assert self.len_func(self.truncate_func(x_str, self.max_cu)) <= self.max_cu
        assert self.len_func(self.truncate_func(het_str, self.max_cu)) <= self.max_cu

        # Truncation of strings less than the length of the given limit returns
        # the original string content
        sub_max_len = 56
        sub_max_str = "Q" * sub_max_len

        sub_max_res = self.truncate_func(sub_max_str, self.max_cu)
        assert self.len_func(sub_max_str) == self.len_func(sub_max_res)
        assert str(sub_max_str.encode("utf-16"), encoding="utf-16") == sub_max_res
