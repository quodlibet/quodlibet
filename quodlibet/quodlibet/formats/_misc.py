# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import contextlib

import mutagen


class AudioFileError(Exception):
    """Base error for AudioFile, mostly IO/parsing related operations"""


class MutagenBug(AudioFileError):
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
    except (mutagen.MutagenError, IOError) as e:
        # old mutagen raised IOError
        raise AudioFileError(e)
    except Exception as e:
        raise MutagenBug(e)
