# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
import os

import pytest

from quodlibet.util.json_data import JSONObjectDict, JSONObject
from . import TestCase, mkstemp
from .helper import capture_output

Field = JSONObject.Field


class TJsonData(TestCase):
    class WibbleData(JSONObject):
        """Test subclass"""

        FIELDS = {
            "name": Field("h name", "name"),
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

    def test_json_object(self):
        blah = JSONObject("blah")
        assert blah.name == "blah"
        assert blah.data == {"name": "blah"}
        assert blah.json == '{"name": "blah"}'

    def test_field(self):
        blah = self.WibbleData("blah")
        assert blah.field("wibble").doc == "wobble"
        assert not blah.field("not_here").doc
        assert blah.field("pattern").human_name == "h pattern"

    def test_nameless_construction(self):
        with pytest.raises(TypeError):
            JSONObject()

    def test_subclass(self):
        blah = self.WibbleData("blah")
        assert blah.name == "blah"
        exp = {"name": "blah", "pattern": None, "wibble": False}
        assert dict(blah.data) == exp
        assert json.loads(blah.json) == exp

    def test_from_invalid_json(self):
        # Invalid JSON
        with capture_output():
            jd = JSONObjectDict.from_json(JSONObject, '{"foo":{}')
            assert not jd
            # Valid but unexpected Command field
            assert not JSONObjectDict.from_json(
                JSONObject, '{"bar":{"name":"bar", "invalid":"foo"}'
            )

        def test_subclass_from_json(self):
            coms = JSONObjectDict.from_json(self.WibbleData, self.WIBBLE_JSON_STR)
            assert len(coms) == 2
            assert coms["foo"].__class__ == self.WibbleData

        def test_save_all(self):
            data = JSONObjectDict.from_json(self.WibbleData, self.WIBBLE_JSON_STR)
            fd, filename = mkstemp(suffix=".json")
            os.close(fd)
            try:
                ret = data.save(filename)
                with open(filename, "rb") as f:
                    jstr = f.read()
                # Check we also return the string as documented...
                assert jstr == ret
            finally:
                os.unlink(filename)

            jstr = jstr.decode("utf-8")

            # Check we have the right number of items
            assert len(json.loads(jstr)) == len(data)

            # Check them one by one (for convenience of debugging)
            parsed = JSONObjectDict.from_json(self.WibbleData, jstr)
            for o in data.values():
                assert parsed[o.name] == o

        def test_from_list(self):
            baz_man = JSONObject("baz man!")
            lst = [JSONObject("foo"), JSONObject("bar"), baz_man]
            data = JSONObjectDict.from_list(lst)
            assert len(data) == len(lst)
            assert "baz man!" in data
            assert baz_man == data["baz man!"]
