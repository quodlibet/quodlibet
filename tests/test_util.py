# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import uuid
import tempfile
import os
import sys
import threading
import traceback
import time
import logging
from pathlib import Path

from senf import fsnative, fsn2bytes, bytes2fsn

from quodlibet import _
from quodlibet.config import HardCodedRatingsPrefs, DurationFormat
from quodlibet import config
from quodlibet import util
from quodlibet.util.dprint import print_exc, format_exception, extract_tb, PrintHandler
from quodlibet.util import (
    format_time_long as f_t_l,
    format_time_preferred,
    format_time_display,
    format_time_seconds,
)
from quodlibet.util import re_escape
from quodlibet.util.library import set_scan_dirs, get_scan_dirs
from quodlibet.util.path import (
    parse_xdg_user_dirs,
    xdg_get_system_data_dirs,
    escape_filename,
    strip_win32_incompat_from_path,
    xdg_get_cache_home,
    xdg_get_data_home,
    unexpand,
    xdg_get_user_dirs,
    xdg_get_config_home,
    get_temp_cover_file,
    mkdir,
    mtime,
)
from quodlibet.util.string import decode, encode, split_escape, join_escape
from quodlibet.util.environment import is_osx

from . import TestCase, skipIf
from .helper import capture_output, locale_numeric_conv, temp_filename

is_win = os.name == "nt"


class Tmkdir(TestCase):
    def test_exists(self):
        mkdir(".")

    def test_notdirectory(self):
        self.assertRaises(OSError, mkdir, __file__)

    def test_manydeep(self):
        assert not os.path.isdir("nonext")
        t = tempfile.mkdtemp()
        path = os.path.join(t, "nonext", "test", "test2", "test3")
        mkdir(path)
        try:
            assert os.path.isdir(path)
        finally:
            os.rmdir(path)
            path = os.path.dirname(path)
            os.rmdir(path)
            path = os.path.dirname(path)
            os.rmdir(path)
            path = os.path.dirname(path)
            os.rmdir(path)
            os.rmdir(t)


class Tgetcwd(TestCase):
    def test_getcwd(self):
        assert isinstance(os.getcwd(), fsnative)


class Tmtime(TestCase):
    def test_equal(self):
        self.assertEqual(mtime("."), os.path.getmtime("."))

    def test_bad(self):
        assert not os.path.exists("/dev/doesnotexist")
        self.assertEqual(mtime("/dev/doesnotexist"), 0)


class Tformat_locale(TestCase):
    def test_format_int_locale(self):
        assert isinstance(util.format_int_locale(1024), str)

    def test_format_float_locale(self):
        assert isinstance(util.format_float_locale(1024.1024), str)

    def test_format_time_seconds(self):
        assert isinstance(util.format_time_seconds(1024), str)

        with locale_numeric_conv():
            assert format_time_seconds(1024) == "1,024 seconds"
            assert format_time_seconds(1) == "1 second"


class Tunexpand(TestCase):
    d = os.path.expanduser("~")
    u = unexpand(d)

    def test_base(self):
        path = unexpand(self.d)
        if is_win:
            self.assertEqual(path, "%USERPROFILE%")
        else:
            self.assertEqual(path, "~")

    def test_only_profile_case(self):
        assert isinstance(unexpand(os.path.expanduser(fsnative("~"))), fsnative)

    def test_base_trailing(self):
        path = unexpand(self.d + os.path.sep)
        self.assertEqual(path, self.u + os.path.sep)

    def test_noprefix(self):
        path = unexpand(self.d + "foobar" + os.path.sep)
        self.assertEqual(path, self.d + "foobar" + os.path.sep)

    def test_subfile(self):
        path = unexpand(os.path.join(self.d, "la", "la"))
        self.assertEqual(path, os.path.join(self.u, "la", "la"))

    def test_case_insensitive_win(self):
        if is_win:
            assert unexpand(self.d.lower()) == "%USERPROFILE%"
            assert unexpand(self.d.upper()) == "%USERPROFILE%"


class Tformat_rating(TestCase):
    def setUp(self):
        self.r = config.RATINGS = HardCodedRatingsPrefs()

    def test_empty(self):
        self.assertEqual(util.format_rating(0, blank=False), "")

    def test_full(self):
        self.assertEqual(
            len(util.format_rating(1, blank=False)), int(1 / self.r.precision)
        )

    def test_rating_length(self):
        config.RATINGS.number = 4
        for i in range(int(1 / self.r.precision + 1)):
            self.assertEqual(
                i, len(util.format_rating(i * self.r.precision, blank=False))
            )

    def test_bogus(self):
        max_length = int(1 / self.r.precision)
        self.assertEqual(len(util.format_rating(2**32 - 1, blank=False)), max_length)
        self.assertEqual(len(util.format_rating(-4.2, blank=False)), 0)

    def test_blank_lengths(self):
        """Check that there are no unsuspected edge-cases
        for various rating precisions"""
        for self.r.number in [1, 5, 4, 3, 2]:
            steps = self.r.number
            self.assertEqual(len(util.format_rating(1)), steps)
            self.assertEqual(len(util.format_rating(0)), steps)
            self.assertEqual(len(util.format_rating(0.5)), steps)
            self.assertEqual(len(util.format_rating(1 / 3.0)), steps)

    def test_blank_values(self):
        self.r.number = 5
        self.r.blank_symbol = "0"
        self.r.full_symbol = "1"
        # Easy ones first
        self.assertEqual(util.format_rating(0.0), "00000")
        self.assertEqual(util.format_rating(0.2), "10000")
        self.assertEqual(util.format_rating(0.8), "11110")
        self.assertEqual(util.format_rating(1.0), "11111")
        # A bit arbitrary, but standard behaviour
        self.assertEqual(util.format_rating(0.51), "11100")
        # Test rounding down...
        self.assertEqual(util.format_rating(0.6), "11100")
        # Test rounding up...
        self.assertEqual(util.format_rating(0.91), "11111")
        # You never know...
        self.assertEqual(util.format_rating(3.0), "11111")
        self.assertEqual(util.format_rating(-0.5), "00000")


class Tpango(TestCase):
    def test_escape_empty(self):
        self.assertEqual(util.escape(""), "")

    def test_roundtrip(self):
        for s in ["foo&amp;", "<&>", "&", "&amp;", "<&testing&amp;>amp;"]:
            esc = util.escape(s)
            self.assertNotEqual(s, esc)
            self.assertEqual(s, util.unescape(esc))

    def test_unescape_empty(self):
        self.assertEqual(util.unescape(""), "")

    def test_format(self):
        self.assertEqual(util.bold("foo"), "<b>foo</b>")
        self.assertEqual(util.italic("foo"), "<i>foo</i>")
        self.assertEqual(util.monospace("foo"), "<tt>foo</tt>")

    def test_format_escape(self):
        assert util.bold("foo & bar") == "<b>foo &amp; bar</b>"
        assert util.italic("foo & bar") == "<i>foo &amp; bar</i>"
        assert util.monospace("foo & bar") == "<tt>foo &amp; bar</tt>"
        assert util.bold_italic("foo & bar") == "<b><i>foo &amp; bar</i></b>"


class Tre_esc(TestCase):
    def test_empty(self):
        self.assertEqual(re_escape(b""), b"")
        assert isinstance(re_escape(b""), bytes)

    def test_empty_unicode(self):
        self.assertEqual(re_escape(""), "")
        assert isinstance(re_escape(""), str)

    def test_safe(self):
        self.assertEqual(re_escape("fo o"), "fo o")

    def test_unsafe(self):
        self.assertEqual(re_escape("!bar"), r"\!bar")

    def test_many_unsafe(self):
        self.assertEqual(re_escape("*quux#argh?woo"), r"\*quux\#argh\?woo")


class Tdecode(TestCase):
    def test_empty(self):
        self.assertEqual(decode(b""), "")

    def test_safe(self):
        self.assertEqual(decode(b"foo!"), "foo!")

    def test_invalid(self):
        self.assertEqual(decode(b"fo\xde"), "fo\ufffd [Invalid Encoding]")


class Tencode(TestCase):
    def test_empty(self):
        self.assertEqual(encode(""), b"")

    def test_unicode(self):
        self.assertEqual(encode("abcde"), b"abcde")


class Tcapitalize(TestCase):
    def test_empty(self):
        self.assertEqual(util.capitalize(""), "")

    def test_firstword(self):
        self.assertEqual(util.capitalize("aa b"), "Aa b")

    def test_preserve(self):
        self.assertEqual(util.capitalize("aa B"), "Aa B")

    def test_nonalphabet(self):
        self.assertEqual(util.capitalize("!aa B"), "!aa B")


class Thuman_sort(TestCase):
    def smaller(self, x, y):
        return util.human_sort_key(x) < util.human_sort_key(y)

    def equal(self, x, y):
        return util.human_sort_key(x) == util.human_sort_key(y)

    def test_human(self):
        self.assertEqual(self.smaller("2", "15"), True)
        self.assertEqual(self.smaller(" 2", "15 "), True)
        self.assertEqual(self.smaller("a2 g", "a 2z"), True)
        self.assertEqual(self.smaller("a2zz", "a2.1z"), True)

        self.assertEqual(self.smaller("42o", "42\xf6"), True)
        self.assertEqual(self.smaller("42\xf6", "42p"), True)

        self.assertEqual(self.smaller("bbb", "zzz3"), True)

        assert self.equal(" foo", "foo")
        assert self.equal(" ", "")
        assert self.smaller("", ".")
        assert self.smaller("a", "b")
        assert self.smaller("A", "b")

    def test_false(self):
        # album browser needs that to sort albums without artist/title
        # to the bottom
        assert not util.human_sort_key("")

    def test_white(self):
        self.assertEqual(
            util.human_sort_key("  3foo    bar6 42.8"),
            util.human_sort_key("3 foo bar6  42.8  "),
        )
        assert 64.0 in util.human_sort_key("64. 8")


class Tformat_time(TestCase):
    def test_seconds(self):
        self.assertEqual(util.format_time(0), "0:00")
        self.assertEqual(util.format_time(59), "0:59")

    def test_minutes(self):
        self.assertEqual(util.format_time(60), "1:00")
        self.assertEqual(util.format_time(60 * 59 + 59), "59:59")

    def test_hourss(self):
        self.assertEqual(util.format_time(60 * 60), "1:00:00")
        self.assertEqual(util.format_time(60 * 60 + 60 * 59 + 59), "1:59:59")

    def test_negative(self):
        self.assertEqual(util.format_time(-124), "-2:04")


class Tparse_time(TestCase):
    def test_invalid(self):
        self.assertEqual(util.parse_time("not a time"), 0)

    def test_except(self):
        self.assertRaises(ValueError, util.parse_time, "not a time", False)

    def test_empty(self):
        self.assertEqual(util.parse_time(""), 0)

    def test_roundtrip(self):
        # The values are the ones tested for Tformat_time, so we know they
        # will be formatted correctly. They're also representative of
        # all the major patterns.
        for i in [0, 59, 60, 60 * 59 + 59, 60 * 60, 60 * 60 + 60 * 59 + 59]:
            self.assertEqual(util.parse_time(util.format_time(i)), i)

    def test_negative(self):
        self.assertEqual(util.parse_time("-2:04"), -124)


class Tparse_date(TestCase):
    def test_invalid(self):
        self.assertRaises(ValueError, util.parse_date, "not a date")
        self.assertRaises(ValueError, util.parse_date, "0")
        self.assertRaises(ValueError, util.parse_date, "2000-13")
        self.assertRaises(ValueError, util.parse_date, "2000-01-32")
        self.assertRaises(ValueError, util.parse_date, "2000-01-0")
        self.assertRaises(ValueError, util.parse_date, "2000-0-01")

    def test_valid(self):
        ref = time.mktime(time.strptime("2004", "%Y"))
        self.assertEqual(util.parse_date("2004"), ref)
        self.assertEqual(util.parse_date("2004-01-01"), ref)
        self.assertEqual(util.parse_date("2004-1-1"), ref)
        self.assertTrue(util.parse_date("2004-01-01") < util.parse_date("2004-01-02"))


class Tparse_year(TestCase):
    def test_common_date_formats(self):
        self.assertEqual(util.parse_year("2022"), "2022")
        self.assertEqual(util.parse_year("2022-02-28"), "2022")
        self.assertEqual(util.parse_year("02/28/2022"), "2022")


class Tdate_key(TestCase):
    def test_compare(self):
        date_key = util.date_key
        assert date_key("2004") == date_key("2004-01-01")
        assert date_key("2004") == date_key("2004-01")
        assert date_key("2004") < date_key("2004-01-02")
        assert date_key("2099-02-02") < date_key("2099-03-30")

        assert date_key("2004-01-foo") == date_key("2004-01")

    def test_validate(self):
        validate = util.validate_query_date

        for valid in ["2004", "2005-01", "3000-3-4"]:
            assert validate(valid)

        for invalid in [
            "",
            "-",
            "3000-",
            "9-0",
            "8-1-0",
            "1-13-1",
            "1-1-32",
            "1-1-1-1-1",
            "a",
            "1-a",
            "1-1-a",
        ]:
            assert not validate(invalid)


class Tformat_size(TestCase):
    def t_dict(self, d):
        for key, value in d.items():
            formatted = util.format_size(key)
            self.assertEqual(formatted, value)
            assert isinstance(formatted, str)

    def test_bytes(self):
        self.t_dict({0: "0 B", 1: "1 B", 1023: "1023 B"})

    def test_kbytes(self):
        self.t_dict({1024: "1.00 KB", 1536: "1.50 KB", 10240: "10 KB", 15360: "15 KB"})

    def test_mbytes(self):
        self.t_dict(
            {
                1024 * 1024: "1.00 MB",
                1024 * 1536: "1.50 MB",
                1024 * 10240: "10.0 MB",
                1024 * 15360: "15.0 MB",
                123456 * 1024: "121 MB",
                765432 * 1024: "747 MB",
            }
        )

    def test_gbytes(self):
        self.t_dict(
            {
                1024 * 1024 * 1024: "1.0 GB",
                1024 * 1024 * 1536: "1.5 GB",
                1024 * 1024 * 10240: "10.0 GB",
                1024 * 1024 * 15360: "15.0 GB",
            }
        )


class Ttag(TestCase):
    def test_empty(self):
        self.assertEqual(util.tag(""), "Invalid tag")

    def test_basic(self):
        self.assertEqual(util.tag("title"), "Title")

    def test_basic_nocap(self):
        self.assertEqual(util.tag("title", False), "title")

    def test_internal(self):
        self.assertEqual(util.tag("~year"), "Year")

    def test_numeric(self):
        self.assertEqual(util.tag("~#year"), "Year")

    def test_two(self):
        self.assertEqual(util.tag("title~version"), "Title / Version")

    def test_two_nocap(self):
        self.assertEqual(util.tag("title~version", False), "title / version")

    def test_precap_handling(self):
        self.assertEqual(util.tag("labelid"), "Label ID")
        self.assertEqual(util.tag("labelid", False), "label ID")


class Ttagsplit(TestCase):
    def test_single_tag(self):
        self.assertEqual(util.tagsplit("foo"), ["foo"])

    def test_synth_tag(self):
        self.assertEqual(util.tagsplit("~foo"), ["~foo"])

    def test_two_tags(self):
        self.assertEqual(util.tagsplit("foo~bar"), ["foo", "bar"])

    def test_two_prefix(self):
        self.assertEqual(util.tagsplit("~foo~bar"), ["foo", "bar"])

    def test_synth(self):
        self.assertEqual(util.tagsplit("~foo~~bar"), ["foo", "~bar"])

    def test_numeric(self):
        self.assertEqual(util.tagsplit("~#bar"), ["~#bar"])

    def test_two_numeric(self):
        self.assertEqual(util.tagsplit("~#foo~~#bar"), ["~#foo", "~#bar"])

    def test_two_synth_start(self):
        self.assertEqual(util.tagsplit("~~people~album"), ["~people", "album"])


class Tpattern(TestCase):
    def test_empty(self):
        self.assertEqual(util.pattern(""), "")

    def test_basic(self):
        self.assertEqual(util.pattern("<title>"), "Title")

    def test_basic_nocap(self):
        self.assertEqual(util.pattern("<title>", False), "title")

    def test_internal(self):
        self.assertEqual(util.pattern("<~plays>"), "Plays")

    def test_tied(self):
        self.assertEqual(util.pattern("<~title~album>"), "Title - Album")

    def test_unknown(self):
        self.assertEqual(util.pattern("<foobarbaz>"), "Foobarbaz")

    def test_condition(self):
        self.assertEqual(
            util.pattern("<~year|<~year> - <album>|<album>>"), "Year - Album"
        )

    def test_escape(self):
        self.assertEqual(util.pattern(r"\<i\><&>\</i\>", esc=True), "<i>&amp;</i>")

    def test_invalid(self):
        self.assertEqual(util.pattern("<date"), "")
        util.pattern("<d\\")

    def test_complex_condition(self):
        self.assertEqual(util.pattern(r"<#(bitrate \> 150)|HQ|LQ>"), "LQ")

    def test_escape_condition(self):
        self.assertEqual(util.pattern(r"<~filename=/\/adsad\/sadads/|BLA|BLU>"), "BLU")


class Tformat_time_long(TestCase):
    def test_second(self):
        self.assertEqual(f_t_l(1).split(", ")[0], _("1 second"))

    def test_seconds(self):
        self.assertEqual(f_t_l(2).split(", ")[0], _("%d seconds") % 2)

    def test_notminutes(self):
        self.assertEqual(f_t_l(59).split(", ")[0], _("%d seconds") % 59)

    def test_minute(self):
        self.assertEqual(f_t_l(60), _("1 minute"))

    def test_minutes(self):
        self.assertEqual(f_t_l(120).split(", ")[0], _("%d minutes") % 2)

    def test_nothours(self):
        self.assertEqual(f_t_l(3599).split(", ")[0], _("%d minutes") % 59)

    def test_hour(self):
        self.assertEqual(f_t_l(3600), _("1 hour"))

    def test_hours(self):
        self.assertEqual(f_t_l(7200), _("%d hours") % 2)

    def test_notdays(self):
        self.assertEqual(f_t_l(86399).split(", ")[0], _("%d hours") % 23)

    def test_seconds_dropped(self):
        self.assertEqual(len(f_t_l(3601).split(", ")), 2)

    def test_day(self):
        self.assertEqual(f_t_l(86400), _("1 day"))

    def test_days(self):
        self.assertEqual(f_t_l(172800).split(", ")[0], _("%d days") % 2)

    def test_notyears(self):
        self.assertEqual(f_t_l(31535999).split(", ")[0], _("%d days") % 364)

    def test_year(self):
        self.assertEqual(f_t_l(31536000), _("1 year"))

    def test_years(self):
        self.assertEqual(f_t_l(63072000).split(", ")[0], _("%d years") % 2)

    def test_drop_zero(self):
        self.assertEqual(f_t_l(3601), ", ".join([_("1 hour"), _("1 second")]))

    def test_limit_zero(self):
        self.assertEqual(f_t_l(1, limit=0), _("1 second"))

    def test_limit(self):
        self.assertEqual(len(f_t_l(2**31).split(", ")), 2)


class TFormatTimePreferred(TestCase):
    def test_default_setting_is_standard(self):
        self.assertEqual(config.DURATION.format, DurationFormat.STANDARD)

    def test_raw_config_is_standard(self):
        self.assertEqual(
            config.get("display", "duration_format"), DurationFormat.STANDARD
        )

    def test_acts_like_long(self):
        self._fuzz_loop(format_time_preferred, f_t_l)

    def _fuzz_loop(self, f, f2):
        x = 1
        while x < 100000000:
            self.assertEqual(f(x), f2(x))
            x = x * 3 / 2 + 1

    def test_acts_like_display(self):
        def fmt_numeric(x):
            return format_time_preferred(x, DurationFormat.NUMERIC)

        self._fuzz_loop(fmt_numeric, format_time_display)

    def test_seconds(self):
        def fmt_seconds(x):
            return format_time_preferred(x, DurationFormat.SECONDS)

        self._fuzz_loop(fmt_seconds, format_time_seconds)


class Tspawn(TestCase):
    def test_simple(self):
        if is_win:
            return
        assert util.spawn(["ls", "."], stdout=True)

    def test_invalid(self):
        from gi.repository import GLib

        self.assertRaises(GLib.GError, util.spawn, ["not a command"])

    def test_get_output(self):
        if is_win:
            return
        fileobj = util.spawn(["echo", "'$1'", '"$2"', ">3"], stdout=True)
        self.assertEqual(fileobj.read().split(), ["'$1'", '"$2"', ">3"])


class Txdg_dirs(TestCase):
    def test_system_data_dirs_posix(self):
        if is_win:
            return

        os.environ["XDG_DATA_DIRS"] = "/xyz"
        self.assertEqual(xdg_get_system_data_dirs()[0], "/xyz")
        del os.environ["XDG_DATA_DIRS"]
        dirs = xdg_get_system_data_dirs()
        self.assertEqual(dirs[0], "/usr/local/share/")
        self.assertEqual(dirs[1], "/usr/share/")

    def test_data_home(self):
        if is_win:
            return

        os.environ["XDG_DATA_HOME"] = "/xyz"
        self.assertEqual(xdg_get_data_home(), "/xyz")
        del os.environ["XDG_DATA_HOME"]
        should = os.path.join(os.path.expanduser("~"), ".local", "share")
        self.assertEqual(xdg_get_data_home(), should)

    def test_get_user_dirs(self):
        xdg_get_user_dirs()

    def test_parse_xdg_user_dirs(self):
        data = b'# foo\nBLA="$HOME/blah"\n'
        vars_ = parse_xdg_user_dirs(data)
        assert b"BLA" in vars_
        expected = os.path.join(os.environ.get("HOME", ""), "blah")
        self.assertEqual(vars_[b"BLA"], expected)

        vars_ = parse_xdg_user_dirs(b'BLA="$HOME/"')
        assert b"BLA" in vars_
        self.assertEqual(vars_[b"BLA"], os.environ.get("HOME", ""))

        # some invalid
        assert not parse_xdg_user_dirs(b"foo")
        assert not parse_xdg_user_dirs(b"foo=foo bar")
        assert not parse_xdg_user_dirs(b"foo='foo")

    def test_on_windows(self):
        assert xdg_get_system_data_dirs()
        assert xdg_get_cache_home()
        assert xdg_get_data_home()
        assert xdg_get_config_home()


class Tlibrary(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_basic(self):
        assert not get_scan_dirs()
        if os.name == "nt":
            set_scan_dirs(["C:\\foo", "D:\\bar", ""])
            self.assertEqual(get_scan_dirs(), ["C:\\foo", "D:\\bar"])
        else:
            set_scan_dirs(["foo", "bar", ""])
            self.assertEqual(get_scan_dirs(), ["foo", "bar"])


class TNormalizePath(TestCase):
    def test_default(self):
        from quodlibet.util.path import normalize_path as norm

        name = norm(tempfile.mkdtemp())
        try:
            self.assertEqual(norm(name), name)
            self.assertEqual(norm(os.path.join(name, "foo", "..")), name)
        finally:
            os.rmdir(name)

    def test_types(self):
        from quodlibet.util.path import normalize_path

        assert isinstance(normalize_path(fsnative("foo"), False), fsnative)
        assert isinstance(normalize_path("foo", False), fsnative)
        assert isinstance(normalize_path(fsnative("foo"), True), fsnative)
        assert isinstance(normalize_path("foo", True), fsnative)

    def test_canonicalise(self):
        from quodlibet.util.path import normalize_path as norm

        f, path = tempfile.mkstemp()
        path = os.path.realpath(path)  # on osx tmp is a symlink
        os.close(f)
        path = norm(path)

        link_dir = tempfile.mkdtemp()
        link = None
        if not is_win:
            link = os.path.join(link_dir, str(uuid.uuid4()))
            os.symlink(path, link)

        try:
            self.assertEqual(norm(path, canonicalise=True), path)
            self.assertEqual(norm(os.path.join(path, "foo", ".."), True), path)
            if link:
                self.assertEqual(norm(link, True), path)
                # A symlink shouldn't be resolved unless asked for
                self.assertNotEqual(norm(link, False), path)
                # And the other behaviour should also work
                unnormalised_path = os.path.join(link, "foo", "..")
                self.assertEqual(norm(unnormalised_path, True), path)
        finally:
            if link:
                os.remove(link)
            os.remove(path)
            os.rmdir(link_dir)

    def test_pathlib_is_equivalent(self):
        from quodlibet.util.path import normalize_path

        with temp_filename() as fn:
            assert normalize_path(Path(fn)) == normalize_path(fn)
        with temp_filename() as fn:
            path = Path(fn)
            assert normalize_path(path / "./..") == normalize_path(fn + "./..")
            assert normalize_path(path / ".." / path.name) == normalize_path(path)


class Tescape_filename(TestCase):
    def test_str(self):
        result = escape_filename("\x00\x01")
        self.assertEqual(result, "%00%01")
        assert isinstance(result, fsnative)

    def test_unicode(self):
        result = escape_filename("abc\xe4")
        self.assertEqual(result, "abc%C3%A4")
        assert isinstance(result, fsnative)

    def test_safe_chars(self):
        result = escape_filename("1, 2, and -3", safe=" -")
        self.assertEqual(result, "1%2C 2%2C and -3")
        assert isinstance(result, fsnative)


@skipIf(is_win, "not on Windows")
class Tload_library(TestCase):
    # This started breaking on newer osx in CI
    # I suspect it is https://bugs.python.org/issue44689
    # so could be re-tried with newer Python
    @skipIf(is_osx(), "broken on osx")
    def test_libc(self):
        lib, name = util.load_library(["c"])
        self.assertEqual(name, "c")

        lib2, name = util.load_library(["c"])
        assert lib is lib2

        lib3, name = util.load_library(["c"], shared=False)
        assert lib2 is not lib3

    def test_glib(self):
        if sys.platform == "darwin":
            fn = "libglib-2.0.0.dylib"
        else:
            fn = "libglib-2.0.so.0"
        lib, name = util.load_library([fn])
        self.assertEqual(name, fn)
        assert lib


class Tstrip_win32_incompat_from_path(TestCase):
    def test_types(self):
        v = strip_win32_incompat_from_path(fsnative(""))
        assert isinstance(v, fsnative)
        v = strip_win32_incompat_from_path(fsnative("foo"))
        assert isinstance(v, fsnative)

        v = strip_win32_incompat_from_path("")
        assert isinstance(v, str)
        v = strip_win32_incompat_from_path("foo")
        assert isinstance(v, str)

    def test_basic(self):
        if is_win:
            v = strip_win32_incompat_from_path("C:\\foo\\<>/a")
            self.assertEqual(v, "C:\\foo\\___a")
        else:
            v = strip_win32_incompat_from_path("/foo/<>a")
            self.assertEqual(v, "/foo/__a")


class TPathHandling(TestCase):
    def test_main(self):
        v = fsnative("foo")
        assert isinstance(v, fsnative)

        v3 = bytes2fsn(fsn2bytes(v, "utf-8"), "utf-8")
        assert isinstance(v3, fsnative)
        self.assertEqual(v, v3)


class Tget_temp_cover_file(TestCase):
    def test_main(self):
        fobj = get_temp_cover_file(b"foobar")
        try:
            assert isinstance(fobj.name, fsnative)
        finally:
            fobj.close()


class Tsplit_escape(TestCase):
    def test_split_escape(self):
        # from mutagen

        inout = [
            (("", ":"), [""]),
            ((":", ":"), ["", ""]),
            ((":", ":", 0), [":"]),
            ((":b:c:", ":", 0), [":b:c:"]),
            ((":b:c:", ":", 1), ["", "b:c:"]),
            ((":b:c:", ":", 2), ["", "b", "c:"]),
            ((":b:c:", ":", 3), ["", "b", "c", ""]),
            (("a\\:b:c", ":"), ["a:b", "c"]),
            (("a\\\\:b:c", ":"), ["a\\", "b", "c"]),
            (("a\\\\\\:b:c\\:", ":"), ["a\\:b", "c:"]),
            (("\\", ":"), [""]),
            (("\\\\", ":"), ["\\"]),
            (("\\\\a\\b", ":"), ["\\a\\b"]),
        ]

        for inargs, out in inout:
            self.assertEqual(split_escape(*inargs), out)

    def test_types(self):
        parts = split_escape(b"\xff:\xff", b":")
        self.assertEqual(parts, [b"\xff", b"\xff"])
        assert isinstance(parts[0], bytes)

        parts = split_escape("a:b", ":")
        self.assertEqual(parts, ["a", "b"])
        assert all(isinstance(p, str) for p in parts)

        parts = split_escape("", ":")
        self.assertEqual(parts, [""])
        assert all(isinstance(p, str) for p in parts)

        parts = split_escape(":", ":")
        self.assertEqual(parts, ["", ""])
        assert all(isinstance(p, str) for p in parts)

    def test_join_escape_types(self):
        self.assertEqual(join_escape([], b":"), b"")
        assert isinstance(join_escape([], b":"), bytes)
        assert isinstance(join_escape([], ":"), str)
        self.assertEqual(join_escape([b"\xff", b"\xff"], b":"), b"\xff:\xff")
        self.assertEqual(join_escape(["\xe4", "\xe4"], ":"), "\xe4:\xe4")

    def test_join_escape(self):
        self.assertEqual(join_escape([b":"], b":"), b"\\:")
        self.assertEqual(join_escape([b"\\:", b":"], b":"), b"\\\\\\::\\:")

    def test_roundtrip(self):
        values = [b"\\:", b":"]
        joined = join_escape(values, b":")
        self.assertEqual(split_escape(joined, b":"), values)


class TMainRunner(TestCase):
    def test_abort_before_call(self):
        runner = util.MainRunner()

        def worker():
            self.assertRaises(util.MainRunnerAbortedError, runner.call, lambda: None)

        thread = threading.Thread(target=worker)
        runner.abort()
        thread.start()
        thread.join()

    def test_timeout(self):
        runner = util.MainRunner()

        def worker():
            self.assertRaises(
                util.MainRunnerTimeoutError, runner.call, lambda: None, timeout=0.00001
            )

        for _i in range(3):
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()
        runner.abort()

    def test_call_exception(self):
        from gi.repository import GLib

        runner = util.MainRunner()
        loop = GLib.MainLoop()

        def func():
            raise KeyError

        def worker():
            try:
                self.assertRaises(util.MainRunnerError, runner.call, func)
            finally:
                loop.quit()

        thread = threading.Thread(target=worker)
        thread.start()
        loop.run()
        runner.abort()
        thread.join()

    def test_from_main_loop(self):
        from gi.repository import GLib

        runner = util.MainRunner()
        loop = GLib.MainLoop()

        def in_main_loop():
            try:
                self.assertRaises(
                    util.MainRunnerError, runner.call, lambda: None, foo=0
                )
                self.assertEqual(runner.call(lambda i: i + 1, 42, priority=0), 43)
                self.assertEqual(runner.call(lambda i: i - 1, 42), 41)
            finally:
                loop.quit()

        GLib.idle_add(in_main_loop)
        loop.run()

    def test_ok(self):
        from gi.repository import GLib

        runner = util.MainRunner()
        loop = GLib.MainLoop()

        def func(i):
            assert util.is_main_thread()
            return i + 1

        def worker():
            try:
                self.assertEqual(runner.call(func, 42), 43)
            finally:
                loop.quit()

        thread = threading.Thread(target=worker)
        thread.start()

        loop.run()
        thread.join()
        runner.abort()

    def test_multi_abort(self):
        runner = util.MainRunner()
        runner.abort()
        runner.abort()

        def worker():
            self.assertRaises(util.MainRunnerError, runner.call, lambda: None)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()


class Tconnect_destroy(TestCase):
    def test_main(self):
        from gi.repository import Gtk

        b = Gtk.Button()

        class A(Gtk.Button):
            def foo(self):
                pass

        a = A()
        ref = sys.getrefcount(a)
        util.connect_destroy(b, "clicked", a.foo)
        self.assertEqual(sys.getrefcount(a), ref + 1)
        a.destroy()
        self.assertEqual(sys.getrefcount(a), ref)


class Tcached_property(TestCase):
    def test_main(self):
        class A:
            @util.cached_property
            def foo(self):
                return object()

        a = A()
        first = a.foo
        assert first is a.foo
        del a.__dict__["foo"]
        assert first is not a.foo

    def test_dunder(self):
        def define_class():
            class A:
                @util.cached_property
                def __foo_(self):
                    return object()

        self.assertRaises(AssertionError, define_class)


@util.enum
class Foo(str):
    FOO = "blah"
    BAR = "not foo"
    BAZ = "baz!"


class Tenum(TestCase):
    def test_main(self):
        @util.enum
        class IntFoo(int):
            FOO = 0
            BAR = 1

        assert issubclass(IntFoo, int)
        assert isinstance(IntFoo.BAR, IntFoo)
        assert isinstance(IntFoo.FOO, IntFoo)
        self.assertEqual(IntFoo.FOO, 0)
        self.assertEqual(IntFoo.BAR, 1)

    def test_str(self):
        assert issubclass(Foo, str)
        assert isinstance(Foo.BAR, Foo)
        self.assertEqual(Foo.FOO, "blah")
        self.assertEqual(repr(Foo.BAR), "Foo.BAR")

    def test_values(self):
        self.assertEqual(Foo.values, {Foo.FOO, Foo.BAR, Foo.BAZ})

    def test_value_of(self):
        self.assertEqual(Foo.value_of("blah"), Foo.FOO)
        self.assertEqual(Foo.value_of("baz!"), Foo.BAZ)

    def test_value_of_raises_for_unknown(self):
        self.assertRaises(ValueError, Foo.value_of, "??")

    def test_value_of_uses_default(self):
        self.assertEqual(Foo.value_of("??", "default"), "default")


class Tlist_unique(TestCase):
    def test_main(self):
        self.assertEqual(util.list_unique([]), [])
        self.assertEqual(util.list_unique(iter([])), [])
        self.assertEqual(util.list_unique([1, 2, 3]), [1, 2, 3])
        self.assertEqual(util.list_unique([1, 2, 1, 4]), [1, 2, 4])
        self.assertEqual(util.list_unique([1, 1, 1, 2]), [1, 2])


class Treraise(TestCase):
    def test_reraise(self):
        try:
            try:
                raise ValueError("foo")
            except Exception as e:
                util.reraise(TypeError, e)
        except Exception as e:
            assert isinstance(e, TypeError)
            assert "ValueError" in traceback.format_exc()
        else:
            raise AssertionError()


class Tenviron(TestCase):
    def test_main(self):
        for v in os.environ.values():
            if os.name == "nt":
                assert isinstance(v, str)
            else:
                assert isinstance(v, str)


class Tget_module_dir(TestCase):
    def test_self(self):
        path = util.get_module_dir()
        assert isinstance(path, fsnative)
        assert os.path.exists(path)

    def test_other(self):
        path = util.get_module_dir(util)
        assert isinstance(path, fsnative)
        assert os.path.exists(path)


class Tget_ca_file(TestCase):
    def test_main(self):
        path = util.get_ca_file()
        if path is not None:
            assert isinstance(path, fsnative)
            assert os.path.exists(path)


class Tprint_exc(TestCase):
    def test_main(self):
        try:
            1 / 0  # noqa
        except Exception:
            with capture_output():
                print_exc()

    def test_pass_exc_info(self):
        try:
            1 / 0  # noqa
        except Exception:
            with capture_output():
                print_exc(exc_info=sys.exc_info(), context="foo")


class TPrintHandler(TestCase):
    def test_main(self):
        handler = PrintHandler()
        for level in range(0, 70, 10):
            record = logging.LogRecord("foo", level, "a.py", 45, "bar", None, None)
            with capture_output():
                handler.handle(record)


class Tformat_exception(TestCase):
    def test_main(self):
        try:
            1 / 0  # noqa
        except Exception:
            result = format_exception(*sys.exc_info())
            assert isinstance(result, list)
            assert all(isinstance(r, str) for r in result)


class Textract_tb(TestCase):
    def test_main(self):
        try:
            1 / 0  # noqa
        except Exception:
            result = extract_tb(sys.exc_info()[2])
            assert isinstance(result, list)
            for fn, l, fu, text in result:
                assert isinstance(fn, fsnative)
                assert isinstance(l, int)
                assert isinstance(fu, str)
                assert isinstance(text, str)


def test_capture_output():
    with capture_output() as (o, e):
        sys.stdout.write("foo")
        sys.stderr.write("bar")
    assert o.getvalue() == "foo"
    assert e.getvalue() == "bar"

    # also make sure sys.stdout.buffer exists and works,
    # for completeness
    with capture_output() as (o, e):
        sys.stdout.write("foo")
        sys.stdout.buffer.write(b"bar")
        sys.stderr.write("baz")
        sys.stderr.buffer.write(b"quux")
    assert o.getvalue() == "foobar"
    assert e.getvalue() == "bazquux"

    # newlines are preserved as is
    with capture_output() as (o, e):
        sys.stdout.write("a\nb\r\nc\rd")
    assert o.getvalue() == "a\nb\r\nc\rd"
