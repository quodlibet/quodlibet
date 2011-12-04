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
import traceback
import warnings

import quodlibet.const
import quodlibet.util

from quodlibet.util.i18n import GlibTranslations
from quodlibet.util.dprint import print_, print_d, print_w, print_e

def _gtk_init(icon=None):
    import pygtk
    pygtk.require('2.0')
    import gtk

    import quodlibet.stock
    quodlibet.stock.init()

    if icon:
        theme = gtk.icon_theme_get_default()
        pixbufs = []
        for size in [64, 48, 32, 16]:
            try: pixbufs.append(theme.load_icon(icon, size, 0))
            except gobject.GError: pass
        gtk.window_set_default_icon_list(*pixbufs)

    def website_wrap(activator, link):
        if not quodlibet.util.website(link):
            from quodlibet.qltk.msg import ErrorMessage
            ErrorMessage(
                main, _("Unable to start web browser"),
                _("A web browser could not be found. Please set "
                  "your $BROWSER variable, or make sure "
                  "/usr/bin/sensible-browser exists.")).run()

    gtk.about_dialog_set_url_hook(website_wrap)

def _gettext_init():
    try: locale.setlocale(locale.LC_ALL, '')
    except locale.Error: pass

    unexpand = quodlibet.util.unexpand

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
        localedir = "share\\locale"

    try:
        t = gettext.translation("quodlibet", localedir,
            class_=GlibTranslations)
    except IOError:
        print_d("No translation found in %r" % unexpand(localedir))
        t = GlibTranslations()
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
        print_w(_("Couldn't find module %s." % ("libc.so.6 (ctypes)", ) + " "
           + _("Not setting process title.")))

def _python_init():
    # The default regex escaping function doesn't work for non-ASCII.
    # Use a blacklist of regex-specific characters instead.
    def re_esc(str, BAD="/.^$*+?{,\\[]|()<>#=!:"):
        needs_escape = lambda c: (c in BAD and "\\" + c) or c
        return "".join(map(needs_escape, str))
    re.escape = re_esc

    # Set up import wrappers for Quod Libet 1.x compatibility.
    old_import = __import__
    def import_ql(module, *args, **kwargs):
        try: return old_import(module, *args, **kwargs)
        except ImportError:
            # If it looks like a plugin import error, forgive it, and
            # try prepending quodlibet to the module name.
            tb = traceback.extract_stack()
            for (filename, linenum, func, text) in tb:
                if "plugins" in filename:
                    warnings.warn(
                        "enabling legacy plugin API", DeprecationWarning)
                    old_import("quodlibet." + module, *args, **kwargs)
                    return sys.modules["quodlibet." + module]
            else:
                raise

    if os.environ.get("QUODLIBET_OLDIMPORT"):
        __builtin__.__dict__["__import__"] = import_ql
    __builtin__.__dict__["print_"] = print_
    __builtin__.__dict__["print_d"] = print_d
    __builtin__.__dict__["print_e"] = print_e
    __builtin__.__dict__["print_w"] = print_w

del(_dummy_gettext)
del(_dummy_ngettext)

_python_init()
_gettext_init()

def init(library=None, icon=None, title=None, name=None):
    print_d("Entering quodlibet.init")

    _gtk_init(icon)

    import gobject

    if title:
        gobject.set_prgname(title)
        set_process_title(title)
        # Issue 736 - set after main loop has started (gtk seems to reset it)
        gobject.idle_add(set_process_title, title)

    if name:
        gobject.set_application_name(name)

    # We already imported this, but Python is dumb and thinks we're rebinding
    # a local when we import it later.
    import quodlibet.util
    quodlibet.util.mkdir(quodlibet.const.USERDIR)

    if library:
        print_d("Initializing main library (%s)" % (
            quodlibet.util.unexpand(library)))

    import quodlibet.library
    library = quodlibet.library.init(library)

    print_d("Initializing debugging extensions")
    import quodlibet.debug
    quodlibet.debug.init()

    print_d("Finished initialization.")

    return library

def init_backend(backend, librarian):
    import quodlibet.player
    print_d("Initializing audio backend (%s)" % backend)
    backend = quodlibet.player.init(backend)
    device = quodlibet.player.init_device(librarian)
    return device

def enable_periodic_save(save_library):
    import quodlibet.library
    from quodlibet.util import copool

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

def _init_signal(window=None):
    """Catches certain signals and destroys the window if they occur.
    If called without a window, it catches all signals and will destroy
    the window shortly after the mainloop gets started.

    Has to be called with a valid window before the mainloop starts."""

    import signal
    import gobject
    import os

    if os.name == "nt":
        return

    _init_signal.window = window

    def pipe_can_read(*args):
        window = _init_signal.window
        if window:
            import gtk
            gtk.gdk.threads_enter()
            window.destroy()
            gtk.gdk.threads_leave()
        return False

    # The signal handler can not call gtk functions, thus we have to
    # build a dummy pipe to pass it into the gtk mainloop

    r, w = os.pipe()
    gobject.io_add_watch(r, gobject.IO_IN, pipe_can_read, window)

    SIGS = [getattr(signal, s, None) for s in "SIGINT SIGTERM SIGHUP".split()]
    for sig in filter(None, SIGS):
        signal.signal(sig, lambda sig, frame: os.write(w, "die!!!"))

def main(window):
    print_d("Entering quodlibet.main")
    import gtk

    def quit_gtk(m):
        # stop all copools
        print_d("Quit GTK: Stop all copools")
        from quodlibet.util import copool
        copool.remove_all()

        # events that add new events to the main loop (like copool)
        # can block the shutdown, so force stop after some time.
        # gtk.main_iteration will return True if quit gets called here
        import gobject
        gobject.timeout_add(4 * 1000, gtk.main_quit,
                            priority=gobject.PRIORITY_HIGH)

        # destroy all open windows so they hide immediately on close:
        # destroying all top level windows doesn't work (weird errors),
        # so we hide them all and only destroy our tracked instances
        # (browser windows, tag editors, pref window etc.)
        from quodlibet.qltk import Window
        map(gtk.Window.hide, gtk.window_list_toplevels())
        map(gtk.Window.destroy, Window.instances)

        print_d("Quit GTK: Process pending events...")
        while gtk.events_pending():
            if gtk.main_iteration(False):
                print_d("Quit GTK: Timeout occured, force quit.")
                break

        gtk.main_quit()
        print_d("Quit GTK: done.")

    window.connect('destroy', quit_gtk)
    window.show()

    _init_signal(window)

    # This has been known to cause segmentation faults in some Python,
    # GTK+, and GStreamer versions.
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()
