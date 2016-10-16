# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import gettext
import locale
import warnings

from senf import environ

from quodlibet import util
from quodlibet.compat import PY2
from quodlibet.const import MinVersions
from quodlibet.util import is_osx, is_windows
from quodlibet.util.i18n import GlibTranslations, set_i18n_envvars, \
    fixup_i18n_envvars, set_translation
from quodlibet.util.dprint import print_d, print_e
from quodlibet.util.path import unexpand

from ._main import get_base_dir, is_release, get_image_dir


_cli_initialized = False
_initialized = False


def _init_gtk_debug(no_excepthook):
    from gi.repository import GLib
    from quodlibet.qltk.debugwindow import excepthook

    print_d("Initializing debugging extensions")

    def _override_exceptions():
        print_d("Enabling custom exception handler.")
        sys.excepthook = excepthook
    if not no_excepthook:
        GLib.idle_add(_override_exceptions)

    # faulthandler gives a python stacktrace on segfaults..
    try:
        import faulthandler
    except ImportError:
        pass
    else:
        faulthandler.enable()


def is_init():
    """Returns if init() was called"""

    global _initialized

    return _initialized


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
    t.set_debug_text(debug_text)
    set_translation(t)


def _init_python():
    if PY2 or is_release():
        MinVersions.PYTHON2.check(sys.version_info)
    else:
        # for non release builds we allow Python3
        MinVersions.PYTHON3.check(sys.version_info)

    if is_osx():
        # We build our own openssl on OSX and need to make sure that
        # our own ca file is used in all cases as the non-system openssl
        # doesn't use the system certs
        util.install_urllib2_ca_file()

    if is_windows():
        # Not really needed on Windows as pygi-aio seems to work fine, but
        # wine doesn't have certs which we use for testing.
        util.install_urllib2_ca_file()


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

    from gi.repository import Gtk, Soup
    from quodlibet.qltk import ThemeOverrider, gtk_version

    # Work around missing annotation in older libsoup (Ubuntu 14.04 at least)
    message = Soup.Message()
    try:
        message.set_request(None, Soup.MemoryUse.COPY, b"")
    except TypeError:
        orig = Soup.Message.set_request

        def new_set_request(self, content_type, req_use, req_body):
            return orig(self, content_type, req_use, req_body, len(req_body))

        Soup.Message.set_request = new_set_request

    # PyGObject doesn't fail anymore when init fails, so do it ourself
    initialized, argv = Gtk.init_check(sys.argv)
    if not initialized:
        raise SystemExit("Gtk.init failed")
    sys.argv = list(argv)

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

    css_override = ThemeOverrider()

    # CSS overrides
    if os.name == "nt":
        # somehow borders are missing under Windows & Gtk+3.14
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            .menu {
                border: 1px solid @borders;
            }
        """)
        css_override.register_provider("", style_provider)

    if sys.platform == "darwin":
        # fix duplicated shadows for popups with Gtk+3.14
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
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
        css_override.register_provider("", style_provider)

    if gtk_version[:2] >= (3, 20):
        # https://bugzilla.gnome.org/show_bug.cgi?id=761435
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            spinbutton, button {
                min-height: 1.8rem;
            }

            .view button {
                min-height: 2.0rem;
            }

            entry {
                min-height: 2.4rem;
            }
        """)
        css_override.register_provider("Adwaita", style_provider)
        css_override.register_provider("HighContrast", style_provider)

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
