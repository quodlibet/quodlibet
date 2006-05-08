#!/usr/bin/env python
# Copyright 2004-2005 Joe Wreschnig, Niklas Janlert
# <quodlibet@lists.sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

import os
import sys

class fakegst(object):
    def element_factory_make(self, element_name):
        if element_name in ["monkeysdec", "mikmod", "modplug", "wavparse"]:
            raise ValueError("unsupported fake module")

def main(argv):
    import util
    util.python_init()
    util.gettext_install()
    util.ctypes_init()

    import const
    opts = util.OptionParser(
        "Ex Falso", const.VERSION,
        _("an audio tag editor"), "[%s]" % _("directory"))

    import config
    config.init(const.CONFIG)

    util.gtk_init()
    import gtk
    icon = os.path.join(const.BASEDIR, "exfalso.")
    try: gtk.window_set_default_icon_from_file(icon + "svg")
    except: gtk.window_set_default_icon_from_file(icon + "png")

    import stock
    stock.init()

    sys.modules["gst"] = fakegst()

    sys.argv.append(os.path.abspath("."))
    opts, args = opts.parse()
    args[0] = os.path.realpath(args[0])
    from qltk.exfalso import ExFalsoWindow
    from qltk.watcher import SongWatcher
    w = ExFalsoWindow(SongWatcher(), args[0])
    w.connect('destroy', gtk.main_quit)
    w.show()

    gtk.main()

if __name__ == "__main__":
    main(sys.argv)
