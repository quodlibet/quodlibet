# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

from quodlibet.util.modulescanner import load_dir_modules
from quodlibet import util
from quodlibet.util.dprint import print_w
from quodlibet.const import MinVersions

mimes = set()
_infos = {}
modules = []

def init():
    global mimes, _infos, modules

    import mutagen
    if mutagen.version < MinVersions.MUTAGEN:
        print_w("Mutagen %s required. %s found."
                % (MinVersions.MUTAGEN, mutagen.version_string))

    base = os.path.dirname(__file__)
    load_pyc = os.name == 'nt'
    formats = load_dir_modules(base,
                               package=__package__,
                               load_compiled=load_pyc)

    for format in formats:
        name = format.__name__

        for ext in format.extensions:
            _infos[ext] = format.info

        if format.extensions:
            for type_ in format.types:
                mimes.update(type_.mimes)
            modules.append(name.split(".")[-1])

        # Migrate pre-0.16 library, which was using an undocumented "feature".
        sys.modules[name.replace(".", "/")] = format
        # Migrate old layout
        if name.startswith("quodlibet."):
            sys.modules[name.split(".", 1)[1]] = format

    modules.sort()

    # Migrate old layout
    try:
        xiph = sys.modules["quodlibet.formats.xiph"]
    except KeyError:
        pass
    else:
        sys.modules["formats.flac"] = xiph
        sys.modules["formats.oggvorbis"] = xiph

    if not _infos:
        raise SystemExit("No formats found!")

init()


def MusicFile(filename):
    for ext in _infos.keys():
        if filename.lower().endswith(ext):
            try:
                # The sys module docs say this is where the interactive
                # interpreter stores exceptions, so it should be safe for
                # us to do it -- if we're in the interpreter this does
                # nothing, and if we're not it lets us access them elsewhere.
                # WARNING: Not threadsafe. Don't add files from threads
                # other than the main one.
                sys.last_type = sys.last_value = sys.last_traceback = None
                return _infos[ext](filename)
            except:
                print_w(_("Error loading %r") % filename)
                util.print_exc()
                lt, lv, tb = sys.exc_info()
                sys.last_type, sys.last_value, sys.last_traceback = lt, lv, tb
                return None
    else: return None

if sys.version_info < (2, 5):
    def supported(song):
        lower = song.key.lower()
        for ext in _infos.keys():
            if lower.endswith(ext):
                return True
        return False
else:
    extensions = tuple(_infos.keys())
    def supported(song):
        return song.key.lower().endswith(extensions)

def filter(filename):
    lower = filename.lower()
    for ext in _infos.keys():
        if lower.endswith(ext): return True
    return False

from quodlibet.formats._audio import USEFUL_TAGS, MACHINE_TAGS, PEOPLE
