import sys

from quodlibet.debug.debugwindow import ExceptionDialog

def init():
    from gi.repository import GObject

    def _override_exceptions():
        print_d("Enabling custom exception handler.")
        sys.excepthook = ExceptionDialog.excepthook
    gobject.idle_add(_override_exceptions)

def cause_error(*args):
    raise Exception
