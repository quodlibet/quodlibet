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
    URI_SRC = 0
    PluginNotFoundError = ValueError

    def element_factory_make(self, element_name):
        if element_name in ["monkeysdec", "mikmod", "modplug", "wavparse",
                            "spcdec"]:
            raise self.PluginNotFoundError("unsupported fake module")

    def element_make_from_uri(self, type_, uri, arg):
        return None

    def registry_get_default(self):
        return self

    def find_plugin(self, plugin):
        return plugin not in ["wavparse", "modplug"]

def main(argv):
    import quodlibet
    from quodlibet import util
    from quodlibet import const

    opts = util.OptionParser(
        "Ex Falso", const.VERSION,
        _("an audio tag editor"), "[%s]" % _("directory"))

    from quodlibet import config
    config.init(const.CONFIG)

    backend, library, player = quodlibet.init(icon="exfalso")

    sys.modules["gst"] = fakegst()

    sys.argv.append(os.path.abspath("."))
    opts, args = opts.parse()
    args[0] = os.path.realpath(args[0])
    from quodlibet.qltk.exfalsowindow import ExFalsoWindow
    from quodlibet.library import SongFileLibrary
    w = ExFalsoWindow(library, args[0])
    quodlibet.main(w)
    config.write(const.CONFIG)

if __name__ == "__main__":
    main(sys.argv)
