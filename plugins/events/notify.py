# -*- coding: utf-8 -*-
# Copyright (c) 2010 Felix Krull <f_krull@gmx.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.


# Note: This plugin is based on notify.py as distributed in the
# quodlibet-plugins package; however, that file doesn't contain a copyright
# note. As for the license, GPLv2 is the only choice anyway, as it calls
# Quod Libet code, which is GPLv2 as well, so I thought it safe to add this.

from xml.sax.saxutils import unescape
import os.path
import tempfile

import dbus
import gtk

from quodlibet import config, const, qltk
from quodlibet.plugins.events import EventPlugin
from quodlibet.parse import XMLFromPattern
from quodlibet.widgets import main as qlmainwindow
from quodlibet.player import playlist as qlplayer


# configuration stuff
DEFAULT_CONFIG = {
    "timeout": 4000,
    "show_notifications": "all",
    "show_only_when_unfocused": True,

    "titlepattern": "<artist|<artist> - ><title>",
    "bodypattern":
"""<~length>
<album|<album><discsubtitle| - <discsubtitle>>
><~year|<~year>>""",
}

def get_conf_value(name, accessor="get"):
    try:
        value = getattr(config, accessor)("plugins", "notify_%s" % name)
    except Exception:
        value = DEFAULT_CONFIG[name]
    return value

get_conf_bool = lambda name: get_conf_value(name, "getboolean")
get_conf_int = lambda name: get_conf_value(name, "getint")

def set_conf_value(name, value):
    config.set("plugins", "notify_%s" % name, unicode(value))


class PaddedWidget(gtk.Alignment):
    def __init__(self, child, top=0, bottom=0, left=0, right=0):
        gtk.Alignment.__init__(self)
        self.add(child)
        self.set_padding(top, bottom, left, right)


class PreferencesWidget(gtk.VBox):
    def __init__(self, parent, plugin_instance):
        gtk.VBox.__init__(self, spacing=12)
        self.set_border_width(6)
        self.plugin_instance = plugin_instance

        # notification text settings
        text_box = gtk.VBox(spacing=3)
        text_frame = qltk.Frame(_("Notification text"), child=text_box)

        title_label = gtk.Label(_("Notification title:"))
        title_label.set_alignment(0, 0.1)
        text_box.pack_start(PaddedWidget(title_label, top=3, left=3))

        title_entry = gtk.Entry()
        title_entry.set_text(get_conf_value("titlepattern"))
        title_entry.connect("focus-out-event", self.on_entry_unfocused,
                            "titlepattern")
        text_box.pack_start(title_entry)

        body_label = gtk.Label(_("Notification body:"))
        body_label.set_alignment(0, 0.1)
        text_box.pack_start(PaddedWidget(body_label, top=3, left=3))

        body_textview = gtk.TextView()
        body_textview.get_buffer().set_text(get_conf_value("bodypattern"))
        body_textview.connect("focus-out-event", self.on_textview_unfocused,
                              "bodypattern")
        body_scrollarea = gtk.ScrolledWindow()
        body_scrollarea.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        body_scrollarea.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        body_scrollarea.add(body_textview)
        text_box.pack_start(body_scrollarea)

        self.pack_start(text_frame)

        # notification display settings
        display_box = gtk.VBox()
        display_frame = qltk.Frame(_("Show notifications"), child=display_box)

        only_user_radio = gtk.RadioButton(label=_(
            "Only on manual song changes"
        ))
        only_user_radio.connect("toggled", self.on_radiobutton_toggled,
                                "show_notifications", "user")
        display_box.pack_start(only_user_radio)

        only_auto_radio = gtk.RadioButton(only_user_radio, label=_(
            "Only on automatic song changes"
        ))
        only_auto_radio.connect("toggled", self.on_radiobutton_toggled,
                                "show_notifications", "auto")
        display_box.pack_start(only_auto_radio)

        all_radio = gtk.RadioButton(only_user_radio, label=_(
            "On all song changes"
        ))
        all_radio.connect("toggled", self.on_radiobutton_toggled,
                          "show_notifications", "all")
        display_box.pack_start(all_radio)

        try:
            {
                "user": only_user_radio,
                "auto": only_auto_radio,
                "all": all_radio
            }[get_conf_value("show_notifications")].set_active(True)
        except KeyError:
            all_radio.set_active(True)
            set_conf_value("show_notifications", "all")

        focus_check = gtk.CheckButton(_("Only when the main window is not "
                                        "focused"))
        focus_check.set_active(get_conf_bool("show_only_when_unfocused"))
        focus_check.connect("toggled", self.on_checkbutton_toggled,
                            "show_only_when_unfocused")
        display_box.pack_start(PaddedWidget(focus_check, top=6))

        self.pack_start(display_frame)

        # preview button
        preview_button = gtk.Button(_("Show notification now"))
        preview_button.set_sensitive(qlplayer.info is not None)
        preview_button.connect("clicked", self.on_preview_button_clicked)
        self.qlplayer_connected_signals = [
            qlplayer.connect("paused", self.on_player_state_changed,
                             preview_button),
            qlplayer.connect("unpaused", self.on_player_state_changed,
                             preview_button),
        ]

        self.pack_start(preview_button)

        self.show_all()
        self.connect("destroy", self.on_destroyed)

    # callbacks
    def on_entry_unfocused(self, entry, event, cfgname):
        set_conf_value(cfgname, entry.get_text())

    def on_textview_unfocused(self, textview, event, cfgname):
        set_conf_value(cfgname,
                       textview.get_buffer().get_text(
                            *textview.get_buffer().get_bounds()
                       ))

    def on_radiobutton_toggled(self, radio, cfgname, value):
        if radio.get_active():
            set_conf_value(cfgname, value)

    def on_checkbutton_toggled(self, button, cfgname):
        set_conf_value(cfgname, button.get_active())

    def on_preview_button_clicked(self, button):
        if qlplayer.info is not None:
            self.plugin_instance.show_notification(qlplayer.info)

    def on_player_state_changed(self, player, preview_button):
        preview_button.set_sensitive(player.info is not None)

    def on_destroyed(self, ev):
        for sig in self.qlplayer_connected_signals:
            qlplayer.disconnect(sig)
        self.qlplayer_connected_signals = []


class Notify(EventPlugin):
    PLUGIN_ID = "Notify"
    PLUGIN_NAME = _("Notify")
    PLUGIN_DESC = _("Display a notification when the song changes.")
    PLUGIN_VERSION = "1.0"

    # quirks
    NONSCALING_DAEMONS = ["Notification Daemon"]
    # can't trust capabilities: NotifyOSD says it does markup, but in fact
    # doesn't seem to handle escaped HTML entities (good thing there are only
    # about 2 somewhat widespread implementations at all)

    # What? n-d also chokes on unescaped entities? I don't get it.
    NO_PROPER_MARKUP_DAEMONS = ["notify-osd", "Notification Daemon"]

    def enabled(self):
        bus = dbus.SessionBus()
        obj = bus.get_object(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications")
        self.ni = dbus.Interface(obj, "org.freedesktop.Notifications")

        # check capabilities
        name = self.ni.GetServerInformation()[0]
        print_d("[notify] talking to %s ..." % name)

        if name in self.NO_PROPER_MARKUP_DAEMONS:
            self.should_escape_contents = False
        else:
            self.should_escape_contents = (
                "body-markup" in self.ni.GetCapabilities())

        self.should_scale_icon = name in self.NONSCALING_DAEMONS

        self.last_id = 0

        # This works because:
        #  - if paused, any on_song_started event will be generated by user
        #    interaction
        #  - if playing, an on_song_ended event will be generated before any
        #    on_song_started event in any case.
        self.was_stopped_by_user = True


    def PluginPreferences(self, parent):
        return PreferencesWidget(parent, self)


    def show_notification(self, song):
        if not song:
            return

        # XMLFromPattern's output is escaped so we unescape it if required,
        # instead of the other way around
        munge = (lambda x: x) if self.should_escape_contents else unescape
        title = munge(XMLFromPattern(get_conf_value("titlepattern")) % song)
        body = munge(XMLFromPattern(get_conf_value("bodypattern")) % song)

        icon = song.find_cover() or None
        if icon:
            icon_name = icon.name
            if self.should_scale_icon:
                # the notification service doesn't scale the provided icon (to
                # the best of our knowledge), so we do it ourselves
                try:
                    img = gtk.gdk.pixbuf_new_from_file_at_size(icon_name,
                                                               48, 48)
                    try:
                        small_icon_name = os.path.join(const.USERDIR,
                                                       "cover.png")
                    except AttributeError:
                        os.path.join(const.DIR, "cover.png")
                    img.save(small_icon_name, "png", {})
                    icon_name = small_icon_name
                except Exception:
                    icon_name = ""
        else:
            icon_name = ""

        self.last_id = self.ni.Notify(
            "Quod Libet", self.last_id, # app name and ID of last notification
            icon_name, title, body,     # actual notification content
            [], {},                     # actions and hints; we don't use those
            get_conf_int("timeout")     # timeout; actually ignored by
                                        # NotifyOSD, but not others
        )

    def on_song_change(self, song, typ):
        if get_conf_value("show_notifications") in [typ, "all"] \
            and not (get_conf_bool("show_only_when_unfocused") \
                     and qlmainwindow.has_toplevel_focus()):
            self.show_notification(song)

    def plugin_on_song_started(self, song):
        typ = "user" if self.was_stopped_by_user else "auto"
        self.on_song_change(song, typ)

    def plugin_on_song_ended(self, song, stopped):
        # if `stopped` is `True`, this song was ended due to some kind of user
        # interaction.
        self.was_stopped_by_user = stopped

