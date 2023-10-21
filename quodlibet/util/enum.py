# Copyright 2014 Christoph Reiter
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


def enum(cls):
    """Class decorator for enum types::

        @enum
        class SomeEnum(int):
            FOO = 0
            BAR = 1

    Result is an int subclass and all attributes are instances of it.
    Each subclass has a property `values` referring to *all* known instances.
    """

    type_ = cls.__bases__[0]

    d = dict(cls.__dict__)
    new_type = type(cls.__name__, (type_,), d)
    new_type.__module__ = cls.__module__

    map_ = {}
    for key, value in d.items():
        if key.upper() == key:
            value_instance = new_type(value)
            setattr(new_type, key, value_instance)
            map_[value] = key
    new_type.values = set(map_.keys())

    def value_of(cls, s, default=None):
        for v in cls.values:
            if v == s:
                return v
        if default is not None:
            return default
        raise ValueError("Can't find %s (try %s)" % (s, cls.values))
    new_type.value_of = classmethod(value_of)

    def repr_(self):
        name = type(self).__name__
        try:
            return "%s.%s" % (name, map_[self])
        except KeyError:
            return "%s(%s)" % (name, self)

    new_type.__repr__ = repr_

    return new_type
