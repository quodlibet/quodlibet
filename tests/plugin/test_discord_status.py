# Copyright 2025 W. Connor Yates <self@wcyates.xyz>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.ext.events.discord_status import (
    DiscordStatusMessage,
    DISCORD_RP_DETAILS_MAX_CODEUNITS,
    _utf16_cu_len,
)

from tests.plugin import PluginTestCase


class TDiscordStatusMessage(PluginTestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_unicode_truncation(self):
        truncate_func = DiscordStatusMessage.truncate_unicode_text
        D_MAX_CU = DISCORD_RP_DETAILS_MAX_CODEUNITS

        # Truncation of simple strings to limit
        x_str = "x" * 145
        # Truncation of heterogeneous strings to limit
        het_str = ("f" * 30) + ("🇦🇶" * 30) + ("🏴‍☠️" * 30)

        assert _utf16_cu_len(truncate_func(x_str, D_MAX_CU)) <= D_MAX_CU
        assert _utf16_cu_len(truncate_func(het_str, D_MAX_CU)) <= D_MAX_CU

        # Truncation of strings less than the length of the given limit returns
        # the original string content
        sub_max_len = 56
        sub_max_str = "Q" * sub_max_len

        sub_max_res = truncate_func(sub_max_str, D_MAX_CU)
        assert _utf16_cu_len(sub_max_str) == _utf16_cu_len(sub_max_res)
        assert str(sub_max_str.encode("utf-16"), encoding="utf-16") == sub_max_res
