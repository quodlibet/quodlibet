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
    from quodlibet import set_process_title

    opts = util.OptionParser(
        "Ex Falso", const.VERSION,
        _("an audio tag editor"), "[%s]" % _("directory"))

    sys.argv.append(os.path.abspath("."))
    opts, args = opts.parse()
    args[0] = os.path.realpath(args[0])

    from quodlibet import config
    config.init(const.CONFIG)
    backend, library, player = quodlibet.init(icon="exfalso", backend="nullbe")

    # Issue 736
    if os.name != "nt": set_process_title(const.PROCESS_TITLE_EF)

    from quodlibet.qltk.exfalsowindow import ExFalsoWindow
    from quodlibet import widgets
    widgets.main = ExFalsoWindow(library, args[0])
    quodlibet.main(widgets.main)
    quodlibet.quit((backend, library, player))
    config.write(const.CONFIG)

if __name__ == "__main__":
    main(sys.argv)
