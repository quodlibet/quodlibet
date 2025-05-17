# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import re
from pathlib import Path

import pytest

from tests import TestCase, skipUnless, QL_BASE_PATH
from tests.helper import ListWithUnused

ACCEPTABLE_STOCK = [b"media-next", b"media-previous", b"media-play", b"media-pause"]

try:
    import polib
except ImportError:
    polib = None

from quodlibet.util.string.titlecase import human_title
from gdist import gettextutil

PO_PATH = QL_BASE_PATH / "po"


def has_gettext_util():
    try:
        gettextutil.check_version()
    except gettextutil.GettextError:
        return False
    return True


class MissingTranslationsError(Exception):
    def __init__(self, missing):
        super().__init__("No reference in POTFILES.in to: " + ", ".join(missing))


@pytest.mark.skipif(not has_gettext_util(), reason="no gettext")
def test_potfile_format():
    with gettextutil.create_pot(PO_PATH) as pot_path:
        gettextutil.check_pot(pot_path)


class TPOTFILESIN(TestCase):
    def test_no_extra_entries(self):
        """Works without polib installed..."""
        with open(PO_PATH / "POTFILES.in") as f:
            for fn in f:
                path = QL_BASE_PATH / fn.strip()
                assert path.is_file(), f"Can't read {path!r} from POTFILES.in"

    @pytest.mark.skipif(not has_gettext_util(), reason="no gettext")
    def test_missing(self):
        results = gettextutil.get_missing(PO_PATH)
        if results:
            raise MissingTranslationsError(results)


@skipUnless(polib, "polib not found")
@pytest.mark.skipif(not has_gettext_util(), reason="no gettext")
class TPot(TestCase):
    @classmethod
    def setUpClass(cls):
        with gettextutil.create_pot(PO_PATH) as pot_path:
            cls.pot = polib.pofile(pot_path)

    def conclude(self, fails, reason):
        if fails:

            def format_occurrences(e):
                return ", ".join("{}:{}".format(*o) for o in e.occurrences)

            msg = "\n".join(f"{e.msgid!r} ({format_occurrences(e)})" for e in fails)
            self.fail(f"One or more messages did not pass ({reason}):\n{msg}")

    def test_multiple_format_placeholders(self):
        fails = []
        reg = re.compile(r"((?<!%)%[sbcdoxXneEfFgG]|\{\})")
        for entry in self.pot:
            if len(reg.findall(entry.msgid)) > 1:
                fails.append(entry)
        self.conclude(fails, "uses multiple non-named format placeholders")

    def test_label_capitals(self):
        """Check that various input labels (strings ending with a ':') are
        written with proper capitalization.

        Examples:
        Dough amount: - ok
        Salt: - ok
        Channel eggs through the Internet: - ok
        All Caps: - title case can't be used for labels

        Caveats:
        The test doesn't yet know which words are usually capitalized, so:
        Send to Kitchen: - will erroneously pass the test
        """
        fails = []
        ok_labels = ListWithUnused("Local _IP:", "Songs with MBIDs:")

        for entry in self.pot:
            if not entry.msgid.endswith(":"):
                continue
            if " " not in entry.msgid.strip():
                continue
            if entry.msgid == human_title(entry.msgid):
                if entry.msgid not in ok_labels:
                    fails.append(entry)

        ok_labels.check_unused()
        self.conclude(fails, "title case used for a label")

    def test_whitespace(self):
        """Check that there are no more than 1 space character ' ' in a row.

        Examples:
        "Quod Libet" - ok
        "Quod  Libet" - extra whitespace
        "Traceback:\n  <snip>" - ok

        Caveats:
        linebreaks and presumably other special characters in the messages
        are stored as literals, so when matching them with regular
        expressions, don't forget to use double backslash.
        """
        fails = []
        regex = re.compile(r"[^\\n] {2,}")

        for entry in self.pot:
            if regex.findall(entry.msgid):
                fails.append(entry)

        self.conclude(fails, "extra whitespace")

    def test_punctuation(self):
        """Check that punctuation marks are used properly.

        Examples:
        Hello! - ok
        Hello ! - extra whitespace
        HH:MM:SS - ok
        example.com - ok
        Open .tags file - ok
        Hello,world - missing whitespace
        """
        fails = []
        regex = re.compile(r"\s[.,:;!?](?![a-z])|[a-z](?<!people)[,:;][a-zA-Z]")

        for entry in self.pot:
            if regex.findall(entry.msgid):
                fails.append(entry)

        self.conclude(fails, "check punctuation")

    def test_ellipsis(self):
        # https://wiki.gnome.org/Initiatives/GnomeGoals/UnicodeUsage

        for entry in self.pot:
            self.assertFalse(
                "..." in entry.msgid,
                msg=f"{entry} should use '…' (ELLIPSIS) instead of '...'",
            )

    def test_markup(self):
        # https://wiki.gnome.org/Initiatives/GnomeGoals/RemoveMarkupInMessages

        fails = []
        for entry in self.pot:
            # This only checks strings starting and ending with a tag.
            # TODO: fix for all cases by adding a translator comment
            # and insert
            if re.match("<.*?>.*</.*?>", entry.msgid):
                fails.append(entry)

        self.conclude(fails, "contains markup, remove it!")

    def test_terms_letter_case(self):
        """Check that some words are always written with a specific
        combination of lower and upper case letters.

        Examples:
        MusicBrainz - ok
        musicbrainz - lower case letters
        musicbrainz_track_id - ok
        musicbrainz.org - ok
        @(musicbrainz - ok
        """
        terms = (
            "AcoustID",
            "D-Bus",
            "Ex Falso",
            "GNOME",
            "GStreamer",
            "Internet",
            "iPod",
            "Last.fm",
            "MusicBrainz",
            "Python",
            "Quod Libet",
            "Replay Gain",
            "ReplayGain",
            "Squeezebox",
            "Wikipedia",
        )
        ok_prefixes = "@("
        ok_suffixes = ("_", ".org")
        fails = []

        for entry in self.pot:
            msg = entry.msgid
            for term in terms:
                if term.lower() not in msg.lower():
                    continue
                i = msg.lower().find(term.lower())
                if msg[:i].endswith(ok_prefixes) or msg[i + len(term) :].startswith(
                    ok_suffixes
                ):
                    continue
                if term not in msg:
                    fails.append(entry)

        self.conclude(fails, "incorrect letter case for a term")

    def test_terms_spelling(self):
        """Check if some words are misspelled. Some of the words are already
        checked in test_terms_letter_case, but some misspellings include
        not only letter case.

        Examples:
        Last.fm - ok
        LastFM - common misspelling
        """
        incorrect_terms = ("Acoustid.org", "ExFalso", "LastFM", "QuodLibet")
        fails = []

        for entry in self.pot:
            for term in incorrect_terms:
                if term in entry.msgid:
                    fails.append(entry)

        self.conclude(fails, "incorrect spelling for a term")

    def test_leading_and_trailing_spaces(self):
        fails = []

        for entry in self.pot:
            if entry.msgid.strip() != entry.msgid:
                fails.append(entry)

        self.conclude(fails, "leading or trailing spaces")


class POMixin:
    lang: str

    @pytest.mark.skipif(not has_gettext_util(), reason="no gettext")
    def test_pos(self):
        po_path = gettextutil.get_po_path(PO_PATH, self.lang)
        gettextutil.check_po(po_path)

    def test_gtk_stock_items(self):
        with open(self.current_po_path(), "rb") as h:
            for line in h:
                if line.strip().startswith(b'msgstr "gtk-'):
                    parts = line.strip().split()
                    value = parts[1].strip('"')[4:]
                    self.assertFalse(
                        value and value not in ACCEPTABLE_STOCK,
                        f"Invalid stock translation in {self.lang}\n{line}",
                    )

    def conclude(self, fails, reason):
        if fails:

            def format_occurrences(e):
                occurences = [(self.lang + ".po", e.linenum)]
                occurences += e.occurrences
                return ", ".join("{}:{}".format(*o) for o in occurences)

            message = "\n".join(
                f"{e.msgid!r} - {e.msgstr!r} ({format_occurrences(e)})" for e in fails
            )
            self.fail(f"One or more messages did not pass ({reason}).\n{message}")

    LANGUAGES_TO_CHECK = ("ru", "de")

    def test_original_punctuation_present(self):
        if polib is None:
            return

        if self.lang not in self.LANGUAGES_TO_CHECK:
            return

        fails = []

        # In some languages, for example Chinese and Japanese, it's usual to
        # put accelerators separately, on the end of the string in parentheses,
        # so the test needs to strip that part before checking the endings.
        par = re.compile(r" ?\(_\w\)$")

        for entry in polib.pofile(str(self.current_po_path())):
            if not entry.msgstr or entry.obsolete or "fuzzy" in entry.flags:
                continue

            # Possible endings for the strings. Make sure to put longer
            # endings before shorter ones, for example: '...', '.'
            # otherwise this pair: 'a...', 'b..' will pass the test.
            ends = [(":", "："), "…", "...", (".", "。"), " "]

            # First find the appropriate ending of msgid
            for end in ends:
                if entry.msgid.endswith(end):
                    break
            else:
                continue

            # ... then check that msgstr ends with it as as well
            if not entry.msgstr.endswith(end):
                matches = par.findall(entry.msgstr)
                if matches and entry.msgstr[: -len(matches[0])].endswith(end):
                    pass
                else:
                    fails.append(entry)

        self.conclude(fails, "ending punctuation missing")

    def current_po_path(self) -> Path:
        return PO_PATH / f"{self.lang}.po"


for lang in gettextutil.list_languages(PO_PATH):
    testcase = type("PO." + str(lang), (TestCase, POMixin), {})
    testcase.lang = lang
    globals()["PO." + lang] = testcase
