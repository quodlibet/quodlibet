from tests import TestCase, add

class TExample(TestCase):
    def test_foobar(self):
        self.assertEqual(42, 42)

add(TExample)
