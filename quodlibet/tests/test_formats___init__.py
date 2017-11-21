# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys

from senf import fsnative

from tests import TestCase, get_data_path
from .helper import capture_output

from quodlibet import formats
from quodlibet.formats import AudioFile, load_audio_files, dump_audio_files, \
    SerializationError
from quodlibet.compat import PY3, long
from quodlibet.util.picklehelper import pickle_dumps
from quodlibet import config


class TFormats(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_presence(self):
        self.failUnless(formats.aac)
        self.failUnless(formats.aiff)
        self.failUnless(formats.midi)
        self.failUnless(formats.mod)
        self.failUnless(formats.monkeysaudio)
        self.failUnless(formats.mp3)
        self.failUnless(formats.mp4)
        self.failUnless(formats.mpc)
        self.failUnless(formats.spc)
        self.failUnless(formats.trueaudio)
        self.failUnless(formats.vgm)
        self.failUnless(formats.wav)
        self.failUnless(formats.wavpack)
        self.failUnless(formats.wma)
        self.failUnless(formats.xiph)

    def test_loaders(self):
        self.failUnless(formats.loaders[".mp3"] is formats.mp3.MP3File)

    def test_migration(self):
        self.failUnless(formats.mp3 is sys.modules["quodlibet.formats.mp3"])
        self.failUnless(formats.mp3 is sys.modules["quodlibet/formats/mp3"])
        self.failUnless(formats.mp3 is sys.modules["formats.mp3"])

        self.failUnless(formats.xiph is sys.modules["formats.flac"])
        self.failUnless(formats.xiph is sys.modules["formats.oggvorbis"])

    def test_filter(self):
        self.assertTrue(formats.filter("foo.mp3"))
        self.assertFalse(formats.filter("foo.doc"))
        self.assertFalse(formats.filter("foomp3"))

    def test_music_file(self):
        path = get_data_path('silence-44-s.mp3')
        self.assertTrue(formats.MusicFile(path))

        # non existing
        with capture_output() as (stdout, stderr):
            song = formats.MusicFile(get_data_path("nope.mp3"))
            self.assertFalse(song)
            self.assertTrue(stderr.getvalue())

        # unknown extension
        with capture_output() as (stdout, stderr):
            song = formats.MusicFile(get_data_path("nope.xxx"))
            self.assertFalse(song)
            self.assertFalse(stderr.getvalue())


class TPickle(TestCase):

    def setUp(self):
        types = formats.types
        instances = []
        for t in types:
            i = AudioFile.__new__(t)
            # we want to pickle/unpickle everything, since historically
            # these things ended up in the file
            dict.__init__(
                i, {b"foo": u"bar", u"quux": b"baz", "a": "b",
                    u"b": 42, "c": 0.25})
            instances.append(i)
        self.instances = instances

    def test_load_audio_files(self):
        for protocol in [0, 1, 2]:
            data = pickle_dumps(self.instances, protocol)
            items = load_audio_files(data)
            assert len(items) == len(formats.types)
            assert all(isinstance(i, AudioFile) for i in items)

    def test_sanitized_py3(self):
        i = AudioFile.__new__(list(formats.types)[0])
        # this is something that old py2 versions could pickle
        dict.__init__(i, {
            b"bytes": b"bytes",
            u"unicode": u"unicode",
            b"~filename": b"somefile",
            u"~mountpoint": u"somemount",
            u"int": 42,
            b"float": 1.25,
        })
        data = pickle_dumps([i], 1)
        items = load_audio_files(data, process=True)
        i = items[0]

        if not PY3:
            return

        assert i["bytes"] == "bytes"
        assert i["unicode"] == "unicode"
        assert isinstance(i["~filename"], fsnative)
        assert isinstance(i["~mountpoint"], fsnative)
        assert i["int"] == 42
        assert i["float"] == 1.25

    def test_sanitize_py2_normal(self):
        if PY3:
            return

        af = AudioFile({
            b"foo": u"bar",
            u"öäü": u"bla",
            "~#num": 1,
            "~#num2": long(2),
            "~#num3": 1.25,
            "~filename": fsnative(u"filename"),
            "~mountpoint": fsnative(u"mount"),
            "~somethingdifferent": u"hello",
        })

        data = dump_audio_files([af])
        new = load_audio_files(data)
        assert dict(new[0]) == dict(af)

    def test_sanitize_py2_fixup(self):
        if PY3:
            return

        old = dict.__new__(AudioFile)
        dict.__init__(old, {
            b"foo": b"bar",
            u"öäü": b"bla",
            "~#num": u"1",
            "~#num2": u"1.25",
            "~#num3": u"bla",
            "~filename": u"text",
            "~mountpoint": b"bytes",
            "~somethingdifferent": b"hello",
        })

        fixed = {
            b"foo": u"bar",
            u"öäü": u"bla",
            "~#num": 1,
            "~#num2": 1.25,
            "~#num3": 0,
            "~filename": fsnative(u"text"),
            "~mountpoint": fsnative(u"bytes"),
            "~somethingdifferent": u"hello",
        }

        data = dump_audio_files([old])
        new = load_audio_files(data)
        assert dict(new[0]) == fixed
        for v1, v2 in zip(sorted(new[0].values()), sorted(fixed.values())):
            assert type(v1) is type(v2)

    def test_dump_audio_files(self):
        data = dump_audio_files(self.instances, process=False)
        items = load_audio_files(data, process=False)

        assert len(items) == len(self.instances)
        for a, b in zip(items, self.instances):
            a = dict(a)
            b = dict(b)
            for key in a:
                assert b[key] == a[key]
            for key in b:
                assert b[key] == a[key]

    def test_save_ascii_keys_as_bytes_on_py3(self):
        i = AudioFile.__new__(list(formats.types)[0])
        dict.__setitem__(i, u"foo", u"bar")
        data = dump_audio_files([i], process=True)
        if PY3:
            items = load_audio_files(data, process=False)
            assert isinstance(list(items[0].keys())[0], bytes)

    def test_dump_empty(self):
        data = dump_audio_files([])
        assert load_audio_files(data) == []

    def test_load_audio_files_missing_class(self):
        for protocol in [0, 1, 2]:
            data = pickle_dumps(self.instances, protocol)

            items = load_audio_files(data)
            self.assertEqual(len(items), len(formats.types))
            assert all(isinstance(i, AudioFile) for i in items)

            broken = data.replace(b"SPCFile", b"FooFile")
            items = load_audio_files(broken)
            self.assertEqual(len(items), len(formats.types) - 1)
            assert all(isinstance(i, AudioFile) for i in items)

            broken = data.replace(b"formats.spc", b"formats.foo")
            items = load_audio_files(broken)
            self.assertEqual(len(items), len(formats.types) - 1)
            assert all(isinstance(i, AudioFile) for i in items)

    def test_unpickle_random_class(self):
        for protocol in [0, 1, 2]:
            data = pickle_dumps([42], protocol)
            with self.assertRaises(SerializationError):
                load_audio_files(data)
