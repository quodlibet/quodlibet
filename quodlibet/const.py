# -*- coding: utf-8 -*-
# Constants used in various parts of QL, mostly strings.

import os
import locale

VERSION = "0.21"

HOME    = os.path.expanduser("~")
USERDIR = os.path.join(HOME, ".quodlibet")
CONTROL = os.path.join(USERDIR, "control")
CONFIG  = os.path.join(USERDIR, "config")
CURRENT = os.path.join(USERDIR, "current")
LIBRARY = os.path.join(USERDIR, "songs")

EMAIL = "quodlibet@lists.sacredchao.net"

BASEDIR = os.path.dirname(os.path.realpath(__file__))

AUTHORS = """\
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

Anders Carlsson (trayicon)
Lee Willis, Jan Arne Petersen (mmkeys)""".split("\n")

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

MENU = """<ui>
  <menubar name='Menu'>
    <menu action='Music'>
      <menuitem action='AddFolders'/>
      <menuitem action='AddFiles'/>
      <menuitem action='AddLocation'/>
      <separator/>
      <menu action='BrowseLibrary'>
      %s
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
      <menuitem action='NotPlayedDay'/>
      <menuitem action='NotPlayedWeek'/>
      <menuitem action='NotPlayedMonth'/>
      <menuitem action='NotPlayedEver'/>
      <separator/>
      <menuitem action='Top'/>
      <menuitem action='Bottom'/>
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
      %s
    </menu>
    <menu action='Help'>
      <menuitem action='About'/>
    </menu>
  </menubar>
</ui>"""

MACHINE_TAGS = (
    "musicbrainz_trackid musicbrainz_trmid musicbrainz_albumid "
    "musicbrainz_albumartistid musicbrainz_artistid musicip_puid "
    "replaygain_track_gain replaygain_album_gain "
    "replaygain_album_peak replaygain_track_peak "
    ).split()

ENCODING = locale.getpreferredencoding()

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
