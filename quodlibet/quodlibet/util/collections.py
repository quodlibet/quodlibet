# Copyright 2006 Joe Wreschnig
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

from collections import MutableSequence, defaultdict

from .misc import total_ordering


@total_ordering
class DictMixin(object):
    """Implement the dict API using keys() and __*item__ methods.

    Similar to UserDict.DictMixin, this takes a class that defines
    __getitem__, __setitem__, __delitem__, and keys(), and turns it
    into a full dict-like object.

    UserDict.DictMixin is not suitable for this purpose because it's
    an old-style class.

    This class is not optimized for very large dictionaries; many
    functions have linear memory requirements. I recommend you
    override some of these functions if speed is required.
    """

    def __iter__(self):
        return iter(self.keys())

    def has_key(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True
    __contains__ = has_key

    def iterkeys(self):
        return iter(self.keys())

    def values(self):
        return [self[k] for k in self.keys()]

    def itervalues(self):
        return iter(self.values())

    def items(self):
        return list(zip(self.keys(), self.values()))

    def iteritems(self):
        return iter(self.items())

    def clear(self):
        for key in list(self.keys()):
            del self[key]

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop takes at most two arguments")
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            else:
                raise
        del(self[key])
        return value

    def popitem(self):
        try:
            key = list(self.keys())[0]
            return key, self.pop(key)
        except IndexError:
            raise KeyError("dictionary is empty")

    def update(self, other=None, **kwargs):
        if other is None:
            self.update(kwargs)
            other = {}

        try:
            for key, value in other.items():
                self[key] = value
        except AttributeError:
            for key, value in other:
                self[key] = value

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self):
        return repr(dict(self.items()))

    def __eq__(self, other):
        return dict(self.items()) == other

    def __lt__(self, other):
        return dict(self.items()) < other

    __hash__ = object.__hash__

    def __len__(self):
        return len(self.keys())


class DictProxy(DictMixin):
    def __init__(self, *args, **kwargs):
        self.__dict = {}
        super(DictProxy, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        return self.__dict[key]

    def __setitem__(self, key, value):
        self.__dict[key] = value

    def __delitem__(self, key):
        del(self.__dict[key])

    def keys(self):
        return self.__dict.keys()


class HashedList(MutableSequence):
    """A list-like collection that can only take hashable items
    and provides fast membership tests.

    Can handle duplicate entries.
    """

    def __init__(self, arg=None):
        self._map = defaultdict(int)
        if arg is None:
            self._data = []
            return

        self._data = list(arg)
        for item in arg:
            self._map[item] += 1

    def __setitem__(self, index, item):
        old_items = self._data[index]
        if not isinstance(index, slice):
            old_items = [old_items]

        for old in old_items:
            self._map[old] -= 1
            if not self._map[old]:
                del self._map[old]

        self._data[index] = item

        items = item
        if not isinstance(index, slice):
            items = [items]

        for item in items:
            self._map[item] += 1

    def __getitem__(self, index):
        return self._data[index]

    def __delitem__(self, index):
        items = self._data[index]
        if not isinstance(index, slice):
            items = [items]
        for item in items:
            self._map[item] -= 1
            if not self._map[item]:
                del self._map[item]
        del self._data[index]

    def __len__(self):
        return len(self._data)

    def insert(self, index, item):
        self._data.insert(index, item)
        self._map[item] += 1

    def __contains__(self, item):
        return item in self._map

    def __iter__(self):
        for item in self._data:
            yield item

    def has_duplicates(self):
        """Returns True if any item is contained more than once"""
        return len(self._map) != len(self)

    def __repr__(self):
        return repr(self._data)
