# -*- coding: utf-8 -*-
# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Steven Robertson,
#           2011-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import config
from quodlibet import _
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.x import Button
from quodlibet.qltk import Icons
from quodlibet.util import connect_obj


class GstBackendPreferences(Gtk.VBox):
    def __init__(self, backend, debug=False):
        super(GstBackendPreferences, self).__init__(spacing=6)

        entry = UndoEntry()
        entry.set_tooltip_text(_("The GStreamer output pipeline used for "
                "playback. Leave blank for the default pipeline. "
                "In case the pipeline contains a sink, "
                "it will be used instead of the default one."))

        entry.set_text(config.get('player', 'gst_pipeline'))

        def changed(entry):
            config.set('player', 'gst_pipeline', entry.get_text())
        entry.connect('changed', changed)

        pipe_label = Gtk.Label(label=_('_Output pipeline:'))
        pipe_label.set_use_underline(True)
        pipe_label.set_mnemonic_widget(entry)

        apply_button = Button(_("_Apply"))

        preview_entry = UndoEntry()
        preview_entry.set_tooltip_text(_(
                "The GStreamer output pipeline used for "
                "preview playback. Leave blank for the default pipeline. "
                "In case the pipeline contains a sink, "
                "it will be used instead of the default one."))

        preview_entry.set_text(config.get('player', 'gst_pipeline_preview'))

        def changed(entry):
            config.set('player', 'gst_pipeline_preview', entry.get_text())
        preview_entry.connect('changed', changed)

        preview_pipe_label = Gtk.Label(label=_('_Preview output pipeline:'))
        preview_pipe_label.set_use_underline(True)
        preview_pipe_label.set_mnemonic_widget(preview_entry)

        preview_apply_button = Button(_("_Apply"))

        def format_buffer(scale, value):
            return _("%.1f seconds") % value

        def scale_changed(scale):
            duration_msec = int(scale.get_value() * 1000)
            backend.get_player()._set_buffer_duration(duration_msec)
            backend.get_preview_player()._set_buffer_duration(duration_msec)

        duration = config.getfloat("player", "gst_buffer")
        scale = Gtk.HScale.new(
            Gtk.Adjustment(value=duration, lower=0.2, upper=10))
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_show_fill_level(True)
        scale.connect('format-value', format_buffer)
        scale.connect('value-changed', scale_changed)

        buffer_label = Gtk.Label(label=_('_Buffer duration:'))
        buffer_label.set_use_underline(True)
        buffer_label.set_mnemonic_widget(scale)

        def rebuild_pipeline(*args):
            backend.get_player()._rebuild_pipeline()
        apply_button.connect('clicked', rebuild_pipeline)

        def rebuild_preview_pipeline(*args):
            backend.get_preview_player()._rebuild_pipeline()
        preview_apply_button.connect('clicked', rebuild_preview_pipeline)

        gapless_button = ConfigCheckButton(
            _('Disable _gapless playback'),
            "player", "gst_disable_gapless", populate=True)
        gapless_button.set_alignment(0.0, 0.5)
        gapless_button.set_tooltip_text(
            _("Disabling gapless playback can avoid track changing problems "
              "with some GStreamer versions."))

        widgets = [(pipe_label, entry, apply_button),
                   (preview_pipe_label, preview_entry, preview_apply_button),
                   (buffer_label, scale, None),
        ]

        table = Gtk.Table(n_rows=len(widgets), n_columns=3)
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        for i, (left, middle, right) in enumerate(widgets):
            left.set_alignment(0.0, 0.5)
            table.attach(left, 0, 1, i, i + 1,
                         xoptions=Gtk.AttachOptions.FILL |
                         Gtk.AttachOptions.SHRINK)
            if right:
                table.attach(middle, 1, 2, i, i + 1)
                table.attach(right, 2, 3, i, i + 1,
                             xoptions=Gtk.AttachOptions.FILL |
                             Gtk.AttachOptions.SHRINK)
            else:
                table.attach(middle, 1, 3, i, i + 1)

        table.attach(gapless_button, 0, 3, 3, 4)

        self.pack_start(table, True, True, 0)

        if debug:
            def print_bin(backend):
                backend.get_player()._print_pipeline()
                backend.get_preview_player()._print_pipeline()

            b = Button("Print Pipelines", Icons.DIALOG_INFORMATION)
            connect_obj(b, 'clicked', print_bin, backend)
            self.pack_start(b, True, True, 0)
