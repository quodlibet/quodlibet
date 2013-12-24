import json
import os

from quodlibet.util.json_data import JSONObjectDict, JSONObject
from tests import TestCase, add, mkstemp
from helper import capture_output


class TJsonData(TestCase):

    class WibbleData(JSONObject):
        """Test subclass"""

        FIELDS = {"name": "name",
                  "pattern": "pattern for stuff",
                  "wibble": "wobble"}

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
        self.failUnlessEqual({"name": "blah"}, blah.data)
        self.failUnlessEqual("{\"name\": \"blah\"}", blah.json)

    def test_field_description(self):
        blah = self.WibbleData('blah')
        self.failUnlessEqual(blah.field_description('wibble'), 'wobble')
        self.failIf(blah.field_description('not_here'))

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
        self.failUnlessEqual(exp, dict(blah.data))
        self.failUnlessEqual(json.dumps(exp), blah.json)

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

add(TJsonData)
