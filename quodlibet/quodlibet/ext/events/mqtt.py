# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

from quodlibet import _
from quodlibet.formats import AudioFile
from quodlibet.util import monospace, escape
from quodlibet.util.tags import _TAGS

_TOTAL_MQTT_ITEMS = 3

try:
    import paho.mqtt.client as mqtt
except ImportError:
    from quodlibet.plugins import MissingModulePluginException, \
        PluginNotSupportedError
    if os.name == "nt":
        raise PluginNotSupportedError
    raise MissingModulePluginException('paho-mqtt')

from gi.repository import Gtk

from quodlibet.pattern import Pattern
from quodlibet.qltk.entry import UndoEntry, ValidatingEntry
from quodlibet import qltk, app
from quodlibet.util import copool

from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins import PluginConfigMixin
from quodlibet.util.dprint import print_d, print_w, print_e
from quodlibet.qltk import Icons, ErrorMessage, Message

EXPAND = Gtk.AttachOptions.EXPAND
FILL = Gtk.AttachOptions.FILL


class Config(object):
    STATUS_SONGLESS = 'no_song_text', ""
    PAT_PLAYING = 'playing_pattern', "♫ <~artist~title> ♫"
    PAT_PAUSED = 'paused_pattern', "<~artist~title> [%s]" % _("paused")
    HOST = 'host', "localhost"
    PORT = 'port', 1883
    TOPIC = 'topic', 'quodlibet/now-playing'

_ACCEPTS_PATTERNS = (_("Accepts QL Patterns e.g. %s") %
                     monospace(escape('<~artist~title>')))


class MqttPublisherPlugin(EventPlugin, PluginConfigMixin):
    PLUGIN_ID = "MQTT Status"
    PLUGIN_NAME = _("MQTT Publisher")
    PLUGIN_DESC = _("Publishes status messages to an MQTT topic.")
    PLUGIN_ICON = Icons.FACE_SMILE

    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client receives a
        CONNACK response from the server."""
        print_d("Connected to %s at %s:%d with result code %s"
                % (self.topic, self.host, self.port, rc))

    def _subscribe(self, client, topic):
        result = client.subscribe(topic)
        if result != mqtt.MQTT_ERR_SUCCESS:
            print_w("Couldn't connect to %s (%s)" % (self.topic, result))

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        print_d("%s: %s" % (msg.topic, msg.payload))

    def _set_up_mqtt_client(self):
        self.client = client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(self.host, self.port, 60)
        # Uses Threading.Thread internally, so we don't have to...
        self.client.loop_start()

    def _set_status(self, text):
        print_d("Setting status to \"%s\"..." % text)
        result, mid = self.client.publish(self.topic, text)
        if result != mqtt.MQTT_ERR_SUCCESS:
            print_w("Couldn't publish to %s at %s:%d (%s)"
                    % (self.topic, self.host, self.port, result))
        self.status = text

    def plugin_on_song_started(self, song):
        self.song = song
        pat_str = self.config_get(*Config.PAT_PLAYING)
        pattern = Pattern(pat_str)
        status = (pattern.format(song) if song
                  else self.config_get(Config.STATUS_SONGLESS, ""))
        self._set_status(status)

    def plugin_on_paused(self):
        pat_str = self.config_get(*Config.PAT_PAUSED)
        pattern = Pattern(pat_str)
        self.status = pattern.format(self.song) if self.song else ""
        self._set_status(self.status)

    def plugin_on_unpaused(self):
        self.plugin_on_song_started(self.song)

    def disabled(self):
        if self.status:
            self._set_status(self.config_get(Config.STATUS_SONGLESS))
        self.client.disconnect()

    def enabled(self):
        self.song = None
        self.status = ''
        self.host = self.config_get(*Config.HOST)
        self.port = int(self.config_get(*Config.PORT))
        self.topic = self.config_get(*Config.TOPIC)
        self._set_up_mqtt_client()

    _CONFIG = [
        (_("Broker hostname"), Config.HOST, _("broker hostname / IP")),

        (_("Broker port"), Config.PORT, _("broker port")),

        (_("Topic"), Config.TOPIC, _("Topic")),

        (_("Playing Pattern"),
         Config.PAT_PLAYING,
         _("Status text when a song is started.") + _ACCEPTS_PATTERNS),

        (_("Paused Pattern"),
         Config.PAT_PAUSED,
         _("Text when a song is paused.") + _ACCEPTS_PATTERNS),

        (_("No-song Text"),
         Config.STATUS_SONGLESS,
         _("Plain text for when there is no current song"))
    ]

    @staticmethod
    def _is_pattern(cfg):
        return cfg[0] in (Config.PAT_PLAYING[0], Config.PAT_PAUSED[0])

    def PluginPreferences(self, parent):
        outer_vb = Gtk.VBox(spacing=12)

        t = self.config_table_for(self._CONFIG[:_TOTAL_MQTT_ITEMS])
        frame = qltk.Frame(_("MQTT Configuration"), child=t)
        outer_vb.pack_start(frame, False, True, 0)

        t = self.config_table_for(self._CONFIG[_TOTAL_MQTT_ITEMS:])
        frame = qltk.Frame(_("Status Text"), child=t)
        outer_vb.pack_start(frame, False, True, 0)

        return outer_vb

    def config_table_for(self, config_data):
        t = Gtk.Table(n_rows=2, n_columns=len(config_data))
        t.set_col_spacings(6)
        t.set_row_spacings(6)
        for i, (label, cfg, tooltip) in enumerate(config_data):
            entry = (ValidatingEntry(validator=validator)
                     if self._is_pattern(cfg) else UndoEntry())
            entry.set_text(str(self.config_get(*cfg)))
            entry.connect('changed', self._on_changed, cfg)
            lbl = Gtk.Label(label=label + ":")
            lbl.set_size_request(140, -1)
            lbl.set_alignment(xalign=0.0, yalign=0.5)
            entry.set_tooltip_markup(tooltip)
            lbl.set_mnemonic_widget(entry)
            t.attach(lbl, 0, 1, i, i + 1, xoptions=FILL)
            t.attach(entry, 1, 2, i, i + 1, xoptions=FILL | EXPAND)
        return t

    def _on_changed(self, entry, cfg):
        self.config_entry_changed(entry, cfg[0])
        if cfg in [Config.HOST, Config.PORT]:
            self.disabled()
            copool.add(self.try_connecting, funcid="connect", timeout=1000)

    def try_connecting(self):
        try:
            self.enabled()
            msg = (_("Connected to broker at %(host)s:%(port)d")
                   % {'host': self.host, 'port': self.port})
            Message(Gtk.MessageType.INFO, app.window, "Success", msg).run()
        except IOError as e:
            template = _("Couldn't connect to %(host)s:%(port)d (%(msg)s)")
            msg = template % {'host': self.host, 'port': self.port, 'msg': e}
            print_w(msg)
            ErrorMessage(app.window, _("Connection error"), msg).run()
        yield


def validator(pat):
    """Validates Patterns a bit.
    TODO: Extract to somewhere good - see #1983"""
    try:
        str = Pattern(pat).format(DUMMY_AF)
        return bool(str)
    except Exception as e:
        print_e("Problem with %s" % (pat,), e)


class FakeAudioFile(AudioFile):

    def __call__(self, *args, **kwargs):
        real = super(FakeAudioFile, self).__call__(*args, **kwargs)
        tag = args[0]
        return real or self.fake_value(tag)

    def get(self, key, default=None):
        if key not in self:
            return default or self.fake_value(key)
        return super(FakeAudioFile, self).get(key, default)

    def fake_value(self, key):
        if key.replace('~', '').replace('#', '') in _TAGS:
            if key.startswith('~#'):
                return 0
            elif key.startswith('~'):
                return "The %s" % key
        if key.startswith('~'):
            raise ValueError("Unknown tag %s" % key)
        return "The %s" % key


DUMMY_AF = FakeAudioFile({'~filename': '/dev/null'})
