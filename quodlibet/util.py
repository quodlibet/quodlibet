# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sre

# Make a directory, including all directories below it.
def mkdir(dir):
    if not os.path.isdir(dir):
        base = os.path.dirname(dir)
        if base and not os.path.isdir(base): mkdir(base)
        os.mkdir(dir)

# Escape a string in a manner suitable for XML/Pango.
def escape(str):
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# Unescape a string that was escaped for XML/Pango.
def unescape(str):
    return str.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

# A better version of sre.escape, that doesn't go nuts on Unicode.
def re_esc(str):
    return "".join(map(
        lambda a: (a in ".^$*+?{,}\\[]|()<>#=!:" and "\\" + a) or a, str))
sre.escape = re_esc

# Check whether or not we can support various formats.
def check_mp3():
    try: import pyid3lib, mad
    except ImportError: return False
    else: return True

def check_ogg():
    try: import ogg.vorbis
    except ImportError: return False
    else: return True

def check_flac():
    try: import flac.decoder
    except ImportError: return False
    else: return True

def decode(s):
    try: return s.decode("utf-8")
    except UnicodeError:
        try: return s.decode("utf-8", "replace") + " [Invalid Unicode]"
        except UnicodeError: return "[Invalid Unicode]"

def encode(s):
    try: return s.encode("utf-8")
    except UnicodeError:
        try: return s.encode("utf-8", "replace") + " [Invalid Unicode]"
        except UnicodeError: return "[Invalid Unicode]"
