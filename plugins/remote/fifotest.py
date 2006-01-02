from plugins.remote import FIFOPlugin
from qltk.msg import WarningMessage

class FIFOTest(FIFOPlugin):
    commands = ["test_a", "test_b"]
    def __init__(self, command, watcher, window, player):
        print _("You said to %s.") % command
