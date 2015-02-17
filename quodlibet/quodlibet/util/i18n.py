# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import __builtin__
import gettext


class GlibTranslations(gettext.GNUTranslations):
    """Provide a glib-like translation API for Python.

    This class adds support for pgettext (and upgettext) mirroring
    glib's C_ macro, which allows for disambiguation of identical
    source strings. It also installs N_, C_, and ngettext into the
    __builtin__ namespace.

    It can also be instantiated and used with any valid MO files
    (though it won't be able to translate anything, of course).
    """

    def __init__(self, fp=None):
        self.path = (fp and fp.name) or ""
        self._catalog = {}
        self.plural = lambda n: n != 1
        gettext.GNUTranslations.__init__(self, fp)

    def ugettext(self, message):
        # force unicode here since __contains__ (used in gettext) ignores
        # our changed defaultencoding for coercion, so utf-8 encoded strings
        # fail at lookup.
        message = unicode(message)
        return unicode(gettext.GNUTranslations.ugettext(self, message))

    def ungettext(self, msgid1, msgid2, n):
        # see ugettext
        msgid1 = unicode(msgid1)
        msgid2 = unicode(msgid2)
        return unicode(
            gettext.GNUTranslations.ungettext(self, msgid1, msgid2, n))

    def unpgettext(self, context, msgid, msgidplural, n):
        context = unicode(context)
        msgid = unicode(msgid)
        msgidplural = unicode(msgidplural)
        real_msgid = u"%s\x04%s" % (context, msgid)
        real_msgidplural = u"%s\x04%s" % (context, msgidplural)
        result = self.ngettext(real_msgid, real_msgidplural, n)
        if result == real_msgid:
            return msgid
        elif result == real_msgidplural:
            return msgidplural
        return result

    def upgettext(self, context, msgid):
        context = unicode(context)
        msgid = unicode(msgid)
        real_msgid = u"%s\x04%s" % (context, msgid)
        result = self.ugettext(real_msgid)
        if result == real_msgid:
            return msgid
        return result

    def install(self, unicode=False, debug_text=None):
        if not unicode:
            raise NotImplementedError

        if debug_text is not None:
            def wrap(f):
                def g(*args, **kwargs):
                    return debug_text + f(*args, **kwargs) + debug_text
                return g
        else:
            def wrap(f):
                return f

        __builtin__.__dict__["_"] = wrap(self.ugettext)
        __builtin__.__dict__["N_"] = wrap(type(u""))
        __builtin__.__dict__["C_"] = wrap(self.upgettext)
        __builtin__.__dict__["ngettext"] = wrap(self.ungettext)
        __builtin__.__dict__["npgettext"] = wrap(self.unpgettext)
