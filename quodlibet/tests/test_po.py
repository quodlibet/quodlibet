# -*- coding: utf-8 -*-
from tests import TestCase, AbstractTestCase, skipIf
from tests.helper import ListWithUnused as L

import os
import re
import glob

try:
    import polib
except ImportError:
    polib = None

import quodlibet
from quodlibet.util.path import iscommand
from quodlibet.util.string.titlecase import human_title
from gdist import gettextutil


PODIR = os.path.join(os.path.dirname(quodlibet.__path__[0]), "po")


class TPOTFILESIN(TestCase):

    def test_missing(self):
        try:
            gettextutil.check_version()
        except gettextutil.GettextError:
            return

        result = gettextutil.get_missing(PODIR, "quodlibet")
        if result:
            raise Exception(result)


@skipIf(polib is None, "polib not found")
class TPot(TestCase):

    @classmethod
    def setUpClass(cls):
        pot_path = gettextutil.update_pot(PODIR, "quodlibet")
        cls.pot = polib.pofile(pot_path)

    def conclude(self, fails, reason):
        if fails:
            def format_occurrences(e):
                return ', '.join('%s:%s' % o for o in e.occurrences)
            messages = [
                "'%s' (%s)" % (e.msgid, format_occurrences(e)) for e in fails
            ]
            self.fail(
                "One or more messages did not pass (%s):\n" % reason
                + '\n'.join(messages))

    def test_multiple_format_placeholders(self):
        fails = []
        reg = re.compile(r"((?<!%)%[sbcdoxXneEfFgGn]|\{\})")
        for entry in self.pot:
            if len(reg.findall(entry.msgid)) > 1:
                fails.append(entry)
        self.conclude(fails,
            "uses multiple non-named format placeholders")

    def test_label_capitals(self):
        """ Check that various input labels (strings ending with a ':') are
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
        ok_labels = L('Local _IP:')

        for entry in self.pot:
            if not entry.msgid.endswith(':'):
                continue
            if ' ' not in entry.msgid.strip():
                continue
            if entry.msgid == human_title(entry.msgid):
                if entry.msgid not in ok_labels:
                    fails.append(entry)

        ok_labels.check_unused()
        self.conclude(fails, "title case used for a label")

    def test_whitespace(self):
        """ Check that there are no more than 1 space character ' ' in a row.

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
        regex = re.compile(r'[^\\n] {2,}')

        for entry in self.pot:
            if regex.findall(entry.msgid):
                fails.append(entry)

        self.conclude(fails, "extra whitespace")

    def test_punctuation(self):
        """ Check that punctuation marks are used properly.

            Examples:
            Hello! - ok
            Hello ! - extra whitespace
            HH:MM:SS - ok
            example.com - ok
            Open .tags file - ok
            Hello,world - missing whitespace
        """
        fails = []
        regex = re.compile(r'\s[.,:;!?](?![a-z])|[a-z][,:;][a-zA-Z]')

        for entry in self.pot:
            if regex.findall(entry.msgid):
                fails.append(entry)

        self.conclude(fails, "check punctuation")

    def test_ellipsis(self):
        # https://wiki.gnome.org/Initiatives/GnomeGoals/UnicodeUsage

        for entry in self.pot:
            self.assertFalse(
                "..." in entry.msgid,
                msg=u"%s should use '…' (ELLIPSIS) instead of '...'" % entry)

    def test_markup(self):
        # https://wiki.gnome.org/Initiatives/GnomeGoals/RemoveMarkupInMessages

        for entry in self.pot:
            # this only checks strings containing "%" where it's likely
            # that the formated content is variable anyway.
            # TODO: fix for all cases by adding a translator comment
            # and insert
            self.assertFalse(
                re.match("<.*?>.*?%.*?</.*?>", entry.msgid),
                msg=u"%s contains markup, remove it!" % entry)

    def test_terms_letter_case(self):
        """ Check that some words are always written with a specific
            combination of lower and upper case letters.

            Examples:
            MusicBrainz - ok
            musicbrainz - lower case letters
            musicbrainz_track_id - ok
            musicbrainz.org - ok
        """
        terms = (
            'AcoustID', 'D-Bus', 'Ex Falso', 'GNOME', 'GStreamer', 'Internet',
            'iPod', 'Last.fm', 'MusicBrainz', 'Python', 'Quod Libet',
            'Replay Gain', 'ReplayGain', 'Squeezebox', 'Wikipedia')
        ok_suffixes = ('_', '.org')
        fails = []

        for entry in self.pot:
            for term in terms:
                if term.lower() not in entry.msgid.lower():
                    continue
                i = entry.msgid.lower().find(term.lower())
                if entry.msgid[i + len(term):].startswith(ok_suffixes):
                    continue
                if term not in entry.msgid:
                    fails.append(entry)

        self.conclude(fails, "incorrect letter case for a term")

    def test_terms_spelling(self):
        """ Check if some words are misspelled. Some of the words are already
            checked in test_terms_letter_case, but some misspellings include
            not only letter case.

            Examples:
            Last.fm - ok
            LastFM - common misspelling
        """
        incorrect_terms = ('Acoustid.org', 'ExFalso', 'LastFM', 'QuodLibet')
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


class PO(AbstractTestCase):
    def test_pos(self):
        if not iscommand("msgfmt"):
            return

        self.failIf(os.system("msgfmt -c po/%s.po > /dev/null" % self.lang))
        try:
            os.unlink("messages.mo")
        except OSError:
            pass

    def test_gtranslator_blows_goats(self):
        for line in open(os.path.join(PODIR, "%s.po" % self.lang), "rb"):
            if line.strip().startswith("#"):
                continue
            self.failIf("\xc2\xb7" in line,
                        "Broken GTranslator copy/paste in %s:\n%s" % (
                self.lang, line))

    def test_gtk_stock_items(self):
        for line in open(os.path.join(PODIR, "%s.po" % self.lang), "rb"):
            if line.strip().startswith('msgstr "gtk-'):
                parts = line.strip().split()
                value = parts[1].strip('"')[4:]
                self.failIf(value and value not in [
                    'media-next', 'media-previous', 'media-play',
                    'media-pause'],
                            "Invalid stock translation in %s\n%s" % (
                    self.lang, line))

    def conclude(self, fails, reason):
        from quodlibet import print_w
        if fails:
            def format_occurrences(e):
                occurences = [(self.lang + ".po", e.linenum)]
                occurences += e.occurrences
                return ', '.join('%s:%s' % o for o in occurences)
            messages = [
                '"%s" - "%s" (%s)' % (e.msgid, e.msgstr, format_occurrences(e))
                for e in fails
            ]
            for message in messages:
                print_w(message)
            self.fail(
                "One or more messages did not pass (%s).\n"
                "Please check the warning messages above." % reason)

    def test_original_punctuation_present(self):
        if polib is None:
            return

        LANGUAGES_TO_CHECK = ('ru', 'de')

        if self.lang not in LANGUAGES_TO_CHECK:
            return

        fails = []

        # In some languages, for example Chinese and Japanese, it's usual to
        # put accelerators separately, on the end of the string in parentheses,
        # so the test needs to strip that part before checking the endings.
        par = re.compile(r' ?\(_\w\)$')

        for entry in polib.pofile(os.path.join(PODIR, "%s.po" % self.lang)):
            if not entry.msgstr or entry.obsolete or 'fuzzy' in entry.flags:
                continue

            # Possible endings for the strings. Make sure to put longer
            # endings before shorter ones, for example: '...', '.'
            # otherwise this pair: 'a...', 'b..' will pass the test.
            ends = [(':', u'：'), u'…', '...', ('.', u'。'), ' ']

            # First find the appropriate ending of msgid
            for end in ends:
                if entry.msgid.endswith(end):
                    break
            else:
                continue

            # ... then check that msgstr ends with it as as well
            if not entry.msgstr.endswith(end):
                matches = par.findall(entry.msgstr)
                if matches and entry.msgstr[:-len(matches[0])].endswith(end):
                    pass
                else:
                    fails.append(entry)

        self.conclude(fails, "ending punctuation missing")


for fn in glob.glob(os.path.join(PODIR, "*.po")):
    lang = os.path.basename(fn)[:-3]
    testcase = type('PO.' + lang, (PO,), {})
    testcase.lang = lang
    globals()['PO.' + lang] = testcase
