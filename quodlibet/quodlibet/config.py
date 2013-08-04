# Copyright 2004-2011 Joe Wreschnig, Christoph Reiter
#           2009-2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Simple proxy to a Python ConfigParser.
# TODO: refactor method names for PEP-8

from StringIO import StringIO
import csv

import os

import const
from quodlibet.util.dprint import print_d, print_w

# We don't need/want variable interpolation.
from ConfigParser import RawConfigParser as ConfigParser, Error


# In newer RawConfigParser it is possible to replace the internal dict. The
# implementation only uses items() for writing, so replace with a dict that
# returns them sorted. This makes it easier to look up entries in the file.
class _sorted_dict(dict):
    def items(self):
        return sorted(super(_sorted_dict, self).items())

try:
    _config = ConfigParser(dict_type=_sorted_dict)
except TypeError:
    _config = ConfigParser()
options = _config.options


def get(*args):
    if len(args) == 3:
        try:
            return _config.get(*args[:2])
        except Error:
            return args[-1]
    return _config.get(*args)


def getboolean(*args):
    if len(args) == 3:
        if not isinstance(args[-1], bool):
            raise ValueError
        try:
            return _config.getboolean(*args[:2])
        # ValueError if the value found in the config file
        # does not match any string representation -> so catch it too
        except (ValueError, Error):
            return args[-1]
    return _config.getboolean(*args)


def getint(*args):
    if len(args) == 3:
        if not isinstance(args[-1], int):
            raise ValueError
        try:
            return _config.getint(*args[:2])
        except Error:
            return args[-1]
    return _config.getint(*args)


def getfloat(*args):
    if len(args) == 3:
        if not isinstance(args[-1], float):
            raise ValueError
        try:
            return _config.getfloat(*args[:2])
        except Error:
            return args[-1]
    return _config.getfloat(*args)


def getstringlist(*args):
    """Gets a list of strings, using CSV to parse and delimit"""
    if len(args) == 3:
        if not isinstance(args[-1], list):
            raise ValueError
        try:
            value = _config.get(*args[:2])
        except Error:
            return args[-1]
    else:
        value = _config.get(*args)
    parser = csv.reader([value])
    vals = [v.decode('utf-8') for v in parser.next()]
    print_d("%s.%s = %s" % (args + (vals,)))
    return vals


def setstringlist(section, option, values):
    """Sets a config item to a list of quoted strings, using CSV"""
    sw = StringIO()
    values = [unicode(v).encode('utf-8') for v in values]
    writer = csv.writer(sw, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(values)
    _config.set(section, option, sw.getvalue())


# RawConfigParser only allows string values but doesn't scream if they are not
# (and it only fails before the first config save..)
def set(section, option, value):
    if not isinstance(value, str):
        value = str(value)
    _config.set(section, option, value)


def setdefault(section, option, default):
    if not _config.has_option(section, option):
        set(section, option, default)


def write(filename):
    if isinstance(filename, basestring):
        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        f = file(filename, "w")
    else:
        f = filename
    _config.write(f)
    f.close()


def save(filename):
    print_d("Writing config...")
    try:
        write(filename)
    except EnvironmentError:
        print_w("Unable to write config.")


def quit():
    for section in _config.sections():
        _config.remove_section(section)


def init(*rc_files):
    if len(_config.sections()):
        raise ValueError("config initialized twice without quitting: %r"
                         % _config.sections())
    initial = {
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
            "gst_buffer": "1.5", # stream buffer duration in seconds
            "gst_device": "",
        },
        "library": {
            "exclude": "",
            "refresh_on_start": "true",
        },
        # State about the player, to restore on startup
        "memory": {
            "song": "", # filename of last song
            "seek": "0", # last song position, in milliseconds
            "volume": "1.0", # internal volume, [0.0, 1.0]
            "browser": "PanedBrowser", # browser name
            "songlist": "true", # on or off
            "queue": "false", # on or off
            "shufflequeue": "false", # on or off
            "sortby": "0album", # <reversed?>tagname, song list sort
            "order": "inorder",
            "plugin_selection": "", # selected plugin in manager
        },
        "browsers": {
            "query_text": "", # none/search bar text
            # panes in paned browser
            "panes":
                "~people	<~year|[b][i]<~year>[/i][/b] - ><album>",
            "pane_selection": "", # selected pane values
            "pane_wide_mode": "0", # browser orientation
            "background": "", # "global" filter for SearchBar
            "albums": "", # album list
            "album_sort": "0", # album sorting mode, default is title
            "album_covers": "1", # album cover display, on/off
            "album_substrings": "1", # include substrings in inline search
            "collection_headers": "~people 0",
            "radio": "", # radio filter selection
            "rating_click": "true", # click to rate song, on/off
            "rating_confirm_multiple": "false", # confirm rating multiple songs
            "cover_size": "-1", # max cover height/width, <= 0 is default
            "search_limit": "false", # Show the limit widgets for SearchBar
        },
        # Kind of a dumping ground right now, should probably be
        # cleaned out later.
        "settings": {
            "scan": "", # scan directories, :-separated
            "jump": "true", # scroll song list on current song change
            "default_rating": "0.5", # initial rating of new song
            "ratings": "4", # maximum rating value
            # (0 = disabled i.e. arithmetic mean)
            "bayesian_rating_factor": "0.0",
            # rating symbol (black star)
            "rating_symbol_full": "\xe2\x98\x85",
            # rating symbol (hollow star)
            "rating_symbol_blank": "\xe2\x98\x86",

            # probably belong in memory
            "repeat": "false",

            # Now deprecated: space-separated headers column
            #"headers": " ".join(const.DEFAULT_COLUMNS),

            # 2.6: this gets migrated from headers entry in code.
            # TODO: re-instate columns here in > 2.6 or once most have migrated
            #"columns": ",".join(const.DEFAULT_COLUMNS),

            # hack to disable hints, see bug #526
            "disable_hints": "false",

            # search as soon as text is typed into search box
            "eager_search": "true",
        },
        "rename": {
            "spaces": "false",
            "windows": "true",
            "ascii": "false",
        },
        "tagsfrompath": {
            "underscores": "false",
            "titlecase": "false",
            "split": "false",
            "add": "false",
        },
        "plugins": {
            "active_plugins": "", # newline separated plugin IDs
        },
        "editing": {
            "split_on": "/ & ,", # words to split on
            "id3encoding": "", # ID3 encodings to try
            "human_title_case": "true",
            "save_to_songs": "true",
            "save_email": const.EMAIL,
            "alltags": "true", # show all tags, or just "human-readable" ones
            # Skip dialog to save or revert changes
            "auto_save_changes": "false"
        },
        "albumart": {
            "round": "true", # use rounded corners for artwork thumbnails
            "prefer_embedded": "false",
            "force_filename": "false",
            "filename": "folder.jpg",
        }
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

    # revision 94d389a710f1
    from_ = ("settings", "round")
    if _config.has_option(*from_):
        _config.set("albumart", "round", _config.get(*from_))
        _config.remove_option(*from_)


def state(arg):
    return _config.getboolean("settings", arg)


def add_section(section):
    if not _config.has_section(section):
        _config.add_section(section)

# Cache
__songlist_columns = None


def get_columns(refresh=False):
    """
    Gets the list of songlist column headings, caching unless `refresh` is True

    This migrates from old to new format if necessary.
    """
    global __songlist_columns
    if not refresh and __songlist_columns:
        return __songlist_columns
    try:
        __songlist_columns = [str(s).lower()
                              for s in getstringlist("settings", "columns")]
        return __songlist_columns
    except Error:
        try:
            __songlist_columns = columns = get("settings", "headers").split()
        except Error:
            return const.DEFAULT_COLUMNS
        else:
            print_d("Migrating from settings.headers to settings.columns...")
            setstringlist("settings", "columns", columns)
            print_d("Removing settings.headers...")
            _config.remove_option("settings", "headers")
            return columns


def set_columns(vals, force=False):
    """
    Persists the settings for songlist headings held in `vals`
    Will override the cache if `force` is True
    """
    global __songlist_columns
    if vals != __songlist_columns or force:
        print_d("Writing: %r" % vals)
        vals = [str(col).lower() for col in vals]
        setstringlist("settings", "columns", vals)
        __songlist_columns = vals
    else:
        print_d("No change in columns to write")
