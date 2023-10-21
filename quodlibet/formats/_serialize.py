# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Code for serializing AudioFile instances"""

import pickle
from senf import bytes2fsn, fsn2bytes

from quodlibet.util.picklehelper import pickle_loads, pickle_dumps
from quodlibet.util import is_windows
from ._audio import AudioFile


class SerializationError(Exception):
    pass


def _py2_to_py3(items):
    for i in items:
        try:
            li = list(i.items())
        except AttributeError as e:
            raise SerializationError from e
        i.clear()
        for k, v in li:
            if isinstance(k, bytes):
                k = k.decode("utf-8", "replace")
            else:
                # strip surrogates
                try:
                    k.encode("utf-8")
                except UnicodeEncodeError:
                    k = k.encode("utf-8", "replace").decode("utf-8")

            if k == "~filename" or k == "~mountpoint":
                if isinstance(v, bytes):
                    try:
                        v = bytes2fsn(v, "utf-8")
                    except ValueError:
                        # just in case, only on Windows
                        assert is_windows()
                        v = v.decode("utf-8", "replace")
            elif isinstance(v, bytes):
                v = v.decode("utf-8", "replace")
            elif isinstance(v, str):
                # strip surrogates
                try:
                    v.encode("utf-8")
                except UnicodeEncodeError:
                    v = v.encode("utf-8", "replace").decode("utf-8")

            i[k] = v

    return items


def _py3_to_py2(items):
    is_win = is_windows()

    new_list = []
    for i in items:
        inst = dict.__new__(i.__class__)
        for key, value in i.items():
            if key in ("~filename", "~mountpoint") and not is_win:
                value = fsn2bytes(value, None)
            try:
                key = key.encode("ascii")
            except UnicodeEncodeError:
                pass
            dict.__setitem__(inst, key, value)
        new_list.append(inst)
    return new_list


def load_audio_files(data, process=True):
    """unpickles the item list and if some class isn't found unpickle
    as a dict and filter them out afterwards.

    In case everything gets filtered out will raise SerializationError
    (because then likely something larger went wrong)

    Args:
        data (bytes)
        process (bool): if the dict key/value types should be converted,
            either to be usable from py3 or to convert to newer types
    Returns:
        List[AudioFile]
    Raises:
        SerializationError
    """

    dummy = type("dummy", (dict,), {})
    error_occured = []
    temp_type_cache = {}

    def lookup_func(base, module, name):
        try:
            real_type = base(module, name)
        except (ImportError, AttributeError):
            error_occured.append(True)
            return dummy

        if module.split(".")[0] not in ("quodlibet", "tests"):
            return real_type

        # return a straight dict subclass so that unpickle doesn't call
        # our __setitem__. Further down we simply change the __class__
        # to our real type.
        if real_type not in temp_type_cache:
            new_type = type(name, (dict,), {"real_type": real_type})
            temp_type_cache[real_type] = new_type

        return temp_type_cache[real_type]

    try:
        items = pickle_loads(data, lookup_func)
    except pickle.UnpicklingError as e:
        raise SerializationError(e) from e

    if error_occured:
        items = [i for i in items if not isinstance(i, dummy)]

        if not items:
            raise SerializationError(
                "all class lookups failed. something is wrong")

    if process:
        items = _py2_to_py3(items)

    try:
        for i in items:
            i.__class__ = i.real_type
    except AttributeError as e:
        raise SerializationError(e) from e

    return items


def dump_audio_files(item_list, process=True):
    """Pickles a list of AudioFiles

    Returns:
        bytes
    Raises:
        SerializationError
    """

    assert isinstance(item_list, list)
    assert not item_list or isinstance(item_list[0], AudioFile)

    if process:
        item_list = _py3_to_py2(item_list)

    try:
        return pickle_dumps(item_list, 2)
    except pickle.PicklingError as e:
        raise SerializationError(e) from e
