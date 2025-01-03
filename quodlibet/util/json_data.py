# Copyright 2012-2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import json
from collections import namedtuple

from quodlibet.util.dprint import print_d, print_w
from quodlibet.util.misc import total_ordering


@total_ordering
class JSONObject:
    """
    Base class for simple, named data objects
    that can be edited and persisted as JSON.
    """

    NAME = ""

    # The format for JSONObject.
    Field = namedtuple("Field", ["human_name", "doc"])
    EMPTY_FIELD = Field(None, None)

    # Override this to specify a set of field names,
    # or a dict of field: FieldData
    # Must include "name" if dict is specified.
    FIELDS: dict[str, Field] = {}

    @classmethod
    def _should_store(cls, field_name):
        """Decides if a field should be stored"""
        return not field_name.startswith("_")

    def __init__(self, name):
        if not name:
            raise ValueError(f"{type(self).__name__} objects must be named")
        self.name = str(name)

    @property
    def data(self):
        """A list of tuples of the persisted key:values in this class"""
        if self.FIELDS:
            return [
                (k, self.__getattribute__(k) if hasattr(self, k) else None)
                for k in self.FIELDS
            ]
        else:
            print_d(f"No order specified for class {type(self).__name__}")
            return {k: v for k, v in self.__dict__.items() if self._should_store(k)}

    def field(self, name):
        """Returns the Field metadata of field `name` if available,
        or a null / empty one"""
        if isinstance(self.FIELDS, dict):
            return self.FIELDS.get(name, self.EMPTY_FIELD)

    @property
    def json(self):
        return json.dumps(dict(self.data))

    def __eq__(self, other):
        return self.data == other.data

    def __lt__(self, other):
        return self.data < other.data

    def __str__(self):
        return f"<{self.__class__.__name__} '{self.name}' with {self.json}>"


class JSONObjectDict(dict):
    """A dict wrapper to persist named `JSONObject`-style objects"""

    def __init__(self, item_cls=JSONObject):
        self.Item = item_cls
        dict.__init__(self)

    @classmethod
    def from_json(cls, item_cls, json_str):
        """
        Factory method for building from an input string,
        a JSON map of {item_name1: {key:value, key2:value2...}, item_name2:...}
        """
        new = cls(item_cls)

        try:
            data = json.loads(json_str)
        except ValueError:
            print_w(f"Broken JSON: {json_str}")
        else:
            for name, blob in data.items():
                try:
                    new[name] = item_cls(**blob)
                except TypeError as e:
                    msg = f"Couldn't instantiate {item_cls.__name__} from JSON ({e})"
                    raise OSError(msg) from e
        return new

    @classmethod
    def from_list(cls, json_objects, raise_errors=True):
        new = cls()
        for j in json_objects:
            if not isinstance(j, JSONObject):
                msg = (
                    f"Incorrect type ({j.__class__.__name__}) found in list of objects"
                )
                if raise_errors:
                    raise TypeError(msg)
                else:
                    print_d(msg)
            else:
                if not j.name and raise_errors:
                    raise ValueError(f"Null key for {cls.__name__} object {j}")
                if j.name in new:
                    print_w(f"Duplicate {cls.__name__} found: '{j.name}'. Removing…")
                new[j.name] = j
        return new

    def save(self, filename=None):
        """
        Takes a list of `JSONObject` objects and returns
        the data serialised as a JSON string,
        also writing (prettily) to file `filename` if specified.
        """
        print_d(f"Saving {len(self):d} {self.Item.__name__}(s) to JSON..")
        try:
            obj_dict = {o.name: dict(o.data) for o in self.values()}
        except AttributeError:
            raise
        json_str = json.dumps(obj_dict, indent=4)
        json_str = json_str.encode("utf-8")
        if filename:
            try:
                with open(filename, "wb") as f:
                    f.write(json_str)
            except OSError as e:
                print_w(
                    "Couldn't write JSON for " f"{type(self).__name__} object(s) ({e})"
                )
        return json_str
