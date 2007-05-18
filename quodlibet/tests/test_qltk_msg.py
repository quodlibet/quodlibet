from tests import TestCase, add

from quodlibet.qltk.msg import *

class _TMessage(TestCase):
    def setUp(self): self.win = self.Kind(None, "title", "description")
    def test_ctr(self): pass
    def tearDown(self): self.win.destroy()

class TWarningMessage(_TMessage): Kind = WarningMessage
add(TWarningMessage)

class TErrorMessage(_TMessage): Kind = ErrorMessage
add(TErrorMessage)

class TConfirmAction(_TMessage): Kind = ConfirmAction
add(TConfirmAction)

class TCancelRevertSave(TestCase):
    def setUp(self): self.win = CancelRevertSave(None)
    def test_ctr(self): pass
    def tearDown(self): self.win.destroy()
add(TCancelRevertSave)
