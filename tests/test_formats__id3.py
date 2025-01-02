# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, get_data_path

import os
from io import BytesIO

from quodlibet import const
from quodlibet.formats._image import EmbeddedImage
from quodlibet.formats.mp3 import MP3File
from quodlibet.formats.aiff import AIFFFile

import mutagen

from .helper import get_temp_copy


class TID3ImagesBase(TestCase):
    KIND = None
    PATH = None

    def setUp(self):
        self.filename = get_temp_copy(self.PATH)

    def tearDown(self):
        os.remove(self.filename)


class TID3ImagesMixin:
    def test_can_change_images(self):
        assert self.KIND(self.filename).can_change_images

    def test_get_primary_image(self):
        assert not self.KIND(self.filename).has_images

        f = mutagen.File(self.filename)
        apic = mutagen.id3.APIC(
            encoding=3, mime="image/jpeg", type=4, desc="foo", data=b"bar"
        )
        f.tags.add(apic)
        f.save()

        song = self.KIND(self.filename)
        assert song.has_images
        image = song.get_primary_image()
        self.assertEqual(image.mime_type, "image/jpeg")
        fn = image.file
        self.assertEqual(fn.read(), b"bar")

        apic = mutagen.id3.APIC(
            encoding=3, mime="image/jpeg", type=3, desc="xx", data=b"bar2"
        )
        f.tags.add(apic)
        f.save()

        song = self.KIND(self.filename)
        assert song.has_images
        image = song.get_primary_image()
        self.assertEqual(image.read(), b"bar2")

        # get_images()
        images = song.get_images()
        assert images and len(images) == 2
        self.assertEqual(images[0].type, 3)
        self.assertEqual(images[1].type, 4)

    def test_clear_images(self):
        f = mutagen.File(self.filename)
        apic = mutagen.id3.APIC(
            encoding=3, mime="image/jpeg", type=4, desc="foo", data=b"bar"
        )
        f.tags.add(apic)
        f.save()

        song = self.KIND(self.filename)
        assert song.has_images
        song.clear_images()

        song = self.KIND(self.filename)
        assert not song.has_images

    def test_set_image(self):
        fileobj = BytesIO(b"foo")
        image = EmbeddedImage(fileobj, "image/jpeg", 10, 10, 8)

        song = self.KIND(self.filename)
        assert not song.has_images
        song.set_image(image)
        assert song.has_images

        song = self.KIND(self.filename)
        assert song.has_images
        self.assertEqual(song.get_primary_image().mime_type, "image/jpeg")

    def test_set_image_no_tag(self):
        f = mutagen.File(self.filename)
        f.delete()
        song = self.KIND(self.filename)
        fileobj = BytesIO(b"foo")
        image = EmbeddedImage(fileobj, "image/jpeg", 10, 10, 8)
        song.set_image(image)

        song = self.KIND(self.filename)
        assert song.has_images


class TID3ImagesMP3(TID3ImagesBase, TID3ImagesMixin):
    KIND = MP3File
    PATH = get_data_path("silence-44-s.mp3")


class TID3ImagesAIFF(TID3ImagesBase, TID3ImagesMixin):
    KIND = AIFFFile
    PATH = get_data_path("test.aiff")


class TID3FileBase(TestCase):
    KIND = None
    PATH = None

    def setUp(self):
        self.filename = get_temp_copy(self.PATH)

    def tearDown(self):
        os.unlink(self.filename)


class TID3FileMixin:
    def test_optional_POPM_count(self):
        # https://github.com/quodlibet/quodlibet/issues/364
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.POPM(const.EMAIL, 42))
        try:
            f.save()
        except TypeError:
            # https://github.com/quodlibet/quodlibet/issues/33
            pass
        else:
            self.KIND(self.filename)

    def test_write_empty_replaygain_track_gain(self):
        f = self.KIND(self.filename)
        f["replaygain_track_gain"] = ""
        f.write()
        f.reload()
        assert f.replay_gain(["track"]) == 1.0

    def test_TXXX_DATE(self):
        # https://github.com/quodlibet/quodlibet/issues/220
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="DATE", text="2010-01-13"))
        f.tags.add(mutagen.id3.TDRC(encoding=3, text="2010-01-14"))
        f.save()
        self.assertEqual(self.KIND(self.filename)["date"], "2010-01-14")
        f.tags.delall("TDRC")
        f.save()
        self.assertEqual(self.KIND(self.filename)["date"], "2010-01-13")
        f.delete()
        self.KIND(self.filename)

    def test_USLT(self):
        """Tests reading and writing of lyrics in USLT"""
        f = mutagen.File(self.filename)
        f.tags.add(
            mutagen.id3.USLT(encoding=3, desc="", lang="\x00\x00\x00", text="lyrics")
        )
        f.tags.add(
            mutagen.id3.USLT(
                encoding=3,
                desc="desc",
                lang="\x00\x00\x00",
                text="lyrics with non-empty desc",
            )
        )
        f.tags.add(
            mutagen.id3.USLT(
                encoding=3, desc="", lang="xyz", text="lyrics with non-empty lang"
            )
        )
        f.save()

        f = mutagen.File(self.filename)
        self.assertEqual(f.tags["USLT::\x00\x00\x00"], "lyrics")
        self.assertEqual(f.tags["USLT:desc:\x00\x00\x00"], "lyrics with non-empty desc")
        self.assertEqual(f.tags["USLT::xyz"], "lyrics with non-empty lang")

        f = self.KIND(self.filename)
        self.assertEqual(
            sorted(f["lyrics"].split("\n")),
            sorted(
                ["lyrics", "lyrics with non-empty lang", "lyrics with non-empty desc"]
            ),
        )
        # multiple USLT tags are not supported so the behavior seems random
        self.assertIn(f["~lyricsdescription"], ["desc", ""])
        self.assertIn(f["~lyricslanguage"], ["xyz", ""])
        f["lyrics"] = "modified lyrics"
        f["~lyricsdescription"] = ""
        f.write()

        f = self.KIND(self.filename)
        self.assertEqual(f["lyrics"], "modified lyrics")
        self.assertEqual(f["~lyricsdescription"], "")
        # languages were invalid regarding ISO_639_2 → *und*efined is written
        self.assertEqual(f["~lyricslanguage"], "und")
        f["lyrics"] = "modified lyrics\nwith two lines"
        f["~lyricsdescription"] = "desc"
        f["~lyricslanguage"] = "eng"
        f.write()

        f = self.KIND(self.filename)
        self.assertEqual(f["lyrics"], "modified lyrics\nwith two lines")
        self.assertEqual(f["~lyricsdescription"], "desc")
        self.assertEqual(f["~lyricslanguage"], "eng")
        del f["lyrics"]
        f.write()

        f = mutagen.File(self.filename)
        self.assertFalse(
            "USLT" in f.tags, "There should be no USLT tag when lyrics were deleted"
        )

        f = self.KIND(self.filename)
        self.assertFalse(
            "lyrics" in f, "There should be no lyrics key when there is no USLT"
        )

    def test_lang_read(self):
        """Tests reading of language from TXXX"""
        # https://github.com/quodlibet/quodlibet/issues/439
        f = mutagen.File(self.filename)
        try:
            lang = "free-text"
            f.tags.add(
                mutagen.id3.TXXX(encoding=3, desc="QuodLibet::language", text=lang)
            )
            f.save()
            self.assertEqual(self.KIND(self.filename)["language"], lang)
        finally:
            f.delete()

    def test_lang_read_TLAN(self):
        """Tests reading language from TLAN"""
        f = mutagen.File(self.filename)
        lang = "eng"
        try:
            f.tags.add(mutagen.id3.TLAN(encoding=3, text=lang))
            f.save()
            self.assertEqual(self.KIND(self.filename)["language"], lang)
        finally:
            f.delete()

    def test_lang_read_multiple_TLAN(self):
        """Tests reading multiple language from TLAN"""
        f = mutagen.File(self.filename)
        # Include an invalid one; current behaviour is to load anyway
        lang = "eng\0der\0fra\0fooooo"
        exp = "eng\nder\nfra\nfooooo"
        try:
            f.tags.add(mutagen.id3.TLAN(encoding=3, text=lang))
            f.save()
            self.assertEqual(self.KIND(self.filename)["language"], exp)
        finally:
            f.delete()

    def test_write_lang_freetext(self):
        """Tests that if you don't use an ISO 639-2 code,
        TXXX gets populated
        """

        af = self.KIND(self.filename)
        for val in ["free-text", "foo", "de", "en"]:
            af["language"] = val
            # Just checking...
            self.assertEqual(af("language"), val)
            af.write()
            tags = mutagen.File(self.filename).tags
            self.assertEqual(tags["TXXX:QuodLibet::language"], val)
            assert "TLAN" not in tags

    def test_write_lang_iso(self):
        """Tests that if you use an ISO 639-2 code, TLAN gets populated"""
        for iso_lang in ["eng", "ger", "zho"]:
            af = self.KIND(self.filename)
            af["language"] = iso_lang
            self.assertEqual(af("language"), iso_lang)
            af.write()
            tags = mutagen.File(self.filename).tags
            self.assertFalse(
                "TXXX:QuodLibet::language" in tags,
                f"Should have used TLAN tag for '{iso_lang}'",
            )
            self.assertEqual(tags["TLAN"], iso_lang)
            af.clear()

    def test_write_multiple_lang_iso(self):
        """Tests using multiple ISO 639-2 codes"""
        iso_langs = ["eng", "ger", "zho"]
        iso_langs_str = "\n".join(iso_langs)
        af = self.KIND(self.filename)
        af["language"] = iso_langs_str
        self.assertEqual(af("language"), iso_langs_str)
        af.write()
        tags = mutagen.File(self.filename).tags
        self.assertFalse(
            "TXXX:QuodLibet::language" in tags,
            f"Should have used TLAN for {iso_langs}",
        )
        self.assertEqual(tags["TLAN"], iso_langs, msg=f"Wrong tags: {tags}")
        af.clear()

    def test_ignore_tlen(self):
        f = mutagen.File(self.filename)
        f.tags.delall("TLEN")
        f.save()
        length = self.KIND(self.filename)("~#length")

        for value in ["20000", "0", "x"]:
            f = mutagen.File(self.filename)
            f.tags.add(mutagen.id3.TLEN(encoding=0, text=[value]))
            f.save()
            self.assertAlmostEqual(self.KIND(self.filename)("~#length"), length, 2)

    def test_load_tcon(self):
        # check if the mutagen preprocessing is used
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TCON(encoding=3, text=["4", "5"]))
        f.save()
        genres = set(self.KIND(self.filename).list("genre"))
        self.assertEqual(genres, {"Funk", "Disco"})

    def test_mb_track_id(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.UFID(owner="http://musicbrainz.org", data=b"x"))
        f.save()
        song = self.KIND(self.filename)
        self.assertEqual(song("musicbrainz_trackid"), "x")
        song["musicbrainz_trackid"] = "y"
        song.write()
        f = mutagen.File(self.filename)
        self.assertEqual(f.tags["UFID:http://musicbrainz.org"].data, b"y")
        del song["musicbrainz_trackid"]
        song.write()
        f = mutagen.File(self.filename)
        assert not f.tags.get("UFID:http://musicbrainz.org")

    def test_mb_release_track_id(self):
        f = mutagen.File(self.filename)
        f.tags.add(
            mutagen.id3.TXXX(
                encoding=3, desc="MusicBrainz Release Track Id", text=["bla"]
            )
        )
        f.save()
        song = self.KIND(self.filename)
        self.assertEqual(song["musicbrainz_releasetrackid"], "bla")
        song["musicbrainz_releasetrackid"] = "foo"
        song.write()
        f = mutagen.File(self.filename)
        frames = f.tags.getall("TXXX:MusicBrainz Release Track Id")
        assert frames
        self.assertEqual(frames[0].text, ["foo"])

    def test_load_comment(self):
        # comm with empty descriptions => comment
        f = mutagen.File(self.filename)
        f.tags.add(
            mutagen.id3.COMM(encoding=3, lang="aar", desc="", text=["foo", "bar"])
        )
        f.save()
        comments = set(self.KIND(self.filename).list("comment"))
        self.assertEqual(comments, {"bar", "foo"})

    def test_foobar2k_replaygain(self):
        # foobar2k saved gain there
        f = mutagen.File(self.filename)
        f.tags.add(
            mutagen.id3.TXXX(encoding=3, desc="replaygain_track_gain", text=["-6 db"])
        )
        f.save()
        song = self.KIND(self.filename)
        self.assertNotAlmostEqual(song.replay_gain(["track"]), 1.0, 1)

        # check if all keys are str
        for k in self.KIND(self.filename).keys():
            assert isinstance(k, str)

        # remove value, save, reload and check if still gone
        del song["replaygain_track_gain"]
        song.write()
        song.reload()

        self.assertAlmostEqual(song.replay_gain(["track"]), 1.0, 1)

    def test_foobar2k_replaygain_read_new(self):
        # Others don't like RVA2, so we have to read/write foobar style
        # https://github.com/quodlibet/quodlibet/issues/1027
        f = mutagen.File(self.filename)

        # use RVA2 in case it's the only one
        f.tags.add(mutagen.id3.RVA2(desc="track", channel=1, gain=-9, peak=1.0))
        f.save()
        song = self.KIND(self.filename)
        self.assertAlmostEqual(song.replay_gain(["track"]), 0.35, 1)

        f.tags.add(
            mutagen.id3.TXXX(encoding=3, desc="replaygain_track_gain", text=["-6 db"])
        )
        f.tags.add(
            mutagen.id3.TXXX(encoding=3, desc="replaygain_track_peak", text=["0.9"])
        )
        f.tags.add(
            mutagen.id3.TXXX(encoding=3, desc="replaygain_album_gain", text=["3 db"])
        )
        f.tags.add(
            mutagen.id3.TXXX(encoding=3, desc="replaygain_album_peak", text=["0.8"])
        )
        f.save()

        song = self.KIND(self.filename)
        self.assertEqual(song("replaygain_track_gain"), "-6 db")
        self.assertEqual(song("replaygain_track_peak"), "0.9")
        self.assertEqual(song("replaygain_album_gain"), "3 db")
        self.assertEqual(song("replaygain_album_peak"), "0.8")

    def test_foobar2k_replaygain_write_new(self):
        # Others don't like RVA2, so we have to read/write foobar style
        # https://github.com/quodlibet/quodlibet/issues/1027
        song = self.KIND(self.filename)
        song["replaygain_track_gain"] = "-6 db"
        song["replaygain_track_peak"] = "0.9"
        song["replaygain_album_gain"] = "3 db"
        song["replaygain_album_peak"] = "0.8"
        song.write()

        f = mutagen.File(self.filename)
        for k in ["track_peak", "track_gain", "album_peak", "album_gain"]:
            assert f[f"TXXX:REPLAYGAIN_{k.upper()}"]

    def test_foobar2k_rg_caseinsensitive(self):
        f = mutagen.File(self.filename)
        f.tags.add(
            mutagen.id3.TXXX(encoding=3, desc="REPLAYGAIN_TRACK_GAIN", text=["-6 db"])
        )
        f.save()
        song = self.KIND(self.filename)
        self.assertEqual(song("replaygain_track_gain"), "-6 db")
        song.write()
        f = mutagen.File(self.filename)
        frames = f.tags.getall("TXXX:REPLAYGAIN_TRACK_GAIN")
        assert frames
        self.assertEqual(frames[0].desc, "REPLAYGAIN_TRACK_GAIN")
        del song["replaygain_track_gain"]
        song.write()
        f = mutagen.File(self.filename)
        assert not f.tags.getall("TXXX:REPLAYGAIN_TRACK_GAIN")

    def test_quodlibet_txxx_inval(self):
        # This shouldn't happen in our namespace, but check anyway since
        # we might open the whole TXXX namespace sometime

        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="QuodLibet::valid", text=["quux"]))
        f.tags.add(
            mutagen.id3.TXXX(encoding=3, desc="QuodLibet::foo=", text=["quux", "bar"])
        )
        f.tags.add(
            mutagen.id3.COMM(
                encoding=3, desc="QuodLibet::öäü", text=["quux", "bar"], lang="aar"
            )
        )
        f.tags.add(mutagen.id3.COMM(encoding=3, desc="", text=["a"], lang="aar"))
        f.tags.add(mutagen.id3.COMM(encoding=3, desc="", text=["b"], lang="foo"))
        f.save()

        # check if all keys are valid
        for k in self.KIND(self.filename).keys():
            assert isinstance(k, str)

        song = self.KIND(self.filename)
        assert "foo=" not in song
        assert "öäü" not in song
        self.assertEqual(set(song.list("comment")), {"a", "b"})
        self.assertEqual(song("valid"), "quux")
        del song["valid"]
        song.write()

        f = mutagen.File(self.filename)
        assert f.tags.getall("TXXX:QuodLibet::foo=")
        assert not f.tags.getall("TXXX:QuodLibet::valid")
        self.assertEqual(len(f.tags.getall("COMM")), 2)
        self.assertEqual(len(f.tags.getall("COMM:")), 1)

    def test_old_comm_to_txxx(self):
        f = mutagen.File(self.filename)
        f.tags.add(
            mutagen.id3.COMM(encoding=3, desc="QuodLibet::foo", text=["a"], lang="aar")
        )
        f.save()

        song = self.KIND(self.filename)
        self.assertEqual(song("foo"), "a")
        song.write()

        f = mutagen.File(self.filename)
        self.assertEqual(f["TXXX:QuodLibet::foo"].text, ["a"])

    def test_txxx_others(self):
        f = mutagen.File(self.filename)
        t1 = mutagen.id3.TXXX(encoding=3, desc="FooBar::invalid", text="quux")
        t2 = mutagen.id3.TXXX(encoding=3, desc="FooBar::öäü", text="bar")

        f.tags.add(t1)
        f.tags.add(t2)
        f.save()

        song = self.KIND(self.filename)
        assert "invalid" not in song
        assert "öäü" not in song
        song.write()

        f = mutagen.File(self.filename)
        assert f[t1.HashKey]
        assert f[t2.HashKey]

    def test_woar(self):
        f = mutagen.File(self.filename)
        t1 = mutagen.id3.WOAR(url="http://this.is.a.test")
        f.tags.add(t1)
        f.save()

        song = self.KIND(self.filename)
        self.assertEqual(song("website"), t1.url)
        song["website"] = "http://another.test\nhttp://omg.another.one"
        song.write()

        f = mutagen.File(self.filename)
        self.assertEqual(len(f.tags.getall("WOAR")), 2)

    def test_unhandled(self):
        f = mutagen.File(self.filename)
        t1 = mutagen.id3.AENC(owner="x", preview_start=1, preview_length=3)
        f.tags.add(t1)
        f.save()

        self.KIND(self.filename)

    def test_encoding(self):
        song = self.KIND(self.filename)
        song["foo"] = "öäü"
        song["bar"] = "abc"
        song["comment"] = "öäü"
        song["artist"] = "xyz"
        song["album"] = "öäü"
        song["tracknumber"] = "ö"
        song["discnumber"] = "9"
        song.write()

        f = mutagen.File(self.filename)
        self.assertEqual(f.tags["TXXX:QuodLibet::foo"].encoding, 1)
        self.assertEqual(f.tags["TXXX:QuodLibet::bar"].encoding, 3)
        self.assertEqual(f.tags["TPE1"].encoding, 3)
        self.assertEqual(f.tags["TALB"].encoding, 1)
        self.assertEqual(f.tags["TPE1"].encoding, 3)
        # FIXME: we shouldn't write invalid TRCK...
        self.assertEqual(f.tags["TRCK"].encoding, 1)
        self.assertEqual(f.tags["TPOS"].encoding, 3)

    def test_tcon(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TMCL(encoding=3, people=[["foo", "bar"]]))
        f.save()

        song = self.KIND(self.filename)
        assert "performer:foo" in song
        self.assertEqual(song("performer:foo"), "bar")

    def test_nonascii_unsup_tcon(self):
        people = [["a=", "a"], ["b~", "b"], ["äöü", "u"], ["quux", "x"]]
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TMCL(encoding=3, people=people))
        f.save()

        # we only support one of them
        self.assertEqual(len(self.KIND(self.filename).list("~performer")), 1)

        # but after writing they should still be there
        song = self.KIND(self.filename)
        song.write()
        f = mutagen.File(self.filename)
        self.assertEqual(len(f.tags["TMCL"].people), 4)
        self.assertEqual(f.tags["TMCL"].people, people)

        # also change something..
        song["performer:quux"] = "foo"
        song.write()
        f = mutagen.File(self.filename)
        self.assertEqual(dict(f.tags["TMCL"].people)["quux"], "foo")

    def test_rva_large(self):
        song = self.KIND(self.filename)
        song["replaygain_track_peak"] = "3"
        song["replaygain_track_gain"] = "100"
        song.write()
        song["replaygain_track_peak"] = "-1"
        song["replaygain_track_gain"] = "-100"
        song.write()

    def test_rva(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.RVA2(desc="track", channel=1, gain=-3, peak=1.0))
        f.tags.add(mutagen.id3.RVA2(desc="album", channel=1, gain=-6, peak=1.0))
        f.save()

        song = self.KIND(self.filename)
        self.assertAlmostEqual(song.replay_gain(["track"]), 0.7, 1)
        self.assertAlmostEqual(song.replay_gain(["album"]), 0.5, 1)
        song.write()

        f = mutagen.File(self.filename)
        self.assertEqual(len(f.tags.getall("RVA2")), 2)

    def test_rva_unknown(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.RVA2(desc="track", channel=2, gain=-6, peak=1.0))
        f.tags.add(mutagen.id3.RVA2(desc="foo", channel=1, gain=-3, peak=1.0))
        f.save()

        # we use foo as track if nothing else is there
        song = self.KIND(self.filename)
        self.assertAlmostEqual(song.replay_gain(["track"]), 0.7, 1)
        song.write()

        # and we write that over track..
        f = mutagen.File(self.filename)
        self.assertAlmostEqual(f.tags["RVA2:track"].gain, -3.0, 1)

        # now that one is there, ignore foo
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.RVA2(desc="foo", channel=1, gain=0, peak=1.0))
        f.save()
        song = self.KIND(self.filename)
        self.assertAlmostEqual(song.replay_gain(["track"]), 0.7, 1)

    def test_rva_inval(self):
        song = self.KIND(self.filename)
        song["replaygain_track_peak"] = "0.1afasf"
        song["replaygain_track_gain"] = "0.1afasf"
        song.write()

    def test_without_id3_tag(self):
        f = mutagen.File(self.filename)
        f.delete()
        f.save()
        song = self.KIND(self.filename)
        song.get_primary_image()
        song.write()

    def test_distrust_latin1(self):
        x = "Å"

        # abuse mutagen a bit, and get some utf-8 in with the wrong encoding
        f = mutagen.File(self.filename)
        f.tags.add(
            mutagen.id3.TPE1(encoding=0, text=x.encode("utf-8").decode("latin-1"))
        )
        f.save()

        # back to utf-8
        song = self.KIND(self.filename)
        self.assertEqual(song("artist"), x)
        song.write()

        # because it's not ascii, saved as utf-16
        f = mutagen.File(self.filename)
        self.assertEqual(f.tags["TPE1"].encoding, 1)

        # and now latin-1 that is not decodable using utf-8/16
        x = "äöü".encode("ibm1026").decode("latin-1")
        f.tags.add(mutagen.id3.TPE1(encoding=0, text=x))
        f.save()

        self.assertEqual(self.KIND(self.filename)("artist"), x)

    def test_handled_txxx_encoding(self):
        song = self.KIND(self.filename)
        song["albumartistsort"] = "Dvo\u0159\xe1k, Anton\xedn"
        song["replaygain_track_peak"] = "Dvo\u0159\xe1k, Anton\xedn"
        song.write()

    def test_albumartistsort(self):
        song = self.KIND(self.filename)
        song["albumartistsort"] = "foo"
        song.write()
        song = self.KIND(self.filename)
        self.assertEqual(song["albumartistsort"], "foo")


class TID3FileMP3(TID3FileBase, TID3FileMixin):
    KIND = MP3File
    PATH = get_data_path("silence-44-s.mp3")


class TID3FileAIFF(TID3FileBase, TID3FileMixin):
    KIND = AIFFFile
    PATH = get_data_path("test.aiff")
