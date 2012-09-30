# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import __builtin__
import gettext
import os

class GlibTranslations(gettext.GNUTranslations):
    """Provide a glib-like translation API for Python.

    This class adds support for qgettext (and uqgettext) mirroring
    glib's Q_ macro, which allows for disambiguation of identical
    source strings. It also installs N_, Q_, and ngettext into the
    __builtin__ namespace.

    It can also be instantiated and used with any valid MO files
    (though it won't be able to translate anything, of course).
    """

    def __init__(self, *args, **kwargs):
        self._catalog = {}
        self.plural = lambda n: n != 1
        gettext.GNUTranslations.__init__(self, *args, **kwargs)

    def qgettext(self, msgid):
        msgstr = self.gettext(msgid)
        if msgstr == msgid:
            try: return msgstr.split("|", 1)[1]
            except IndexError: return msgstr
        else:
            return msgstr

    def uqgettext(self, msgid):
        msgstr = self.ugettext(msgid)
        if msgstr == msgid:
            try: return msgstr.split(u"|", 1)[1]
            except IndexError: return msgstr
        else:
            return msgstr

    def install(self, unicode=False):
        if unicode:
            _ = self.ugettext
            _Q = self.uqgettext
            ngettext = self.ungettext
            _N = unicode
        else:
            _ = self.gettext
            _Q = self.qgettext
            ngettext = self.ngettext
            _N = lambda s: s

        test_key = "QUODLIBET_TEST_TRANS"
        if test_key in os.environ:
            text = os.environ[test_key]
            def wrap(f):
                def g(*args):
                    return text + f(*args) + text
                return g

            _ = wrap(_)
            _Q = wrap(_Q)
            _N = wrap(_N)
            ngettext = wrap(ngettext)

        __builtin__.__dict__["_"] = _
        __builtin__.__dict__["Q_"] = _Q
        __builtin__.__dict__["N_"] = _N
        __builtin__.__dict__["ngettext"] = ngettext
