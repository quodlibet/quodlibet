# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

import gtk
import pango

gtk_216 = gtk.gtk_version >= (2, 16)
if not gtk_216:
    try:
        import egg.trayicon as trayicon
    except ImportError:
        import _trayicon as trayicon

from quodlibet import browsers
from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import stock
from quodlibet import util
from quodlibet.parse import Pattern
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.controls import StopAfterMenu

from quodlibet.player import playlist as player
from quodlibet.widgets import main as window, watcher
from quodlibet.qltk.playorder import ORDERS
from quodlibet.library import library

from gtk.gdk import SCROLL_LEFT, SCROLL_RIGHT, SCROLL_UP, SCROLL_DOWN

class Preferences(gtk.VBox):
    """A small window to configure the tray icon's tooltip."""

    def __init__(self, activator):
        super(Preferences, self).__init__(spacing=12)

        self.set_border_width(6)

        combo = gtk.combo_box_new_text()
        combo.append_text(_("Scroll wheel adjusts volume\n"
                            "Shift and scroll wheel changes song"))
        combo.append_text(_("Scroll wheel changes song\n"
                            "Shift and scroll wheel adjusts volume"))
        try: combo.set_active(int(
            config.getboolean("plugins", "icon_modifier_swap")))
        except config.error: combo.set_active(0)
        combo.connect('changed', self.__changed_combo)

        self.pack_start(qltk.Frame(_("Scroll _Wheel"), child=combo))

        box = gtk.VBox(spacing=12)
        table = gtk.Table(2, 4)
        table.set_row_spacings(6)
        table.set_col_spacings(12)

        cbs = []
        for i, tag in enumerate([
            "genre", "artist", "album", "discnumber", "part", "tracknumber",
            "title", "version"]):
            cb = gtk.CheckButton(util.tag(tag))
            cb.tag = tag
            cbs.append(cb)
            table.attach(cb, i%3, i%3+1, i//3, i//3+1)
        box.pack_start(table)

        entry = gtk.Entry()
        box.pack_start(entry, expand=False)

        preview = gtk.Label()
        preview.set_ellipsize(pango.ELLIPSIZE_END)
        ev = gtk.EventBox()
        ev.add(preview)
        box.pack_start(ev, expand=False)

        frame = qltk.Frame(_("Tooltip Display"), child=box)
        frame.get_label_widget().set_mnemonic_widget(entry)
        self.pack_start(frame)

        for cb in cbs:
            cb.connect('toggled', self.__changed_cb, cbs, entry)
        entry.connect(
            'changed', self.__changed_entry, cbs, preview, player)
        try:
            entry.set_text(config.get("plugins", "icon_tooltip"))
        except:
            entry.set_text(
                "<album|<album~discnumber~part~tracknumber~title~version>|"
                "<artist~title~version>>")

        self.show_all()

    def __changed_combo(self, combo):
        config.set(
            "plugins", "icon_modifier_swap", str(bool(combo.get_active())))

    def __changed_cb(self, cb, cbs, entry):
        text = "<%s>" % "~".join([cb.tag for cb in cbs if cb.get_active()])
        entry.set_text(text)

    def __changed_entry(self, entry, cbs, label, player):
        text = entry.get_text()
        if text[0:1] == "<" and text[-1:] == ">":
            parts = text[1:-1].split("~")
            for cb in cbs:
                if parts and parts[0] == cb.tag:
                    parts.pop(0)
            if parts:
                for cb in cbs:
                    cb.set_inconsistent(True)
            else:
                parts = text[1:-1].split("~")
                for cb in cbs:
                    cb.set_inconsistent(False)
                    cb.set_active(cb.tag in parts)
        else:
            for cb in cbs: cb.set_inconsistent(True)

        if player.info is None: text = _("Not playing")
        else: text = Pattern(entry.get_text()) % player.info
        label.set_text(text)
        label.get_parent().set_tooltip_text(text)
        config.set("plugins", "icon_tooltip", entry.get_text())

class EggTrayIconWrapper(object):
    __popup_sig = None
    __activate_sig = None
    __button_press_sig = None
    __size_changed_sig = None
    __icon = None

    def __init__(self):
        self.__icon = trayicon.TrayIcon("quodlibet")
        self.__tips = gtk.Tooltips()
        self.__eb = gtk.EventBox()
        self.__image = gtk.Image()
        self.__eb.add(self.__image)
        self.__icon.add(self.__eb)
        self.__icon.show_all()

    def destroy(self):
        if self.__icon:
            self.__icon.destroy()

    def connect(self, *args):
        if args[0] == "size-changed":
            self.__size_changed_sig = args[1]
            self.__eb.connect('size-allocate', self.__size_changed)
        elif args[0] == "activate":
            self.__activate_sig = args[1]
        elif args[0] == "popup-menu":
            self.__popup_sig = args[1]
        elif args[0] == "button-press-event":
            self.__button_press_sig = args[1]
            self.__eb.connect(args[0], self.__button_press)
        elif args[0] == "scroll-event":
            return self.__eb.connect(*args)
        return None

    def __button_press(self, eb, event):
        if event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
            self.__activate_sig(eb)
        elif event.button == 2:
            self.__button_press_sig(eb, event)
        elif event.button == 3:
            self.__popup_sig(eb, event.button, event.time)

    def __size_changed(self, eb, rect):
        self.__size_changed_sig(eb, rect.height)

    def set_visible(self, val):
        if val:
            self.__icon.show()
        else:
            self.__icon.hide()

    def set_from_pixbuf(self, pb):
        self.__image.set_from_pixbuf(pb)

    def set_tooltip(self, tip):
        self.__tips.set_tip(self.__icon, tip)

    def place_menu(self, menu):
        (width, height) = menu.size_request()
        (menu_xpos, menu_ypos) = self.__icon.window.get_origin()
        menu_xpos += self.__icon.allocation.x
        menu_ypos += self.__icon.allocation.y
        if menu_ypos > self.__icon.get_screen().get_height() / 2:
            menu_ypos -= height
        else:
            menu_ypos += self.__icon.allocation.height
        return (menu_xpos, menu_ypos, True)

class TrayIcon(EventPlugin):
    __icon = None
    __pixbuf = None
    __pixbuf_paused = None
    __icon_theme = None
    __position = None
    __menu = None
    __size = -1
    __w_sig_map = None
    __w_sig_del = None
    __stop_after = None
    __first_map = True
    __pattern = Pattern(
        "<album|<album~discnumber~part~tracknumber~title~version>|"
        "<artist~title~version>>")

    PLUGIN_ID = "Tray Icon"
    PLUGIN_NAME = _("Tray Icon")
    PLUGIN_DESC = _("Control Quod Libet from the system tray.")
    PLUGIN_VERSION = "2.0"

    def enabled(self):
        global gtk_216
        filename = os.path.join(const.IMAGEDIR, "quodlibet.")
        if gtk_216:
            self.__icon = gtk.StatusIcon()
        else:
            self.__icon =  EggTrayIconWrapper()

        self.__icon_theme = gtk.icon_theme_get_default()
        self.__icon_theme.connect('changed', self.__theme_changed)

        self.__icon.connect('size-changed', self.__size_changed)
        #no size-changed under win32
        if sys.platform == "win32":
            self.__size = 16

        self.__icon.connect('popup-menu', self.__button_right)
        self.__icon.connect('activate', self.__button_left)

        self.__icon.connect('scroll-event', self.__scroll)
        self.__icon.connect('button-press-event', self.__button_middle)

        self.__w_sig_map = window.connect('map-event', self.__window_map)
        self.__w_sig_del = window.connect('delete-event', self.__window_delete)

        self.__stop_after = StopAfterMenu(player)

        self.plugin_on_paused()
        self.plugin_on_song_started(player.song)

    def disabled(self):
        window.disconnect(self.__w_sig_map)
        window.disconnect(self.__w_sig_del)
        self.__icon.set_visible(False)
        try: self.__icon.destroy()
        except AttributeError: pass
        self.__icon = None
        self.__show_window()

    def PluginPreferences(self, parent):
        p = Preferences(self)
        p.connect('destroy', self.__prefs_destroy)
        return p

    def __update_icon(self):
        if self.__size <= 0:
            return

        pixbuf_size = int(self.__size * 0.75)
        #windows panel has enough padding
        if sys.platform == "win32":
            pixbuf_size = self.__size

        filename = os.path.join(const.IMAGEDIR, "quodlibet.")

        if not self.__pixbuf:
            try:
                self.__pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                    filename + "svg", pixbuf_size * 2, pixbuf_size * 2)
            except:
                self.__pixbuf = gtk.gdk.pixbuf_new_from_file(filename + "png")
            self.__pixbuf = self.__pixbuf.scale_simple(
                pixbuf_size, pixbuf_size, gtk.gdk.INTERP_BILINEAR)

        if player.paused:
            if not self.__pixbuf_paused:
                base = self.__pixbuf.copy()
                overlay = self.__icon_theme.load_icon(
                    gtk.STOCK_MEDIA_PAUSE,
                    pixbuf_size, gtk.ICON_LOOKUP_FORCE_SVG)

                w, h = base.get_width(), base.get_height()
                wo, ho = overlay.get_width(), overlay.get_height()
                r = 2
                b = 8
                l = b - r

                overlay.composite(base, w * r // b, h * r // b,
                    l * w // b, l * h // b,
                    w * r // b, h * r // b + 1,
                    float(l * w) / b / wo, float(l * h) / b / ho,
                    gtk.gdk.INTERP_BILINEAR, 255)
                self.__pixbuf_paused = base

            new_pixbuf = self.__pixbuf_paused
        else:
            new_pixbuf = self.__pixbuf

        #we need to fill the whole height that is given to us, or
        #the KDE panel will emit size-changed until we reach 0
        w, h = new_pixbuf.get_width(), new_pixbuf.get_height()
        background = gtk.gdk.Pixbuf(
            gtk.gdk.COLORSPACE_RGB, True, 8, w, self.__size)
        background.fill(0)
        new_pixbuf.copy_area(0, 0, w, h, background, 0, (self.__size-h)/2)

        self.__icon.set_from_pixbuf(background)

    def __theme_changed(self, theme, *args):
        self.__pixbuf_paused = None
        self.__update_icon()

    def __size_changed(self, icon, size, *args):
        if size != self.__size:
            self.__pixbuf = None
            self.__pixbuf_paused = None

            self.__size = size
            self.__update_icon()
        return True

    def __prefs_destroy(self, *args):
        if self.__icon:
            self.plugin_on_song_started(player.song)

    def __window_delete(self, win, event):
        self.__hide_window()
        return True

    def __window_map(self, win, event):
        try:
            visible = config.getboolean("plugins", "icon_window_visible")
        except config.error:
            return

        config.set("plugins", "icon_window_visible", "true")

        #only restore window state on start
        if not visible and self.__first_map:
            self.__hide_window()

    def __hide_window(self):
        self.__first_map = False
        self.__position = window.get_position()
        window.hide()
        config.set("plugins", "icon_window_visible", "false")

    def __show_window(self):
        if self.__position:
            window.move(*self.__position)

        window.show()
        window.present()

    def __button_left(self, icon):
        if self.__destroy_win32_menu(): return
        if window.get_property('visible'):
            self.__hide_window()
        else:
            self.__show_window()

    def __button_middle(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 2:
            if self.__destroy_win32_menu(): return
            self.__play_pause()

    def __play_pause(self, *args):
        if player.song:
            player.paused ^= True
        else:
            player.reset()

    def __scroll(self, widget, event):
        try:
            event.state ^= config.getboolean("plugins", "icon_modifier_swap")
        except config.error:
            pass

        if event.direction in [SCROLL_LEFT, SCROLL_RIGHT]:
            event.state = gtk.gdk.SHIFT_MASK

        if event.state & gtk.gdk.SHIFT_MASK:
            if event.direction in [SCROLL_UP, SCROLL_LEFT]:
                player.previous()
            elif event.direction in [SCROLL_DOWN, SCROLL_RIGHT]:
                player.next()
        else:
            if event.direction in [SCROLL_UP, SCROLL_LEFT]:
                player.volume += 0.05
            elif event.direction in [SCROLL_DOWN, SCROLL_RIGHT]:
                player.volume -= 0.05

    def plugin_on_song_started(self, song):
        if not self.__icon: return

        if song:
            try:
                pattern = Pattern(config.get("plugins", "icon_tooltip"))
            except (ValueError, config.error):
                pattern = self.__pattern

            tooltip = pattern % song
        else:
            tooltip = _("Not playing")

        self.__icon.set_tooltip(tooltip)

    def __destroy_win32_menu(self):
        """Returns True if current action should only hide the menu"""
        if sys.platform == "win32" and self.__menu:
            self.__menu.destroy()
            self.__menu = None
            return True

    def __button_right(self, icon, button, time):
        global gtk_216

        if self.__destroy_win32_menu(): return
        self.__menu = menu = gtk.Menu()

        pp_icon = [gtk.STOCK_MEDIA_PAUSE, gtk.STOCK_MEDIA_PLAY][player.paused]
        playpause = gtk.ImageMenuItem(pp_icon)
        playpause.connect('activate', self.__play_pause)

        previous = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PREVIOUS)
        previous.connect('activate', lambda *args: player.previous())
        next = gtk.ImageMenuItem(gtk.STOCK_MEDIA_NEXT)
        next.connect('activate', lambda *args: player.next())

        orders = gtk.MenuItem(_("Play _Order"))

        repeat = gtk.CheckMenuItem(_("_Repeat"))
        repeat.set_active(window.repeat.get_active())
        repeat.connect('toggled',
            lambda s: window.repeat.set_active(s.get_active()))


        def set_safter(widget, stop_after):
            stop_after.active = widget.get_active()

        safter = gtk.CheckMenuItem(_("Stop _after this song"))
        safter.set_active(self.__stop_after.active)
        safter.connect('activate', set_safter, self.__stop_after)

        def set_order(widget, num):
            window.order.set_active(num)

        order_items = [None]
        for i, Kind in enumerate(ORDERS):
            name = Kind.accelerated_name
            order_items.append(gtk.RadioMenuItem(order_items[-1], name))
            order_items[-1].connect('toggled', set_order, i)

        del order_items[0]
        order_items[window.order.get_active()].set_active(True)

        order_sub = gtk.Menu()
        order_sub.append(repeat)
        order_sub.append(safter)
        order_sub.append(gtk.SeparatorMenuItem())
        map(order_sub.append, order_items)
        orders.set_submenu(order_sub)

        browse = gtk.MenuItem(_("_Browse Library"), gtk.STOCK_FIND)
        browse_sub = gtk.Menu()

        for Kind in browsers.browsers:
            i = gtk.MenuItem(Kind.accelerated_name)
            i.connect_object('activate', LibraryBrowser, Kind, library)
            browse_sub.append(i)

        browse.set_submenu(browse_sub)

        props = gtk.ImageMenuItem(stock.EDIT_TAGS)
        props.connect('activate', self.__properties)

        info = gtk.ImageMenuItem(gtk.STOCK_INFO)
        info.connect('activate', self.__information)

        rating = gtk.MenuItem(_("_Rating"))
        rating_sub = gtk.Menu()
        def set_rating(value):
            song = player.song
            if song is None: return
            else:
                song["~#rating"] = value
                watcher.changed([song])

        for i in range(0, int(1.0 / util.RATING_PRECISION) + 1):
            j = i * util.RATING_PRECISION
            item = gtk.MenuItem("%0.2f\t%s" % (j, util.format_rating(j)))
            item.connect_object('activate', set_rating, j)
            rating_sub.append(item)

        rating.set_submenu(rating_sub)

        quit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        quit.connect('activate', window.destroy)

        menu.append(playpause)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(previous)
        menu.append(next)
        menu.append(orders)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(browse)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(props)
        menu.append(info)
        menu.append(rating)
        menu.append(gtk.SeparatorMenuItem())
        menu.append(quit)

        menu.show_all()

        if sys.platform == "win32":
            menu.popup(None, None, None, button, time, self.__icon)
        elif gtk_216:
            menu.popup(None, None, gtk.status_icon_position_menu,
                button, time, self.__icon)
        else:
            menu.popup(None, None, self.__icon.place_menu, button, time)

    plugin_on_paused = __update_icon
    plugin_on_unpaused = __update_icon

    def __properties(self, *args):
        if player.song:
            SongProperties(watcher, [player.song])

    def __information(self, *args):
        if player.song:
            Information(watcher, [player.song])
