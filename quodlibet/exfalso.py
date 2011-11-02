#!/usr/bin/env python
# Copyright 2004-2005 Joe Wreschnig, Niklas Janlert
# <quod-libet-development@googlegroups.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import sys

def main():
    import quodlibet
    from quodlibet import util
    from quodlibet import const
    import gobject

    quodlibet._init_signal()

    opts = util.OptionParser(
        "Ex Falso", const.VERSION,
        _("an audio tag editor"), "[%s]" % _("directory"))

    sys.argv.append(os.path.abspath("."))
    opts, args = opts.parse()
    args[0] = os.path.realpath(args[0])

    from quodlibet import config
    config.init(const.CONFIG)

    library = quodlibet.init(icon="exfalso",
                             name="Ex Falso",
                             title=const.PROCESS_TITLE_EF)

    player = quodlibet.init_backend("nullbe", library.librarian)

    from quodlibet.qltk.exfalsowindow import ExFalsoWindow
    window = ExFalsoWindow(library, args[0])

    quodlibet.enable_periodic_save(save_library=False)

    from quodlibet.qltk import session
    session.init("exfalso", window)

    from quodlibet import widgets
    widgets.main = window
    widgets.watcher = library.librarian

    quodlibet.main(window)

    config.save(const.CONFIG)

    print_d("Finished shutdown.")

if __name__ == "__main__":
    main()
