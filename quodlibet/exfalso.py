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

def print_help(output=sys.stdout):
    output.write(to(_("""\
Ex Falso - an audio file tagger
Usage: %s [directory]

For more information, see the manual page (`man 1 exfalso').
""")) % sys.argv[0])
    raise SystemExit(output == sys.stderr)

def print_version(output=sys.stdout):
    output.write(to(_("""\
Ex Falso %s - <quodlibet@lists.sacredchao.net>
Copyright 2004-2005 Joe Wreschnig, Michael Urman, and others

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
""")) % const.VERSION)
    raise SystemExit(output == sys.stderr)

if __name__ == "__main__":
    import locale, gettext
    gettext.bindtextdomain("quodlibet")
    gettext.textdomain("quodlibet")
    gettext.install("quodlibet", unicode=True)
    try: locale.setlocale(locale.LC_ALL, '')
    except: pass

    basedir = os.path.split(os.path.realpath(__file__))[0]
    sys.path.insert(1, os.path.join(basedir, "quodlibet.zip"))

    import const
    from util import to

    if "--help" in sys.argv or "-h" in sys.argv: print_help()
    elif "--version" in sys.argv or "-v" in sys.argv: print_version()

    import config
    config.init(const.CONFIG)

    if len(sys.argv) < 2:
        sys.argv.append(os.environ["HOME"])
    elif (sys.argv[1].startswith("--") and
          (sys.argv[1] != "--" or len(sys.argv) == 2)):
        print_help(sys.stderr)

    sys.argv[1] = os.path.realpath(sys.argv[1])
    os.chdir(basedir)

    import pygtk
    pygtk.require('2.0')
    import gtk, widgets
    w = widgets.ExFalsoWindow(sys.argv[1])
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
