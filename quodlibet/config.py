# Copyright 2004 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
from ConfigParser import SafeConfigParser as ConfigParser

_config = ConfigParser()
get = _config.get
set = _config.set
getboolean = _config.getboolean

def init(rc_file):
    _config.add_section("settings")
    _config.set("settings", "scan", "")
    _config.set("settings", "cover", "true")
    _config.set("settings", "color", "true")
    _config.set("settings", "headers", "=# title album artist")
    _config.read([rc_file])

def state(arg):
    return _config.getboolean("settings", arg)

def write(*args):
    _config.write(*args)
