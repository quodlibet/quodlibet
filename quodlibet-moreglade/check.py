#!/usr/bin/env python
# check.py -- check for system requirements
# public domain

NAME = "Quod Libet"

import sys

sys.stdout.write("Checking Python version: ")
sys.stdout.write(".".join(map(str, sys.version_info[:2])) + "\n")
if sys.version_info < (2, 3):
    raise SystemExit("%s requires at least Python 2.3. "
                     "(http://www.python.org)" % NAME)

sys.stdout.write("Checking for PyGTK >= 2.4: ")
try:
    import pygtk
    pygtk.require('2.0')
    import gtk
    if gtk.pygtk_version < (2, 4) or gtk.gtk_version < (2, 4):
        raise ImportError
    import gtk.glade
except ImportError:
    raise SystemExit("not found\n%s requires PyGTK 2.4 and Glade. "
                     "(http://www.pygtk.org)" % NAME)
else: print "found"

sys.stdout.write("Checking for ogg.vorbis: ")
try: import ogg.vorbis
except ImportError:
    print ("not found\n%s recommends libvorbis/pyvorbis. "
           "(http://www.andrewchatham.com/pyogg/)" % NAME)
else: print "found"

sys.stdout.write("Checking for MAD: ")
try: import mad
except ImportError:
    print ("not found\n%s recommends MAD/pymad. "
           "(http://www.mars.org/home/rob/proj/mpeg/)" % NAME)
else: print "found"

sys.stdout.write("Checking for id3lib: ")
try: import pyid3lib
except ImportError:
    print ("not found\n%s recommends id3lib. "
           "(http://pyid3lib.sourceforge.net/)" % NAME)
else: print "found"

sys.stdout.write("Checking for pyflac: ")
try: import flac
except ImportError:
    print ("not found\n%s recommends pyflac. "
           "(http://users.dart.net.au/~collett/software/pyflac-0.0.1.tar.gz)" % NAME)
else: print "found"

sys.stdout.write("Checking for ao: ")
try: import ao
except ImportError:
    print ("not found\n%s recommends libao/pyao (for ALSA/aRts/ESD output).\n"
           " (http://www.andrewchatham.com/pyogg/)" % NAME)
else: print "found"

print "\nYour system meets the requirements to install %s." % NAME
print "Type 'make install' (as root) to install it."
print "You may want to make some extensions first; see the README file."
