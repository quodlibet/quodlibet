import __builtin__

import gettext
import locale
import re
import sys
import traceback
import warnings

from quodlibet.util.i18n import GlibTranslations

def gettext_install():
    try: locale.setlocale(locale.LC_ALL, '')
    except locale.Error: pass
    try:
        t = gettext.translation("quodlibet", class_=GlibTranslations)
    except IOError:
        t = GlibTranslations()
    t.install(unicode=True)

def python_init():
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

def gtk_init():
    import pygtk
    pygtk.require('2.0')
    import gtk
    # http://bugzilla.gnome.org/show_bug.cgi?id=318953
    if gtk.gtk_version < (2, 8, 8):
        class TVProxy(gtk.TreeView):
            def set_search_equal_func(self, func, *args): pass
        gtk.TreeView = TVProxy

def init():
    python_init()
    gettext_install()
