# Copyright 2010-14 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet import util
from quodlibet.qltk import Icons
from quodlibet.plugins.editing import EditTagsPlugin
from quodlibet.plugins import PluginConfigMixin
from quodlibet.util.string.titlecase import _humanise


class TitleCase(EditTagsPlugin, PluginConfigMixin):
    PLUGIN_ID = "Title Case"
    PLUGIN_NAME = _("Title Case")
    PLUGIN_DESC = _("Title-cases tag values in the tag editor.")
    PLUGIN_ICON = Icons.TOOLS_CHECK_SPELLING
    CONFIG_SECTION = "titlecase"

    # Issue 753: Allow all caps (as before).
    # Set to False means you get Run Dmc, Ac/Dc, Cd 1/2 etc
    allow_all_caps = True

    def process_tag(self, value):
        if not self.allow_all_caps:
            value = value.lower()
        value = util.title(value)
        return _humanise(value) if self.human else value

    def __init__(self, tag, value):
        self.allow_all_caps = self.config_get_bool("allow_all_caps", True)
        self.human = self.config_get_bool("human_title_case", True)

        super().__init__(
            label=_("Title-_case Value"), use_underline=True)
        self.set_image(
            Gtk.Image.new_from_icon_name(Icons.TOOLS_CHECK_SPELLING,
                                         Gtk.IconSize.MENU))
        self.set_sensitive(self.process_tag(value) != value)

    @classmethod
    def PluginPreferences(cls, window):
        vb = Gtk.VBox()
        vb.set_spacing(8)
        config_toggles = [
            ("allow_all_caps", _("Allow _ALL-CAPS in tags"), None, True),
            ("human_title_case", _("_Human title case"),
             _("Uses common English rules for title casing, as in"
               ' "Dark Night of the Soul"'), True),
        ]
        for key, label, tooltip, default in config_toggles:
            ccb = cls.ConfigCheckButton(label, key, default)
            if tooltip:
                ccb.set_tooltip_text(tooltip)
            vb.pack_start(ccb, True, True, 0)
        return vb

    def activated(self, tag, value):
        return [(tag, self.process_tag(value))]
