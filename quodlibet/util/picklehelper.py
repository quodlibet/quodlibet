# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""One interface for pickle/cPickle for both Python 2/3"""

from io import BytesIO, BufferedReader

import pickle
from pickle import PicklingError, UnpicklingError, PickleError


PickleError  # noqa


def pickle_dumps(obj, protocol=0):
    """Like pickle.dumps

    Raises:
        pickle.PicklingError
    """

    if not 0 <= protocol <= 2:
        raise ValueError("Only protocol 0, 1, 2 allowed")

    try:
        # pickle.PicklingError is not cPickle.PicklingError
        # so this makes sure we only raise pickle.PicklingError even if
        # we use cPickle
        return pickle.dumps(obj, protocol)
    except PicklingError:
        raise
    except Exception as e:
        raise PicklingError(e) from e


def pickle_dump(obj, file, protocol=0):
    """Like pickle.dump

    Raises:
        pickle.PicklingError
    """

    if not 0 <= protocol <= 2:
        raise ValueError("Only protocol 0, 1, 2 allowed")

    try:
        return pickle.dump(obj, file, protocol)
    except PicklingError:
        raise
    except Exception as e:
        raise PicklingError(e) from e


def pickle_load(file, lookup_func=None):
    """Allows unpickling with manual control over class lookup on both Python
    2 and Python 3.

    Will unpickle from the current position to the final stop marker.

    lookup_func gets passed a function for global lookup, the mod name
    to import and the attribute name to return from the module

    The lookup function passed to the callback can raise ImportError
    or AttributeError.

    Args:
        file (fileobj)
        lookup_func (callable or None)
    Returns:
        The unpickled objects
    Raises:
        pickle.UnpicklingError
    """

    if lookup_func is not None:

        class CustomUnpickler(pickle.Unpickler):
            def find_class(self, module, name):
                func = super().find_class
                return lookup_func(func, module, name)

        unpickler_type = CustomUnpickler
    else:
        unpickler_type = pickle.Unpickler

    # helps a lot, but only on py3
    if isinstance(file, BytesIO):
        file = BufferedReader(file)

    inst = unpickler_type(file, encoding="bytes")

    try:
        return inst.load()
    except UnpicklingError:
        raise
    except Exception as e:
        # unpickle can fail in many ways
        raise UnpicklingError(e) from e


def pickle_loads(data, lookup_func=None):
    """Like pickle_load() but takes bytes instead of a file-like

    Args:
        data (bytes)
        lookup_func (callable or None)
    Returns:
        The unpickled objects
    Raises:
        pickle.UnpicklingError
    """

    return pickle_load(BytesIO(data), lookup_func=lookup_func)
