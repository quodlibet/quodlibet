# Copyright 2004 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Simple proxy to a Python ConfigParser.
import os

# Need to use a RawConfigParser because the PMP-related keys can
# contain %s, which breaks the "smart" ConfigParser's interpolation.
from ConfigParser import RawConfigParser as ConfigParser

_config = ConfigParser()
get = _config.get
set = _config.set
getboolean = _config.getboolean
getint = _config.getint
getfloat = _config.getfloat
write = _config.write
options = _config.options

def write(filename):
    if isinstance(filename, str):
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        f = file(filename, "w")
    else: f = filename
    _config.write(f)
    f.close()

def init(*rc_files):
    initial = {
        # User-defined tag name -> human name mappings
        "header_maps": {},

        # State about the player, to restore on startup
        "memory":
        { "size": "400 350", # player window size
          "song": "", # filename of last song
          "volume": "1.0", # internal volume, [0.0, 1.0]
          "browser": "1", # none, search, playlist, panes
          "songlist": "true", # on or off
          "sortby": "1artist" # <asc/desc>tagname, song list sort
          },

        "browsers":
        { "query_text": "", # none/search bar text
          "color": "true", # color search terms in search bar
          "panes": "artist album", # panes in paned browser
          "pane_selection": "", # selected pane values
          "background": "", # "global" filter for SearchBar
          },

        # Kind of a dumping ground right now, should probably be
        # cleaned out later.
        "settings":
        { "scan": "", # scan directories, :-separated
          "masked": "", # masked directories, :-separated

          "gain": "2", # replaygain - none, radio, audiophile
          "cover": "true", # display album cover images
          "jump": "true", # scroll song list on current song change
          "osd": "0", # OSD - none, top, bottom
          "osdcolors": "#ffbb00 #ff8700", # color for the OSD, fed to Pango
          "osdfont": "Sans 18", # font for the OSD, fed to Pango

          # probably belong in memory
          "shuffle": "false",
          "repeat": "false",

          "tbp_space": "false", # replace _s with spaces in TBP
          "addreplace": "0", # 0 - replace tags, 1 - add tags, in TBP
          "titlecase": "false", # titlecase values in TBP
          "splitval": "true", # split values in TBP
          "nbp_space": "false", # replace spaces with _s in renaming
          "windows": "true", # replace invalid Win32 characters with _s
          "ascii": "false", # replace non-ASCII characters with _s
          "allcomments": "true", # show all comments, or just "human" ones
          "splitters": ",;&/",

          "backend": "ao:alsa09", # audio backend

          # initial column headers
          "headers": "~#track ~title~version ~album~part artist ~length"
          },

        "plugins":
        { "icon_tooltip":
          "<album|<album~discnumber~part~tracknumber~title~version>|"
          "<artist~title~version>>", # tooltip for the tray icon
          "icon_close": "false", # delete-event minimizes to system tray

          },

        "exfalso":
        { "shutup": "false", # don't whine about QL running.
          }
        }

    for section, values in initial.iteritems():
        _config.add_section(section)
        for key, value in values.iteritems():
            _config.set(section, key, value)

    _config.read(rc_files)

def state(arg):
    return _config.getboolean("settings", arg)
