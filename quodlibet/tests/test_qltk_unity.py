from tests import TestCase, add

from quodlibet.qltk import unity


class TUnityQuickList(TestCase):

    def test_init(self):
        unity.init("quodlibet.desktop", None)

add(TUnityQuickList)
