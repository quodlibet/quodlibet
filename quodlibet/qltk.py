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

from gettext import ngettext

# Everything connects to this to get updates about the library and player.
class SongWatcher(gtk.Object):
    SIG_PYOBJECT = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,))
    SIG_NONE = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
    
    __gsignals__ = {
        # Songs in the library have changed.
        'changed': SIG_PYOBJECT,

        # Songs were removed from the library.
        'removed': SIG_PYOBJECT,

        # Songs were added to the library.
        'added': SIG_PYOBJECT,

        # A group of changes has been finished; all library views should
        # do a global refresh if necessary
        'refresh': SIG_NONE,

        # A new song started playing (or the current one was restarted).
        'song-started': SIG_PYOBJECT,

        # The song was seeked within.
        'seek': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                 (object, int)),

        # A new song started playing (or the current one was restarted).
        # The boolean is True if the song was stopped rather than simply
        # ended.
        'song-ended': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                       (object, bool)),

        # Playback was paused.
        'paused': SIG_NONE,

        # Playback was unpaused.
        'unpaused': SIG_NONE,

        # A song was missing (i.e. disappeared from the filesystem).
        # When QL is running it will also result in a removed signal
        # (caused by MainWindow).
        'missing': SIG_PYOBJECT
        }

    # (current_in_msec, total_in_msec)
    # (0, 1) when no song is playing.
    time = (0, 1)

    # the currently playing song.
    song = None

    def changed(self, songs):
        gobject.idle_add(self.emit, 'changed', songs)

    def added(self, songs):
        gobject.idle_add(self.emit, 'added', songs)

    def removed(self, songs):
        gobject.idle_add(self.emit, 'removed', songs)

    def missing(self, song):
        gobject.idle_add(self.emit, 'missing', song)

    def song_started(self, song):
        if song: self.time = (0, song["~#length"] * 1000)
        else: self.time = (0, 1)
        self.song = song
        gobject.idle_add(self.emit, 'song-started', song)

    def song_ended(self, song, stopped):
        gobject.idle_add(self.emit, 'song-ended', song, stopped)

    def refresh(self):
        gobject.idle_add(self.emit, 'refresh')

    def set_paused(self, paused):
        if paused: gobject.idle_add(self.emit, 'paused')
        else: gobject.idle_add(self.emit, 'unpaused')

    def seek(self, song, position_in_msec):
        gobject.idle_add(self.emit, 'seek', song, position_in_msec)

    def reload(self, song):
        try: song.reload()
        except Exception, err:
            from library import library
            sys.stdout.write(str(err) + "\n")
            if library: library.remove(song)
            self.removed([song])
        else: self.changed([song])

    error = reload

gobject.type_register(SongWatcher)

class GetStringDialog(gtk.Dialog):
    def __init__(self, parent, title, text, options=[], okbutton=gtk.STOCK_OPEN):
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
            self.__entry = gtk.combo_box_entry_new_text()
            for o in options: self.__entry.append_text(o)
            self.__val = self.__entry.child
            box.pack_start(self.__entry)
        else:
            self.__val = gtk.Entry()
            box.pack_start(self.__val)
        self.vbox.pack_start(box)
        self.child.show_all()

    def run(self):
        self.show()
        self.__val.set_text("")
        self.__val.set_activates_default(True)
        self.__val.grab_focus()
        resp = gtk.Dialog.run(self)
        if resp == gtk.RESPONSE_OK:
            value = self.__val.get_text()
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
        l = ngettext("Permanently delete this file?",
                     "Permanently delete these files?", len(files))
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

class Message(gtk.MessageDialog):
    """A message dialog that destroys itself after it is run, uses
    markup, and defaults to an 'OK' button."""

    def __init__(self, kind, parent, title, description, buttons=None):
        buttons = buttons or gtk.BUTTONS_OK
        text = "<span size='xx-large'>%s</span>\n\n%s" % (title, description)
        gtk.MessageDialog.__init__(
            self, parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            kind, buttons)
        self.set_markup(text)

    def run(self, destroy=True):
        gtk.MessageDialog.run(self)
        if destroy: self.destroy()

class ConfirmAction(Message):
    """A message dialog that asks a yes/no question."""

    def __init__(self, *args, **kwargs):
        kwargs["buttons"] = gtk.BUTTONS_YES_NO
        Message.__init__(self, gtk.MESSAGE_WARNING, *args, **kwargs)

    def run(self, destroy = True):
        """Returns True if yes was clicked, False otherwise."""
        resp = gtk.MessageDialog.run(self)
        if destroy: self.destroy()
        if resp == gtk.RESPONSE_YES: return True
        else: return False

class CancelRevertSave(gtk.MessageDialog):
    def __init__(self, parent):
        title = _("Discard tag changes?")
        description = _("Tags have been changed but not saved. Save these "
                        "files, or revert and discard changes?")
        text = "<span size='xx-large'>%s</span>\n\n%s" % (title, description)
        gtk.MessageDialog.__init__(
            self, parent, flags=0, type=gtk.MESSAGE_WARNING,
            buttons=gtk.BUTTONS_NONE)
        self.add_buttons(gtk.STOCK_SAVE, gtk.RESPONSE_YES,
                         gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_REVERT_TO_SAVED, gtk.RESPONSE_NO)
        self.set_default_response(gtk.RESPONSE_NO)
        self.set_markup(text)

    def run(self):
        resp = gtk.MessageDialog.run(self)
        self.destroy()
        return resp

class ErrorMessage(Message):
    """Like Message, but uses an error-indicating picture."""
    def __init__(self, *args):
        Message.__init__(self, gtk.MESSAGE_ERROR, *args)

class WarningMessage(Message):
    """Like Message, but uses an warning-indicating picture."""
    def __init__(self, *args):
        Message.__init__(self, gtk.MESSAGE_WARNING, *args)

class Notebook(gtk.Notebook):
    """A regular gtk.Notebook, except when appending a page, if no
    label is given, the page's 'title' attribute (either a string or
    a widget) is used."""
    
    def append_page(self, page, label=None):
        if label is not None:
            if not isinstance(label, gtk.Widget): label = gtk.Label(label)
            gtk.Notebook.append_page(self, page, label)
        else:
            if hasattr(page, 'title'):
                title = page.title
                if not isinstance(title, gtk.Widget): title = gtk.Label(title)
                gtk.Notebook.append_page(self, page, title)
            else: raise TypeError("no page.title and no label given")

class ConfigCheckButton(gtk.CheckButton):
    """A CheckButton that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is *not* set to the current config value initially."""

    def __init__(self, label, section, option):
        gtk.CheckButton.__init__(self, label)
        self.connect('toggled', ConfigCheckButton.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())

class ComboBoxEntrySave(gtk.ComboBoxEntry):
    """A ComboBoxEntry that remembers the past 'count' strings entered,
    and can save itself to (and load itself from) a filename or file-like."""

    models = {}
    
    def __init__(self, f=None, initial=[], count=10, model=None):
        self.count = count
        if model:
            try:
                gtk.ComboBoxEntry.__init__(self, self.models[model], 0)
            except KeyError:
                gtk.ComboBoxEntry.__init__(self, gtk.ListStore(str), 0)
                self.models[model] = self.get_model()
                self.__fill(f, initial)
        else:
            gtk.ComboBoxEntry.__init__(self, gtk.ListStore(str), 0)
            self.__fill(f, initial)
        self.connect_object('destroy', self.set_model, None)

    def __fill(self, f, initial):
        if f is not None and not hasattr(f, 'readlines'):
            if os.path.exists(f):
                for line in file(f).readlines():
                    self.append_text(line.strip())
        elif f is not None:
            for line in f.readlines():
                self.append_text(line.strip())
        for c in initial: self.append_text(c)

    def prepend_text(self, text):
        try: self.remove_text(self.get_text().index(text))
        except ValueError: pass
        gtk.ComboBoxEntry.prepend_text(self, text)
        while len(self.get_model()) > self.count:
            self.remove_text(self.count)

    def insert_text(self, position, text):
        try: self.remove_text(self.get_text().index(text))
        except ValueError: pass
        if position >= self.count: return
        else:
            gtk.ComboBoxEntry.insert_text(self, position, text)
            while len(self.get_model()) > self.count:
                self.remove_text(self.count)

    def append_text(self, text):
        if text not in self.get_text():
            if len(self.get_model()) < self.count:
                gtk.ComboBoxEntry.append_text(self, text)

    def get_text(self):
        """Return a list of all entries in the history."""
        return [m[0] for m in self.get_model()]

    def write(self, f, create=True):
        """Save to f, a filename or file-like. If create is True, any
        needed parent directories will be created."""
        try:
            if not hasattr(f, 'read'):
                if ("/" in f and create and
                    not os.path.isdir(os.path.dirname(f))):
                    os.makedirs(os.path.dirname(f))
                f = file(f, "w")
            f.write("\n".join(self.get_text()) + "\n")
        except (IOError, OSError): pass

def Frame(label=None, border=0, bold=False, child=None):
    if isinstance(label, basestring):
        format = "%s"
        if bold: format  = "<b>%s</b>" % format
        markup = util.escape(label)
        markup = format % markup
        label = gtk.Label()
        label.set_markup(markup)
        label.set_use_underline(True)

    frame = gtk.Frame()
    frame.set_border_width(border)
    align = gtk.Alignment(xalign=0.0, yalign=0.0, xscale=1.0, yscale=1.0)
    align.set_padding(3, 0, 12, 0)
    frame.add(align)
    if child: align.add(child)
    frame.set_shadow_type(gtk.SHADOW_NONE)
    frame.set_label_widget(label)
    return frame

def MenuItem(text, image):
    i = gtk.ImageMenuItem(text)
    i.get_image().set_from_stock(image, gtk.ICON_SIZE_MENU)
    return i

def Button(text, image):
    # Stock image with custom label.
    hbox = gtk.HBox(spacing=2)
    i = gtk.Image()
    i.set_from_stock(image, gtk.ICON_SIZE_BUTTON)
    hbox.pack_start(i)
    l = gtk.Label(text)
    l.set_use_underline(True)
    hbox.pack_start(l)
    b = gtk.Button()
    b.add(hbox)
    return b

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
            sig = parent.connect('configure-event', self.__recenter)
            self.connect_object(
                'destroy', WaitLoadWindow.__disconnect, self, sig)
            self.set_transient_for(parent)
            parent.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self.set_modal(True)
        self.set_decorated(False)
        self.set_resizable(False)
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

class TreeViewHints(gtk.Window):
    """Handle 'hints' for treeviews. This includes expansions of truncated
    columns, and in the future, tooltips."""

    __gsignals__ = dict.fromkeys(
        ['button-press-event', 'button-release-event',
        'motion-notify-event', 'scroll-event'],
        'override')

    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.__label = label = gtk.Label()
        label.set_alignment(0.5, 0.5)
        self.realize()
        self.add_events(gtk.gdk.BUTTON_MOTION_MASK | gtk.gdk.BUTTON_PRESS_MASK |
                gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.KEY_PRESS_MASK |
                gtk.gdk.KEY_RELEASE_MASK | gtk.gdk.ENTER_NOTIFY_MASK |
                gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.SCROLL_MASK)
        self.add(label)

        self.set_app_paintable(True)
        self.set_resizable(False)
        self.set_name("gtk-tooltips")
        self.set_border_width(1)
        self.connect('expose-event', self.__expose)
        self.connect('enter-notify-event', self.__enter)
        self.connect('leave-notify-event', self.__check_undisplay)

        self.__handlers = {}
        self.__current_path = self.__current_col = None
        self.__current_renderer = None

    def connect_view(self, view):
        self.__handlers[view] = [
            view.connect('motion-notify-event', self.__motion),
            view.connect('scroll-event', self.__undisplay),
            view.connect('key-press-event', self.__undisplay),
            view.connect('destroy', self.disconnect_view),
        ]

    def disconnect_view(self, view):
        try:
            for handler in self.__handlers[view]: view.disconnect(handler)
            del self.__handlers[view]
        except KeyError: pass

    def __expose(self, widget, event):
        w, h = self.get_size_request()
        self.style.paint_flat_box(self.window,
                gtk.STATE_NORMAL, gtk.SHADOW_OUT,
                None, self, "tooltip", 0, 0, w, h)

    def __enter(self, widget, event):
        # on entry, kill the hiding timeout
        try: gobject.source_remove(self.__timeout_id)
        except AttributeError: pass
        else: del self.__timeout_id

    def __motion(self, view, event):
        # trigger over row area, not column headers
        if event.window is not view.get_bin_window(): return
        if event.get_state() & gtk.gdk.MODIFIER_MASK: return

        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return # no hints where no rows exist

        if self.__current_path == path and self.__current_col == col: return

        # need to handle more renderers later...
        try: renderer, = col.get_cell_renderers()
        except ValueError: return
        if not isinstance(renderer, gtk.CellRendererText): return
        if renderer.get_property('ellipsize') == pango.ELLIPSIZE_NONE: return

        model = view.get_model()
        col.cell_set_cell_data(model, model.get_iter(path), False, False)
        cellw = col.cell_get_position(renderer)[1]

        label = self.__label
        label.set_text(renderer.get_property('text'))
        w, h0 = label.get_layout().get_pixel_size()
        try: markup = renderer.markup
        except AttributeError: h1 = h0
        else:
            if isinstance(markup, int): markup = model[path][markup]
            label.set_markup(markup)
            w, h1 = label.get_layout().get_pixel_size()

        if w + 5 < cellw: return # don't display if it doesn't need expansion

        x, y, cw, h = list(view.get_cell_area(path, col))
        self.__dx = x
        self.__dy = y
        y += view.get_bin_window().get_position()[1]
        ox, oy = view.window.get_origin()
        x += ox; y += oy; w += 5#; h += h1 - h0
        screen_width = gtk.gdk.screen_width()
        x_overflow = min([x, x + w - screen_width])
        label.set_ellipsize(pango.ELLIPSIZE_NONE)
        if x_overflow > 0:
            self.__dx -= x_overflow
            x -= x_overflow
            w = min([w, screen_width])
            label.set_ellipsize(pango.ELLIPSIZE_END)
        if not((x<=int(event.x_root) < x+w) and (y <= int(event.y_root) < y+h)):
            return # reject if cursor isn't above hint

        self.__target = view
        self.__current_renderer = renderer
        self.__edit_id = renderer.connect('editing-started', self.__undisplay)
        self.__current_path = path
        self.__current_col = col
        self.__time = event.time
        self.__timeout(id=gobject.timeout_add(100, self.__undisplay))
        self.set_size_request(w, h)
        self.resize(w, h)
        self.move(x, y)
        self.show_all()

    def __check_undisplay(self, ev1, event):
        if self.__time < event.time + 50: self.__undisplay()

    def __undisplay(self, *args):
        if self.__current_renderer and self.__edit_id:
            self.__current_renderer.disconnect(self.__edit_id)
        self.__current_renderer = self.__edit_id = None
        self.__current_path = self.__current_col = None
        self.hide()

    def __timeout(self, ev=None, event=None, id=None):
        try: gobject.source_remove(self.__timeout_id)
        except AttributeError: pass
        if id is not None: self.__timeout_id = id

    def __event(self, event):
        if event.type != gtk.gdk.SCROLL:
            event.x += self.__dx
            event.y += self.__dy 

        # modifying event.window is a necessary evil, made okay because
        # nobody else should tie to any TreeViewHints events ever.
        event.window = self.__target.get_bin_window()

        gtk.main_do_event(event)
        return True

    def do_button_press_event(self, event): return self.__event(event)
    def do_button_release_event(self, event): return self.__event(event)
    def do_motion_notify_event(self, event): return self.__event(event)
    def do_scroll_event(self, event): return self.__event(event)

gobject.type_register(TreeViewHints)

class HintedTreeView(gtk.TreeView):
    """A TreeView that pops up a tooltip when you hover over a cell that
    contains ellipsized text."""

    def __init__(self, *args):
        gtk.TreeView.__init__(self, *args)
        try: tvh = HintedTreeView.hints
        except AttributeError: tvh = HintedTreeView.hints = TreeViewHints()
        tvh.connect_view(self)

class BigCenteredImage(gtk.Window):
    """Load an image and display it, scaling down to 1/2 the screen's
    dimensions if necessary.

    This might leak memory, but it could just be Python's GC being dumb."""

    def __init__(self, title, filename):
        gtk.Window.__init__(self)
        width = gtk.gdk.screen_width() / 2
        height = gtk.gdk.screen_height() / 2
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)

        x_rat = pixbuf.get_width() / float(width)
        y_rat = pixbuf.get_height() / float(height)
        if x_rat > 1 or y_rat > 1:
            if x_rat > y_rat: height = int(pixbuf.get_height() / x_rat)
            else: width = int(pixbuf.get_width() / y_rat)
            pixbuf = pixbuf.scale_simple(
                width, height, gtk.gdk.INTERP_BILINEAR)

        self.set_title(title)
        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_modal(False)
        self.set_icon(pixbuf)
        self.add(gtk.Frame())
        self.child.set_shadow_type(gtk.SHADOW_OUT)
        self.child.add(gtk.EventBox())
        self.child.child.add(gtk.Image())
        self.child.child.child.set_from_pixbuf(pixbuf)

        self.child.child.connect_object(
            'button-press-event', BigCenteredImage.__destroy, self)
        self.child.child.connect_object(
            'key-press-event', BigCenteredImage.__destroy, self)
        self.show_all()

    def __destroy(self, event):
        self.destroy()

class PopupHSlider(gtk.EventBox):
    # Based on the Rhythmbox volume control button; thanks to Colin Walters,
    # Richard Hult, Michael Fulbright, Miguel de Icaza, and Federico Mena.

    def __init__(self):
        gtk.EventBox.__init__(self)
        button = gtk.Button()
        button.add(gtk.HBox(spacing=3))
        self.label = gtk.Label()
        button.child.pack_start(self.label)
        button.child.pack_start(
            gtk.Arrow(gtk.ARROW_RIGHT, gtk.SHADOW_IN), expand=False)
        self.add(button)
        button.connect('clicked', self.__clicked)
        self.show_all()

        window = self.__window = gtk.Window(gtk.WINDOW_POPUP)
        self.__adj = gtk.Adjustment(0, 0, 0, 3600, 15000, 0)

        frame = gtk.Frame()
        frame.set_border_width(0)
        frame.set_shadow_type(gtk.SHADOW_OUT)

        hscale = gtk.HScale(self.__adj)
        hscale.set_size_request(190, -1)
        window.connect('button-press-event', self.__button)
        hscale.connect('key-press-event', self.__key)
        hscale.set_draw_value(False)
        hscale.set_update_policy(gtk.UPDATE_DELAYED)
        self.scale = hscale
        window.add(frame)
        frame.add(hscale)
        button.connect('scroll-event', self.__scroll, hscale)
        self.__window.connect('scroll-event', self.__scroll, hscale)

    def __clicked(self, button):
        if self.__window.get_property('visible'): return
        max_y = gtk.gdk.screen_height()
        req = self.__window.size_request()
        x, y = self.child.child.window.get_origin()
        w, h = self.child.child.window.get_size()
        self.__window.show_all()
        ww, wh = self.__window.child.parent.get_size()

        sx = x + w + 3
        sy = y + (h - wh)/2
        self.__window.move(sx, sy)
        self.__window.grab_focus()
        self.__window.grab_add()
        pointer = gtk.gdk.pointer_grab(
            self.__window.window, True,
            gtk.gdk.BUTTON_PRESS_MASK |
            gtk.gdk.BUTTON_RELEASE_MASK |
            gtk.gdk.BUTTON_MOTION_MASK |
            gtk.gdk.POINTER_MOTION_MASK |
            gtk.gdk.SCROLL_MASK, None, None, gtk.get_current_event_time())
        keyboard = gtk.gdk.keyboard_grab(
            self.__window.window, True, gtk.get_current_event_time())

        if pointer != gtk.gdk.GRAB_SUCCESS or keyboard != gtk.gdk.GRAB_SUCCESS:
            self.__window.grab_remove()
            self.__window.hide()

            if pointer == gtk.gdk.GRAB_SUCCESS:
                gtk.gdk.pointer_ungrab(gtk.get_current_event_time())
            if keyboard == gtk.gdk.GRAB_SUCCESS:
                gtk.gdk.keyboark_ungrab(gtk.get_current_event_time())

    def __scroll(self, widget, ev, hscale):
        adj = self.__adj
        v = hscale.get_value()
        if ev.direction in [gtk.gdk.SCROLL_DOWN, gtk.gdk.SCROLL_LEFT]:
            v += adj.step_increment
        elif ev.direction in [gtk.gdk.SCROLL_UP, gtk.gdk.SCROLL_RIGHT]:
            v -= adj.step_increment
        v = min(adj.upper, max(adj.lower, v))
        hscale.set_value(v)
        hscale.emit('adjust-bounds', v)

    def __button(self, widget, ev):
        self.__popup_hide()

    def __key(self, hscale, ev):
        if ev.string in ["\n", "\r", " ", "\x1b"]: # enter, space, escape
            self.__popup_hide()

    def __popup_hide(self):
        self.__window.grab_remove()
        gtk.gdk.pointer_ungrab(gtk.get_current_event_time())
        gtk.gdk.keyboard_ungrab(gtk.get_current_event_time())
        self.__window.hide()
