# -*- coding: utf-8 -*-
# Short string constants and long non-translated ones.

import os

VERSION = "0.11"

HOME    = os.path.expanduser("~")
DIR     = os.path.join(HOME, ".quodlibet")
CONTROL = os.path.join(DIR,  "control")
CONFIG  = os.path.join(DIR,  "config")
CURRENT = os.path.join(DIR,  "current")
LIBRARY = os.path.join(DIR,  "songs")
ACCELS  = os.path.join(DIR,  "accels")

PLUGINS = os.path.join(DIR, "plugins")
QUERIES  = os.path.join(DIR, "lists",  "queries")

CREDITS = ["Joe Wreschnig",
           "Michael Urman",
           "Iñigo Serna",
           "Bastian Kleineidam",
           "Michal Nowikowski",
           "Ben Zeigler",
           "Niklas Janlert",

           "Anders Carlsson",
           "Lee Willis",
           "Jan Arne Petersen",
           "Gustavo J. A. M. Carneiro"]

TBP = os.path.join(DIR, "lists", "tagpatterns")
TBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
<artist> - <album>/<tracknumber>. <title>
<artist>/<album>/<tracknumber> - <title>"""

NBP = os.path.join(DIR, "lists", "renamepatterns")
NBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber|<tracknumber>. ><title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
/path/<artist> - <album>/<tracknumber>. <title>
/path/<artist>/<album>/<tracknumber> - <title>"""

COPYRIGHT = """\
<u><span weight="bold" size="xx-large">Quod Libet %s</span></u>
&lt;quodlibet@lists.sacredchao.net&gt;
http://www.sacredchao.net/quodlibet
Copyright © 2004-2005""" % VERSION

MENU = """<ui>
  <menubar name='Menu'>
    <menu action='Music'>
      <menuitem action='AddMusic'/>
      <menuitem action='NewPlaylist'/>
      <separator/>
      <menuitem action='Preferences'/>
      <separator/>
      <menuitem action='RefreshLibrary'/>
      <menuitem action='ReloadLibrary'/>
      <separator/>
      <menuitem action='Quit'/>
    </menu>
    <menu action='Filters'>
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
    <menu action='Song'>
      <menuitem action='Previous'/>
      <menuitem action='PlayPause'/>
      <menuitem action='Next'/>
      <separator/>
      <menuitem action='FilterGenre'/>
      <menuitem action='FilterArtist'/>
      <menuitem action='FilterAlbum'/>
      <separator/>
      <menuitem action='Properties'/>
      <separator/>
      <menuitem action='Jump'/>
    </menu>
    <menu action='View'>
      <menuitem action='Songlist'/>
      <separator/>
      <menuitem action='BrowserDisable'/>
      <menuitem action='BrowserSearch'/>
      <menuitem action='BrowserPlaylist'/>
      <menuitem action='BrowserPaned'/>
    </menu>
    <menu action='Help'>
      <menuitem action='About'/>
    </menu>
  </menubar>
</ui>"""
