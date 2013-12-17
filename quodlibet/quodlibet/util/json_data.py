# Copyright 2012-2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import json
from quodlibet.util.dprint import print_d, print_w


class JSONObject(object):
    """
    Base class for simple, named data objects
    that can be edited and persisted as JSON.
    """

    # Override this to specify a set of field names, or a map of field: doc
    # Must include "name" if specified.
    FIELDS = {}

    @classmethod
    def _should_store(cls, field_name):
        """Decides if a field should be stored"""
        return not field_name.startswith("_")

    def __init__(self, name):
        if not name:
            raise ValueError("%s objects must be named" % type(self).__name__)
        self.name = str(name)

    @property
    def data(self):
        """A list of tuples of the persisted key:values in this class"""
        if self.FIELDS:
            return [(k, self.__getattribute__(k) if hasattr(self, k) else None)
                    for k in self.FIELDS]
        else:
            print_d("No order specified for class %s" % type(self).__name__)
            return dict([(k, v) for k, v in self.__dict__.items()
                         if self._should_store(k)])

    def field_description(self, name):
        """Returns the description of field `name` if available, else None"""
        if isinstance(self.FIELDS, dict):
            return self.FIELDS.get(name, None)

    @property
    def json(self):
        return json.dumps(dict(self.data))

    def __cmp__(self, other):
        return cmp(self.data, other.data)

    def __str__(self):
        return "<%s '%s' with %s>" % (self.__class__.__name__,
                                      self.name, self.json)


class JSONObjectDict(dict):
    """A dict wrapper to persist named `JSONObject`-style objects"""

    def __init__(self, Item=JSONObject):
        self.Item = Item
        dict.__init__(self)

    @classmethod
    def from_json(cls, ItemKind, json_str):
        """
        Factory method for building from an input string,
        a JSON map of {item_name1: {key:value, key2:value2...}, item_name2:...}
        """
        new = cls(ItemKind)

        try:
            data = json.loads(json_str)
        except ValueError:
            print_w("Broken JSON: %s" % json_str)
        else:
            for name, blob in data.items():
                try:
                    new[name] = ItemKind(**blob)
                except TypeError as e:
                    raise IOError("Couldn't instantiate %s from JSON (%s)"
                                  % (ItemKind.__name__, e))
        return new

    @classmethod
    def from_list(cls, json_objects, raise_errors=True):
        new = cls()
        for j in json_objects:
            if not isinstance(j, JSONObject):
                msg = ("Incorrect type (%s) found in list of objects"
                       % j.__class__.__name__)
                if raise_errors:
                    raise TypeError(msg)
                else:
                    print_d(msg)
            else:
                if not j.name and raise_errors:
                    raise ValueError("Null key for %s object %s"
                                     % (cls.__name__, j))
                if j.name in new:
                    print_w("Duplicate %s found named '%s'. Removing..."
                            % (cls.__name__, j.name))
                new[j.name] = j
        return new

    def save(self, filename=None):
        """
        Takes a list of `JSONObject` objects and returns
        the data serialised as a JSON string,
        also writing (prettily) to file `filename` if specified.
        """
        print_d("Saving %d %s(s) to JSON.." % (len(self), self.Item.__name__))
        try:
            obj_dict = dict([(o.name, dict(o.data)) for o in self.values()])
        except AttributeError:
            raise
        json_str = json.dumps(obj_dict, indent=4)
        if filename:
            try:
                with open(filename, "w") as f:
                    f.write(json_str)
            except IOError as e:
                print_w("Couldn't write JSON for %s object(s) (%s)"
                        % (type(self).__name__, e))
        return json_str
