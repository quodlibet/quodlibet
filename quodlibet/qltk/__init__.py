# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Widget wrappers for GTK.
import os, sys
import gobject, gtk, pango
import config
import util

def get_top_parent(widget):
    """Return the ultimate parent of a widget; the assumption that code
    using this makes is that it will be a gtk.Window, i.e. the widget
    is fully packed when this is called."""
    if widget is not None:
        while widget.parent is not None: widget = widget.parent
    return widget

# Legacy plugin/code support.
from qltk.msg import *
from qltk.x import *

class GetStringDialog(gtk.Dialog):
    def __init__(
        self, parent, title, text, options=[], okbutton=gtk.STOCK_OPEN):
        gtk.Dialog.__init__(self, title, parent)
        self.set_border_width(6)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         okbutton, gtk.RESPONSE_OK)
        self.vbox.set_spacing(6)
        self.set_default_response(gtk.RESPONSE_OK)

        box = gtk.VBox(spacing=6)
        lab = gtk.Label(text)
        box.set_border_width(6)
        lab.set_line_wrap(True)
        lab.set_justify(gtk.JUSTIFY_CENTER)
        box.pack_start(lab)

        if options:
            self._entry = gtk.combo_box_entry_new_text()
            for o in options: self._entry.append_text(o)
            self._val = self._entry.child
            box.pack_start(self._entry)
        else:
            self._val = gtk.Entry()
            box.pack_start(self._val)
        self.vbox.pack_start(box)
        self.child.show_all()

    def run(self):
        self.show()
        self._val.set_text("")
        self._val.set_activates_default(True)
        self._val.grab_focus()
        resp = gtk.Dialog.run(self)
        if resp == gtk.RESPONSE_OK:
            value = self._val.get_text()
        else: value = None
        self.destroy()
        return value

class DeleteDialog(gtk.Dialog):
    def __init__(self, files):
        gtk.Dialog.__init__(self, _("Delete Files"))
        self.set_border_width(6)
        self.vbox.set_spacing(6)
        self.set_has_separator(False)
        self.action_area.set_border_width(0)
        self.set_resizable(False)
        # This is the GNOME trash can for at least some versions.
        # The FreeDesktop spec is complicated and I'm not sure it's
        # actually used by anything.
        if os.path.isdir(os.path.expanduser("~/.Trash")):
            b = Button(_("_Move to Trash"), gtk.STOCK_DELETE)
            self.add_action_widget(b, 0)

        self.add_button(gtk.STOCK_CANCEL, 1)
        self.add_button(gtk.STOCK_DELETE, 2)

        hbox = gtk.HBox()
        hbox.set_border_width(6)
        i = gtk.Image()
        i.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        i.set_padding(12, 0)
        i.set_alignment(0.5, 0.0)
        hbox.pack_start(i, expand=False)
        vbox = gtk.VBox(spacing=6)
        base = os.path.basename(files[0])
        if len(files) == 1: l = _("Permanently delete this file?")
        else: l = _("Permanently delete these files?")
        if len(files) == 1:
            exp = gtk.Expander("%s" % util.fsdecode(base))
        else:
            exp = gtk.Expander(ngettext("%(title)s and %(count)d more...",
                "%(title)s and %(count)d more...", len(files)-1) %
                {'title': util.fsdecode(base), 'count': len(files) - 1})

        lab = gtk.Label()
        lab.set_markup("<big><b>%s</b></big>" % l)
        lab.set_alignment(0.0, 0.5)
        vbox.pack_start(lab, expand=False)

        lab = gtk.Label("\n".join(
            map(util.fsdecode, map(util.unexpand, files))))
        lab.set_alignment(0.1, 0.0)
        exp.add(gtk.ScrolledWindow())
        exp.child.add_with_viewport(lab)
        exp.child.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        exp.child.child.set_shadow_type(gtk.SHADOW_NONE)
        vbox.pack_start(exp)
        hbox.pack_start(vbox)
        self.vbox.pack_start(hbox)
        self.vbox.show_all()

class ConfigCheckButton(gtk.CheckButton):
    """A CheckButton that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is *not* set to the current config value initially."""

    def __init__(self, label, section, option):
        gtk.CheckButton.__init__(self, label)
        self.connect('toggled', ConfigCheckButton.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())

class ValidatingEntry(gtk.Entry):
    """An entry with visual feedback as to whether it is valid or not.
    The given validator function gets a string and returns True (green),
    False (red), or a color string, or None (black).

    parser.is_valid_color mimicks the behavior of the search bar.

    If the "Color search terms" option is off, the entry will not
    change color."""

    def __init__(self, validator=None, *args):
        gtk.Entry.__init__(self, *args)
        if validator: self.connect_object('changed', self.__color, validator)

    def __color(self, validator):
        if config.getboolean('browsers', 'color'):
            value = validator(self.get_text())
            if value is True: color = "dark green"
            elif value is False: color = "red"
            elif isinstance(value, str): color = value
            else: color = None

            if color and self.get_property('sensitive'):
                self.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(color))
        else:
            self.modify_text(gtk.STATE_NORMAL, None)

class WaitLoadWindow(gtk.Window):
    """A window with a progress bar and some nice updating text,
    as well as pause/stop buttons.

    Example:

    w = WaitLoadWindow(None, 5, "%d/%d", (0, 5))
    for i in range(1, 6): w.step(i, 5)
    w.destroy()
    """

    def __init__(self, parent, count, text, initial=(), limit=5,
                 show=True):
        """parent: the parent window, or None
        count: the total amount of items expected, or 0 unknown/indefinite
        text: text to display in the window; may contain % formats
        initial: initial values for % formats (text % initial)
        limit: count must be greater than limit (or 0) for pause/stop to appear
        show: show the window right away; you want this to be True

        The current iteration of the counter can be gotten as
        window.current. count can be gotten as window.count.
        """

        gtk.Window.__init__(self)
        if parent:
            parent = get_top_parent(parent)
            sig = parent.connect('configure-event', self.__recenter)
            self.connect_object(
                'destroy', WaitLoadWindow.__disconnect, self, sig)
            self.set_transient_for(parent)
            parent.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self.set_modal(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_focus_on_map(False)
        self.add(gtk.Frame())
        self.child.set_shadow_type(gtk.SHADOW_OUT)
        vbox = gtk.VBox(spacing=12)
        vbox.set_border_width(12)
        self.__label = gtk.Label()
        self.__label.set_size_request(170, -1)
        self.__label.set_use_markup(True)
        self.__label.set_line_wrap(True)
        self.__label.set_justify(gtk.JUSTIFY_CENTER)
        vbox.pack_start(self.__label)
        self.__progress = gtk.ProgressBar()
        self.__progress.set_pulse_step(0.08)
        vbox.pack_start(self.__progress)

        self.current = 0
        self.count = count
        if self.count > limit or self.count == 0:
            # Display a stop/pause box. count = 0 means an indefinite
            # number of steps.
            hbox = gtk.HBox(spacing=6, homogeneous=True)
            b1 = gtk.Button(stock=gtk.STOCK_STOP)
            b2 = gtk.ToggleButton(gtk.STOCK_MEDIA_PAUSE)
            b2.set_use_stock(True)
            b1.connect('clicked', self.__cancel_clicked)
            b2.connect('clicked', self.__pause_clicked)
            hbox.pack_start(b1)
            hbox.pack_start(b2)
            vbox.pack_start(hbox)

        self.child.add(vbox)

        self.__text = text
        self.__paused = False
        self.__quit = False

        self.__label.set_markup(self.__text % initial)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        if show: self.show_all()
        while gtk.events_pending(): gtk.main_iteration()

    def __pause_clicked(self, button):
        self.__paused = button.get_active()

    def __cancel_clicked(self, button):
        self.__quit = True

    def step(self, *values):
        """Advance the counter by one. Arguments are applied to the
        originally-supplied text as a format string.

        This function doesn't return if the dialog is paused (though
        the GTK main loop will still run), and returns True if stop
        was pressed.
        """

        self.__label.set_markup(self.__text % values)
        if self.count:
            self.current += 1
            self.__progress.set_fraction(
                max(0, min(1, self.current / float(self.count))))
        else:
            self.__progress.pulse()

        while not self.__quit and (self.__paused or gtk.events_pending()):
            gtk.main_iteration()
        return self.__quit

    def __recenter(self, parent, event):
        x, y = parent.get_position()
        dx, dy = parent.get_size()
        dx2, dy2 = self.get_size()
        self.move(x + dx/2 - dx2/2, y + dy/2 - dy2/2)

    def __disconnect(self, sig):
        self.get_transient_for().window.set_cursor(None)
        self.get_transient_for().disconnect(sig)

class WritingWindow(WaitLoadWindow):
    def __init__(self, parent, count):
        WaitLoadWindow.__init__(
            self, parent, count,
            (_("Saving the songs you changed.") + "\n\n" +
             _("%d/%d songs saved")), (0, count))

    def step(self):
        return WaitLoadWindow.step(self, self.current + 1, self.count)

class RPaned(object):
    """A Paned that supports relative (percentage) width/height setting."""

    def get_relative(self):
        if self.get_property('max-position') > 0:
            return float(self.get_position())/self.get_property('max-position')
        else: return 0.5

    def set_relative(self, v):
        return self.set_position(int(v * self.get_property('max-position')))

class RHPaned(RPaned, gtk.HPaned): pass
class RVPaned(RPaned, gtk.VPaned): pass

class LibraryBrowser(Window):
    def __init__(self, Kind, watcher):
        super(LibraryBrowser, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Library Browser"))

        from qltk.songlist import SongList
        view = SongList(watcher)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.browser = browser = Kind(watcher, main=False)
        browser.connect_object('songs-selected', SongList.set_songs, view)
        if browser.reordered: view.enable_drop()

        if Kind.expand:
            container = Kind.expand()
            container.pack1(browser, resize=True)
            container.pack2(sw, resize=True)
            self.add(container)
        else:
            vbox = gtk.VBox(spacing=6)
            vbox.pack_start(browser, expand=False)
            vbox.pack_start(sw)
            self.add(vbox)

        view.connect('button-press-event', self.__button_press, watcher)
        view.connect('popup-menu', self.__menu, 3, 0, watcher)
        view.connect('drag-data-received', self.__drag_data_recv)
        view.connect('row-activated', self.__enqueue)
        if browser.headers is not None:
            view.connect('columns-changed', self.__cols_changed, browser)
            self.__cols_changed(view, browser)
        self.set_default_size(500, 300)
        sw.show_all()
        self.child.show()
        self.show()

    def __enqueue(self, view, path, column):
        from widgets import widgets
        widgets.main.playlist.enqueue([view.get_model()[path][0]])

    def __drag_data_recv(self, view, *args):
        if callable(self.browser.reordered): self.browser.reordered(view)
        view.set_sort_by(None, refresh=False)

    def __cols_changed(self, view, browser):
        for header in view.get_columns():
            tag = header.header_name
            if "~" in tag[1:]: tag = filter(None, tag.split("~"))[0]
            header.set_visible(tag in browser.headers)

    def __button_press(self, view, event, watcher):
        if event.button != 3: return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        view.grab_focus()
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        self.__menu(view, event.button, event.time, watcher)
        return True

    def __menu(self, view, button, time, watcher):
        path, col = view.get_cursor()
        header = col.header_name
        view.Menu(header, self.browser, watcher).popup(
            None, None, None, button, time)
        return True

