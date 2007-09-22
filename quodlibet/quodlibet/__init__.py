import __builtin__

_dummy_gettext = lambda value: value
_dummy_ngettext = lambda v1, v2, count: value == 1 and v1 or v2
__builtin__.__dict__["_"] = _dummy_gettext
__builtin__.__dict__["Q_"] = _dummy_gettext
__builtin__.__dict__["N_"] = _dummy_gettext
__builtin__.__dict__["ngettext"] = _dummy_ngettext

import gettext
import locale
import os
import re
import signal
import sys
import time
import traceback
import warnings

import quodlibet.const
import quodlibet.util
import quodlibet.util.logging

from quodlibet.const import ENCODING
from quodlibet.util.i18n import GlibTranslations

def _gtk_init(icon=None):
    import pygtk
    pygtk.require('2.0')
    import gtk

    # http://bugzilla.gnome.org/show_bug.cgi?id=318953
    if gtk.gtk_version < (2, 8, 8):
        class TVProxy(gtk.TreeView):
            def set_search_equal_func(self, func, *args): pass
        gtk.TreeView = TVProxy

    import quodlibet.stock
    quodlibet.stock.init()

    if icon:
        icon = os.path.join(quodlibet.const.IMAGEDIR, icon)
        try: gtk.window_set_default_icon_from_file(icon + ".svg")
        except: gtk.window_set_default_icon_from_file(icon + ".png")

def _gettext_init():
    try: locale.setlocale(locale.LC_ALL, '')
    except locale.Error: pass
    try:
        t = gettext.translation("quodlibet", class_=GlibTranslations)
    except IOError:
        t = GlibTranslations()
    t.install(unicode=True)

def print_(string, frm="utf-8", prefix="", output=sys.stdout, log=None):
    if prefix:
        string = prefix + ("\n" + prefix).join(string.splitlines())

    quodlibet.util.logging.log(string, log)

    if isinstance(string, unicode):
        string = string.encode(ENCODING, "replace")
    else:
        string = string.decode(frm).encode(ENCODING, "replace")

    if output:
        if isinstance(string, unicode):
            string = string.encode(ENCODING, "replace")
        else:
            string = string.decode(frm).encode(ENCODING, "replace")
        print >>output, string

def print_d(string, context=""):
    """Print debugging information."""
    if quodlibet.const.DEBUG:
        output = sys.stderr
    else:
        output = None

    if context and not isinstance(context, str):
        try:
            context = type(context).__name__
            context += "." + traceback.extract_stack()[-2][2] + ": "
        except AttributeError:
            context = "Unknown Context"

    timestr = "%0.2f" % time.time()
    string = "%s: %s%s" % (timestr[-6:], context, string)
    print_(string, prefix="D: ", log="Debug", output=output)

def print_w(string):
    """Print warnings."""
    # Translators: "W" as in "Warning". It is prepended to
    # terminal output. APT uses a similar output format.
    print_(string, prefix=_("W: "), log="Warnings", output=sys.stderr)

def print_e(string):
    """Print errors."""
    # Translators: "E" as in "Error". It is prepended to
    # terminal output. APT uses a similar output format.
    print_(string, prefix=_("E: "), log="Errors", output=sys.stderr)

def _python_init():
    # The default regex escaping function doesn't work for non-ASCII.
    # Use a blacklist of regex-specific characters instead.
    def re_esc(str, BAD="/.^$*+?{,\\[]|()<>#=!:"):
        needs_escape = lambda c: (c in BAD and "\\" + c) or c
        return "".join(map(needs_escape, str))
    re.escape = re_esc

    # Python 2.4 has sre.Scanner but not re.Scanner. Python 2.5 has
    # deprecated sre and moved Scanner to re.
    try: re.Scanner
    except AttributeError:
        from sre import Scanner
        re.Scanner = Scanner

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
    __builtin__.__dict__["__import__"] = import_ql
    __builtin__.__dict__["print_"] = print_
    __builtin__.__dict__["print_d"] = print_d
    __builtin__.__dict__["print_e"] = print_e
    __builtin__.__dict__["print_w"] = print_w

del(_dummy_gettext)
del(_dummy_ngettext)

_python_init()
_gettext_init()

def init(gtk=True, backend=None, library=None, player=None, icon=None):
    if gtk:
        _gtk_init(icon)

    # We already imported this, but Python is dumb and thinks we're rebinding
    # a local when we import it later.
    import quodlibet.util
    quodlibet.util.mkdir(const.USERDIR)

    if backend:
        import quodlibet.player
        print_(_("Initializing audio backend (%s)") % backend)
        backend = quodlibet.player.init(backend)
    if library:
        print_(_("Initializing main library (%s)") % util.unexpand(library))
    import quodlibet.library
    library = quodlibet.library.init(library)

    if const.DEBUG:
        import quodlibet.debug
        quodlibet.debug.init()

    return (backend, library, player)

def main(window):
    import gtk

    SIGNALS = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]
    for sig in SIGNALS:
        signal.signal(sig, gtk.main_quit)

    window.connect('destroy', gtk.main_quit)
    window.show()

    gtk.gdk.threads_init()
    gtk.main()

def error_and_quit(error):
    from qltk.msg import ErrorMessage
    ErrorMessage(None, error.short_desc, error.long_desc).run()
