#!/usr/bin/env python
# Copyright 2004-2005 Joe Wreschnig, Niklas Janlert
# <quod-libet-development@googlegroups.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import sys

def main(argv):
    import quodlibet
    from quodlibet import util
    from quodlibet import const

    opts = util.OptionParser(
        "Ex Falso", const.VERSION,
        _("an audio tag editor"), "[%s]" % _("directory"))

    sys.argv.append(os.path.abspath("."))
    opts, args = opts.parse()
    args[0] = os.path.realpath(args[0])

    from quodlibet import config
    config.init(const.CONFIG)
    backend, library, player = quodlibet.init(icon="exfalso", backend="nullbe")

    from quodlibet.qltk.exfalsowindow import ExFalsoWindow
    w = ExFalsoWindow(library, args[0])
    quodlibet.main(w)
    quodlibet.quit((backend, library, player))
    config.write(const.CONFIG)

if __name__ == "__main__":
    main(sys.argv)
