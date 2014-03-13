from tests import TestCase, AbstractTestCase, skipIf

from quodlibet.formats import USEFUL_TAGS
from quodlibet.qltk import is_wayland


class TagsCombo(AbstractTestCase):
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


@skipIf(is_wayland(), "crashes..")
class TTagsComboBox(TagsCombo):
    from quodlibet.qltk.tagscombobox import TagsComboBox as Kind


@skipIf(is_wayland(), "crashes..")
class TTagsComboBoxEntry(TagsCombo):
    from quodlibet.qltk.tagscombobox import TagsComboBoxEntry as Kind

    def test_custom(self):
        self.all.get_child().set_text("a new tag")
        self.failUnlessEqual(self.all.tag, "a new tag")
