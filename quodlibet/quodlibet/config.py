# Copyright 2004 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Simple proxy to a Python ConfigParser.

import os

import const

# We don't need/want variable interpolation.
from ConfigParser import RawConfigParser as ConfigParser, Error as error

_config = ConfigParser()
get = _config.get
set = _config.set
getboolean = _config.getboolean
getint = _config.getint
getfloat = _config.getfloat
options = _config.options

def write(filename):
    if isinstance(filename, basestring):
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        f = file(filename, "w")
    else: f = filename
    _config.write(f)
    f.close()

def quit():
    for section in _config.sections():
        _config.remove_section(section)

def init(*rc_files):
    if len(_config.sections()):
        raise ValueError("config initialized twice without quitting: %r" % _config.sections())
    initial = {
        # User-defined tag name -> human name mappings
        "header_maps": {},

        "player":
        { "time_remaining": "false",
          "replaygain": "on",
          "fallback_gain" : "0.0",
          "pre_amp_gain" : "0.0",
          "backend": "gstbe",
          "gst_pipeline": "",
          },

        "library":
        { "exclude": "",
          "refresh_on_start": "true",
          },

        # State about the player, to restore on startup
        "memory":
        { "size": "400 350", # player window size
          "position": "0 0", # player window position
          "maximized": "0", # main window maximized
          "exfalso_size": "700 500", # ex falso window size
          "exfalso_maximized": "0", # ex falso window maximized
          "browser_size": "500 300", # library browser window size
          "song": "", # filename of last song
          "seek": "0", # last song position, in milliseconds
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
          "panes": "~people	<~year|<~year> - <album>|<album>>", # panes in paned browser
          "pane_selection": "", # selected pane values
          "background": "", # "global" filter for SearchBar
          "albums": "", # album list
          "album_sort": "0", # album sorting mode, default is title
          "album_covers": "1", # album cover display, on/off
          "album_substrings": "1", # include substrings in inline search
          "rating_click": "true", # click to rate song, on/off
          "rating_confirm_multiple": "false", # confirm rating multiple songs
          },

        # Kind of a dumping ground right now, should probably be
        # cleaned out later.
        "settings":
        { "scan": "", # scan directories, :-separatd
          "round": "true", # use rounded corners for artwork thumbnails
          "jump": "true", # scroll song list on current song change
          "default_rating": "0.5", # initial rating of new song
          "ratings": "4", # maximum rating value

          # probably belong in memory
          "repeat": "false",

          # initial column headers
          "headers": "~#track ~title~version ~album~discsubtitle ~#length",

          # hack to disable hints, see bug #526
          "disable_hints": "false",

          # search as soon as text is typed into search box
          "eager_search": "true",
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

        "plugins": { },

        "editing":
        { "split_on": "/ & ,", # words to split on
          "id3encoding": "", # ID3 encodings to try
          "human_title_case": "true",
          "save_to_songs": "true",
          "save_email": const.EMAIL,
          "alltags": "true", # show all tags, or just "human-readable" ones
          },
        }

    # <=2.2.1 QL created the user folder in the profile folder
    # but it should be in the appdata folder, so move it.
    if os.name == "nt":
        old_dir = os.path.join(os.path.expanduser("~"), ".quodlibet")
        new_dir = const.USERDIR
        if not os.path.isdir(new_dir) and os.path.isdir(old_dir):
            import shutil
            shutil.move(old_dir, new_dir)

    for section, values in initial.iteritems():
        _config.add_section(section)
        for key, value in values.iteritems():
            _config.set(section, key, value)

    _config.read(rc_files)

def state(arg):
    return _config.getboolean("settings", arg)

def add_section(section):
    if not _config.has_section(section):
        _config.add_section(section)

