#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
# <quodlibet@lists.sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

import os, sys

def main():
    import signal, gtk, widgets
    SIGNALS = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]

    window = widgets.init()

    from threading import Thread
    t = Thread(target = player.playlist.play, args = (window,))
    t.start()
    for sig in SIGNALS: signal.signal(sig, gtk.main_quit)
    enable_periodic_save()
    gtk.quit_add(0, save_and_quit, t)
    gtk.main()

def save_and_quit(thread):
    player.playlist.quitting()
    thread.join()
    print to(_("Saving song library."))
    library.save(const.LIBRARY)
    config.write(const.CONFIG)
    cleanup()

def print_help(out = sys.stdout):
    out.write(to(_("""\
Quod Libet - a music library and player
Options:
  --help, -h        Display this help message
  --version         Display version and copyright information
  --refresh-library Rescan your song cache and then exit.
  --print-playing   Print the currently playing song.

 Player controls:
  --next, --previous, --play-pause, --play, --pause
    Change songs or pause/resume playing.
  --volume +|-|0..100
    Increase, decrease, or set the volume.
  --shuffle 0|1|t, --repeat 0|1|t
    Enable, disable, or toggle shuffle and repeat.  
  --query search-string
    Make a new playlist from the given search.
  --seek [+|-][HH:MM:]SS
    Seek to a position in the current song.
  --play-file filename
    Play this file, adding it to the library if necessary.

For more information, see the manual page (`man 1 quodlibet').
""")))

    raise SystemExit(out == sys.stderr)

def print_version(out = sys.stdout):
    print to(_("""\
Quod Libet %s - <quodlibet@lists.sacredchao.net>
Copyright 2004-2005 Joe Wreschnig, Michael Urman, and others

This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\
""")) % const.VERSION
    raise SystemExit(out == sys.stderr)

def refresh_cache():
    if isrunning():
        raise SystemExit(to(_(
            "The library cannot be refreshed while Quod Libet is running.")))
    import library, config, const
    config.init(const.CONFIG)
    library.init()
    print to(_("Loading, scanning, and saving your library."))
    library.library.load(const.LIBRARY)
    for x, y in library.library.rebuild(): pass
    library.library.save(const.LIBRARY)
    raise SystemExit

def print_playing(fstring = "<artist~album~tracknumber~title>"):
    import util; from util import to, FileFromPattern
    from formats.audio import AudioFile
    try:
        fn = file(const.CURRENT)
        data = {}
        for line in fn:
            line = line.strip()
            parts = line.split("=")
            key = parts[0]
            val = "=".join(parts[1:])
            if key.startswith("~#"):
                try: data[key] = int(val)
                except ValueError: data[key] = 0
            else:
                if key != "~filename": val = util.decode(val)
                if key in data: data[key] += "\n" + val
                else: data[key] = val
        print to(FileFromPattern(fstring, False).match(AudioFile(data)))
        raise SystemExit
    except (OSError, IOError):
        print to(_("No song is currently playing."))
        raise SystemExit(True)

def isrunning():
    return os.path.exists(const.CONTROL)

def control(c):
    if not isrunning():
        raise SystemExit(to(_("Quod Libet is not running.")))
    else:
        try:
            import signal
            # This is a total abuse of Python! Hooray!
            signal.signal(signal.SIGALRM, lambda: "" + 2)
            signal.alarm(1)
            f = file(const.CONTROL, "w")
            signal.signal(signal.SIGALRM, signal.SIG_IGN)
            f.write(c)
            f.close()
        except (OSError, IOError, TypeError):
            os.unlink(const.CONTROL)
            print to(_("Unable to write to %s. Removing it.") % const.CONTROL)
            if c != '!': raise SystemExit(True)
        else:
            raise SystemExit

def enable_periodic_save():
    # Check every 5 minutes to see if the library/config on disk are
    # over 15 minutes old; if so, update them. This function can, in theory,
    # break if saving the library takes more than 5 minutes.
    import gobject, time
    from threading import Thread
    def save(save_library, save_config):
        if (time.time() - os.path.mtime(const.LIBRARY)) > 15*60:
            library.save(const.LIBRARY)
        if (time.time() - os.path.mtime(const.CONFIG)) > 15*60:
            config.write(const.CONFIG)
        thread = Thread(target = save, args = (True, True))
        gobject.timeout_add(5*60, thread.start, priority=gobject.PRIORITY_LOW)
    thread = Thread(target = save, args = (False, False))
    gobject.timeout_add(5*60, thread.start, priority=gobject.PRIORITY_LOW)

def cleanup(*args):
    for filename in [const.CURRENT, const.CONTROL]:
        try: os.unlink(filename)
        except OSError: pass

if __name__ == "__main__":
    basedir = os.path.split(os.path.realpath(__file__))[0]
    sys.path.insert(0, os.path.join(basedir, "quodlibet.zip"))
    i18ndir = "/usr/share/locale"

    import locale, gettext
    try: locale.setlocale(locale.LC_ALL, '')
    except: pass
    from util import to

    gettext.bindtextdomain("quodlibet")
    gettext.textdomain("quodlibet")
    gettext.install("quodlibet", unicode = True)

    import const

    # Check command-line parameters before doing "real" work, so they
    # respond quickly.
    opts = sys.argv[1:]
    controls = {"--next": ">", "--previous": "<", "--play": ")",
                "--pause": "|", "--play-pause": "-", "--volume-up": "v+",
                "--volume-down": "v-", }
    controls_opt = { "--seek-to": "s", "--seek": "s", "--shuffle": "&",
                     "--repeat": "@", "--query": "q", "--volume": "v" }
    try:
        for i, command in enumerate(opts):
            if command in ["--help", "-h"]: print_help()
            elif command in ["--version", "-v"]: print_version()
            elif command in ["--refresh-library"]: refresh_cache()
            elif command in controls: control(controls[command])
            elif command in controls_opt:
                control(controls_opt[command] + opts[i+1])
            elif command in ["--play-file"]:
                filename = os.path.abspath(os.path.expanduser(opts[i+1]))
                if os.path.isdir(filename): control("d" + filename)
                else: control("p" + filename)
            elif command in ["--print-playing"]:
                try: print_playing(opts[i+1])
                except IndexError: print_playing()
            else:
                sys.stderr.write(
                    to(_("E: Unknown command line option: %s") % command)+"\n")
                raise SystemExit(to(_("E: Try %s --help") % sys.argv[0]))
    except IndexError:
        sys.stderr.write(
            to(_("E: Option `%s' requires an argument.") % command) + "\n")
        raise SystemExit(to(_("E: Try %s --help") % sys.argv[0]))

    if os.path.exists(const.CONTROL):
        print _("Quod Libet is already running.")
        control('!')

    # Get to the right directory for our data.
    os.chdir(basedir)
    # Initialize GTK.
    import pygtk
    pygtk.require('2.0')
    import gtk
    if gtk.pygtk_version < (2, 4, 1) or gtk.gtk_version < (2, 6):
        sys.stderr.write(to(_("E: You need GTK+ 2.6 and PyGTK 2.4 or greater to run Quod Libet."))+"\n")
        sys.stderr.write(to(_("E: You have GTK+ %s and PyGTK %s.") % (
            ".".join(map(str, gtk.gtk_version)),
            ".".join(map(str, gtk.pygtk_version)))) + "\n")
        raise SystemExit(to(_("E: Please upgrade GTK+/PyGTK.")))

    import util; from util import to

    # Load configuration data and scan the library for new/changed songs.
    import config
    config.init(const.CONFIG)

    # Load the library.
    import library
    library.init(const.LIBRARY)
    print to(_("Loaded song library."))
    from library import library

    if config.get("settings", "scan"):
        for a, c in library.scan(config.get("settings", "scan").split(":")):
            pass

    # Try to initialize the playlist and audio output.
    print to(_("Opening audio device."))
    import player
    try: player.init(config.get("settings", "backend"))
    except IOError:
        import widgets
        gtk.idle_add(widgets.error_and_quit)
        gtk.main()
        config.write(const.CONFIG)
        raise SystemExit(True)

    try: main()
    finally: cleanup()
