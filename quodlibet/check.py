#!/usr/bin/env python
# check.py -- check for system requirements
# public domain

import os
import sys

NAME = "Quod Libet"

if __name__ == "__main__":
    print "Checking Python version:",
    print ".".join(map(str, sys.version_info[:2]))
    if sys.version_info < (2, 4):
        raise SystemExit("%s requires at least Python 2.4. "
                         "(http://www.python.org)" % NAME)

    print "Checking for PyGTK >= 2.8:",
    try:
        import pygtk
        pygtk.require('2.0')
        import gtk
        if gtk.pygtk_version < (2, 8) or gtk.gtk_version < (2, 8):
            raise ImportError
    except ImportError:
        raise SystemExit("not found\n%s requires PyGTK 2.8. "
                         "(http://www.pygtk.org)" % NAME)
    else: print "found"

    print "Checking for PyGSt >= 0.10.1:",
    try:
        import pygst
        pygst.require("0.10")
        import gst
        if gst.pygst_version < (0, 10, 1):
            raise ImportError
    except ImportError:
        raise SystemExit("not found\n%s requires gst-python 0.10.1. "
                         "(http://gstreamer.freedesktop.org)" % NAME)
    else: print "found"

    print "Checking for Mutagen >= 1.9:",
    try:
        import mutagen
        if mutagen.version < (1, 9):
            raise ImportError
    except ImportError:
        raise SystemExit("not found\n%s requires Mutagen 1.9.\n"
                         "(http://www.sacredchao.net/quodlibet/wiki/Development/Mutagen)" % NAME)
    else: print "found"

    print "Checking for ctypes:",
    try: import ctypes
    except ImportError:
        print ("not found\n%s recommends ctypes.\n"
               "\t(http://starship.python.net/crew/theller/ctypes/)" % NAME)
    else: print "found"

    print "\nYour system meets the requirements to install %s." % NAME
    print "Type 'make install' (as root) to install it."
    print "You may want to make some extensions first; see the README file."

    if sys.argv[1:] and os.path.isdir(sys.argv[1]):
        print "\nIt looks like you might have Quod Libet installed already."
        print "Installing directly over an old version is not supported."
        print "Please remove %s before continuing." % sys.argv[1]
