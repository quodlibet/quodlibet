# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import contextlib

import mutagen

from quodlibet import util
from quodlibet.util import print_w, print_d, reraise
from quodlibet.util.importhelper import load_dir_modules
from quodlibet.const import MinVersions


mimes = set()
"""A set of supported mime types"""

loaders = {}
"""A dict mapping file extensions to loaders (func returning an AudioFile)"""

types = set()
"""A set of AudioFile subclasses/implementations"""


class AudioFileError(Exception):
    """Base error for AudioFile, mostly IO/parsing related operations"""


class MutagenBug(AudioFileError):  # noqa
    """Raised in is caused by a mutagen bug, so we can highlight it"""


@contextlib.contextmanager
def translate_errors():
    """Context manager for mutagen calls to load/save. Translates exceptions
    to local ones.
    """

    try:
        yield
    except AudioFileError:
        raise
    except mutagen.MutagenError as e:
        reraise(AudioFileError, e)
    except Exception as e:
        reraise(MutagenBug, e)


def init():
    """Load/Import all formats.

    Before this is called loading a file and unpickling will not work.
    """

    global mimes, loaders, types

    MinVersions.MUTAGEN.check(mutagen.version)

    base = util.get_module_dir()
    formats = load_dir_modules(base, package=__package__)

    module_names = []
    for format in formats:
        name = format.__name__

        for ext in format.extensions:
            loaders[ext] = format.loader

        types.update(format.types)

        if format.extensions:
            for type_ in format.types:
                mimes.update(type_.mimes)
            module_names.append(name.split(".")[-1])

        # Migrate pre-0.16 library, which was using an undocumented "feature".
        sys.modules[name.replace(".", "/")] = format
        # Migrate old layout
        if name.startswith("quodlibet."):
            sys.modules[name.split(".", 1)[1]] = format

    # This can be used for the quodlibet.desktop file
    desktop_mime_types = "MimeType=" + \
        ";".join(sorted({m.split(";")[0] for m in mimes})) + ";"
    print_d(desktop_mime_types)

    s = ", ".join(sorted(module_names))
    print_d("Supported formats: %s" % s)

    if not loaders:
        raise SystemExit("No formats found!")


def get_loader(filename):
    """Returns a callable which takes a filename and returns
    AudioFile or raises AudioFileError, or returns None.
    """

    ext = os.path.splitext(filename)[-1]
    return loaders.get(ext.lower())


def MusicFile(filename):  # noqa
    """Returns a AudioFile instance or None"""

    loader = get_loader(filename)
    if loader is not None:
        try:
            return loader(filename)
        except AudioFileError:
            print_w("Error loading %r" % filename)
            util.print_exc()
        except Exception:
            print_w("Error loading %r" % filename)
            raise


def filter(filename):
    """Returns True if the file extension is supported"""

    return get_loader(filename) is not None
