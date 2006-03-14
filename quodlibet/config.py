# Copyright 2004 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Simple proxy to a Python ConfigParser.
import os

# We don't need/want variable interpolation.
from ConfigParser import RawConfigParser as ConfigParser, Error as error

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

        "player":
        { "time_remaining": "false",
          },

        # State about the player, to restore on startup
        "memory":
        { "size": "400 350", # player window size
          "song": "", # filename of last song
          "volume": "1.0", # internal volume, [0.0, 1.0]
          "browser": "SearchBar", # browser name
          "songlist": "true", # on or off
          "queue": "false", # on or off
          "shufflequeue": "false", # on or off
          "sortby": "0album", # <reversed?>tagname, song list sort
          "order": "inorder",
          },

        "browsers":
        { "query_text": "", # none/search bar text
          "color": "true", # color search terms in search bar
          "panes": "~people album", # panes in paned browser
          "pane_selection": "", # selected pane values
          "background": "", # "global" filter for SearchBar
          "albums": "", # album list
          "album_sort": "0", # album sorting mode, default is title
          "album_covers": "1", # album cover display, on/off
          },

        # Kind of a dumping ground right now, should probably be
        # cleaned out later.
        "settings":
        { "scan": "", # scan directories, :-separated

          "gain": "2", # replaygain - none, radio, audiophile
          "jump": "true", # scroll song list on current song change
          "ratings": "4", # maximum rating value

          # probably belong in memory
          "repeat": "false",

          "pipeline": "", # GStreamer audio pipeline

          # initial column headers
          "headers": "~#track ~title~version ~album~part artist ~#length",

          # hack to disable hints, see bug #526
          "disable_hints": "false",
          },

        "rename":
        { "spaces": "false",
          "windows": "true",
          "ascii": "false",
          },

        "tagsfrompath":
        { "underscores": "false",
          "titlecase": "false",
          "split": "false",
          "add": "false",
          },

        "plugins":
        { "icon_tooltip":
          "<album|<album~discnumber~part~tracknumber~title~version>|"
          "<artist~title~version>>", # tooltip for the tray icon
          "icon_modifier_swap": "false",
          "active": "", # activated plugins
          },

        "editing":
        { "split_on": "& , /", # words to split on
          "id3encoding": "", # ID3 encodings to try
          "alltags": "true", # show all comments, or just "human" ones
          },
        }

    for section, values in initial.iteritems():
        _config.add_section(section)
        for key, value in values.iteritems():
            _config.set(section, key, value)

    _config.read(rc_files)

def state(arg):
    return _config.getboolean("settings", arg)
