# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Code for serializing AudioFile instances"""

import pickle

from quodlibet.util.picklehelper import pickle_loads, pickle_dumps


class SerializationError(Exception):
    pass


def load_audio_files(data):
    """unpickles the item list and if some class isn't found unpickle
    as a dict and filter them out afterwards.

    In case everything gets filtered out will raise SerializationError
    (because then likely something larger went wrong)

    Returns:
        List[AudioFile]
    Raises:
        SerializationError
    """

    class dummy(dict):
        pass

    error_occured = []

    def lookup_func(base, module, name):
        try:
            return base(module, name)
        except (ImportError, AttributeError):
            error_occured.append(True)
            return dummy

    try:
        items = pickle_loads(data, lookup_func)
    except pickle.UnpicklingError as e:
        raise SerializationError(e)

    if error_occured:
        items = [i for i in items if not isinstance(i, dummy)]
        if not items:
            raise SerializationError(
                "all class lookups failed. something is wrong")

    return items


def dump_audio_files(item_list):
    """Pickles a list of AudioFiles

    Returns:
        bytes
    Raises:
        SerializationError
    """

    assert isinstance(item_list, list)

    # While protocol 2 is usually faster it uses __setitem__
    # for unpickle and we override it to clear the sort cache.
    # This roundtrip makes it much slower, so we use protocol 1
    # unpickle numbers (py2.7):
    #   2: 0.66s / 2 + __set_item__: 1.18s / 1 + __set_item__: 0.72s
    # see: http://bugs.python.org/issue826897

    try:
        return pickle_dumps(item_list, 1)
    except pickle.PicklingError as e:
        raise SerializationError(e)
