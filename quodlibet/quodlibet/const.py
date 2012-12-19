# -*- coding: utf-8 -*-
# Constants used in various parts of QL, mostly strings.

import os
import locale

if os.name == "nt":
    from win32com.shell import shellcon, shell

class Version(tuple):
    """Represent the version of a dependency as a tuple"""

    def __new__(cls, *args):
        # Support tuple or varargs instantiation
        value = args[0] if len(args) == 1 else args
        return tuple.__new__(Version, value)

    def human_version(self):
        return ".".join(map(str, self))

    def __str__(self):
        return self.human_version()

class MinVersions(object):
    """Dependency requirements for Quod Libet / Ex Falso"""
    PYTHON = Version(2, 6)
    PYGTK = Version((2, 16))
    MUTAGEN = Version(1, 14)

VERSION_TUPLE = Version(2, 5)
VERSION = str(VERSION_TUPLE)

PROCESS_TITLE_QL = "quodlibet"
PROCESS_TITLE_EF = "exfalso"

# expanduser doesn't work with unicode on win...
if os.name == "nt":
    # the last 0 means SHGFP_TYPE_CURRENT
    HOME = shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, 0, 0)
else:
    HOME = os.path.expanduser("~")

if 'QUODLIBET_USERDIR' in os.environ:
    USERDIR = os.environ['QUODLIBET_USERDIR']
else:
    if os.name == "nt":
        USERDIR = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        USERDIR = os.path.join(USERDIR, "Quod Libet")
    else:
        USERDIR = os.path.join(HOME, ".quodlibet")

CONTROL = os.path.join(USERDIR, "control")
CONFIG  = os.path.join(USERDIR, "config")
CURRENT = os.path.join(USERDIR, "current")
LIBRARY = os.path.join(USERDIR, "songs")
LOGDIR  = os.path.join(USERDIR, "logs")

DEFAULT_RATING = 0.5

# entry point for the user guide / wiki
ONLINE_HELP = "http://code.google.com/p/quodlibet/wiki/QuickStart"
SEARCH_HELP = "http://code.google.com/p/quodlibet/wiki/SearchingGuide"

# Email used as default for reading/saving per-user data in tags, etc.
EMAIL = os.environ.get("EMAIL", "quodlibet@lists.sacredchao.net")

# Displayed as registered / help email address
SUPPORT_EMAIL = "quod-libet-development@googlegroups.com"

BASEDIR = os.path.dirname(os.path.realpath(__file__))
IMAGEDIR = os.path.join(BASEDIR, "images")

AUTHORS = sorted("""\
Joe Wreschnig
Michael Urman
Iñigo Serna
Ben Zeigler
Niklas Janlert
Joshua Kwan
Nikolai Prokoschenko
Lalo Martins
Tomasz Torcz
Alexey Bobyakov
Zack Weinberg
Bastian Kleineidam
Eduardo Gonzalez
Decklin Foster
Federico Pelloni
Alexandre Passos
Mickael Royer
Robert Muth
Markus Koller
Martin Bergström
Lukáš Lalinský
Anders Carlsson
Lee Willis
Guillaume Chazarain
Javier Kohen
Erich Schubert
David Kågedal
Remi Vanicat
Ari Pollak
Jan Arne Petersen
Josh Lee
Steven Robertson
Christoph Reiter
Anton Shestakov
Nicholas J. Michalek
David Schneider
Türerkan İnce
Philipp Weis
Johan Hovold
Bastien Gorissen
Nick Boultbee
""".strip().split("\n"))

ARTISTS = sorted("""\
Tobias
Jakub Steiner
Fabien Devaux
""".strip().split("\n"))

TBP = os.path.join(USERDIR, "lists", "tagpatterns")
TBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
<artist> - <album>/<tracknumber>. <title>
<artist>/<album>/<tracknumber> - <title>"""

NBP = os.path.join(USERDIR, "lists", "renamepatterns")
NBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber|<tracknumber>. ><title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
/path/<artist> - <album>/<tracknumber>. <title>
/path/<artist>/<album>/<tracknumber> - <title>"""

DEBUG = "QUODLIBET_DEBUG" in os.environ

MENU = """<ui>
  <menubar name='Menu'>
    <menu action='Music'>
      <menuitem action='AddFolders'/>
      <menuitem action='AddFiles'/>
      <menuitem action='AddLocation'/>
      <separator/>
      <menu action='BrowseLibrary'>
      %(browsers)s
      </menu>
      <separator/>
      <menuitem action='Preferences'/>
      <menuitem action='Plugins'/>
      <separator/>
      <menuitem action='RefreshLibrary'/>
      <menuitem action='ReloadLibrary'/>
      <separator/>
      <menuitem action='Quit'/>
    </menu>
    <menu action='Filters'>
      <menuitem action='FilterGenre'/>
      <menuitem action='FilterArtist'/>
      <menuitem action='FilterAlbum'/>
      <separator/>
      <menuitem action='RandomGenre'/>
      <menuitem action='RandomArtist'/>
      <menuitem action='RandomAlbum'/>
      <separator/>
      <menuitem action='PlayedRecently'/>
      <menuitem action='AddedRecently'/>
      <menuitem action='TopRated'/>
    </menu>
    <menu action='Control'>
      <menuitem action='Previous'/>
      <menuitem action='PlayPause'/>
      <menuitem action='Next'/>
      <separator/>
      <menuitem action='EditTags'/>
      <menuitem action='Information'/>
      <separator/>
      <menuitem action='Jump'/>
    </menu>
    <menu action='View'>
      <menuitem action='SongList'/>
      <menuitem action='Queue'/>
      <separator/>
      %(views)s
    </menu>
    <menu action='Help'>
      <menuitem action='OnlineHelp'/>
      <menuitem action='SearchHelp'/>
      <menuitem action='About'/>
      %(debug)s
    </menu>
  </menubar>
</ui>"""

try: ENCODING = locale.getpreferredencoding()
except locale.Error: ENCODING = "utf-8"

# http://developer.gnome.org/doc/API/2.0/glib/glib-running.html
if "G_FILENAME_ENCODING" in os.environ:
    FSCODING = os.environ["G_FILENAME_ENCODING"].split(",")[0]
    if FSCODING == "@locale":
        FSCODING = ENCODING
elif "G_BROKEN_FILENAMES" in os.environ:
    FSCODING = ENCODING
else: FSCODING = "utf-8"

del(os)
del(locale)

