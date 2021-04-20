# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
import os

from quodlibet.util.json_data import JSONObjectDict, JSONObject
from . import TestCase, mkstemp
from .helper import capture_output

Field = JSONObject.Field


class TJsonData(TestCase):

    class WibbleData(JSONObject):
        """Test subclass"""

        FIELDS = {"name": Field("h name", "name"),
                  "pattern": Field("h pattern", "pattern for stuff"),
                  "wibble": Field("h wibble", "wobble"),
        }

        def __init__(self, name=None, pattern=None, wibble=False):
            JSONObject.__init__(self, name)
            self.pattern = pattern
            self.wibble = wibble
            self._dont_wibble = not wibble

    WIBBLE_JSON_STR = """{
            "foo":{"name":"foo", "pattern":"echo '<~artist~title>.mp3'"},
            "bar":{"name":"bar", "wibble":true}
    }"""

    def test_JSONObject(self):
        blah = JSONObject('blah')
        self.failUnlessEqual(blah.name, 'blah')
        self.failUnlessEqual(blah.data, {"name": "blah"})
        self.failUnlessEqual(blah.json, "{\"name\": \"blah\"}")

    def test_field(self):
        blah = self.WibbleData('blah')
        self.failUnlessEqual(blah.field('wibble').doc, 'wobble')
        self.failIf(blah.field('not_here').doc)
        self.failUnlessEqual(blah.field("pattern").human_name, "h pattern")

    def test_nameless_construction(self):
        try:
            self.failIf(JSONObject())
        except TypeError:
            pass
        else:
            self.fail("Name should be enforced at constructor")

    def test_subclass(self):
        blah = self.WibbleData('blah')
        self.failUnlessEqual(blah.name, 'blah')
        exp = {"name": "blah", "pattern": None, "wibble": False}
        self.failUnlessEqual(dict(blah.data), exp)
        self.failUnlessEqual(json.loads(blah.json), exp)

    def test_from_invalid_json(self):
        # Invalid JSON
        with capture_output():
            jd = JSONObjectDict.from_json(JSONObject, '{"foo":{}')
            self.failIf(jd)
            # Valid but unexpected Command field
            self.failIf(JSONObjectDict.from_json(JSONObject,
                '{"bar":{"name":"bar", "invalid":"foo"}'))

    def test_subclass_from_json(self):
        coms = JSONObjectDict.from_json(self.WibbleData, self.WIBBLE_JSON_STR)
        self.failUnlessEqual(len(coms), 2)
        self.failUnlessEqual(coms['foo'].__class__, self.WibbleData)

    def test_save_all(self):
        data = JSONObjectDict.from_json(self.WibbleData, self.WIBBLE_JSON_STR)
        fd, filename = mkstemp(suffix=".json")
        os.close(fd)
        try:
            ret = data.save(filename)
            with open(filename, "rb") as f:
                jstr = f.read()
            # Check we also return the string as documented...
            self.failUnlessEqual(jstr, ret)
        finally:
            os.unlink(filename)

        jstr = jstr.decode("utf-8")

        # Check we have the right number of items
        self.failUnlessEqual(len(json.loads(jstr)), len(data))

        # Check them one by one (for convenience of debugging)
        parsed = JSONObjectDict.from_json(self.WibbleData, jstr)
        for o in data.values():
            self.failUnlessEqual(parsed[o.name], o)

    def test_from_list(self):
        baz_man = JSONObject("baz man!")
        lst = [JSONObject("foo"), JSONObject("bar"), baz_man]
        data = JSONObjectDict.from_list(lst)
        self.failUnlessEqual(len(data), len(lst))
        self.failUnless("baz man!" in data)
        self.failUnlessEqual(baz_man, data["baz man!"])
