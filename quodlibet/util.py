# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

# Make a directory, including all directories below it.
def mkdir(dir):
    if not os.path.exists(dir):
        base = os.path.split(dir)[0]
        if base and not os.path.exists(base): mkdir(base)
        os.mkdir(dir)

# Escape a string in a manner suitable for XML/Pango.
def escape(str):
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# Check whether or not we can support various formats.
def check_mp3():
    try: import pyid3lib, mad
    except ImportError: return False
    else: return True

def check_ogg():
    try: import ogg.vorbis
    except ImportError: return False
    else: return True
