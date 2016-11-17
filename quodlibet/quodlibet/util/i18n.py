# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import gettext
import locale

from quodlibet.compat import text_type, PY2


def bcp47_to_language(code):
    """Takes a BCP 47 language identifier and returns a value suitable for the
    LANGUAGE env var.

    Only supports a small set of inputs and might return garbage..
    """

    if code == "zh-Hans":
        return "zh_CN"
    elif code == "zh-Hant":
        return "zh_TW"

    parts = code.split("-")
    is_iso = lambda s: len(s) == 2 and s.isalpha()

    # we only support ISO 639-1
    if not is_iso(parts[0]):
        return parts[0].replace(":", "")
    lang_subtag = parts[0]

    region = ""
    if len(parts) >= 2 and is_iso(parts[1]):
        region = parts[1]
    elif len(parts) >= 3 and is_iso(parts[2]):
        region = parts[2]

    if region:
        return "%s_%s" % (lang_subtag, region)
    return lang_subtag


def osx_locale_id_to_lang(id_):
    """Converts a NSLocale identifier to something suitable for LANG"""

    if not "_" in id_:
        return id_
    # id_ can be "zh-Hans_TW"
    parts = id_.rsplit("_", 1)
    ll = parts[0]
    ll = bcp47_to_language(ll).split("_")[0]
    return "%s_%s" % (ll, parts[1])


def set_i18n_envvars():
    """Set the LANG/LANGUAGE environment variables if not set in case the
    current platform doesn't use them by default (OS X, Window)
    """

    if os.name == "nt":
        from quodlibet.util.winapi import GetUserDefaultUILanguage, \
            GetSystemDefaultUILanguage

        langs = filter(None, map(locale.windows_locale.get,
                                 [GetUserDefaultUILanguage(),
                                  GetSystemDefaultUILanguage()]))
        if langs:
            os.environ.setdefault('LANG', langs[0])
            os.environ.setdefault('LANGUAGE', ":".join(langs))
    elif sys.platform == "darwin":
        from AppKit import NSLocale
        locale_id = NSLocale.currentLocale().localeIdentifier()
        lang = osx_locale_id_to_lang(locale_id)
        os.environ.setdefault('LANG', lang)

        preferred_langs = NSLocale.preferredLanguages()
        if preferred_langs:
            languages = map(bcp47_to_language, preferred_langs)
            os.environ.setdefault('LANGUAGE', ":".join(languages))
    else:
        return


def fixup_i18n_envvars():
    """Sanitizes env vars before gettext can use them.

    LANGUAGE should support a priority list of languages with fallbacks, but
    doesn't work due to "en" no being known to gettext (This could be solved
    by providing a en.po in QL but all other libraries don't define it either)

    This tries to fix that.
    """

    try:
        langs = os.environ["LANGUAGE"].split(":")
    except KeyError:
        return

    # So, this seems to be an undocumented feature where C selects
    # "no translation". Append it to any en/en_XX so that when not found
    # it falls back to "en"/no translation.
    sanitized = []
    for lang in langs:
        sanitized.append(lang)
        if lang.startswith("en") and len(langs) > 1:
            sanitized.append("C")

    os.environ["LANGUAGE"] = ":".join(sanitized)


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
        self._debug_text = None

    def ugettext(self, message):
        # force unicode here since __contains__ (used in gettext) ignores
        # our changed defaultencoding for coercion, so utf-8 encoded strings
        # fail at lookup.
        message = text_type(message)
        if PY2:
            return text_type(gettext.GNUTranslations.ugettext(self, message))
        else:
            return text_type(gettext.GNUTranslations.gettext(self, message))

    def ungettext(self, msgid1, msgid2, n):
        # see ugettext
        msgid1 = text_type(msgid1)
        msgid2 = text_type(msgid2)
        if PY2:
            return text_type(
                gettext.GNUTranslations.ungettext(self, msgid1, msgid2, n))
        else:
            return text_type(
                gettext.GNUTranslations.ngettext(self, msgid1, msgid2, n))

    def unpgettext(self, context, msgid, msgidplural, n):
        context = text_type(context)
        msgid = text_type(msgid)
        msgidplural = text_type(msgidplural)
        real_msgid = u"%s\x04%s" % (context, msgid)
        real_msgidplural = u"%s\x04%s" % (context, msgidplural)
        result = self.ngettext(real_msgid, real_msgidplural, n)
        if result == real_msgid:
            return msgid
        elif result == real_msgidplural:
            return msgidplural
        return result

    def upgettext(self, context, msgid):
        context = text_type(context)
        msgid = text_type(msgid)
        real_msgid = u"%s\x04%s" % (context, msgid)
        result = self.ugettext(real_msgid)
        if result == real_msgid:
            return msgid
        return result

    def set_debug_text(self, debug_text):
        self._debug_text = debug_text

    def wrap_text(self, value):
        if self._debug_text is None:
            return value
        else:
            return self._debug_text + value + self._debug_text

    def install(self, *args, **kwargs):
        raise NotImplementedError("We no longer do builtins")


_translations = GlibTranslations()


def set_translation(trans):
    global _translations

    _translations = trans


def _(message):
    """
    Args:
        message (text_type)
    Returns:
        text_type

    Lookup the translation for message
    """

    return _translations.wrap_text(_translations.ugettext(message))


def N_(message):
    """
    Args:
        message (text_type)
    Returns:
        text_type

    Only marks a string for translation
    """

    return text_type(message)


def C_(context, message):
    """
    Args:
        context (text_type)
        message (text_type)
    Returns:
        text_type

    Lookup the translation for message for a context
    """

    return _translations.wrap_text(
        _translations.upgettext(context, message))


def ngettext(singular, plural, n):
    """
    Args:
        singular (text_type)
        plural (text_type)
        n (int)
    Returns:
        text_type

    Returns the translation for a singular or plural form depending
    on the value of n.
    """

    return _translations.wrap_text(
        _translations.ungettext(singular, plural, n))


def numeric_phrase(singular, plural, n, template_var=None):
    """Returns a final locale-specific phrase with pluralisation if necessary
    and grouping of the number.

    This is added to custom gettext keywords to allow us to use as-is.

    Args:
        singular (text_type)
        plural (text_type)
        n (int)
        template_var (text_type)
    Returns:
        text_type

    For example,

    ``numeric_phrase('Add %d song', 'Add %d songs', 12345)``
    returns
    `"Add 12,345 songs"`
    (in `en_US` locale at least)
    """
    num_text = locale.format('%d', n, grouping=True)
    if not template_var:
        template_var = '%d'
        replacement = '%s'
        params = num_text
    else:
        template_var = '%(' + template_var + ')d'
        replacement = '%(' + template_var + ')s'
        params = dict()
        params[template_var] = num_text
    return (ngettext(singular.replace(template_var, replacement),
            plural.replace(template_var, replacement), n) % params)


def npgettext(context, singular, plural, n):
    """
    Args:
        context (text_type)
        singular (text_type)
        plural (text_type)
        n (int)
    Returns:
        text_type

    Like ngettext, but with also depends on the context.
    """

    return _translations.wrap_text(
        _translations.unpgettext(context, singular, plural, n))
