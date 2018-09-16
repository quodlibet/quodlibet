# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.util.massagers import Massager, validate, is_valid, \
    error_message, get_options, ValidationError


class TMassagers(TestCase):
    def validate(self, key, values):
        massager = Massager.for_tag(key)
        for val in values:
            self.assertTrue(massager.is_valid(val))
            self.assertTrue(
                isinstance(massager.validate(str(val)), str))

    def invalidate(self, key, values):
        for val in values:
            self.failIf(Massager.for_tag(key).is_valid(val))

    def equivs(self, key, equivs):
        massager = Massager.for_tag(key)
        for value, normed in equivs.items():
            self.assertEqual(normed, massager.validate(value))
            self.assertTrue(
                isinstance(massager.validate(str(value)), str))

    def test_validate_helper(self):
        self.assertEqual(validate("foo", "bar"), "bar")
        self.assertRaises(ValidationError, validate, "date", "bar")
        self.assertEqual(validate("date", "2000"), "2000")

    def test_is_valid_helper(self):
        self.assertTrue(is_valid("foo", "bar"))
        self.assertFalse(is_valid("date", "bar"))
        self.assertTrue(is_valid("date", "2000"))

    def test_error_message_helper(self):
        self.assertFalse(error_message("foo", "bar"))
        self.assertTrue(error_message("date", "2000"))

    def test_get_options_helper(self):
        self.assertFalse(get_options("foo"))
        self.assertTrue(get_options("language"))

    def test_date_valid(self):
        self.validate("date", ["2002-10-12", "2000", "1200-10", "0000-00-00",
                               "1999/09/12"])

    def test_date_invalid(self):
        self.invalidate("date", ["200", "date-or-no", "", "2000-00-00-00"])

    def test_date_equivs(self):
        self.equivs("date", {"2000": "2000", "1999-99-99": "1999-99-99",
                             "1999/12/09": "1999-12-09"})

    def test_gain_valid(self):
        gains = ["+2.12 dB", "99. dB", "-1.11 dB", "-0.99 dB", "0 dB"]
        self.validate('replaygain_track_gain', gains)
        self.validate('replaygain_album_gain', gains)

    def test_gain_invalid(self):
        gains = ["hooray", "", "dB dB"]
        self.invalidate('replaygain_track_gain', gains)
        self.invalidate('replaygain_album_gain', gains)

    def test_gain_equivs(self):
        equivs = {"12.1 dB": "+12.1 dB", "-1.00 dB": "-1.00 dB", "0": "+0. dB"}
        self.equivs("replaygain_track_gain", equivs)
        self.equivs("replaygain_album_gain", equivs)

    def test_peak_valid(self):
        peaks = ["0.54", "0.999", "0", "1.234", "1.99"]
        self.validate('replaygain_track_peak', peaks)
        self.validate('replaygain_album_peak', peaks)

    def test_peak_invalid(self):
        peaks = ["", "100 dB", "woooo", "12.12.12", "-18", "2.23"]
        self.invalidate('replaygain_track_peak', peaks)
        self.invalidate('replaygain_album_peak', peaks)

    def test_mbid_valid(self):
        self.validate("musicbrainz_trackid",
                      ["cafebabe-ffff-eeee-0101-deadbeafffff",
                       "Fef1F0f4-dead-a5da-d0D0-86753099ffff"])

    def test_mbid_invalid(self):
        self.invalidate("musicbrainz_trackid",
                        ["", "cafebab!-ffff-eeee-0101-deadbeaf",
                         "Fef1F0f4-dead-a5da-d0D0-8675309z"])

    def test_mbid_equivs(self):
        self.equivs("musicbrainz_trackid",
                    {"cafebabe-ffff-eeee-0101-deadbeafffff":
                     "cafebabe-ffff-eeee-0101-deadbeafffff",
                     "Fef1F0f4-dead-a5da-d0D0-86753099ffff":
                     "fef1f0f4-dead-a5da-d0d0-86753099ffff"
                     })

    def test_albumstatus(self):
        self.validate("musicbrainz_albumstatus",
                      ["official", "promotional", "bootleg"])
        self.invalidate("musicbrainz_albumstatus",
                        ["", "unofficial", "\x99"])

    def test_language_valid(self):
        self.validate("language", ["eng", "zho", "lol", "fre", "ger", "zza"])
        self.validate("language", ["deu", "fra", "msa"])
        # self.invalidate("language", ["xxx", "ROFL", "", "es", "ENG"])
        # Issue 439: Actually, allow free-text.
        self.validate("language", ["", "German", "Chinese", "Foobarlanguage"])
        mas = Massager.for_tag("language")

        # Check completion help too
        for code in ["eng", "fra", "fre", "deu", "zho"]:
            self.failUnless(code in mas.options,
                "'%s' should be in languages options" % code)
        self.failIf("" in mas.options)
