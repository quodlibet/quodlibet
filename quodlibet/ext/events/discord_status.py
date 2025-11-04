# discord_status: Set Discord status as current song.
#
# Copyright (c) 2022 Aditi K <105543244+teeleafs@users.noreply.github.com>
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
            Presence, InvalidID, DiscordNotFound,
            ActivityType, StatusDisplayType
        )
except ImportError:
    from quodlibet.plugins import MissingModulePluginException
    raise MissingModulePluginException("pypresence")

# The below resources are from/uploaded-to the Discord Application portal.
DISCORD_APP_ID = '974521025356242984'
QL_LOGO_IMAGE_URL = "io-github-quodlibet-quodlibet"

QL_HOMEPAGE_LINK = "https://github.com/quodlibet/quodlibet"

VERSION = "1.0"

# Default Rich Presence status lines.
CONFIG_DEFAULT_RP_LINE1 = "<artist> / <title>"
CONFIG_DEFAULT_RP_LINE2 = "<album>"


class DiscordStatusConfig:
    _config = PluginConfig(__name__)

    rp_line1 = ConfProp(_config, "rp_line1", CONFIG_DEFAULT_RP_LINE1)
    rp_line2 = ConfProp(_config, "rp_line2", CONFIG_DEFAULT_RP_LINE2)


discord_status_config = DiscordStatusConfig()


class DiscordStatusMessage(EventPlugin):
    PLUGIN_ID = _("Discord status message")
    PLUGIN_NAME = _("Discord Status Message")
    PLUGIN_DESC = _("Change your Discord status message according to what "
                    "you're currently listening to.")
    VERSION = VERSION

    def __init__(self):
        self.song: AudioFile = None
        self.details: str = None
        self.state: str = None
        try:
            self.discordrp = Presence(DISCORD_APP_ID, pipe=0)
            self.discordrp.connect()
        except (DiscordNotFound, ConnectionRefusedError):
            self.discordrp = None

    def update_discordrp(self,
                         time_start: int | None = None,
                         time_end: int | None = None) -> None:
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
                #large_url=QL_HOMEPAGE_LINK,
                large_text=app.name,
            )
        except InvalidID:
            # XXX Discord was closed?
            self.discordrp = None

    def update_details(self):
        if self.song:
            details = Pattern(discord_status_config.rp_line1) % self.song
            state = Pattern(discord_status_config.rp_line2) % self.song

            # The details and state fields must be atleast 2 characters.
            if len(details) < 2:
                details = None
            elif app.player.paused:
                details = details + " " + _("(Paused)")

            if len(state) < 2:
                state = None

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
        position = app.player.get_position() / 1000
        ts_now = int(time()) - position
        ts_before = ts_now
        ts_left = ts_now + self.song["~#length"]
        self.update_details()
        self.update_discordrp(time_start=ts_before, time_end=ts_left)

    def plugin_on_seek(self, song: AudioFile, msec: int):
        if not app.player.paused:
            position = app.player.get_position() / 1000
            ts_now = round(time()) - position
            ts_before = ts_now
            ts_left = ts_now + self.song["~#length"]
            self.update_discordrp(time_start=ts_before, time_end=ts_left)

    def plugin_on_song_started(self, song: AudioFile):
        self.song = song
        if song is not None:
            if not app.player.paused:
                # a new song is being played
                ts_now = round(time())
                ts_before = ts_now
                ts_left = ts_now + self.song["~#length"]

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
        vb = Gtk.VBox(spacing=6)

        def rp_line1_changed(entry):
            discord_status_config.rp_line1 = entry.get_text()
            if not app.player.paused:
                self.plugin_on_unpaused()

        def rp_line2_changed(entry):
            discord_status_config.rp_line2 = entry.get_text()
            if not app.player.paused:
                self.plugin_on_unpaused()

        status_line1_box = Gtk.HBox(spacing=6)
        status_line1_box.set_border_width(3)

        status_line1 = Gtk.Entry()
        status_line1.set_text(discord_status_config.rp_line1)
        status_line1.connect('changed', rp_line1_changed)

        status_line1_box.pack_start(Gtk.Label(label=_("Status Line #1")),
                                    False, True, 0)
        status_line1_box.pack_start(status_line1, True, True, 0)

        status_line2_box = Gtk.HBox(spacing=3)
        status_line2_box.set_border_width(3)

        status_line2 = Gtk.Entry()
        status_line2.set_text(discord_status_config.rp_line2)
        status_line2.connect('changed', rp_line2_changed)

        status_line2_box.pack_start(Gtk.Label(label=_('Status Line #2')),
                                    False, True, 0)
        status_line2_box.pack_start(status_line2, True, True, 0)

        vb.pack_start(status_line1_box, True, True, 0)
        vb.pack_start(status_line2_box, True, True, 0)

        return vb
