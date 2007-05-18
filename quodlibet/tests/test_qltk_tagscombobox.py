from tests import TestCase, add

from quodlibet.formats import USEFUL_TAGS

class TagsCombo(TestCase):
    def setUp(self):
        self.all = self.Kind()
        self.some = self.Kind(["artist", "album", "~people", "foobar"])

    def test_none(self):
        self.failUnlessRaises(ValueError, self.Kind, [])

    def test_some(self):
        self.some.set_active(2)
        self.failUnlessEqual(self.some.tag, "foobar")

    def test_all(self):
        tags = list(USEFUL_TAGS)
        tags.sort()
        for i, value in enumerate(tags):
            self.all.set_active(i)
            self.failUnlessEqual(self.all.tag, value)

    def tearDown(self):
        self.all.destroy()
        self.some.destroy()

class TTagsComboBox(TagsCombo):
    from quodlibet.qltk.tagscombobox import TagsComboBox as Kind
add(TTagsComboBox)

class TTagsComboBoxEntry(TagsCombo):
    from quodlibet.qltk.tagscombobox import TagsComboBoxEntry as Kind

    def test_custom(self):
        self.all.child.set_text("a new tag")
        self.failUnlessEqual(self.all.tag, "a new tag")
add(TTagsComboBoxEntry)
