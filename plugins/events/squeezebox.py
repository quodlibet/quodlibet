# Copyright 2011 Nick Boultbee
#
# Inspired in parts by PySqueezeCenter (c) 2010 JingleManSweep
# SqueezeCenter is copyright Logitech
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#

from quodlibet import player, qltk, config, widgets, print_w, print_d
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.msg import Message
from telnetlib import Telnet
import gtk
import socket
import urllib
#import pygtk
#pygtk.require('2.0')
_DEBUG = False


class SqueezeboxPlayerSettings(dict):
    """Encapsulates player settings"""
    def __str__(self):
        try:
            return _("Squeezebox server at %s:%d") % (
                self['hostname'], int(self['port']))
        except KeyError:
            return _("unidentified Squeezebox server")


class SqueezeboxException(Exception):
    """Errors communicating with the Squeezebox"""


class SqueezeboxServer:
    """Encapsulates access to a Squeezebox player via a squeezecenter server"""

    _TIMEOUT = 10
    _SYNC_FUDGE_MS = 750    
    telnet = None
    is_connected = False
    current_player = 0
    players = []
    config = SqueezeboxPlayerSettings()

    def __init__(self, hostname="localhost", port=9090, user="", password="",
        library_dir='', current_player = 0 ):
        if hostname:
            try:
                self.config = SqueezeboxPlayerSettings(locals())
                del self.config["self"]
                if _DEBUG: print "Trying %s..." % self.config
                self.telnet = Telnet(hostname, port, self._TIMEOUT)
            except socket.error:
                print_w(_("Couldn't talk to %s") % (self.config))
            else:
                result = self.request("login %s %s" % (user, password))
                if (result != 6 * "*"):
                    raise SqueezeboxException(
                        "Couldn't log in to squeezebox: response was '%s'"
                         % result)
                self.is_connected = True
                print_d("Connected to Squeezebox Server!")
                self.get_players()

    def get_library_dir(self):
        return self.config['library_dir']

    def request(self, line, raw=False):
        """
        Send a request to the server, if connected, and return its response
        """
        line = line.strip()

        if not (self.is_connected or line.split()[0] == 'login'):
            print_d("Can't do '%s' - not connected" % line.split()[0])
            return None

        if _DEBUG: print "Sending:  \"%s\"" % line
        self.telnet.write(line + "\n")
        raw_response = self.telnet.read_until("\n").strip()
        response = raw_response if raw else urllib.unquote(raw_response)
        if _DEBUG: print "Response: \"%s\"" % (response)
        return response[len(line) - 1:] if line.endswith("?")\
            else response[len(line) + 1:]

    def get_players(self):
        pairs = self.request("players 0 99", True).split(" ")

        def demunge(string):
            str = urllib.unquote(string)
            cpos = str.index(":")
            return (str[0:cpos], str[cpos + 1:])

        # Do a meaningful URL-unescaping and tuplification for all values
        pairs = map(demunge, pairs)

        # First element is always count
        count = int(pairs.pop(0)[1])
        self.players = []
        for pair in pairs:
            if pair[0] == "playerindex":
                playerindex = int(pair[1])
                self.players.append(SqueezeboxPlayerSettings())
            else:
                self.players[playerindex][pair[0]] = pair[1]
        if _DEBUG:
            print "Found %d player(s): %s" % (len(self.players), self.players)
        assert (count == len(self.players))
        return self.players

    def player_request(self, line):
        try:
            return self.request(
                "%s %s" % (self.players[self.current_player]["playerid"], line))
        except IndexError:
            return None

    def get_version(self):
        if self.is_connected:
            return self.request("version ?")
        else:
            return "(not connected)"

    def play(self):
        self.player_request("play")

    def is_stopped(self):
        """Returns whether the player is in any sort of non-playing mode"""
        response = self.player_request("mode ?")
        return "play" != response

    def playlist_play(self, path):
        """Play song immediately"""
        self.player_request("playlist play %s" % (urllib.quote(path)))

    def change_song(self, path):
        """Queue up a song"""
        self.player_request("playlist clear")
        self.player_request("playlist insert %s" % (urllib.quote(path)))

    def seek_to(self, seconds):
        self.player_request("time %d" % (seconds))

    def pause(self):
        self.player_request("pause 1")

    def unpause(self):
        if self.is_stopped(): self.play()
        ms = player.playlist.get_position()
        self.seek_to((ms + self._SYNC_FUDGE_MS) / 1000)
        #self.player_request("pause 0")

    def stop(self):
        self.player_request("stop")


class GetPlayerDialog(gtk.Dialog):
    def __init__(self, parent, players):
        title = _("Choose Squeezebox player")
        super(GetPlayerDialog, self).__init__(title, parent)
        self.set_border_width(6)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)

        box = gtk.VBox(spacing=6)
        label = gtk.Label(_("Found Squeezebox server. Please choose the player"))
        box.set_border_width(6)
        label.set_line_wrap(True)
        label.set_justify(gtk.JUSTIFY_CENTER)
        box.pack_start(label)

        player_combo = gtk.combo_box_new_text()
        for player in players:
            player_combo.append_text(player["name"])
        player_combo.set_active(0)
        self._val = player_combo
        box.pack_start(self._val)
        self.vbox.pack_start(box)
        self.child.show_all()

    def run(self, text=""):
        self.show()
        #self._val.set_activates_default(True)
        self._val.grab_focus()
        resp = super(GetPlayerDialog, self).run()
        if resp == gtk.RESPONSE_OK:
            value = self._val.get_active()
        else: value = None
        self.destroy()
        return value


class SqueezeboxSyncPlugin(EventPlugin):
    PLUGIN_ID = 'Squeezebox Output'
    PLUGIN_NAME = _('Squeezebox Sync')
    PLUGIN_DESC = _("Make Logitech Squeezebox mirror QL output, "
        "provided both read from an identical library")
    PLUGIN_ICON = gtk.STOCK_MEDIA_PLAY
    PLUGIN_VERSION = '0.1'
    server = None

    def __init__(self):
        super(EventPlugin, self)

    def cfg_get(self, name, default=None):
        try:
            return config.get("plugins", "squeezebox_" + name)
        except config.error:
            # Set the missing config
            config.set("plugins", "squeezebox_" + name, default)
            return default

    def cfg_set(self, name, value):
        try:
            config.set("plugins", "squeezebox_" + name, value)
        except:
            pass

    def check_settings(self, button):
        self.init_server()
        if self.server.is_connected:
            #dialog = Message(gtk.MESSAGE_INFO, widgets.main, "Squeezebox", "Worked OK")
            dialog = GetPlayerDialog(widgets.main, self.server.players)
            self.server.current_player = dialog.run()
            self.cfg_set("current_player", self.server.current_player)
        else:
            dialog = Message(gtk.MESSAGE_ERROR, widgets.main,
                "Squeezebox", _("Couldn't connect"))
            dialog.connect('response', lambda dia, resp: dia.destroy())
            dialog.run()
        #return (self.server.is_connected)

    def PluginPreferences(self, parent):
        def value_changed(entry, key):
            if entry.get_property('sensitive'):
                self.server.config[key] = entry.get_text()
                config.set("plugins", "squeezebox_" + key, entry.get_text())

        vb = gtk.VBox(spacing=12)
        cfg = self.server.config

        # Server settings Frame
        cfg_frame = gtk.Frame(_("<b>Squeezebox Server</b>"))
        cfg_frame.set_shadow_type(gtk.SHADOW_NONE)
        cfg_frame.get_label_widget().set_use_markup(True)
        cfg_frame_align = gtk.Alignment(0, 0, 1, 1)
        cfg_frame_align.set_padding(6, 6, 12, 12)
        cfg_frame.add(cfg_frame_align)

        # Tabulate all settings for neatness
        table = gtk.Table(3, 2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        rows = []

        ve = UndoEntry()
        ve.set_text(cfg["hostname"])
        ve.connect('changed', value_changed, 'server_hostname')
        rows.append((gtk.Label(_("Hostname:")), ve))

        ve = UndoEntry()
        ve.set_width_chars(5)
        ve.set_text(str(cfg["port"]))
        ve.connect('changed', value_changed, 'server_port')
        rows.append((gtk.Label(_("Port:")), ve))

        ve = UndoEntry()
        ve.set_text(cfg["user"])
        ve.connect('changed', value_changed, 'server_user')
        rows.append((gtk.Label(_("Username:")), ve))

        ve = UndoEntry()
        ve.set_text(str(cfg["password"]))
        ve.connect('changed', value_changed, 'server_password')
        rows.append((gtk.Label(_("Password:")), ve))

        ve = UndoEntry()
        ve.set_text(str(cfg["library_dir"]))
        ve.set_tooltip_text(_("Library directory the server connects to."))
        ve.connect('changed', value_changed, 'server_library_dir')
        rows.append((gtk.Label(_("Library path:")), ve))

        row = 0
        for (label, entry) in rows:
            table.attach(label, 0, 1, row, row + 1)
            table.attach(entry, 1, 2, row, row + 1)
            row = row + 1

        # Verify config button
        button = gtk.Button(_("_Verify settings"))
        button.connect('clicked', self.check_settings)
        table.attach(button, 0, 2, row, row + 1)

        cfg_frame_align.add(table)
        vb.pack_start(cfg_frame)
        return vb

    def init_server(self):
        self.server = SqueezeboxServer(
            hostname=self.cfg_get("server_hostname", "localhost"),
            port=self.cfg_get("server_port", 9090),
            user=self.cfg_get("server_user", ""),
            password=self.cfg_get("server_password", ""),
            library_dir=self.cfg_get("server_library_dir", self.ql_base_dir),
            current_player=self.cfg_get("current_player", 0))
        print_d("Squeezebox server version: " + self.server.get_version())

    def enabled(self):
        self.ql_base_dir = config.get("settings", "scan")
        self.init_server()
        self.server.pause()
        if self.server.is_connected:
            pass
        else:
            qltk.ErrorMessage(
                None,
                _("Error finding Squeezebox device"),
                _("Error finding %s. Please check settings") % self.server.config
            ).run()

    def disabled(self):
        # Stopping might be annoying in some situations, but seems more correct
        if self.server: self.server.stop()

    def plugin_on_song_started(self, song):
        if _DEBUG:
            print("Song start - "  + "paused" if player.playlist.paused else "not paused")
        if song is None:
            return
        if (self.server and self.server.is_connected):
            path = song('~filename')
            path = self.server.get_library_dir() + path.replace(self.ql_base_dir, "")
            if player.playlist.paused:
                self.server.change_song(path)
            else:
                self.server.playlist_play(path)

    def plugin_on_paused(self):
        if self.server: self.server.pause()

    def plugin_on_unpaused(self):
        if self.server: self.server.unpause()

    def plugin_on_seek(self, song, msec):
        # This is known to be very out of sync anyway.
        if not player.playlist.paused:
            if self.server:
                self.server.seek_to(round(msec / 1000))
                self.server.play()
        else: pass #self.server.pause()
