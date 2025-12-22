# Copyright (c) 2010 Felix Krull <f_krull@gmx.de>
#               2011-2013 Christoph Reiter <reiter.christoph@gmail.com>
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

import re

from gi.repository import Gtk, GLib, Gio
from senf import fsn2uri

from quodlibet import _
from quodlibet import qltk, app
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins import PluginConfig
from quodlibet.pattern import XMLFromPattern
from quodlibet.qltk.textedit import TextView, TextBuffer
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk import Icons
from quodlibet.util import unescape, print_w


pconfig = PluginConfig("notify")
pconfig.defaults.set("timeout", 4000)
pconfig.defaults.set("show_notifications", "all")
pconfig.defaults.set("show_only_when_unfocused", True)
pconfig.defaults.set("show_next_button", True)
pconfig.defaults.set("titlepattern", "<artist|<artist> - ><title>")
pconfig.defaults.set(
    "bodypattern",
    """<~length>
<album|<album><discsubtitle| - <discsubtitle>>
><~year|<~year>>""",
)


class PreferencesWidget(Gtk.Box):
    def __init__(self, parent, plugin_instance):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.plugin_instance = plugin_instance

        # notification text settings
        table = Gtk.Table(n_rows=2, n_columns=3)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        text_frame = qltk.Frame(_("Notification text"), child=table)

        title_entry = UndoEntry()
        title_entry.set_text(pconfig.gettext("titlepattern"))

        def on_entry_changed(entry, cfgname):
            pconfig.settext(cfgname, entry.get_text())

        title_entry.connect("changed", on_entry_changed, "titlepattern")
        table.attach(title_entry, 1, 2, 0, 1)

        title_label = Gtk.Label(label=_("_Title:"))
        title_label.set_use_underline(True)
        title_label.set_alignment(0, 0.5)
        title_label.set_mnemonic_widget(title_entry)
        table.attach(
            title_label,
            0,
            1,
            0,
            1,
            xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK,
        )

        title_revert = Gtk.Button()
        title_revert.add(
            Gtk.Image.new_from_icon_name(Icons.DOCUMENT_REVERT, Gtk.IconSize.NORMAL)
        )
        title_revert.set_tooltip_text(_("Revert to default pattern"))
        title_revert.connect(
            "clicked",
            lambda *x: title_entry.set_text(pconfig.defaults.gettext("titlepattern")),
        )
        table.attach(title_revert, 2, 3, 0, 1, xoptions=Gtk.AttachOptions.SHRINK)

        body_textbuffer = TextBuffer()
        body_textview = TextView(buffer=body_textbuffer)
        body_textview.set_size_request(-1, 85)
        body_textview.get_buffer().set_text(pconfig.gettext("bodypattern"))

        def on_textbuffer_changed(text_buffer, cfgname):
            start, end = text_buffer.get_bounds()
            text = text_buffer.get_text(start, end, True)
            pconfig.settext(cfgname, text)

        body_textbuffer.connect("changed", on_textbuffer_changed, "bodypattern")
        body_scrollarea = Gtk.ScrolledWindow()
        body_scrollarea.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        body_scrollarea.add(body_textview)
        table.attach(body_scrollarea, 1, 2, 1, 2)

        body_label = Gtk.Label(label=_("_Body:"))
        body_label.set_padding(0, 3)
        body_label.set_use_underline(True)
        body_label.set_alignment(0, 0)
        body_label.set_mnemonic_widget(body_textview)
        table.attach(body_label, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.SHRINK)

        body_revert = Gtk.Button()
        body_revert.add(
            Gtk.Image.new_from_icon_name(Icons.DOCUMENT_REVERT, Gtk.IconSize.NORMAL)
        )
        body_revert.set_tooltip_text(_("Revert to default pattern"))
        body_revert.connect(
            "clicked",
            lambda *x: body_textbuffer.set_text(
                pconfig.defaults.gettext("bodypattern")
            ),
        )
        table.attach(
            body_revert,
            2,
            3,
            1,
            2,
            xoptions=Gtk.AttachOptions.SHRINK,
            yoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK,
        )

        # preview button
        preview_button = qltk.Button(_("_Show notification"), Icons.SYSTEM_RUN)
        preview_button.set_sensitive(app.player.info is not None)
        preview_button.connect("clicked", self.on_preview_button_clicked)
        self.qlplayer_connected_signals = [
            app.player.connect("paused", self.on_player_state_changed, preview_button),
            app.player.connect(
                "unpaused", self.on_player_state_changed, preview_button
            ),
        ]

        table.attach(
            preview_button,
            0,
            3,
            2,
            3,
            xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK,
        )

        self.prepend(text_frame)

        # notification display settings
        display_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        display_frame = qltk.Frame(_("Show notifications"), child=display_box)

        radio_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        display_box.prepend(radio_box)

        only_user_radio = Gtk.CheckButton(
            label=_("Only on <i>_manual</i> song changes"), use_underline=True
        )
        only_user_radio.get_child().set_use_markup(True)
        only_user_radio.connect(
            "toggled", self.on_radiobutton_toggled, "show_notifications", "user"
        )
        radio_box.prepend(only_user_radio)

        only_auto_radio = Gtk.CheckButton(
            group=only_user_radio,
            label=_("Only on <i>_automatic</i> song changes"),
            use_underline=True,
        )
        only_auto_radio.get_child().set_use_markup(True)
        only_auto_radio.connect(
            "toggled", self.on_radiobutton_toggled, "show_notifications", "auto"
        )
        radio_box.prepend(only_auto_radio)

        all_radio = Gtk.CheckButton(
            group=only_user_radio,
            label=_("On <i>a_ll</i> song changes"),
            use_underline=True,
        )
        all_radio.get_child().set_use_markup(True)
        all_radio.connect(
            "toggled", self.on_radiobutton_toggled, "show_notifications", "all"
        )
        radio_box.prepend(all_radio)

        {"user": only_user_radio, "auto": only_auto_radio, "all": all_radio}.get(
            pconfig.gettext("show_notifications"), all_radio
        ).set_active(True)

        focus_check = Gtk.CheckButton(
            label=_("Only when the main window is not _focused"), use_underline=True
        )
        focus_check.set_active(pconfig.getboolean("show_only_when_unfocused"))
        focus_check.connect(
            "toggled", self.on_checkbutton_toggled, "show_only_when_unfocused"
        )
        display_box.prepend(focus_check)

        show_next = Gtk.CheckButton(label=_('Show "_Next" button'), use_underline=True)
        show_next.set_active(pconfig.getboolean("show_next_button"))
        show_next.connect("toggled", self.on_checkbutton_toggled, "show_next_button")
        display_box.prepend(show_next)

        self.prepend(display_frame)

        self.show_all()
        self.connect("destroy", self.on_destroyed)

    def on_radiobutton_toggled(self, radio, cfgname, value):
        if radio.get_active():
            pconfig.set(cfgname, value)

    def on_checkbutton_toggled(self, button, cfgname):
        pconfig.set(cfgname, button.get_active())

    def on_preview_button_clicked(self, button):
        if app.player.info is not None:
            if not self.plugin_instance.show_notification(app.player.info):
                ErrorMessage(
                    self,
                    _("Connection Error"),
                    _("Couldn't connect to notification daemon."),
                ).run()

    def on_player_state_changed(self, player, preview_button):
        preview_button.set_sensitive(player.info is not None)

    def on_destroyed(self, ev):
        for sig in self.qlplayer_connected_signals:
            app.player.disconnect(sig)
        self.qlplayer_connected_signals = []
        self.plugin_instance = None


class Notify(EventPlugin):
    PLUGIN_ID = "Notify"
    PLUGIN_NAME = _("Song Notifications")
    PLUGIN_DESC = _("Displays a notification when the song changes.")
    PLUGIN_ICON = Icons.DIALOG_INFORMATION

    DBUS_NAME = "org.freedesktop.Notifications"
    DBUS_IFACE = "org.freedesktop.Notifications"
    DBUS_PATH = "/org/freedesktop/Notifications"

    # these can all be used even if it wasn't enabled
    __enabled = False
    __last_id = 0
    __image_fp = None
    __interface = None
    __action_sig = None
    __watch = None

    def enabled(self):
        self.__enabled = True

        # This works because:
        #  - if paused, any on_song_started event will be generated by user
        #    interaction
        #  - if playing, an on_song_ended event will be generated before any
        #    on_song_started event in any case.
        self.__was_stopped_by_user = True

        self.__force_notification = False
        self.__caps = None
        self.__spec_version = None

        self.__enable_watch()

    def disabled(self):
        self.__disable_watch()
        self.__disconnect()
        self.__enabled = False
        self._set_image_fileobj(None)

    def __enable_watch(self):
        """Enable events for dbus name owner change"""
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            # This also triggers for existing name owners
            self.__watch = Gio.bus_watch_name_on_connection(
                bus,
                self.DBUS_NAME,
                Gio.BusNameWatcherFlags.NONE,
                None,
                self.__owner_vanished,
            )
        except GLib.Error:
            pass

    def __disable_watch(self):
        """Disable name owner change events"""
        if self.__watch:
            Gio.bus_unwatch_name(self.__watch)
            self.__watch = None

    def __disconnect(self):
        if self.__interface is None:
            return

        if self.__action_sig:
            self.__interface.disconnect(self.__action_sig)
            self.__action_sig = None

        self.__interface = None

    def __owner_vanished(self, bus, owner):
        # In case the owner gets removed, remove all references to it
        self.__disconnect()

    def PluginPreferences(self, parent):
        return PreferencesWidget(parent, self)

    def __get_interface(self):
        """Returns a fresh proxy + info about the server"""

        interface = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            self.DBUS_NAME,
            self.DBUS_PATH,
            self.DBUS_IFACE,
            None,
        )

        name, vendor, version, spec_version = list(
            map(str, interface.GetServerInformation())
        )
        spec_version = list(map(int, spec_version.split(".")))
        caps = list(map(str, interface.GetCapabilities()))

        return interface, caps, spec_version

    def close_notification(self):
        """Closes the last opened notification"""

        if not self.__last_id:
            return

        try:
            interface = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.NONE,
                None,
                self.DBUS_NAME,
                self.DBUS_PATH,
                self.DBUS_IFACE,
                None,
            )
            interface.CloseNotification("(u)", self.__last_id)
        except GLib.Error:
            pass
        else:
            self.__last_id = 0

    def _set_image_fileobj(self, fileobj):
        if self.__image_fp is not None:
            self.__image_fp.close()
            self.__image_fp = None
        self.__image_fp = fileobj

    def _get_image_uri(self, song):
        """A unicode file URI or an empty string"""

        fileobj = app.cover_manager.get_cover(song)
        self._set_image_fileobj(fileobj)
        if fileobj:
            return fsn2uri(fileobj.name)
        return ""

    def show_notification(self, song):
        """Returns True if showing the notification was successful"""

        if not song:
            return True

        try:
            if self.__enabled:
                # we are enabled try to work with the data we have and
                # keep it fresh
                if not self.__interface:
                    iface, caps, spec = self.__get_interface()
                    self.__interface = iface
                    self.__caps = caps
                    self.__spec_version = spec
                    if "actions" in caps:
                        self.__action_sig = iface.connect("g-signal", self._on_signal)
                else:
                    iface = self.__interface
                    caps = self.__caps
                    spec = self.__spec_version
            else:
                # not enabled, just get everything temporary,
                # probably preview
                iface, caps, spec = self.__get_interface()

        except GLib.Error:
            print_w("[notify] {}".format(_("Couldn't connect to notification daemon.")))
            self.__disconnect()
            return False

        def strip_markup(t):
            return re.subn("</?[iub]>", "", t)[0]

        def strip_links(t):
            return re.subn("</?a.*?>", "", t)[0]

        def strip_images(t):
            return re.subn("<img.*?>", "", t)[0]

        title = XMLFromPattern(pconfig.gettext("titlepattern")) % song
        title = unescape(strip_markup(strip_links(strip_images(title))))

        body = ""
        if "body" in caps:
            body = XMLFromPattern(pconfig.gettext("bodypattern")) % song

            if "body-markup" not in caps:
                body = strip_markup(body)
            if "body-hyperlinks" not in caps:
                body = strip_links(body)
            if "body-images" not in caps:
                body = strip_images(body)

        actions = []
        if pconfig.getboolean("show_next_button") and "actions" in caps:
            actions = ["next", _("Next")]

        hints = {
            "desktop-entry": GLib.Variant("s", "io.github.quodlibet.QuodLibet"),
        }

        image_uri = self._get_image_uri(song)
        if image_uri:
            hints["image_path"] = GLib.Variant("s", image_uri)
            hints["image-path"] = GLib.Variant("s", image_uri)

        try:
            self.__last_id = iface.Notify(
                "(susssasa{sv}i)",
                "Quod Libet",
                self.__last_id,
                image_uri,
                title,
                body,
                actions,
                hints,
                pconfig.getint("timeout"),
            )
        except GLib.Error:
            print_w("[notify] {}".format(_("Couldn't connect to notification daemon.")))
            self.__disconnect()
            return False

        # preview done, remove all references again
        if not self.__enabled:
            self.__disconnect()

        return True

    def _on_signal(self, proxy, sender, signal, args):
        if signal == "ActionInvoked":
            notify_id = args[0]
            key = args[1]
            self.on_dbus_action(notify_id, key)

    def on_dbus_action(self, notify_id, key):
        if notify_id == self.__last_id and key == "next":
            # Always show a new notification if the next button got clicked
            self.__force_notification = True
            app.player.next()

    def on_song_change(self, song, typ):
        if not song:
            self.close_notification()
        if (
            pconfig.gettext("show_notifications") in [typ, "all"]
            and not (
                pconfig.getboolean("show_only_when_unfocused")
                and app.window.has_toplevel_focus()
            )
            or self.__force_notification
        ):

            def idle_show(song):
                self.show_notification(song)

            GLib.idle_add(idle_show, song)
            self.__force_notification = False

    def plugin_on_song_started(self, song):
        typ = (self.__was_stopped_by_user and "user") or "auto"
        self.on_song_change(song, typ)

    def plugin_on_song_ended(self, song, stopped):
        # if `stopped` is `True`, this song was ended due to some kind of user
        # interaction.
        self.__was_stopped_by_user = stopped
