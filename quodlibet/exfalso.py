#!/usr/bin/env python
# Copyright 2004-2005 Joe Wreschnig, Niklas Janlert
# <quodlibet@lists.sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

import os, sys

class fakegst(object):
    def element_factory_make(self, element_name):
        if element_name in ["monkeysdec"]:
            raise ValueError("unsupported fake module")

if __name__ == "__main__":
    basedir = os.path.dirname(os.path.realpath(__file__))
    if not os.path.exists(os.path.join(basedir, "exfalso.py")):
        if os.path.exists(os.path.join(os.getcwd(), "exfalso.py")):
            basedir = os.getcwd()
    if basedir.endswith("/share/quodlibet"):
        sys.path.append(basedir[:-15] + "lib/quodlibet")

    import locale, gettext, util
    try: locale.setlocale(locale.LC_ALL, '')
    except: pass
    gettext.bindtextdomain("quodlibet")
    gettext.textdomain("quodlibet")
    util.gettext_install("quodlibet", unicode=True)
    util.ctypes_init()

    import const
    opts = util.OptionParser(
        "Ex Falso", const.VERSION,
        _("an audio tag editor"), "[%s]" % _("directory"))

    import config
    config.init(const.CONFIG)

    sys.argv.append(os.path.abspath("."))
    opts, args = opts.parse()
    args[0] = os.path.realpath(args[0])
    os.chdir(basedir)

    import pygtk
    pygtk.require('2.0')
    import gtk
    try: gtk.window_set_default_icon_from_file("exfalso.svg")
    except: gtk.window_set_default_icon_from_file("exfalso.png")
    util.gtk_init()

    sys.modules["gst"] = fakegst()
    import gst
    assert isinstance(gst, fakegst)

    import stock
    stock.init()

    from qltk.exfalso import ExFalsoWindow
    from qltk.watcher import SongWatcher
    w = ExFalsoWindow(SongWatcher(), args[0])
    w.connect('destroy', gtk.main_quit)
    w.show()

    gtk.main()
