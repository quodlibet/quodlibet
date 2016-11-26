# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.compat import cBytesIO, PY2

if PY2:
    import cPickle
import pickle


def unpickle_load(file, lookup_func=None):
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

    if PY2:
        inst = cPickle.Unpickler(file)

        if lookup_func is not None:
            # this is just a dummy unpickler we use for fallback class lookup
            unpickler = pickle.Unpickler(cBytesIO())

            def find_global(mod, name):
                return lookup_func(unpickler.find_class, mod, name)

            inst.find_global = find_global
    else:
        if lookup_func is not None:

            class CustomUnpickler(pickle.Unpickler):

                def find_class(self, module, name):
                    func = super(CustomUnpickler, self).find_class
                    return lookup_func(func, module, name)

            unpickler_type = CustomUnpickler
        else:
            unpickler_type = pickle.Unpickler

        inst = unpickler_type(file, encoding="bytes")

    try:
        return inst.load()
    except pickle.UnpicklingError:
        raise
    except Exception as e:
        # unpickle can fail in many ways
        raise pickle.UnpicklingError(e)


def unpickle_loads(data, lookup_func=None):
    """Like unpickle_load() but takes bytes instead of a file-like

    Args:
        data (bytes)
        lookup_func (callable or None)
    Returns:
        The unpickled objects
    Raises:
        pickle.UnpicklingError
    """

    if PY2:
        from cStringIO import StringIO
        f = StringIO(data)
    else:
        from io import BytesIO, BufferedReader
        f = BufferedReader(BytesIO(data))

    return unpickle_load(f, lookup_func=lookup_func)
