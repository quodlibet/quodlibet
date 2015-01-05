#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Niklas Janlert
#           2012 Christoph Reiter
# <quod-libet-development@googlegroups.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import os
import sys

import quodlibet
from quodlibet import app
from quodlibet import util
from quodlibet import const
from quodlibet import config
from quodlibet.util.path import fsdecode


def main():
    from quodlibet.qltk import add_signal_watch
    add_signal_watch(app.quit)

    opts = util.OptionParser(
        "Ex Falso", const.VERSION,
        _("an audio tag editor"), "[%s]" % _("directory"))

    # FIXME: support unicode on Windows, sys.argv isn't good enough
    sys.argv.append(os.path.abspath("."))
    opts, args = opts.parse()
    args[0] = os.path.realpath(args[0])

    config.init(const.CONFIG)

    app.library = quodlibet.init(icon="exfalso",
                                 name="Ex Falso",
                                 title=const.PROCESS_TITLE_EF)
    app.player = quodlibet.init_backend("nullbe", app.librarian)
    from quodlibet.qltk.songlist import PlaylistModel
    app.player.setup(PlaylistModel(), None, 0)
    pm = quodlibet.init_plugins()
    pm.rescan()

    from quodlibet.qltk.exfalsowindow import ExFalsoWindow
    dir_ = args[0]
    if os.name == "nt":
        dir_ = fsdecode(dir_)
    app.window = ExFalsoWindow(app.library, dir_)
    app.window.init_plugins()

    from quodlibet.qltk import session
    session.init("exfalso")

    quodlibet.enable_periodic_save(save_library=False)
    quodlibet.main(app.window)

    quodlibet.finish_first_session(const.PROCESS_TITLE_EF)
    config.save(const.CONFIG)

    print_d("Finished shutdown.")


if __name__ == "__main__":
    main()
