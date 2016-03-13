# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gettext
import locale
import os
import sys
import warnings

from quodlibet.compat import builtins, PY2

if PY2:
    # some code depends on utf-8 default encoding (pygtk used to set it)
    reload(sys)
    sys.setdefaultencoding("utf-8")

from quodlibet.util import set_process_title, environ, cached_func
from quodlibet.util import windows, is_osx, is_windows
from quodlibet.util.path import mkdir, unexpand
from quodlibet.util.i18n import GlibTranslations, set_i18n_envvars, \
    fixup_i18n_envvars
from quodlibet.util.dprint import print_, print_d, print_w, print_e
from quodlibet import const
from quodlibet.const import MinVersions
from quodlibet.compat import PY2


PLUGIN_DIRS = ["editing", "events", "playorder", "songsmenu", "playlist",
               "gstreamer", "covers", "query"]


GlibTranslations().install(unicode=True)

_cli_initialized = False
_initialized = False


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

    player_options = None
    """A PlayerOptions instance or None in case there is no playback support"""

    cover_manager = None

    name = None
    """The application name e.g. 'Quod Libet'"""

    id = None
    """The application ID e.g. 'quodlibet'"""

    @property
    def icon_name(self):
        return self.id

    @property
    def symbolic_icon_name(self):
        return "%s-symbolic" % self.icon_name

    @property
    def librarian(self):
        return self.library.librarian

    @property
    def browser(self):
        return self.window.browser

    def quit(self):
        from gi.repository import GLib

        def idle_quit():
            if self.window:
                self.window.destroy()

        # so this can be called from a signal handler and before
        # the main loop starts
        GLib.idle_add(idle_quit, priority=GLib.PRIORITY_HIGH)

    def show(self):
        from quodlibet.qltk import Window
        for window in Window.windows:
            window.show()

    def present(self):
        # deiconify is needed if the window is on another workspace
        from quodlibet.qltk import Window
        for window in Window.windows:
            window.deiconify()
            window.present()

    def hide(self):
        from quodlibet.qltk import Window
        for window in Window.windows:
            window.hide()

app = Application()


def is_release():
    """Returns whether the running version is a stable release or under
    development.
    """

    return const.VERSION_TUPLE[-1] != -1


@cached_func
def get_base_dir():
    """The path to the quodlibet package"""

    file_path = __file__
    if os.name == "nt":
        file_path = file_path.decode(sys.getfilesystemencoding())
    return os.path.dirname(os.path.realpath(file_path))


@cached_func
def get_image_dir():
    """The path to the image directory in the quodlibet package"""

    return os.path.join(get_base_dir(), "images")


@cached_func
def get_user_dir():
    """Place where QL saves its state, database, config etc."""

    if os.name == "nt":
        USERDIR = os.path.join(windows.get_appdate_dir(), "Quod Libet")
    else:
        USERDIR = os.path.join(os.path.expanduser("~"), ".quodlibet")

    if not PY2:
        USERDIR += "_py3"

    if 'QUODLIBET_USERDIR' in environ:
        USERDIR = environ['QUODLIBET_USERDIR']

    # XXX: Exec conf.py in this directory, used to override const globals
    # e.g. for setting USERDIR for the Windows portable version
    # Note: execfile doesn't handle unicode paths on windows, so encode.
    # (this doesn't use the old win api in case of str compared to os.*)
    _CONF_PATH = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "conf.py")

    if PY2:
        locals_ = {}
        # FIXME: PY3PORT
        try:
            execfile(_CONF_PATH, globals(), locals_)
        except IOError:
            pass
        else:
            USERDIR = locals_["USERDIR"]

    # XXX: users shouldn't assume the dir is there, but we currently do in
    # some places
    mkdir(USERDIR, 0o750)

    return USERDIR


def _fix_gst_leaks():
    """gst_element_add_pad and gst_bin_add are wrongly annotated and lead
    to PyGObject refing the passed element.

    Work around by adding a wrapper that unrefs afterwards.
    Can be called multiple times.

    https://bugzilla.gnome.org/show_bug.cgi?id=741390
    https://bugzilla.gnome.org/show_bug.cgi?id=702960
    """

    from gi.repository import Gst

    assert Gst.is_initialized()

    def do_wrap(func):
        def wrap(self, obj):
            result = func(self, obj)
            obj.unref()
            return result
        return wrap

    parent = Gst.Bin()
    elm = Gst.Bin()
    parent.add(elm)
    if elm.__grefcount__ == 3:
        elm.unref()
        Gst.Bin.add = do_wrap(Gst.Bin.add)

    pad = Gst.Pad.new("foo", Gst.PadDirection.SRC)
    parent.add_pad(pad)
    if pad.__grefcount__ == 3:
        pad.unref()
        Gst.Element.add_pad = do_wrap(Gst.Element.add_pad)


def _init_g():
    """Call before using GdkPixbuf/GLib/Gio/GObject"""

    import gi

    gi.require_version("GLib", "2.0")
    gi.require_version("Gio", "2.0")
    gi.require_version("GObject", "2.0")
    gi.require_version("GdkPixbuf", "2.0")

    from gi.repository import GdkPixbuf

    # On windows the default variants only do ANSI paths, so replace them.
    # In some typelibs they are replaced by default, in some don't..
    if os.name == "nt":
        for name in ["new_from_file_at_scale", "new_from_file_at_size",
                     "new_from_file"]:
            cls = GdkPixbuf.Pixbuf
            setattr(cls, name, getattr(cls, name + "_utf8", name))

    # https://bugzilla.gnome.org/show_bug.cgi?id=670372
    if not hasattr(GdkPixbuf.Pixbuf, "savev"):
        GdkPixbuf.Pixbuf.savev = GdkPixbuf.Pixbuf.save

    # Newer glib is noisy regarding deprecated signals/properties
    # even with stable releases.
    if is_release():
        warnings.filterwarnings(
            'ignore', '.* It will be removed in a future version.',
            Warning)

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["glib"] = None
    sys.modules["gobject"] = None


def _init_gtk():
    """Call before using Gtk/Gdk"""

    import gi

    # pygiaio 3.14rev16 switched to fontconfig for PangoCairo. As this results
    # in 100% CPU under win7 revert it. Maybe we need to update the
    # cache in the windows installer for it to work... but for now revert.
    if is_windows():
        os.environ['PANGOCAIRO_BACKEND'] = 'win32'

    # disable for consistency and trigger events seem a bit flaky here
    if is_osx():
        os.environ["GTK_OVERLAY_SCROLLING"] = "0"

    # make sure GdkX11 doesn't get used under Windows
    if os.name == "nt":
        sys.modules["gi.repository.GdkX11"] = None

    try:
        # not sure if this is available under Windows
        gi.require_version("GdkX11", "3.0")
        from gi.repository import GdkX11
        GdkX11
    except (ValueError, ImportError):
        pass

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("Pango", "1.0")
    gi.require_version('Soup', '2.4')

    from gi.repository import Gtk, Gdk

    # PyGObject doesn't fail anymore when init fails, so do it ourself
    initialized, argv = Gtk.init_check(sys.argv)
    if not initialized:
        raise SystemExit("Gtk.init failed")
    sys.argv = list(argv)

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

    if not hasattr(Gdk, "EVENT_PROPAGATE"):
        Gdk.EVENT_PROPAGATE = 0
        Gdk.EVENT_STOP = 1

    # include our own icon theme directory
    theme = Gtk.IconTheme.get_default()
    theme_search_path = get_image_dir()
    assert os.path.exists(theme_search_path)
    theme.append_search_path(theme_search_path)

    # Force menu/button image related settings. We might show too many atm
    # but this makes sure we don't miss cases where we forgot to force them
    # per widget.
    # https://bugzilla.gnome.org/show_bug.cgi?id=708676
    warnings.filterwarnings('ignore', '.*g_value_get_int.*', Warning)

    # some day... but not now
    warnings.filterwarnings(
        'ignore', '.*Stock items are deprecated.*', Warning)
    warnings.filterwarnings(
        'ignore', '.*:use-stock.*', Warning)
    warnings.filterwarnings(
        'ignore', '.*The property GtkAlignment:[^\s]+ is deprecated.*',
        Warning)

    settings = Gtk.Settings.get_default()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        settings.set_property("gtk-button-images", True)
        settings.set_property("gtk-menu-images", True)
    if hasattr(settings.props, "gtk_primary_button_warps_slider"):
        # https://bugzilla.gnome.org/show_bug.cgi?id=737843
        settings.set_property("gtk-primary-button-warps-slider", True)

    # Make sure PyGObject includes support for foreign cairo structs
    try:
        gi.require_foreign("cairo")
    except AttributeError:
        # older pygobject
        pass
    except ImportError:
        print_e("PyGObject is missing cairo support")
        exit(1)

    # CSS overrides
    if os.name == "nt":
        # somehow borders are missing under Windows & Gtk+3.14
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data("""
            .menu {
                border: 1px solid @borders;
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    if sys.platform == "darwin":
        # fix duplicated shadows for popups with Gtk+3.14
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data("""
            GtkWindow {
                box-shadow: none;
            }
            .tooltip {
                border-radius: 0;
                padding: 0;
            }
            .tooltip.background {
                background-clip: border-box;
            }
            """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # https://bugzilla.gnome.org/show_bug.cgi?id=708676
    warnings.filterwarnings('ignore', '.*g_value_get_int.*', Warning)

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["gtk"] = None
    sys.modules["gpod"] = None
    sys.modules["gnome"] = None

    from quodlibet.qltk import pygobject_version, gtk_version

    MinVersions.GTK.check(gtk_version)
    MinVersions.PYGOBJECT.check(pygobject_version)


def _init_gst():
    """Call once before importing GStreamer"""

    assert "gi.repository.Gst" not in sys.modules

    import gi

    # We don't want python-gst, it changes API..
    assert "gi.overrides.Gst" not in sys.modules
    sys.modules["gi.overrides.Gst"] = None

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["gst"] = None

    # We don't depend on Gst overrides, so make sure it's initialized.
    try:
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except (ValueError, ImportError):
        return

    if Gst.is_initialized():
        return

    from gi.repository import GLib

    try:
        ok, argv = Gst.init_check(sys.argv)
    except GLib.GError:
        print_e("Failed to initialize GStreamer")
        # Uninited Gst segfaults: make sure no one can use it
        sys.modules["gi.repository.Gst"] = None
    else:
        sys.argv = argv

        # monkey patching ahead
        _fix_gst_leaks()

        # https://bugzilla.gnome.org/show_bug.cgi?id=710447
        import threading
        threading.Thread(target=lambda: None).start()


def _init_dbus():
    """Setup dbus mainloop integration. Call before using dbus"""

    try:
        from dbus.mainloop.glib import DBusGMainLoop, threads_init
    except ImportError:
        try:
            import dbus.glib
            dbus.glib
        except ImportError:
            return
    else:
        threads_init()
        DBusGMainLoop(set_as_default=True)


def _init_gettext():
    """Call before using gettext helpers"""

    set_i18n_envvars()
    fixup_i18n_envvars()

    print_d("LANGUAGE: %r" % environ.get("LANGUAGE"))
    print_d("LANG: %r" % environ.get("LANG"))

    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass

    # Use the locale dir in ../build/share/locale if there is one
    base_dir = get_base_dir()
    localedir = os.path.dirname(base_dir)
    localedir = os.path.join(localedir, "build", "share", "locale")
    if not os.path.isdir(localedir) and os.name == "nt":
        # py2exe case
        localedir = os.path.join(
            base_dir, "..", "..", "share", "locale")

    if os.path.isdir(localedir):
        print_d("Using local localedir: %r" % unexpand(localedir))
    else:
        localedir = gettext.bindtextdomain("quodlibet")

    try:
        t = gettext.translation("quodlibet", localedir,
            class_=GlibTranslations)
    except IOError:
        print_d("No translation found in %r" % unexpand(localedir))
        t = GlibTranslations()
    else:
        print_d("Translations loaded: %r" % unexpand(t.path))

    debug_text = environ.get("QUODLIBET_TEST_TRANS")
    t.install(unicode=True, debug_text=debug_text)


def _init_python():
    if PY2 or is_release():
        MinVersions.PYTHON2.check(sys.version_info)
    else:
        # for non release builds we allow Python3
        MinVersions.PYTHON3.check(sys.version_info)

    builtins.__dict__["print_"] = print_
    builtins.__dict__["print_d"] = print_d
    builtins.__dict__["print_e"] = print_e
    builtins.__dict__["print_w"] = print_w


def _init_formats():
    from quodlibet.formats import init
    init()


def init_cli(no_translations=False):
    """This needs to be called before any API can be used.
    Might raise in case of an error.

    Like init() but for code not using Gtk etc.
    """

    global _cli_initialized

    if _cli_initialized:
        return

    from quodlibet import config

    _init_python()
    config.init_defaults()
    if not no_translations and "QUODLIBET_NO_TRANS" not in environ:
        _init_gettext()
    _init_formats()
    _init_g()

    _cli_initialized = True


def init(no_translations=False, no_excepthook=False):
    """This needs to be called before any API can be used.
    Might raise in case of an error.

    Pass no_translations=True to disable translations (used by tests)
    """

    global _initialized

    if _initialized:
        return

    init_cli(no_translations=no_translations)
    _init_gtk()
    _init_gtk_debug(no_excepthook=no_excepthook)
    _init_gst()
    _init_dbus()

    _initialized = True


def init_plugins(no_plugins=False):
    print_d("Starting plugin manager")

    from quodlibet import plugins
    folders = [os.path.join(get_base_dir(), "ext", kind)
               for kind in PLUGIN_DIRS]
    folders.append(os.path.join(get_user_dir(), "plugins"))
    print_d("Scanning folders: %s" % folders)
    pm = plugins.init(folders, no_plugins)
    pm.rescan()

    from quodlibet.qltk.edittags import EditTags
    from quodlibet.qltk.renamefiles import RenameFiles
    from quodlibet.qltk.tagsfrompath import TagsFromPath
    EditTags.init_plugins()
    RenameFiles.init_plugins()
    TagsFromPath.init_plugins()

    return pm


def enable_periodic_save(save_library):
    import quodlibet.library
    from quodlibet.util import copool
    from quodlibet import config

    timeout = 5 * 60 * 1000  # 5 minutes

    def periodic_config_save():
        while 1:
            config.save()
            yield

    copool.add(periodic_config_save, timeout=timeout)

    if not save_library:
        return

    def periodic_library_save():
        while 1:
            # max every 15 minutes
            quodlibet.library.save(save_period=15 * 60)
            yield

    copool.add(periodic_library_save, timeout=timeout)


def is_first_session(app_name):
    """Returns True if the current session is the first one to e.g.
    show a wizard/setup dialog etc.

    Will return True after each upgrade as well.

    app_name: e.g. 'quodlibet'
    """

    from quodlibet import config
    from quodlibet import const

    value = config.get("memory", "%s_last_active_version" % app_name, "")

    if value != const.VERSION:
        return True

    return False


def finish_first_session(app_name):
    """Call on shutdown so that is_first_session() works"""

    from quodlibet import config
    from quodlibet import const

    config.set("memory", "%s_last_active_version" % app_name, const.VERSION)


def _init_gtk_debug(no_excepthook):
    from gi.repository import GLib
    from quodlibet.qltk.debugwindow import ExceptionDialog

    print_d("Initializing debugging extensions")

    def _override_exceptions():
        print_d("Enabling custom exception handler.")
        sys.excepthook = ExceptionDialog.excepthook
    if not no_excepthook:
        GLib.idle_add(_override_exceptions)

    # faulthandler gives a python stacktrace on segfaults..
    try:
        import faulthandler
    except ImportError:
        pass
    else:
        faulthandler.enable()


def _init_osx(window):
    from AppKit import NSObject, NSApplication
    import objc

    try:
        import gi
        gi.require_version('GtkosxApplication', '1.0')
        from gi.repository import GtkosxApplication
    except (ValueError, ImportError):
        print_d("importing GtkosxApplication failed, no native menus")
    else:
        osx_app = GtkosxApplication.Application()
        window.set_as_osx_window(osx_app)
        osx_app.ready()

    shared_app = NSApplication.sharedApplication()
    gtk_delegate = shared_app.delegate()

    # Instead of quitting when the main window gets closed just hide it.
    # If the dock icon gets clicked we get
    # applicationShouldHandleReopen_hasVisibleWindows_ and show everything.
    class Delegate(NSObject):

        @objc.signature('B@:#B')
        def applicationShouldHandleReopen_hasVisibleWindows_(
                self, ns_app, flag):
            print_d("osx: handle reopen")
            app.present()
            return True

        def applicationShouldTerminate_(self, sender):
            print_d("osx: block termination")
            # FIXME: figure out why idle_add is needed here
            from gi.repository import GLib
            GLib.idle_add(app.quit)
            return False

        def applicationDockMenu_(self, sender):
            return gtk_delegate.applicationDockMenu_(sender)

    delegate = Delegate.alloc().init()
    delegate.retain()
    shared_app.setDelegate_(delegate)

    # QL shouldn't exit on window close, EF should
    if window.get_osx_is_persistent():
        window.connect(
            "delete-event", lambda window, event: window.hide() or True)


def set_application_info(icon_name, process_title, app_name):
    """Call after init() and before creating any windows to apply default
    values for names and icons.
    """

    assert _initialized

    from gi.repository import Gtk, GLib

    set_process_title(process_title)
    # Issue 736 - set after main loop has started (gtk seems to reset it)
    GLib.idle_add(set_process_title, process_title)

    GLib.set_prgname(process_title)
    GLib.set_application_name(app_name)

    theme = Gtk.IconTheme.get_default()
    assert theme.has_icon(icon_name)
    Gtk.Window.set_default_icon_name(icon_name)


def main(window, before_quit=None):
    print_d("Entering quodlibet.main")
    from gi.repository import Gtk, Gdk

    assert _initialized

    def quit_gtk(window):

        if before_quit is not None:
            before_quit()

        # disable plugins
        import quodlibet.plugins
        quodlibet.plugins.quit()

        # for debug: this will list active copools
        from quodlibet.util import copool
        copool.pause_all()

        # See which browser windows are open and save their names
        # so we can restore them on start
        from quodlibet.qltk.browser import LibraryBrowser
        LibraryBrowser.save()

        # destroy all open windows so they hide immediately on close:
        # destroying all top level windows doesn't work (weird errors),
        # so we hide them all and only destroy our tracked instances
        # (browser windows, tag editors, pref window etc.)
        from quodlibet.qltk import Window
        for toplevel in Gtk.Window.list_toplevels():
            toplevel.hide()

        for window in Window.windows:
            window.destroy()

        Gtk.main_quit()

        print_d("Quit GTK: done.")

    window.connect('destroy', quit_gtk)

    if sys.platform == "darwin":
        _init_osx(window)

    if not window.show_maybe():
        # if we don't show a window, startup isn't completed, so call manually
        Gdk.notify_startup_complete()

    # set QUODLIBET_START_PERF to measure startup time until the
    # windows is first shown.
    if "QUODLIBET_START_PERF" in os.environ:
        window.connect("draw", Gtk.main_quit)
        Gtk.main()
        sys.exit()
    else:
        Gtk.main()

    print_d("Gtk.main() done.")
