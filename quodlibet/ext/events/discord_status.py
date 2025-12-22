# discord_status: Set Discord status as current song.
#
# Copyright (c) 2022 Aditi K <105543244+teeleafs@users.noreply.github.com>
#               2025 W. Connor Yates <self@wcyates.xyz>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from time import time

from quodlibet import _, app
from quodlibet.plugins import PluginConfig, ConfProp
from quodlibet.plugins.events import EventPlugin
from quodlibet.pattern import Pattern
from quodlibet.formats import AudioFile

from gi.repository import Gtk

try:
    from pypresence import (
        Presence,
        InvalidID,
        DiscordNotFound,
        ActivityType,
        StatusDisplayType,
    )
except ImportError as err:
    from quodlibet.plugins import MissingModulePluginError

    raise MissingModulePluginError("pypresence") from err

try:
    import regex as re
except ImportError as err:
    from quodlibet.plugins import MissingModulePluginError

    raise MissingModulePluginError("regex") from err


# The below resources are from/uploaded-to the Discord Application portal.
DISCORD_APP_ID: str = "974521025356242984"
QL_LOGO_IMAGE_URL: str = "io-github-quodlibet-quodlibet"

QL_HOMEPAGE_LINK: str = "https://github.com/quodlibet/quodlibet"

DISCORD_RP_DETAILS_MIN_CODEUNITS: int = 2
DISCORD_RP_DETAILS_MAX_CODEUNITS: int = 128
DISCORD_RP_DETAILS_TRUNC_SUFFIX: str = "…"

GRAPHEME_PATTERN: re.Pattern = re.compile(r"\X", re.UNICODE)

VERSION: str = "1.0"

# Default Rich Presence status lines.
CONFIG_DEFAULT_RP_LINE1: str = "<artist> / <title>"
CONFIG_DEFAULT_RP_LINE2: str = "<album>"


class DiscordStatusConfig:
    _config: PluginConfig = PluginConfig(__name__)

    rp_line1: ConfProp = ConfProp(_config, "rp_line1", CONFIG_DEFAULT_RP_LINE1)
    rp_line2: ConfProp = ConfProp(_config, "rp_line2", CONFIG_DEFAULT_RP_LINE2)


discord_status_config: DiscordStatusConfig = DiscordStatusConfig()


def _utf16_cu_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


class DiscordStatusMessage(EventPlugin):
    PLUGIN_ID: str = _("Discord status message")
    PLUGIN_NAME: str = _("Discord Status Message")
    PLUGIN_DESC: str = _(
        "Change your Discord status message according to what "
        "you're currently listening to."
    )
    VERSION: str = VERSION

    def __init__(self):
        self.song: AudioFile | None = None
        self.details: str | None = None
        self.state: str | None = None
        self.discordrp: Presence | None = None

        try:
            self.discordrp: Presence | None = Presence(DISCORD_APP_ID, pipe=0)
            self.discordrp.connect()
        except (DiscordNotFound, ConnectionRefusedError):
            self.discordrp = None

    def update_discordrp(
        self, time_start: int | None = None, time_end: int | None = None
    ) -> None:
        """
        Update the Discord Rich Presence via the open Discord instance, if
        possible.

        :param time_start: Optional timestamp in seconds from Unix epoch
            representing the time the activity would have started from.
            In this plugin, it represents the position/progress of the song
            subtracted from the system time at the time that the song is
            unpaused.
            (i.e. the timestamp for when the song would have started from)
        :type time_start: int or None
        :param time_end: Optional timestamp in seconds from Unix epoch
            representing the time the activity would end by.
            In this plugin, it represents the remaining time of the song added
            to the system time at the time that the song is unpaused.
            (i.e. the timestamp for when the song would be expected to end)
        :type time_end: int or None
        :rtype: None
        """
        # The connection can be lost/closed if Discord is closed while the
        # plugin is active.
        # The connection can fail to be established when Discord is not open.
        if not self.discordrp:
            try:
                self.discordrp = Presence(DISCORD_APP_ID, pipe=0)
                self.discordrp.connect()
            except (DiscordNotFound, ConnectionRefusedError):
                self.discordrp = None
                return

        try:
            self.discordrp.update(
                name=app.name,
                details=self.details,
                state=self.state,
                start=time_start,
                end=time_end,
                status_display_type=StatusDisplayType.DETAILS,
                activity_type=ActivityType.LISTENING,
                large_image=QL_LOGO_IMAGE_URL,
                large_text=app.name,
            )
        except InvalidID:
            # XXX Discord was closed?
            self.discordrp = None

    @staticmethod
    def truncate_unicode_text(text: str, num: int) -> str:
        """
        Truncate a given unicode string to a string that is less than the given
        number of unicode code points that has an affixed truncation indicator
        character.
        In this plugin, this is used to ensure details and state strings are
        fit to publish to rich presence without error.

        :param text: A unicode string to truncate.
        :type text: str
        :param num: The number of unicode code points to truncate to.
        :type num: int
        :return: The truncated string in UTF-16.
        :rtype: str
        """
        # Return the same text [in UTF-16] if it doesn't need to be truncated
        if _utf16_cu_len(text) <= num:
            return str(text.encode("utf-16"), encoding="utf-16")

        # Cache the byte lengths of the truncation indicator/suffix
        trunc_char_len: int = _utf16_cu_len(DISCORD_RP_DETAILS_TRUNC_SUFFIX)

        # Factor in the code point length of the truncation character
        clen: int = trunc_char_len
        # Iterate through unicode graphemes and build the string to return
        x: str = ""
        for grapheme_match in GRAPHEME_PATTERN.finditer(text):
            # O(num) worst case
            grapheme: str = grapheme_match[0]
            # Append the number of code points for the grapheme
            # (bytes divided by 2)
            clen += _utf16_cu_len(grapheme)
            # Break when the total found code point length exceeds the limit
            if clen > num:
                break
            x += grapheme

        return str(
            (x + DISCORD_RP_DETAILS_TRUNC_SUFFIX).encode("utf-16"), encoding="utf-16"
        )

    def update_details(self):
        if self.song:
            details: str | None = Pattern(discord_status_config.rp_line1) % self.song
            state: str | None = Pattern(discord_status_config.rp_line2) % self.song

            # The details and state fields must be at least 2 UTF-16 code units
            # (DISCORD_RP_DETAILS_MIN_CODEUNITS) and less than or equal to 128
            # UTF-16 code units (DISCORD_RP_DETAILS_MAX_CODEUNITS), minus the
            # byte-order mark.
            # The use of `utf-16-le` encoding strips the BOM mark to get the
            # actual length of the string in pure code units.

            if _utf16_cu_len(details) < DISCORD_RP_DETAILS_MIN_CODEUNITS:
                details = None
            elif app.player.paused:
                pause_suffix: str = " " + _("(Paused)")
                details = self.truncate_unicode_text(
                    details,
                    DISCORD_RP_DETAILS_MAX_CODEUNITS - _utf16_cu_len(pause_suffix),
                )
                details += pause_suffix
            else:
                details = self.truncate_unicode_text(
                    details, DISCORD_RP_DETAILS_MAX_CODEUNITS
                )

            if _utf16_cu_len(state) < DISCORD_RP_DETAILS_MIN_CODEUNITS:
                state = None
            else:
                state = self.truncate_unicode_text(
                    state, DISCORD_RP_DETAILS_MAX_CODEUNITS
                )

            self.state = state
            self.details = details

    def handle_paused(self):
        if self.discordrp:
            if self.song is not None:
                self.update_details()
                self.update_discordrp()
            else:
                self.discordrp.clear()

    def handle_unpaused(self):
        if not self.song:
            self.song = app.player.song
        position: int = app.player.get_position() // 1000
        ts_now: int = round(time()) - position
        ts_before: int = ts_now
        ts_left: int = ts_now + self.song["~#length"]
        self.update_details()
        self.update_discordrp(time_start=ts_before, time_end=ts_left)

    def plugin_on_seek(self, song, msec):
        if not app.player.paused:
            position: int = app.player.get_position() // 1000
            ts_now: int = round(time()) - position
            ts_before: int = ts_now
            ts_left: int = ts_now + song["~#length"]
            self.update_discordrp(time_start=ts_before, time_end=ts_left)

    def plugin_on_song_started(self, song):
        self.song = song
        if song is not None:
            if not app.player.paused:
                # a new song is being played
                ts_now: int = round(time())
                ts_before: int = ts_now
                ts_left: int = ts_now + self.song["~#length"]

                self.update_details()
                self.update_discordrp(ts_before, ts_left)
            else:
                # this branch can execute when the app just launched
                # (i.e. song from previous session is loaded, but paused)
                self.handle_paused()
        else:
            # this branch can execute when the last song of the queue ends
            # (i.e. song is removed from player w/o a substitute)
            self.handle_paused()

    def plugin_on_paused(self):
        self.handle_paused()

    def plugin_on_unpaused(self):
        self.handle_unpaused()

    def enabled(self):
        if app.player.paused:
            self.handle_paused()
        else:
            self.handle_unpaused()

    def disabled(self):
        if self.discordrp:
            self.discordrp.clear()
            self.discordrp.close()
            self.discordrp = None
            self.song = None

    def PluginPreferences(self, parent):
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        def rp_line1_changed(entry):
            discord_status_config.rp_line1 = entry.get_text()
            if not app.player.paused:
                self.plugin_on_unpaused()

        def rp_line2_changed(entry):
            discord_status_config.rp_line2 = entry.get_text()
            if not app.player.paused:
                self.plugin_on_unpaused()

        status_line1_box = Gtk.Box(spacing=6)
        status_line1_box.set_border_width(3)

        status_line1: Gtk.Entry = Gtk.Entry()
        status_line1.set_text(discord_status_config.rp_line1)
        status_line1.connect("changed", rp_line1_changed)

        status_line1_box.prepend(Gtk.Label(label=_("Status Line #1")), False, True, 0)
        status_line1_box.prepend(status_line1)

        status_line2_box = Gtk.Box(spacing=3)
        status_line2_box.set_border_width(3)

        status_line2: Gtk.Entry = Gtk.Entry()
        status_line2.set_text(discord_status_config.rp_line2)
        status_line2.connect("changed", rp_line2_changed)

        status_line2_box.prepend(Gtk.Label(label=_("Status Line #2")), False, True, 0)
        status_line2_box.prepend(status_line2)

        vb.prepend(status_line1_box)
        vb.prepend(status_line2_box)

        return vb
