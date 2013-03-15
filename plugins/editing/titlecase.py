# Copyright 2010-12 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet import util
from quodlibet.plugins.editing import EditTagsPlugin
from quodlibet.plugins import PluginConfigMixin

# Cheat list for human title-casing in English. See Issue 424.
ENGLISH_INCORRECTLY_CAPITALISED_WORDS = \
    [u"The", u"An", u"A", u"'N'", u"'N", u"N'", u"Tha", u"De", u"Da",
     u"In", u"To", u"For", u"Up", u"With", u"As", u"At", u"From",
     u"Into", u"On", u"Out",
     #, u"Over",
     u"Of", u"By", u"'Til", u"Til",
     u"And", u"Or", u"Nor",
#    u"Is", u"Are", u"Am"
    ]

# Allow basic sentence-like concepts eg "Artist: The Greatest Hits"
ENGLISH_SENTENCE_ENDS = [".", ":", "-"]


def previous_real_word(words, i):
    """Returns the first word from words before position i that is non-null"""
    while i > 0:
        i -= 1
        if words[i] != "":
            break
    return words[i]


def humanise(text):
    """Returns a more natural (English) title-casing of text
    Intended for use after util.title() only"""
    words = text.split(" ")   # Yes: to preserve double spacing (!)
    for i in xrange(1, len(words) - 1):
        word = words[i]
        if word in ENGLISH_INCORRECTLY_CAPITALISED_WORDS:
            prev = previous_real_word(words, i)
            if (prev and (not prev[-1] in ENGLISH_SENTENCE_ENDS
                    # Add an exception for would-be ellipses...
                    or prev[-3:] == '...')):
                words[i] = word.lower()
    return u" ".join(words)


class TitleCase(EditTagsPlugin, PluginConfigMixin):
    PLUGIN_ID = "Title Case"
    PLUGIN_NAME = _("Title Case")
    PLUGIN_DESC = _("Title-case tag values in the tag editor.")
    PLUGIN_ICON = gtk.STOCK_SPELL_CHECK
    PLUGIN_VERSION = "1.3"
    CONFIG_SECTION = "titlecase"

    # Issue 753: Allow all caps (as before).
    # Set to False means you get Run Dmc, Ac/Dc, Cd 1/2 etc
    allow_all_caps = True

    def process_tag(self, value):
        if not self.allow_all_caps:
            value = value.lower()
        value = util.title(value)
        return humanise(value) if self.human else value

    def __init__(self, tag, value):
        self.allow_all_caps = self.config_get_bool('allow_all_caps', True)
        self.human = self.config_get_bool('human_title_case', True)

        super(TitleCase, self).__init__(_("Title-_case Value"))
        self.set_image(
            gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
        self.set_sensitive(self.process_tag(value) != value)

    @classmethod
    def PluginPreferences(cls, window):
        vb = gtk.VBox()
        vb.set_spacing(8)
        config_toggles = [
            ('allow_all_caps', _("Allow _ALL-CAPS in tags"), None, True),
            ('human_title_case', _("_Human title case"),
             _("Uses common English rules for title casing, as in"
               " \"Dark Night of the Soul\""), True),
        ]
        for key, label, tooltip, default in config_toggles:
            ccb = cls.ConfigCheckButton(label, key, default)
            if tooltip:
                ccb.set_tooltip_text(tooltip)
            vb.pack_start(ccb)
        return vb

    def activated(self, tag, value):
        return [(tag, self.process_tag(value))]
