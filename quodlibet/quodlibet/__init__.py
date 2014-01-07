# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import __builtin__

_dummy_gettext = lambda value: value
_dummy_ngettext = lambda v1, v2, count: (count == 1) and v1 or v2
__builtin__.__dict__["_"] = _dummy_gettext
__builtin__.__dict__["Q_"] = _dummy_gettext
__builtin__.__dict__["N_"] = _dummy_gettext
__builtin__.__dict__["ngettext"] = _dummy_ngettext

import gettext
import locale
import os
import re
import sys

import quodlibet.const
import quodlibet.util

from quodlibet.util.path import mkdir, unexpand
from quodlibet.util.i18n import GlibTranslations
from quodlibet.util.dprint import print_, print_d, print_w, print_e
from quodlibet.const import MinVersions, Version


class Application(object):
    """A main application class for controlling the application as a whole
    and accessing sub-modules.

    window    - The main window which is present as long as QL is running
    library   - The main library (see library.SongFileLibrary)
    librarian - The main (and atm only) librarian (see library.SongLibrarian)
    player    - see player._base

    quit()    - Quit the application

    """

    window = None
    library = None
    player = None

    @property
    def librarian(self):
        return self.library.librarian

    def quit(self):
        from gi.repository import GLib

        def idle_quit():
            if self.window and not self.window.in_destruction():
                self.window.destroy()

        # so this can be called from a signal handler and before
        # the main loop starts
        GLib.idle_add(idle_quit, priority=GLib.PRIORITY_HIGH)

    def show(self):
        from quodlibet.qltk import Window
        self.window.show()
        for window in Window.instances:
            window.show()

    def present(self):
        # deiconify is needed if the window is on another workspace
        from quodlibet.qltk import Window
        self.window.deiconify()
        self.window.present()
        for window in Window.instances:
            window.deiconify()
            window.present()

    def hide(self):
        from quodlibet.qltk import Window
        for window in Window.instances:
            window.hide()
        self.window.hide()

app = Application()


def _gtk_init(icon=None):
    import gi

    try:
        # not sure if this is available under Windows
        gi.require_version("GdkX11", "3.0")
        from gi.repository import GdkX11
    except (ValueError, ImportError):
        pass

    gi.require_version("GLib", "2.0")
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GObject", "2.0")
    gi.require_version("Pango", "1.0")
    gi.require_version("GdkPixbuf", "2.0")
    gi.require_version("Gio", "2.0")

    from gi.repository import Gtk, GObject, GLib, Gdk

    # add Gtk.TreePath.__getitem__/__len__ for PyGObject 3.2
    try:
        Gtk.TreePath()[0]
    except TypeError:
        Gtk.TreePath.__getitem__ = lambda self, index: list(self)[index]
        Gtk.TreePath.__len__ = lambda self: self.get_depth()

    # GTK+ 3.4+ constants
    if not hasattr(Gdk, "BUTTON_PRIMARY"):
        Gdk.BUTTON_PRIMARY = 1
        Gdk.BUTTON_MIDDLE = 2
        Gdk.BUTTON_SECONDARY = 3

    # Make sure PyGObject includes support for foreign cairo structs
    some_window = Gtk.OffscreenWindow()
    some_window.show()
    try:
        some_window.get_surface()
    except TypeError:
        print_e("PyGObject is missing cairo support")
        exit(1)

    # We don't depend on Gst overrides, so make sure it's initialized.
    try:
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except (ValueError, ImportError):
        pass
    else:
        if not Gst.is_initialized():
            try:
                ok, argv = Gst.init_check(sys.argv)
            except GLib.GError:
                print_e("Failed to initialize GStreamer")
                # Uninited Gst segfaults: make sure no one can use it
                sys.modules["gi.repository.Gst"] = None
            else:
                sys.argv = argv

                # https://bugzilla.gnome.org/show_bug.cgi?id=710447
                import threading
                threading.Thread(target=lambda: None).start()

    # some code depends on utf-8 default encoding (pygtk used to set it)
    reload(sys)
    sys.setdefaultencoding("utf-8")

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["gtk"] = None
    sys.modules["gpod"] = None
    sys.modules["glib"] = None
    sys.modules["gobject"] = None
    sys.modules["gnome"] = None

    from quodlibet.qltk import pygobject_version
    if pygobject_version < (3, 9):
        GObject.threads_init()

    theme = Gtk.IconTheme.get_default()
    theme.append_search_path(quodlibet.const.IMAGEDIR)

    if icon:
        Gtk.Window.set_default_icon_name(icon)


def _dbus_init():
    try:
        from dbus.mainloop.glib import DBusGMainLoop, threads_init
    except ImportError:
        try:
            import dbus.glib
        except ImportError:
            return
    else:
        threads_init()
        DBusGMainLoop(set_as_default=True)


def _gettext_init():
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass

    unexpand = quodlibet.util.path.unexpand

    # Use the locale dir in ../build/share/locale if there is one
    localedir = os.path.dirname(quodlibet.const.BASEDIR)
    localedir = os.path.join(localedir, "build", "share", "locale")
    if os.path.isdir(localedir):
        print_d("Using local localedir: %r" % unexpand(localedir))
        gettext.bindtextdomain("quodlibet", localedir)

    localedir = gettext.bindtextdomain("quodlibet")
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        langs = filter(None, map(locale.windows_locale.get,
            [k32.GetUserDefaultLCID(), k32.GetSystemDefaultLCID()]))
        os.environ.setdefault('LANG', ":".join(langs))
        localedir = os.path.join(
            quodlibet.const.BASEDIR, "..", "..", "share", "locale")

    try:
        t = gettext.translation("quodlibet", localedir,
            class_=GlibTranslations)
    except IOError:
        print_d("No translation found in %r" % unexpand(localedir))
        t = GlibTranslations()
    else:
        print_d("Translations loaded: %r" % unexpand(t.path))

    t.install(unicode=True)


def set_process_title(title):
    """Sets process name as visible in ps or top. Requires ctypes libc
    and is almost certainly *nix-only. See issue 736"""

    if os.name == "nt":
        return

    try:
        import ctypes
        libc = ctypes.CDLL('libc.so.6')
        # 15 = PR_SET_NAME, apparently
        libc.prctl(15, title, 0, 0, 0)
    except:
        print_d("Couldn't find module libc.so.6 (ctypes). "
                "Not setting process title.")


def _python_init():

    import sys
    if sys.version_info < MinVersions.PYTHON:
        actual = Version(sys.version_info[:3])
        print_w("Python %s required. %s found." % (MinVersions.PYTHON, actual))

    # The default regex escaping function doesn't work for non-ASCII.
    # Use a blacklist of regex-specific characters instead.
    def re_esc(str, BAD="/.^$*+?{,\\[]|()<>#=!:"):
        needs_escape = lambda c: (c in BAD and "\\" + c) or c
        return "".join(map(needs_escape, str))
    re.escape = re_esc

    __builtin__.__dict__["print_"] = print_
    __builtin__.__dict__["print_d"] = print_d
    __builtin__.__dict__["print_e"] = print_e
    __builtin__.__dict__["print_w"] = print_w

del(_dummy_gettext)
del(_dummy_ngettext)

_python_init()
_gettext_init()


def exit(status=None, notify_startup=False):
    """Call this to abort the startup before any mainloop starts.

    notify_startup needs to be true if QL could potentially have been
    called from the desktop file.
    """

    if notify_startup:
        from gi.repository import Gdk
        Gdk.notify_startup_complete()
    raise SystemExit(status)


def init(library=None, icon=None, title=None, name=None):
    print_d("Entering quodlibet.init")

    _gtk_init(icon)
    _dbus_init()

    from gi.repository import GLib

    if title:
        GLib.set_prgname(title)
        set_process_title(title)
        # Issue 736 - set after main loop has started (gtk seems to reset it)
        GLib.idle_add(set_process_title, title)

    if name:
        GLib.set_application_name(name)

    # We already imported this, but Python is dumb and thinks we're rebinding
    # a local when we import it later.
    import quodlibet.util
    quodlibet.util.path.mkdir(quodlibet.const.USERDIR, 0750)

    if library:
        print_d("Initializing main library (%s)" % (
            quodlibet.util.path.unexpand(library)))

    import quodlibet.library
    library = quodlibet.library.init(library)

    _init_debug()

    print_d("Finished initialization.")

    return library


def init_plugins(no_plugins=False):
    print_d("Starting plugin manager")

    from quodlibet import plugins
    folders = [os.path.join(quodlibet.const.BASEDIR, "plugins", "editing"),
               os.path.join(quodlibet.const.BASEDIR, "plugins", "events"),
               os.path.join(quodlibet.const.BASEDIR, "plugins", "playorder"),
               os.path.join(quodlibet.const.BASEDIR, "plugins", "songsmenu"),
               os.path.join(quodlibet.const.BASEDIR, "plugins", "gstreamer"),
               os.path.join(quodlibet.const.BASEDIR, "plugins", "covers"),
               os.path.join(quodlibet.const.USERDIR, "plugins")]
    pm = plugins.init(folders, no_plugins)
    pm.rescan()

    from quodlibet.qltk.edittags import EditTags
    from quodlibet.qltk.renamefiles import RenameFiles
    from quodlibet.qltk.tagsfrompath import TagsFromPath
    EditTags.init_plugins()
    RenameFiles.init_plugins()
    TagsFromPath.init_plugins()

    return pm


def init_backend(backend, librarian):
    import quodlibet.player
    print_d("Initializing audio backend (%s)" % backend)
    backend = quodlibet.player.init(backend)
    device = backend.init(librarian)
    return device


def enable_periodic_save(save_library):
    import quodlibet.library
    from quodlibet.util import copool
    from quodlibet import config

    timeout = 5 * 60 * 1000  # 5 minutes

    def periodic_config_save():
        while 1:
            config.save(quodlibet.const.CONFIG)
            yield

    copool.add(periodic_config_save, timeout=timeout)

    if not save_library:
        return

    def periodic_library_save():
        while 1:
            quodlibet.library.save()
            yield

    copool.add(periodic_library_save, timeout=timeout)


def _init_debug():
    from gi.repository import GLib
    from quodlibet.qltk.debugwindow import ExceptionDialog

    print_d("Initializing debugging extensions")

    def _override_exceptions():
        print_d("Enabling custom exception handler.")
        sys.excepthook = ExceptionDialog.excepthook
    GLib.idle_add(_override_exceptions)

    # faulthandler gives a python stacktrace on segfaults..
    try:
        import faulthandler
    except ImportError:
        pass
    else:
        faulthandler.enable()


def _init_signal():
    """Catches certain signals and quits the application once the
    mainloop has started."""

    import os

    if os.name == "nt":
        return

    def signal_action():
        app.quit()

    import signal
    import gi
    gi.require_version("GLib", "2.0")
    from gi.repository import GLib

    SIGS = [getattr(signal, s, None) for s in "SIGINT SIGTERM SIGHUP".split()]
    for sig in filter(None, SIGS):
        # Before the mainloop starts we catch signals in python
        # directly and idle_add the app.quit
        def idle_handler(*args):
            print_d("Python signal handler activated.")
            GLib.idle_add(signal_action, priority=GLib.PRIORITY_HIGH)
        print_d("Register Python signal handler: %r" % sig)
        signal.signal(sig, idle_handler)

        # After the mainloop has started the python handler
        # blocks if no mainloop is active (for whatever reason).
        # Override the python handler with the GLib one, which works here.
        def install_glib_handler(sig):

            def handler(*args):
                print_d("GLib signal handler activated.")
                signal_action()
            unix_signal_add = None

            if hasattr(GLib, "unix_signal_add"):
                unix_signal_add = GLib.unix_signal_add
            elif hasattr(GLib, "unix_signal_add_full"):
                unix_signal_add = GLib.unix_signal_add_full

            if unix_signal_add:
                print_d("Register GLib signal handler: %r" % sig)
                unix_signal_add(GLib.PRIORITY_HIGH, sig, handler, None)
            else:
                print_d("Can't install GLib signal handler, too old gi.")
        GLib.idle_add(install_glib_handler, sig, priority=GLib.PRIORITY_HIGH)

# minimal emulation of gtk.quit_add

_quit_funcs = []


def quit_add(level, func, *args):
    assert level in (0, 1)
    _quit_funcs.append([level, func, args])


def _quit_before():
    for level, func, args in _quit_funcs:
        if level != 0:
            func(*args)


def _quit_after():
    for level, func, args in _quit_funcs:
        if level == 0:
            func(*args)


def main(window):
    print_d("Entering quodlibet.main")
    from gi.repository import Gtk

    def quit_gtk(m):
        _quit_before()
        # disable plugins
        import quodlibet.plugins
        quodlibet.plugins.quit()

        # stop all copools
        print_d("Quit GTK: Stop all copools")
        from quodlibet.util import copool
        copool.remove_all()

        # events that add new events to the main loop (like copool)
        # can block the shutdown, so force stop after some time.
        # gtk.main_iteration will return True if quit gets called here
        from gi.repository import GLib
        GLib.timeout_add(4 * 1000, Gtk.main_quit,
                         priority=GLib.PRIORITY_HIGH)

        # See which browser windows are open and save their names
        # so we can restore them on start
        from quodlibet.qltk.browser import LibraryBrowser
        LibraryBrowser.save()

        # destroy all open windows so they hide immediately on close:
        # destroying all top level windows doesn't work (weird errors),
        # so we hide them all and only destroy our tracked instances
        # (browser windows, tag editors, pref window etc.)
        from quodlibet.qltk import Window
        map(Gtk.Window.hide, Gtk.Window.list_toplevels())
        map(Gtk.Window.destroy, Window.instances)

        print_d("Quit GTK: Process pending events...")
        while Gtk.events_pending():
            if Gtk.main_iteration_do(False):
                print_d("Quit GTK: Timeout occurred, force quit.")
                break
        else:
            Gtk.main_quit()

        print_d("Quit GTK: done.")

    window.connect('destroy', quit_gtk)
    window.show()

    Gtk.main()

    _quit_after()
