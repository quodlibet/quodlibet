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
    _config.add_section("settings")
    _config.add_section("memory")
    _config.add_section("browsers")
    _config.add_section("header_maps")

    _config.set("settings", "scan", "")
    _config.set("settings", "gain", "2")
    _config.set("settings", "osd", "0")

    _config.set("settings", "shuffle", "false")
    _config.set("settings", "repeat", "false")

    _config.set("settings", "jump", "true")
    _config.set("settings", "cover", "true")
    _config.set("settings", "color", "true")
    _config.set("settings", "osdcolors", "#ffbb00 #ff8700")
    _config.set("settings", "osdfont", "Sans 18")

    _config.set("settings", "tbp_space", "false")
    _config.set("settings", "addreplace", "0")
    _config.set("settings", "titlecase", "false")
    _config.set("settings", "splitval", "true")
    _config.set("settings", "nbp_space", "false")
    _config.set("settings", "windows", "true")
    _config.set("settings", "ascii", "false")
    _config.set("settings", "allcomments", "true")

    _config.set("settings", "backend", "ao:alsa09")
    _config.set("settings", "masked", "")
    _config.set("settings", "splitters", ",;&/")
    _config.set("settings", "headers", "~#track ~title~version ~album~part artist ~length")

    _config.set("memory", "size", "400 350")
    _config.set("memory", "song", "")
    _config.set("memory", "widths", "1 80 80 80 50")
    _config.set("memory", "volume", "1.0")
    _config.set("memory", "browser", "1")
    _config.set("memory", "songlist", "true")
    _config.set("memory", "sortby", "0artist")

    for k, v in {"query_text": "",
                 "pane_selection": "<b>All</b>\n<b>All</b>",
                 "panes": "artist album"}.items():
        _config.set("browsers", k, v)

    _config.read(rc_files)

def state(arg):
    return _config.getboolean("settings", arg)
