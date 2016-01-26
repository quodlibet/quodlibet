# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.compat import iteritems


def enum(cls):
    """Class decorator for enum types::

        @enum
        class SomeEnum(int):
            FOO = 0
            BAR = 1

    Result is an int subclass and all attributes are instances of it.
    """

    type_ = cls.__bases__[0]

    d = dict(cls.__dict__)
    new_type = type(cls.__name__, (type_,), d)
    new_type.__module__ = cls.__module__

    map_ = {}
    for key, value in iteritems(d):
        if key.upper() == key:
            value_instance = new_type(value)
            setattr(new_type, key, value_instance)
            map_[value] = key

    def repr_(self):
        if self in map_:
            return "%s.%s" % (type(self).__name__, map_[self])
        else:
            return "%s(%s)" % (type(self).__name__, self)

    setattr(new_type, "__repr__", repr_)

    return new_type
