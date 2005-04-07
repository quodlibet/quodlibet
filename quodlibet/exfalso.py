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

if __name__ == "__main__":
    import locale, gettext
    gettext.bindtextdomain("quodlibet")
    gettext.textdomain("quodlibet")
    gettext.install("quodlibet", unicode=True)
    try: locale.setlocale(locale.LC_ALL, '')
    except: pass

    basedir = os.path.split(os.path.realpath(__file__))[0]
    sys.path.insert(1, os.path.join(basedir, "quodlibet.zip"))

    HELP = _("""\
Ex Falso - an audio file tagger
Usage: %s [directory]

For more information, see the manual page (`man 1 exfalso').
""") % sys.argv[0]


    import const
    from util import to

    # FIXME: UGLY
    import quodlibet; quodlibet.to = to
    opts = quodlibet.OptionParser("Ex Falso", const.VERSION)
    opts.set_help(HELP)    

    import config
    config.init(const.CONFIG)

    sys.argv.append(os.environ["HOME"])
    opts, args = opts.parse()
    args[0] = os.path.realpath(args[0])
    os.chdir(basedir)

    import pygtk
    pygtk.require('2.0')
    import gtk, widgets
    w = widgets.ExFalsoWindow(args[0])
    w.show_all()

    if (os.path.exists(const.CONTROL) and
        not config.getboolean('exfalso', 'shutup')):
        import qltk
        qltk.WarningMessage(
            w, _("Quod Libet is running"),
            _("It looks like you are running Quod Libet right now. "
              "If you edit songs also in Quod Libet's library while it is "
              "running, you may need to refresh or re-add them.\n\n"
              "If you are not running Quod Libet, or are editing songs "
              "outside of its library, you may ignore this warning.")).run()

    gtk.main()
