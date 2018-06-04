# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#           2012 Christoph Reiter
#      2011-2014 Nick Boultbee
#           2014 Jan Path
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
import datetime

from gi.repository import Gtk, Pango, GLib, Gio
from senf import fsnative, fsn2text

from quodlibet import _
from quodlibet import util
from quodlibet import config
from quodlibet import app
from quodlibet.pattern import Pattern
from quodlibet.qltk.views import TreeViewColumnButton
from quodlibet.qltk import add_css
from quodlibet.util.path import unexpand
from quodlibet.formats._audio import FILESYSTEM_TAGS
from quodlibet.compat import text_type, string_types, listvalues, listitems
from quodlibet.qltk.x import CellRendererPixbuf


def create_songlist_column(t):
    """Returns a SongListColumn instance for the given tag"""

    if t in ["~#added", "~#mtime", "~#lastplayed", "~#laststarted"]:
        return DateColumn(t)
    elif t in ["~length", "~#length"]:
        return LengthColumn()
    elif t == "~#filesize":
        return FilesizeColumn()
    elif t in ["~rating"]:
        return RatingColumn()
    elif t.startswith("~#"):
        return NumericColumn(t)
    elif t in FILESYSTEM_TAGS:
        return FSColumn(t)
    elif "<" in t:
        return PatternColumn(t)
    elif "~" not in t and t != "title":
        return NonSynthTextColumn(t)
    else:
        return WideTextColumn(t)


def _highlight_current_cell(cr, background_area, cell_area, flags):
    """Draws a 'highlighting' background for the cell. Look depends on
    the active theme.
    """

    # Use drawing code/CSS for Entry (reason being that it looks best here)
    dummy_widget = Gtk.Entry()
    style_context = dummy_widget.get_style_context()
    style_context.save()
    # Make it less prominent
    state = Gtk.StateFlags.INSENSITIVE | Gtk.StateFlags.BACKDROP
    style_context.set_state(state)
    color = style_context.get_border_color(state)
    add_css(dummy_widget,
            "* { border-color: rgba(%d, %d, %d, 0.3); }" % (
                    color.red * 255, color.green * 255, color.blue * 255))
    ba = background_area
    ca = cell_area
    # Draw over the left and right border so we don't see the rounded corners
    # and borders. Use height for the overshoot as rounded corners + border
    # should never be larger than the height..
    # Ideally we would draw over the whole background but the cell area only
    # redraws the cell_area so we get leftover artifacts if we draw
    # above/below.
    draw_area = (ba.x - ca.height, ca.y,
                 ba.width + ca.height * 2, ca.height)
    cr.save()
    cr.new_path()
    cr.rectangle(ba.x, ca.y, ba.width, ca.height)
    cr.clip()
    Gtk.render_background(style_context, cr, *draw_area)
    Gtk.render_frame(style_context, cr, *draw_area)
    cr.restore()
    style_context.restore()


class SongListCellAreaBox(Gtk.CellAreaBox):

    highlight = False

    def do_render(self, context, widget, cr, background_area, cell_area,
                  flags, paint_focus):
        if self.highlight and not flags & Gtk.CellRendererState.SELECTED:
            _highlight_current_cell(cr, background_area, cell_area, flags)
        return Gtk.CellAreaBox.do_render(
            self, context, widget, cr, background_area, cell_area,
            flags, paint_focus)

    def do_apply_attributes(self, tree_model, iter_, is_expander, is_expanded):
        self.highlight = tree_model.get_path(iter_) == tree_model.current_path
        return Gtk.CellAreaBox.do_apply_attributes(
            self, tree_model, iter_, is_expander, is_expanded)


class SongListColumn(TreeViewColumnButton):

    def __init__(self, tag):
        """tag e.g. 'artist'"""

        title = self._format_title(tag)
        super(SongListColumn, self).__init__(
            title=title, cell_area=SongListCellAreaBox())
        self.set_tooltip_text(title)
        self.header_name = tag

        self.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.set_visible(True)
        self.set_sort_indicator(False)

        self._last_rendered = None

    def _format_title(self, tag):
        """Format the column title based on the tag"""

        return util.tag(tag)

    def _needs_update(self, value):
        """Call to check if the last passed value was the same.

        This is used to reduce formatting if the input is the same
        either because of redraws or all columns have the same value
        """

        if self._last_rendered == value:
            return False
        self._last_rendered = value
        return True


class TextColumn(SongListColumn):
    """Base text column"""

    def __init__(self, tag):
        super(TextColumn, self).__init__(tag)

        self._render = Gtk.CellRendererText()
        self.pack_start(self._render, True)
        self.set_cell_data_func(self._render, self._cdf)
        self.set_clickable(True)

        # We check once in a while if the font size has changed. If it has
        # we reset the min/fixed width and force at least one cell to update
        # (which might trigger other column size changes..)
        self._last_width = None
        self._force_update = False
        self._deferred_width_check = util.DeferredSignal(
            self._check_width_update, timeout=500)

        def on_tv_changed(column, old, new):
            if new is None:
                self._deferred_width_check.abort()
            else:
                self._deferred_width_check.call()

        self.connect("tree-view-changed", on_tv_changed)

    def _get_min_width(self):
        return -1

    def _cell_width(self, text):
        """Returns the column width needed for the passed text"""

        widget = self.get_tree_view()
        assert widget is not None
        layout = widget.create_pango_layout(text)
        text_width = layout.get_pixel_size()[0]
        cell_pad = self._render.get_property('xpad')

        return text_width + 8 + cell_pad

    def _check_width_update(self):
        width = self._cell_width(u"abc 123")
        if self._last_width == width:
            self._force_update = False
            return
        self._last_width = width
        self._force_update = True
        self.queue_resize()

    def _needs_update(self, value):
        return self._force_update or \
            super(TextColumn, self)._needs_update(value)

    def _cdf(self, column, cell, model, iter_, user_data):
        self._deferred_width_check()
        if self._force_update:
            min_width = self._get_min_width()
            self.set_min_width(min_width)
            if not self.get_resizable():
                self.set_fixed_width(min_width)
            # calling it in the cell_data_func leads to broken drawing..
            GLib.idle_add(self.queue_resize)

        value = self._fetch_value(model, iter_)
        if not self._needs_update(value):
            return
        self._apply_value(model, iter_, cell, value)

    def _fetch_value(self, model, iter_):
        """Should return everything needed for formatting the final value"""

        raise NotImplementedError

    def _apply_value(self, model, iter_, cell, value):
        """Should format the value and set it on the cell renderer"""

        raise NotImplementedError


class RatingColumn(TextColumn):
    """Render ~rating directly

    (simplifies filtering, saves a function call).
    """

    def __init__(self, *args, **kwargs):
        super(RatingColumn, self).__init__("~rating", *args, **kwargs)
        self.set_expand(False)
        self.set_resizable(False)

    def _get_min_width(self):
        return self._cell_width(util.format_rating(1.0))

    def _fetch_value(self, model, iter_):
        song = model.get_value(iter_)
        rating = song.get("~#rating")
        default = config.RATINGS.default
        return (rating, default)

    def _apply_value(self, model, iter_, cell, value):
        rating, default = value
        cell.set_sensitive(rating is not None)
        value = rating if rating is not None else default
        cell.set_property('text', util.format_rating(value))


class WideTextColumn(TextColumn):
    """Resizable and ellipsized at the end. Used for any key with
    a '~' in it, and 'title'.
    """

    def __init__(self, *args, **kwargs):
        super(WideTextColumn, self).__init__(*args, **kwargs)
        self._render.set_property('ellipsize', Pango.EllipsizeMode.END)
        self.set_resizable(True)

    def _get_min_width(self):
        return self._cell_width("000")

    def _fetch_value(self, model, iter_):
        return model.get_value(iter_).comma(self.header_name)

    def _apply_value(self, model, iter_, cell, value):
        cell.set_property('text', value)


class DateColumn(WideTextColumn):
    """The '~#' keys that are dates."""

    def _fetch_value(self, model, iter_):
        return model.get_value(iter_)(self.header_name)

    def _apply_value(self, model, iter_, cell, stamp):
        if not stamp:
            cell.set_property('text', _("Never"))
        else:
            try:
                date = datetime.datetime.fromtimestamp(stamp).date()
            except (OverflowError, ValueError, OSError):
                text = u""
            else:
                format_setting = config.gettext("settings",
                                      "datecolumn_timestamp_format")

                # use format configured in Advanced Preferences
                if format_setting:
                    format_ = format_setting
                # use default behaviour-format
                else:
                    today = datetime.datetime.now().date()
                    days = (today - date).days
                    if days == 0:
                        format_ = "%X"
                    elif days < 7:
                        format_ = "%A"
                    else:
                        format_ = "%x"

                stamp = time.localtime(stamp)
                text = time.strftime(format_, stamp)
            cell.set_property('text', text)


class NonSynthTextColumn(WideTextColumn):
    """Optimize for non-synthesized keys by grabbing them directly.
    Used for any tag without a '~' except 'title'.
    """

    def _fetch_value(self, model, iter_):
        return model.get_value(iter_).get(self.header_name, "")

    def _apply_value(self, model, iter_, cell, value):
        cell.set_property('text', value.replace("\n", ", "))


class FSColumn(WideTextColumn):
    """Contains text in the filesystem encoding, so needs to be
    decoded safely (and also more slowly).
    """

    def __init__(self, *args, **kwargs):
        super(FSColumn, self).__init__(*args, **kwargs)
        self._render.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

    def _fetch_value(self, model, iter_):
        values = model.get_value(iter_).list(self.header_name)
        return values[0] if values else fsnative(u"")

    def _apply_value(self, model, iter_, cell, value):
        cell.set_property('text', fsn2text(unexpand(value)))


class PatternColumn(WideTextColumn):

    def __init__(self, *args, **kwargs):
        super(PatternColumn, self).__init__(*args, **kwargs)

        try:
            self._pattern = Pattern(self.header_name)
        except ValueError:
            self._pattern = None

    def _format_title(self, tag):
        return util.pattern(tag)

    def _fetch_value(self, model, iter_):
        song = model.get_value(iter_)
        if self._pattern is not None:
            return self._pattern % song
        return u""

    def _apply_value(self, model, iter_, cell, value):
        cell.set_property('text', value)


class NumericColumn(TextColumn):
    """Any '~#' keys except dates."""

    def __init__(self, *args, **kwargs):
        super(NumericColumn, self).__init__(*args, **kwargs)
        self._render.set_property('xalign', 1.0)
        self.set_alignment(1.0)
        self.set_expand(False)
        self.set_resizable(False)

        self._texts = {}
        self._timeout = None

        def on_tv_changed(column, old, new):
            if new is None and self._timeout is not None:
                GLib.source_remove(self._timeout)
                self._timeout = None

        self.connect("tree-view-changed", on_tv_changed)

    def _get_min_width(self):
        """Give the initial and minimum width. override if needed"""

        # Best efforts for the general minimum width case
        # Allows well for >=1000 Kbps, -12.34 dB RG values, "Length" etc
        return self._cell_width("-22.22")

    def _fetch_value(self, model, iter_):
        return model.get_value(iter_).comma(self.header_name)

    def _apply_value(self, model, iter_, cell, value):
        if isinstance(value, float):
            text = u"%.2f" % round(value, 2)
        else:
            text = text_type(value)

        cell.set_property('text', text)
        self._recalc_width(model.get_path(iter_), text)

    def _delayed_recalc(self):
        self._timeout = None

        tv = self.get_tree_view()
        assert tv is not None
        range_ = tv.get_visible_range()
        if not range_:
            return

        start, end = range_
        start = start[0]
        end = end[0]

        # compute the cell width for all drawn cells in range +/- 3
        for key, value in listitems(self._texts):
            if not (start - 3) <= key <= (end + 3):
                del self._texts[key]
            elif isinstance(value, string_types):
                self._texts[key] = self._cell_width(value)

        # resize if too small or way too big and above the minimum
        width = self.get_width()
        needed_width = max([self._get_min_width()] + listvalues(self._texts))
        if width < needed_width:
            self._resize(needed_width)
        elif width - needed_width >= self._cell_width("0"):
            self._resize(needed_width)

    def _resize(self, width):
        # In case the treeview has no other expanding columns, setting the
        # width will have no effect on the actual width. Calling queue_resize()
        # in that case would result in an endless recalc loop. So stop here.
        if width == self.get_fixed_width() and width == self.get_max_width():
            return

        self.set_fixed_width(width)
        self.set_max_width(width)
        self.queue_resize()

    def _recalc_width(self, path, text):
        self._texts[path[0]] = text
        if self._timeout is not None:
            GLib.source_remove(self._timeout)
            self._timeout = None
        self._timeout = GLib.idle_add(self._delayed_recalc,
            priority=GLib.PRIORITY_LOW)


class LengthColumn(NumericColumn):

    def __init__(self):
        super(LengthColumn, self).__init__("~#length")

    def _get_min_width(self):
        # 1:22:22, allows entire albums as files (< 75mins)
        return self._cell_width(util.format_time_display(60 * 82 + 22))

    def _fetch_value(self, model, iter_):
        return model.get_value(iter_).get("~#length", 0)

    def _apply_value(self, model, iter_, cell, value):
        text = util.format_time_display(value)
        cell.set_property('text', text)
        self._recalc_width(model.get_path(iter_), text)


class FilesizeColumn(NumericColumn):

    def __init__(self):
        super(FilesizeColumn, self).__init__("~#filesize")

    def _get_min_width(self):
        # e.g "2.22 MB"
        return self._cell_width(util.format_size(2.22 * (1024 ** 2)))

    def _fetch_value(self, model, iter_):
        return model.get_value(iter_).get("~#filesize", 0)

    def _apply_value(self, model, iter_, cell, value):
        text = util.format_size(value)
        cell.set_property('text', text)
        self._recalc_width(model.get_path(iter_), text)


class CurrentColumn(SongListColumn):
    """Displays the current song indicator, either a play or pause icon."""

    def __init__(self):
        super(CurrentColumn, self).__init__("~current")
        self._render = CellRendererPixbuf()
        self.pack_start(self._render, True)
        self._render.set_property('xalign', 0.5)

        self.set_fixed_width(24)
        self.set_expand(False)
        self.set_cell_data_func(self._render, self._cdf)

    def _format_title(self, tag):
        return u""

    def _cdf(self, column, cell, model, iter_, user_data):
        PLAY = "media-playback-start"
        PAUSE = "media-playback-pause"
        STOP = "media-playback-stop"
        ERROR = "dialog-error"

        row = model[iter_]

        if row.path == model.current_path:
            player = app.player
            if player.error:
                name = ERROR
            elif model.sourced:
                name = [PLAY, PAUSE][player.paused]
            else:
                name = STOP
        else:
            name = None

        if not self._needs_update(name):
            return

        if name is not None:
            gicon = Gio.ThemedIcon.new_from_names(
                [name + "-symbolic", name])
        else:
            gicon = None

        cell.set_property('gicon', gicon)
