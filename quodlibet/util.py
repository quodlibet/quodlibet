# Copyright 2004 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sre, string

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

def iscommand(s):
    if not s or s[0] == "/":
        return os.path.exists(s)
    else:
        s = s.split()[0]
        for p in os.environ["PATH"].split(":"):
            p2 = os.path.join(p, s)
            if os.path.exists(p2): return True
        else: return False

# Split a string on ;s and ,s.
def split_value(s, splitters = ",;&"):
    values = s.split("\n")
    for spl in splitters:
        new_values = []
        for v in values:
            new_values.extend(map(string.strip, v.split(spl)))
        values = new_values
    return values

def split_title(s, splitters = ",;&"):
    title, subtitle = find_subtitle(s)
    if not subtitle: return (s, [])
    else:
        return (title.strip(), split_value(subtitle, splitters))

def split_people(s, splitters = ",;&"):
    title, subtitle = find_subtitle(s)
    if not subtitle:
        parts = s.split(" ")
        if len(parts) > 2:
            for feat in ["feat.", "featuring", "feat", "with", "w/"]:
                try:
                    i = map(string.lower, parts).index(feat)
                    orig = " ".join(parts[:i])
                    others = " ".join(parts[i+1:])
                    return (orig, split_value(others, splitters))
                except (ValueError, IndexError): pass
        return (s, [])
    else:
        for feat in ["feat.", "featuring", "feat", "with", "w/"]:
            if subtitle.startswith(feat):
                subtitle = subtitle.replace(feat, "", 1)
                subtitle.lstrip()
                break
        values = split_value(subtitle, splitters)
        return (title.strip(), values)

def split_album(s):
    name, disc = find_subtitle(s)
    if not disc:
        parts = s.split(" ")
        if len(parts) > 2:
            lower = parts[-2].lower()
            if "disc" in lower or "disk" in lower:
                return (" ".join(parts[:-2]), parts[-1])
        return (s, None)
    else:
        parts = disc.split()
        if (len(parts) == 2 and
            parts[0].lower() in ["disc", "disk", "cd", "vol", "vol."]):
            try: return (name, parts[1])
            except: return (s, None)

def find_subtitle(title):
    for pair in [("[", "]"), ("(", ")"), ("~", "~"), ("-", "-")]:
        if pair[0] in title and title[-1] == pair[1]:
            l = title[0:-1].rindex(pair[0])
            if l != 0:
                subtitle = title[l+1:-1]
                title = title[:l]
                return title.rstrip(), subtitle
    else: return title, None

def unexpand(filename):
    if filename.startswith(os.environ["HOME"]):
        filename = filename.replace(os.environ["HOME"], "~", 1)
    return filename
