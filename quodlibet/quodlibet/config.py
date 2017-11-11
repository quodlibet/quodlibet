# -*- coding: utf-8 -*-
# Copyright 2004-2008 Joe Wreschnig
#           2009-2017 Nick Boultbee
#           2011-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil

from quodlibet.util import enum
from . import const
from quodlibet.util.config import Config, Error
from quodlibet.util import print_d, print_w
from quodlibet.compat import PY2, iteritems, text_type

# Some plugins can be enabled on first install
AUTO_ENABLED_PLUGINS = ["Shuffle Playlist", "Remove Playlist Duplicates"]


def _config_text(text):
    # raw config values are utf-8 encoded on PY2, while they are unicode
    # with surrogates on PY2. this makes initing the defaults work

    assert isinstance(text, text_type)
    if PY2:
        return text.encode("utf-8")
    return text


# this defines the initial and default values
INITIAL = {
    # User-defined tag name -> human name mappings
    "header_maps": {
    },

    "player": {
        "time_remaining": "false",
        "replaygain": "on",
        "fallback_gain": "0.0",
        "pre_amp_gain": "0.0",
        "backend": "gstbe",
        "gst_pipeline": "",

        # stream buffer duration in seconds
        "gst_buffer": "3",

        "gst_device": "",
        "gst_disable_gapless": "false",
    },
    "library": {
        "exclude": "",
        "refresh_on_start": "true",
    },

    # State about the player, to restore on startup
    "memory": {

        # filename of last song
        "song": "",

        # last song position, in milliseconds
        "seek": "0",

        # internal volume, [0.0, 1.0]
        "volume": "1.0",

        # browser name
        "browser": "PanedBrowser",

        "queue": "false",
        "queue_expanded": "false",
        "shufflequeue": "false",
        "queue_stop_once_empty": "false",

        # <reversed?>tagname, song list sort
        "sortby": "0album",

        # Repeat on or off
        "repeat": "false",

        # The Repeat (Order) to use
        "repeat_mode": "repeat_song",

        # Shuffle on or off
        "shuffle": "false",

        # The Shuffle (Order) to use
        "shuffle_mode": "random",

        # selected plugin in manager
        "plugin_selection": "",

        # column widths in c1,w1,c2,w2... format
        "column_widths": "",

        "column_expands": "",
    },

    "browsers": {

        # search bar text
        "query_text": "",

        # panes in paned browser
        "panes":
            "~people\t<~year|[b][i]<~year>[/i][/b] - ><album>",

        # selected pane values
        "pane_selection": "",

        # browser orientation
        "pane_wide_mode": "0",

        # equal pane width in paned browser
        "equal_pane_width": "true",

        # "global" filter for SearchBar
        "background": "",

        # album list
        "albums": "",

        # album sorting mode, default is title
        "album_sort": "0",

        # album cover display, on/off
        "album_covers": "1",

        # include substrings in inline search
        "album_substrings": "1",

        # Collections browser: tag to collect, merge or not (0 = no)
        "collection_headers": "~people 0",

        # radio filter selection
        "radio": "",

        # click to rate song, on/off
        "rating_click": "true",

        # confirm rating multiple songs
        "rating_confirm_multiple": "false",

        # max cover height/width, <= 0 is default
        "cover_size": "-1",

        # Show the limit widgets for SearchBar
        "search_limit": "false",

        # show text in covergrid view
        "album_text": "1",

        # Cover magnifcation factor in covergrid view
        "covergrid_magnification": "3.0",

        # show "all albums" in covergrid view
        "covergrid_all": "0",
    },

    # Kind of a dumping ground right now, should probably be
    # cleaned out later.
    "settings": {

        # scan directories, :-separated
        "scan": "",

        # scroll song list on current song change
        "jump": "true",

        # Unrated songs are given this value
        "default_rating": "0.5",

        # Rating scale i.e. maximum number of symbols
        "ratings": "4",

        # (0 = disabled i.e. arithmetic mean)
        "bayesian_rating_factor": "0.0",

        # rating symbol (black star)
        "rating_symbol_full": _config_text(u'\u2605'),

        # rating symbol (hollow star)
        "rating_symbol_blank": _config_text(u'\u2606'),

        # Comma-separated columns to display in the song list
        "columns": ",".join(const.DEFAULT_COLUMNS),

        # hack to disable hints, see bug #526
        "disable_hints": "false",

        # search as soon as text is typed into search box
        "eager_search": "true",

        # tags which get searched in addition to the ones present in the
        # song list, separate with ","
        "search_tags": "",

        # If set to "true" allow directly deleting files, even on systems that
        # support sending them to the trash.
        "bypass_trash": "false",

        # osx implementation might be buggy so let users disable it
        "disable_mmkeys": "false",

        # the UI language to use, empty means system default
        "language": "",

        # the pattern for the main window title
        "window_title_pattern": "~title~version~~people",

        # the format of the timestamps in DateColumn
        "datecolumn_timestamp_format": "",
    },

    "rename": {
        "spaces": "false",
        "windows": "true",
        "ascii": "false",
        "move_art": "false",
        "move_art_overwrite": "false",
        "remove_empty_dirs": "false",
    },

    "tagsfrompath": {
        "underscores": "false",
        "titlecase": "false",
        "split": "false",
        "add": "false",
    },

    "plugins": {
        # newline-separated plugin IDs
        "active_plugins": "\n".join(AUTO_ENABLED_PLUGINS),

        # Issue 1231: Maximum number of SongsMenu plugins to run at once
        "default_max_plugin_invocations": 30,
    },

    "editing": {
        # characters to split tags on
        "split_on": "/ & ,",

        # ID3 encodings to try
        "id3encoding": "",

        "human_title_case": "true",
        "save_to_songs": "true",
        "save_email": const.EMAIL,

        # show all tags, or just "human-readable" ones
        "alltags": "true",

        # Skip dialog to save or revert changes
        "auto_save_changes": "false",

        # e.g. "title,artist"
        "default_tags": "",
    },

    "albumart": {
        "prefer_embedded": "false",
        "force_filename": "false",
        "filename": "folder.jpg",
        "search_filenames": "cover.jpg,folder.jpg,.folder.jpg",
    },

    "display": {
        "duration_format": "standard"
    }
}

# global instance
_config = Config(version=0)

options = _config.options
get = _config.get
gettext = _config.gettext
getboolean = _config.getboolean
getint = _config.getint
getfloat = _config.getfloat
getstringlist = _config.getstringlist
setstringlist = _config.setstringlist
getlist = _config.getlist
setlist = _config.setlist
set = _config.set
settext = _config.settext
write = _config.write
reset = _config.reset
add_section = _config.add_section
has_option = _config.has_option
remove_option = _config.remove_option
register_upgrade_function = _config.register_upgrade_function
getbytes = _config.getbytes
setbytes = _config.setbytes

_filename = None
"""The filename last used for loading"""


def init_defaults():
    """Fills in the defaults, so they are guaranteed to be available"""

    _config.defaults.clear()
    for section, values in iteritems(INITIAL):
        _config.defaults.add_section(section)
        for key, value in iteritems(values):
            _config.defaults.set(section, key, value)


def init(filename=None):
    global _filename

    if not _config.is_empty():
        _config.clear()

    _filename = filename

    if filename is not None:
        try:
            _config.read(filename)
        except (Error, EnvironmentError):
            print_w("Reading config file %r failed." % filename)

            # move the broken file out of the way
            try:
                shutil.copy(filename, filename + ".not-valid")
            except EnvironmentError:
                pass


def save(filename=None):
    """Writes the active config to filename, ignoring all possible errors.

    If not filename is given the one used for loading is used.
    """

    global _filename

    if filename is None:
        filename = _filename
        if filename is None:
            return

    print_d("Writing config...")
    try:
        _config.write(filename)
    except EnvironmentError:
        print_w("Unable to write config.")


def quit():
    """Clears the active config"""

    _config.clear()


def state(arg):
    return _config.getboolean("settings", arg)


class RatingsPrefs(object):
    """
    Models Ratings settings as configured by the user, with caching.
    """

    def __init__(self):
        self.__number = self.__default = None
        self.__full_symbol = self.__blank_symbol = None

    @property
    def precision(self):
        """Returns the smallest ratings delta currently configured"""
        return 1.0 / self.number

    @property
    def number(self):
        if self.__number is None:
            self.__number = getint("settings", "ratings")
        return self.__number

    @number.setter
    def number(self, i):
        """The (maximum) integer number of ratings icons configured"""
        self.__number = self.__save("ratings", int(i))

    @property
    def default(self):
        """The current default floating-point rating"""
        if self.__default is None:
            self.__default = getfloat("settings", "default_rating")
        return self.__default

    @default.setter
    def default(self, f):
        self.__default = self.__save("default_rating", float(f))

    @property
    def full_symbol(self):
        """The symbol to use for a full (active) rating"""
        if self.__full_symbol is None:
            self.__full_symbol = self.__get_symbol("full")
        return self.__full_symbol

    @full_symbol.setter
    def full_symbol(self, s):
        self.__full_symbol = self.__save("rating_symbol_full", s)

    @property
    def blank_symbol(self):
        """The symbol to use for a blank (inactive) rating, if needed"""
        if self.__blank_symbol is None:
            self.__blank_symbol = self.__get_symbol("blank")
        return self.__blank_symbol

    @blank_symbol.setter
    def blank_symbol(self, s):
        self.__blank_symbol = self.__save("rating_symbol_blank", s)

    @property
    def all(self):
        """Returns all the possible ratings currently available"""
        return [float(i) / self.number for i in range(0, self.number + 1)]

    @staticmethod
    def __save(key, value):
        set("settings", key, value)
        return value

    @staticmethod
    def __get_symbol(variant="full"):
        return gettext("settings", "rating_symbol_%s" % variant)


class HardCodedRatingsPrefs(RatingsPrefs):
    number = int(INITIAL["settings"]["ratings"])
    default = float(INITIAL["settings"]["default_rating"])
    blank_symbol = INITIAL["settings"]["rating_symbol_blank"]
    full_symbol = INITIAL["settings"]["rating_symbol_full"]
    if PY2:
        blank_symbol = blank_symbol.decode("utf-8")
        full_symbol = full_symbol.decode("utf-8")


# Need an instance just for imports to work
RATINGS = RatingsPrefs()


@enum
class DurationFormat(str):
    NUMERIC, SECONDS = "numeric", "numeric-seconds"
    STANDARD, FULL = "standard", "text-full"


class DurationFormatPref(object):
    @property
    def format(self):
        raw = get("display", "duration_format")
        return DurationFormat.value_of(raw, DurationFormat.STANDARD)

    @format.setter
    def format(self, value):
        set("display", "duration_format", value)


DURATION = DurationFormatPref()
