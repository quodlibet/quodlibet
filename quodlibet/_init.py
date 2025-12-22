# Copyright 2012 Christoph Reiter
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import warnings
import logging

from senf import fsn2text

from quodlibet.const import MinVersions
from quodlibet import config
from quodlibet.util import is_osx, is_windows, i18n
from quodlibet.util.dprint import print_e, PrintHandler, print_d
from quodlibet.util.urllib import install_urllib2_ca_file

from ._main import get_base_dir, is_release, get_cache_dir


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
        language = "C"
    else:
        language = config.gettext("settings", "language")
        if language:
            print_d(f"Using language in QL settings: {language!r}")
        else:
            language = None

    i18n.init(language)

    # Use the locale dir in ../build/share/locale if there is one
    localedir = os.path.join(
        os.path.dirname(get_base_dir()), "build", "share", "locale"
    )
    if os.path.isdir(localedir):
        print_d(f"Using local locale dir {localedir}")
    else:
        localedir = None

    i18n.register_translation("quodlibet", localedir)
    debug_text = os.environ.get("QUODLIBET_TEST_TRANS")
    if debug_text is not None:
        i18n.set_debug_text(fsn2text(debug_text))


def _init_python():
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
        # If you hit this, do a "setup.py clean -all" to get rid of the
        # bytecode cache then start things with "MSYSTEM= ..."
        raise AssertionError("MSYSTEM is set ({!r})".format(os.environ.get("MSYSTEM")))

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

    # To make GDBus fail early and we don't have to wait for a timeout
    if is_osx() or is_windows():
        os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = "something-invalid"
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = "something-invalid"

    try:
        from dbus.mainloop.glib import DBusGMainLoop, threads_init
    except ImportError:
        try:
            import dbus.glib

            dbus.glib  # noqa
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

    # Newer glib is noisy regarding deprecated signals/properties
    # even with stable releases.
    if is_release():
        warnings.filterwarnings(
            "ignore", ".* It will be removed in a future version.", Warning
        )

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["glib"] = None
    sys.modules["gobject"] = None


def _init_gtk():
    """Call before using Gtk/Gdk"""

    import gi

    if (
        config.getboolean("settings", "pangocairo_force_fontconfig")
        and "PANGOCAIRO_BACKEND" not in os.environ
    ):
        os.environ["PANGOCAIRO_BACKEND"] = "fontconfig"

    # disable for consistency and trigger events seem a bit flaky here
    if config.getboolean("settings", "scrollbar_always_visible"):
        os.environ["GTK_OVERLAY_SCROLLING"] = "0"

    try:
        # not sure if this is available under Windows
        gi.require_version("GdkX11", "4.0")
        from gi.repository import GdkX11

        GdkX11  # noqa
    except (ValueError, ImportError):
        pass

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("Pango", "1.0")
    gi.require_version("Soup", "3.0")
    gi.require_version("PangoCairo", "1.0")

    from gi.repository import Gtk
    from quodlibet.qltk import ThemeOverrider, gtk_version

    # PyGObject doesn't fail any more when init fails, so do it ourselves
    initialized = Gtk.init_check()
    if not initialized:
        raise SystemExit("Gtk.init failed")

    # GTK4 compatibility: Add show_all/hide_all/set_no_show_all as no-ops
    if not hasattr(Gtk.Widget, "show_all"):
        Gtk.Widget.show_all = lambda self: None
    if not hasattr(Gtk.Widget, "hide_all"):
        Gtk.Widget.hide_all = lambda self: self.set_visible(False)
    if not hasattr(Gtk.Widget, "set_no_show_all"):
        Gtk.Widget.set_no_show_all = lambda self, value: None

    # GTK4 compatibility: Add Gtk.AttachOptions for Table compatibility
    # (Gtk.Table removed in GTK4, but plugins still use it)
    if not hasattr(Gtk, "AttachOptions"):
        from enum import IntFlag

        class AttachOptions(IntFlag):
            EXPAND = 1 << 0
            SHRINK = 1 << 1
            FILL = 1 << 2

        Gtk.AttachOptions = AttachOptions

    # GTK4 compatibility: Window type hints removed
    if not hasattr(Gtk.Window, "set_type_hint"):
        Gtk.Window.set_type_hint = lambda self, hint: None
        Gtk.Window.get_type_hint = lambda self: None

    # GTK4 compatibility: Gdk.WindowTypeHint removed
    from gi.repository import Gdk

    if not hasattr(Gdk, "WindowTypeHint"):
        from enum import IntEnum

        class WindowTypeHint(IntEnum):
            NORMAL = 0
            DIALOG = 1
            MENU = 2
            TOOLBAR = 3

        Gdk.WindowTypeHint = WindowTypeHint

    # TODO: include our own icon theme directory
    # theme = Gtk.IconTheme.get_default()
    # theme_search_path = get_image_dir()
    # assert os.path.exists(theme_search_path)
    # theme.append_search_path(theme_search_path)

    # Force menu/button image related settings. We might show too many atm
    # but this makes sure we don't miss cases where we forgot to force them
    # per widget.
    # https://bugzilla.gnome.org/show_bug.cgi?id=708676
    warnings.filterwarnings("ignore", ".*g_value_get_int.*", Warning)

    # some day... but not now
    warnings.filterwarnings("ignore", ".*Stock items are deprecated.*", Warning)
    warnings.filterwarnings("ignore", ".*:use-stock.*", Warning)
    warnings.filterwarnings(
        "ignore", r".*The property GtkAlignment:[^\s]+ is deprecated.*", Warning
    )

    settings = Gtk.Settings.get_default()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # settings.set_property("gtk-button-images", True)
        # settings.set_property("gtk-menu-images", True)
    if hasattr(settings.props, "gtk_primary_button_warps_slider"):
        # https://bugzilla.gnome.org/show_bug.cgi?id=737843
        settings.set_property("gtk-primary-button-warps-slider", True)

    # Make sure PyGObject includes support for foreign cairo structs
    try:
        gi.require_foreign("cairo")
    except ImportError:
        print_e("PyGObject is missing cairo support")
        sys.exit(1)

    css_override = ThemeOverrider()

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
                min-height: 22px;
            }

            .view button {
                min-height: 24px;
            }

            entry {
                min-height: 28px;
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
        # https://github.com/quodlibet/quodlibet/issues/2677
        css_override.register_provider("Clearlooks-Phenix", style_provider)
        # https://github.com/quodlibet/quodlibet/issues/2997
        css_override.register_provider("Breeze", style_provider)

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
    warnings.filterwarnings("ignore", ".*g_value_get_int.*", Warning)

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["gtk"] = None
    sys.modules["gpod"] = None
    sys.modules["gnome"] = None

    from quodlibet.qltk import pygobject_version, gtk_version

    MinVersions.GTK.check(gtk_version)
    MinVersions.PYGOBJECT.check(pygobject_version)


def _init_gst():
    """Call once before importing GStreamer"""

    arch_key = "64" if sys.maxsize > 2**32 else "32"
    registry_name = f"gst-registry-{sys.platform}-{arch_key}.bin"
    os.environ["GST_REGISTRY"] = os.path.join(get_cache_dir(), registry_name)

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
        ok, sys.argv[:] = Gst.init_check(sys.argv)
    except GLib.GError:
        print_e("Failed to initialize GStreamer")
        # Uninited Gst segfaults: make sure no one can use it
        sys.modules["gi.repository.Gst"] = None
    else:
        # monkey patching ahead
        _fix_gst_leaks()
