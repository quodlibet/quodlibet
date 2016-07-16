# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

import mutagen

from quodlibet.util.importhelper import load_dir_modules
from quodlibet import util
from quodlibet.util import print_w, print_d
from quodlibet.const import MinVersions

mimes = set()
_infos = {}
modules = []
names = []
types = []


def init():
    global mimes, _infos, modules, names

    MinVersions.MUTAGEN.check(mutagen.version)

    base = util.get_module_dir()
    load_pyc = util.is_windows() or util.is_osx()
    formats = load_dir_modules(base,
                               package=__package__,
                               load_compiled=load_pyc)

    for format in formats:
        name = format.__name__

        for ext in format.extensions:
            _infos[ext] = format.info

        types.extend(format.types)

        if format.extensions:
            for type_ in format.types:
                mimes.update(type_.mimes)
                names.append(type_.format)
            modules.append(name.split(".")[-1])

        # Migrate pre-0.16 library, which was using an undocumented "feature".
        sys.modules[name.replace(".", "/")] = format
        # Migrate old layout
        if name.startswith("quodlibet."):
            sys.modules[name.split(".", 1)[1]] = format

    modules.sort()
    names.sort()

    # This can be used for the quodlibet.desktop file
    desktop_mime_types = "MimeType=" + \
        ";".join(sorted({m.split(";")[0] for m in mimes})) + ";"
    print_d(desktop_mime_types)

    if not _infos:
        raise SystemExit("No formats found!")


def get_loader(filename):
    """Returns a callable which takes a filename and returns
    AudioFile or raises AudioFileError, or returns None.
    """

    ext = os.path.splitext(filename)[-1]
    return _infos.get(ext.lower())


def MusicFile(filename):
    """Returns a AudioFile instance or None"""

    loader = get_loader(filename)
    if loader is not None:
        try:
            return loader(filename)
        except AudioFileError:
            print_w("Error loading %r" % filename)
            util.print_exc()


def filter(filename):
    """Returns True if the file extension is supported"""

    return get_loader(filename) is not None


from ._audio import PEOPLE, AudioFile, DUMMY_SONG, decode_value
from ._image import EmbeddedImage, APICType
from ._misc import AudioFileError

AudioFile
AudioFileError
EmbeddedImage
DUMMY_SONG
PEOPLE
decode_value
APICType
