# Copyright 2005 Joe Wreschnig
#           2012 Christoph Reiter
#      2011-2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time
import datetime
from collections import deque

from gi.repository import Gtk, Pango, GLib

from quodlibet import util
from quodlibet import config
from quodlibet import const
from quodlibet.parse import Pattern
from quodlibet.qltk.views import TreeViewColumnButton
from quodlibet.util.path import fsdecode, unexpand
from quodlibet.formats._audio import FILESYSTEM_TAGS


def create_songlist_column(t):
    """Returns a SongListColumn instance for the given tag"""

    if t in ["~#added", "~#mtime", "~#lastplayed", "~#laststarted"]:
        return DateColumn(t)
    elif t in ["~length", "~#length"]:
        return LengthColumn()
    elif t == "~#filesize":
        return FilesizeColumn()
    elif t in ["~rating", "~#rating"]:
        return RatingColumn()
    elif t.startswith("~#"):
        return NumericColumn(t)
    elif t in FILESYSTEM_TAGS:
        return FSColumn(t)
    elif t.startswith("<"):
        return PatternColumn(t)
    elif "~" not in t and t != "title":
        return NonSynthTextColumn(t)
    else:
        return WideTextColumn(t)


class SongListColumn(TreeViewColumnButton):

    __last_rendered = None

    def __init__(self, tag):
        """tag e.g. 'artist'"""

        title = self._format_title(tag)
        super(SongListColumn, self).__init__(title)
        self.set_tooltip_text(title)
        self.header_name = tag

        self.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.set_visible(True)
        self.set_sort_indicator(False)

    def _format_title(self, tag):
        """Format the column title based on the tag"""

        return util.tag(tag)

    def _needs_update(self, value):
        """Call to check if the last passed value was the same.

        This is used to reduce formating if the input is the same
        either because of redraws or all columns have the same value
        """

        if self.__last_rendered == value:
            return False
        self.__last_rendered = value
        return True


class TextColumn(SongListColumn):
    """Base text column"""

    __label = Gtk.Label().create_pango_layout("")

    def __init__(self, tag):
        super(TextColumn, self).__init__(tag)

        self._render = Gtk.CellRendererText()
        self.pack_start(self._render, True)
        self.set_cell_data_func(self._render, self._cdf)

        self.set_clickable(True)

    def _cell_width(self, text, pad=8):
        """Returns the column width needed for the passed text"""

        cell_pad = self._render.get_property('xpad')
        return self._text_width(text) + pad + cell_pad

    def _text_width(self, text):
        self.__label.set_text(text, -1)
        return self.__label.get_pixel_size()[0]

    def _cdf(self, column, cell, model, iter_, user_data):
        """CellRenderer cell_data_func"""

        raise NotImplementedError


class RatingColumn(TextColumn):
    """Render ~#rating directly

    (simplifies filtering, saves a function call).
    """

    def __init__(self, *args, **kwargs):
        super(RatingColumn, self).__init__("~#rating", *args, **kwargs)
        self.set_expand(False)
        self.set_resizable(False)
        width = self._cell_width(util.format_rating(1.0))
        self.set_fixed_width(width)
        self.set_min_width(width)

    def _cdf(self, column, cell, model, iter_, user_data):
        value = model.get_value(iter_).get(
            "~#rating", config.RATINGS.default)
        if not self._needs_update(value):
            return
        cell.set_property('text', util.format_rating(value))


class WideTextColumn(TextColumn):
    """Resizable and ellipsized at the end. Used for any key with
    a '~' in it, and 'title'.
    """

    def __init__(self, *args, **kwargs):
        super(WideTextColumn, self).__init__(*args, **kwargs)
        self._render.set_property('ellipsize', Pango.EllipsizeMode.END)
        self.set_resizable(True)
        self.set_min_width(self._cell_width("000"))

    def _cdf(self, column, cell, model, iter_, user_data):
        text = model.get_value(iter_).comma(self.header_name)
        if not self._needs_update(text):
            return
        cell.set_property('text', text)


class DateColumn(WideTextColumn):
    """The '~#' keys that are dates."""

    def _cdf(self, column, cell, model, iter_, user_data):
        stamp = model.get_value(iter_)(self.header_name)
        if not self._needs_update(stamp):
            return

        if not stamp:
            cell.set_property('text', _("Never"))
        else:
            date = datetime.datetime.fromtimestamp(stamp).date()
            today = datetime.datetime.now().date()
            days = (today - date).days
            if days == 0:
                format_ = "%X"
            elif days < 7:
                format_ = "%A"
            else:
                format_ = "%x"
            stamp = time.localtime(stamp)
            text = time.strftime(format_, stamp).decode(const.ENCODING)
            cell.set_property('text', text)


class NonSynthTextColumn(WideTextColumn):
    """Optimize for non-synthesized keys by grabbing them directly.
    Used for any tag without a '~' except 'title'.
    """

    def _cdf(self, column, cell, model, iter_, user_data):
        value = model.get_value(iter_).get(self.header_name, "")
        if not self._needs_update(value):
            return
        cell.set_property('text', value.replace("\n", ", "))


class FSColumn(WideTextColumn):
    """Contains text in the filesystem encoding, so needs to be
    decoded safely (and also more slowly).
    """

    def __init__(self, *args, **kwargs):
        super(FSColumn, self).__init__(*args, **kwargs)
        self._render.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)

    def _cdf(self, column, cell, model, iter_, user_data):
        value = model.get_value(iter_).comma(self.header_name)
        if not self._needs_update(value):
            return
        cell.set_property('text', unexpand(fsdecode(value)))


class PatternColumn(WideTextColumn):

    def __init__(self, *args, **kwargs):
        super(PatternColumn, self).__init__(*args, **kwargs)

        try:
            self._pattern = Pattern(self.header_name)
        except ValueError:
            self._pattern = None

    def _format_title(self, tag):
        return util.pattern(tag)

    def _cdf(self, column, cell, model, iter_, user_data):
        song = model.get_value(iter_)
        if not self._pattern:
            return
        value = self._pattern % song
        if not self._needs_update(value):
            return
        cell.set_property('text', value)


class NumericColumn(TextColumn):
    """Any '~#' keys except dates."""

    def __init__(self, *args, **kwargs):
        super(NumericColumn, self).__init__(*args, **kwargs)
        self._render.set_property('xalign', 1.0)
        self.set_alignment(1.0)
        self.__min_width = self._get_min_width()
        self.set_fixed_width(self.__min_width)

        self.set_expand(False)
        self.set_resizable(False)

        self._single_char_width = self._text_width("0")
        self._texts = {}
        self._timeout = None

    def _get_min_width(self):
        """Give the initial and minimum width. override if needed"""

        # Best efforts for the general minimum width case
        # Allows well for >=1000 Kbps, -12.34 dB RG values, "Length" etc
        return self._cell_width("-22.22")

    def _cdf(self, column, cell, model, iter_, user_data):
        value = model.get_value(iter_).comma(self.header_name)
        if not self._needs_update(value):
            return
        text = unicode(value)
        cell.set_property('text', text)
        self._recalc_width(model.get_path(iter_), text)

    def _delayed_recalc(self):
        self._timeout = None

        tv = self.get_tree_view()
        if not tv:
            return
        range_ = tv.get_visible_range()
        if not range_:
            return

        start, end = range_
        start = start[0]
        end = end[0]

        # compute the cell width for all drawn cells in range +/- 3
        for key, value in self._texts.items():
            if not (start - 3) <= key <= (end + 3):
                del self._texts[key]
            elif isinstance(value, basestring):
                self._texts[key] = self._cell_width(value)

        # resize if too small or way too big and above the minimum
        width = self.get_width()
        max_width = max(self._texts.values() or [width])
        if width < max_width:
            self.set_fixed_width(max_width)
            self.set_min_width(max_width)
        elif (width - max_width >= self._single_char_width and
                max_width >= self.__min_width):
            self.set_fixed_width(max_width)
            self.set_max_width(max_width)

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
        return self._cell_width(util.format_time(60 * 82 + 22))

    def _cdf(self, column, cell, model, iter_, user_data):
        value = model.get_value(iter_).get("~#length", 0)
        if not self._needs_update(value):
            return
        text = util.format_time(value)
        cell.set_property('text', text)
        self._recalc_width(model.get_path(iter_), text)


class FilesizeColumn(NumericColumn):

    def __init__(self):
        super(FilesizeColumn, self).__init__("~#filesize")

    def _get_min_width(self):
        # e.g "2.22 MB"
        return self._cell_width(util.format_size(2.22 * (1024 ** 2)))

    def _cdf(self, column, cell, model, iter_, user_data):
        value = model.get_value(iter_).get("~#filesize", 0)
        if not self._needs_update(value):
            return
        text = util.format_size(value)
        cell.set_property('text', text)
        self._recalc_width(model.get_path(iter_), text)
