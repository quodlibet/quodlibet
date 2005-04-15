#!/usr/bin/python -u
# check.py -- check for system requirements
# public domain

NAME = "Quod Libet"

import sys

if __name__ == "__main__":
    print "Checking Python version:",
    print ".".join(map(str, sys.version_info[:2]))
    if sys.version_info < (2, 3):
        raise SystemExit("%s requires at least Python 2.3."
                         "(http://www.python.org)" % NAME)

    print "Checking for PyGTK >= 2.6:",
    try:
        import pygtk
        pygtk.require('2.0')
        import gtk
        if gtk.pygtk_version < (2, 6) or gtk.gtk_version < (2, 6):
            raise ImportError
    except ImportError:
        raise SystemExit("not found\n%s requires PyGTK 2.6. "
                         "(http://www.pygtk.org)" % NAME)
    else: print "found"

    print "Checking for ogg.vorbis:",
    try: import ogg.vorbis
    except ImportError:
        print ("not found\n%s recommends libvorbis/pyvorbis. "
               "(http://www.andrewchatham.com/pyogg/)" % NAME)
    else: print "found"

    print "Checking for MAD:",
    try: import mad
    except ImportError:
        print ("not found\n%s recommends MAD/pymad. "
               "(http://www.mars.org/home/rob/proj/mpeg/)" % NAME)
    else: print "found"

    print "Checking for id3lib: ",
    try: import pyid3lib
    except ImportError:
        print ("not found\n%s recommends id3lib. "
               "(http://pyid3lib.sourceforge.net/)" % NAME)
    else: print "found"

    print "Checking for ao:",
    try: import ao
    except ImportError:
        print ("not found\n%s recommends libao/pyao "
               "(for ALSA/aRts/ESD output).\n"
               " (http://www.andrewchatham.com/pyogg/)" % NAME)
    else: print "found"

    print "\nYour system meets the requirements to install %s." % NAME
    print "Type 'make install' (as root) to install it."
    print "You may want to make some extensions first; see the README file."
