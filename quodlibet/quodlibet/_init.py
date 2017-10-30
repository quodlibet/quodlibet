# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import warnings
import logging

from senf import environ, argv, fsn2text

from quodlibet.compat import PY2
from quodlibet.const import MinVersions
from quodlibet import config
from quodlibet.util import is_osx, is_windows, i18n
from quodlibet.util.dprint import print_e, PrintHandler
from quodlibet.util.urllib import install_urllib2_ca_file

from ._main import get_base_dir, is_release, get_image_dir


_cli_initialized = False
_initialized = False


def _init_gtk_debug(no_excepthook):
    from quodlibet.errorreport import enable_errorhook

    enable_errorhook(not no_excepthook)


def is_init():
    """Returns if init() was called"""

    global _initialized

    return _initialized


def init(no_translations=False, no_excepthook=False, config_file=None):
    """This needs to be called before any API can be used.
    Might raise in case of an error.

    Pass no_translations=True to disable translations (used by tests)
    """

    global _initialized

    if _initialized:
        return

    init_cli(no_translations=no_translations, config_file=config_file)
    _init_gtk()
    _init_gtk_debug(no_excepthook=no_excepthook)
    _init_gst()
    _init_dbus()

    _initialized = True


def _init_gettext(no_translations=False):
    """Call before using gettext helpers"""

    if no_translations:
        language = u"C"
    else:
        language = config.gettext("settings", "language")
        if not language:
            language = None

    i18n.init(language)

    # Use the locale dir in ../build/share/locale if there is one
    base_dir = get_base_dir()
    localedir = os.path.dirname(base_dir)
    localedir = os.path.join(localedir, "build", "share", "locale")
    if not os.path.isdir(localedir) and os.name == "nt":
        localedir = os.path.join(
            base_dir, "..", "..", "share", "locale")

    i18n.register_translation("quodlibet", localedir)
    debug_text = environ.get("QUODLIBET_TEST_TRANS")
    if debug_text is not None:
        i18n.set_debug_text(fsn2text(debug_text))


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
        install_urllib2_ca_file()

    if is_windows():
        # Not really needed on Windows as pygi-aio seems to work fine, but
        # wine doesn't have certs which we use for testing.
        install_urllib2_ca_file()

    if is_windows() and os.sep != "\\":
        # In the MSYS2 console MSYSTEM is set, which breaks os.sep/os.path.sep
        # If you hit this do a "setup.py clean -all" to get rid of the
        # bytecode cache then start things with "MSYSTEM= ..."
        raise AssertionError("MSYSTEM is set (%r)" % environ.get("MSYSTEM"))

    if is_windows():
        # gdbm is broken under msys2, this makes shelve use another backend
        sys.modules["gdbm"] = None
        sys.modules["_gdbm"] = None

    logging.getLogger().addHandler(PrintHandler())


def _init_formats():
    from quodlibet.formats import init
    init()


def init_cli(no_translations=False, config_file=None):
    """This needs to be called before any API can be used.
    Might raise in case of an error.

    Like init() but for code not using Gtk etc.
    """

    global _cli_initialized

    if _cli_initialized:
        return

    _init_python()
    config.init_defaults()
    if config_file is not None:
        config.init(config_file)
    _init_gettext(no_translations)
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
            setattr(
                cls, name, getattr(cls, name + "_utf8", getattr(cls, name)))

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
        environ['PANGOCAIRO_BACKEND'] = 'win32'
        environ["GTK_CSD"] = "0"

    # disable for consistency and trigger events seem a bit flaky here
    if is_osx():
        environ["GTK_OVERLAY_SCROLLING"] = "0"

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

    from gi.repository import Gtk
    from quodlibet.qltk import ThemeOverrider, gtk_version

    # PyGObject doesn't fail anymore when init fails, so do it ourself
    initialized, argv[:] = Gtk.init_check(argv)
    if not initialized:
        raise SystemExit("Gtk.init failed")

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

            entry.cell {
                min-height: 0;
            }
        """)
        css_override.register_provider("Adwaita", style_provider)
        css_override.register_provider("HighContrast", style_provider)

        # https://github.com/quodlibet/quodlibet/issues/2541
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            treeview.view.separator {
                min-height: 2px;
                color: @borders;
            }
        """)
        css_override.register_provider("Ambiance", style_provider)
        css_override.register_provider("Radiance", style_provider)

    if gtk_version[:2] >= (3, 18):
        # Hack to get some grab handle like thing for panes
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            GtkPaned.vertical, paned.vertical >separator {
                -gtk-icon-source: -gtk-icontheme("view-more-symbolic");
                -gtk-icon-transform: rotate(90deg) scaleX(0.1) scaleY(3);
            }

            GtkPaned.horizontal, paned.horizontal >separator {
                -gtk-icon-source: -gtk-icontheme("view-more-symbolic");
                -gtk-icon-transform: rotate(0deg) scaleX(0.1) scaleY(3);
            }
        """)
        css_override.register_provider("", style_provider)

    # https://bugzilla.gnome.org/show_bug.cgi?id=708676
    warnings.filterwarnings('ignore', '.*g_value_get_int.*', Warning)

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["gtk"] = None
    sys.modules["gpod"] = None
    sys.modules["gnome"] = None

    from quodlibet.qltk import pygobject_version, gtk_version, libsoup_version

    MinVersions.GTK.check(gtk_version)
    MinVersions.PYGOBJECT.check(pygobject_version)
    MinVersions.LIBSOUP.check(libsoup_version)


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
        ok, argv[:] = Gst.init_check(argv)
    except GLib.GError:
        print_e("Failed to initialize GStreamer")
        # Uninited Gst segfaults: make sure no one can use it
        sys.modules["gi.repository.Gst"] = None
    else:
        # monkey patching ahead
        _fix_gst_leaks()

        # https://bugzilla.gnome.org/show_bug.cgi?id=710447
        import threading
        threading.Thread(target=lambda: None).start()
