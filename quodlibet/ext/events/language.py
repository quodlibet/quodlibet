# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Pango

from quodlibet import _
from quodlibet import config
from quodlibet.qltk import Icons
from quodlibet.util.i18n import get_available_languages
from quodlibet.util import iso639, escape
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk.models import ObjectStore


class LanguagePreference(EventPlugin):
    PLUGIN_ID = "Change Language"
    PLUGIN_NAME = _("Change Language")
    PLUGIN_DESC = _("Change the user interface language.")
    PLUGIN_CAN_ENABLE = False
    PLUGIN_ICON = Icons.PREFERENCES_SYSTEM

    def PluginPreferences(self, *args):
        current = config.gettext("settings", "language")
        if not current:
            current = None

        combo = Gtk.ComboBox()
        model = ObjectStore()
        combo.set_model(model)
        for lang_id in [None] + sorted(get_available_languages("quodlibet")):
            iter_ = model.append(row=[lang_id])
            if lang_id == current:
                combo.set_active_iter(iter_)

        def cell_func(combo, render, model, iter_, *args):
            value = model.get_value(iter_)
            if value is None:
                text = escape(_("System Default"))
            else:
                if value == "C":
                    value = "en"
                translated = escape(iso639.translate(value.split("_", 1)[0]))
                text = f"{escape(value)} <span weight='light'>({translated})</span>"
            render.set_property("markup", text)

        render = Gtk.CellRendererText()
        render.props.ellipsize = Pango.EllipsizeMode.END
        combo.prepend(render, True)
        combo.set_cell_data_func(render, cell_func)

        def on_combo_changed(combo):
            new_language = model.get_value(combo.get_active_iter())
            if new_language is None:
                new_language = ""
            config.settext("settings", "language", new_language)

        combo.connect("changed", on_combo_changed)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.prepend(combo, False, False, 0)
        box.prepend(
            Gtk.Label(
                label=_("A restart is required for any changes to take effect"),
                wrap=True,
                xalign=0,
            ),
            False,
            False,
            0,
        )

        return box
