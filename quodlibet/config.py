# Copyright 2004 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Simple proxy to a Python ConfigParser.

import os
from ConfigParser import SafeConfigParser as ConfigParser

_config = ConfigParser()
get = _config.get
set = _config.set
getboolean = _config.getboolean
write = _config.write
options = _config.options

def init(rc_file):
    # So far we only have/need one section...
    _config.add_section("settings")
    _config.add_section("memory")
    _config.add_section("header_maps")
    _config.set("settings", "scan", "")
    _config.set("settings", "jump", "true")
    _config.set("settings", "cover", "true")
    _config.set("settings", "color", "true")
    _config.set("settings", "backend", "oss")
    _config.set("settings", "splitters", ",;&/")
    _config.set("settings", "headers", "=# title album artist")
    _config.set("memory", "size", "400 350")
    _config.set("memory", "song", "")
    _config.set("memory", "query", "")
    try: _config.read([rc_file])
    except: pass

def state(arg):
    return _config.getboolean("settings", arg)
