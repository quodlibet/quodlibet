import sys

from quodlibet.debug.debugwindow import ExceptionDialog

def init():
    import gobject
    def _override_exceptions():
        print_d("Enabling custom exception handler.")
        sys.excepthook = ExceptionDialog.excepthook
    gobject.idle_add(_override_exceptions)
