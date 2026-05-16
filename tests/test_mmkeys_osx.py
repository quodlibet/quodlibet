# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
"""Tests for the macOS media keys backend (quodlibet/mmkeys/osx.py)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests import TestCase
from quodlibet.formats import AudioFile
from quodlibet.mmkeys._base import MMKeysAction

# Skip the entire module when pyobjc / MediaPlayer is unavailable (non-macOS).
pytest.importorskip("MediaPlayer")

from MediaPlayer import (  # noqa: E402
    MPMediaItemPropertyAlbumTitle,
    MPMediaItemPropertyArtist,
    MPMediaItemPropertyArtwork,
    MPMediaItemPropertyPlaybackDuration,
    MPMediaItemPropertyTitle,
    MPNowPlayingInfoPropertyElapsedPlaybackTime,
    MPNowPlayingInfoPropertyPlaybackRate,
)
from quodlibet.mmkeys.osx import OSXBackend, _CommandDispatcher  # noqa: E402

_MOD = "quodlibet.mmkeys.osx"


def _make_backend(callback=None):
    """Create an OSXBackend with all ObjC framework calls mocked out."""
    with (
        patch(f"{_MOD}.MPRemoteCommandCenter"),
        patch(f"{_MOD}.MPNowPlayingInfoCenter"),
    ):
        return OSXBackend("TestApp", callback or MagicMock())


class TOSXBackendNowPlaying(TestCase):
    def setUp(self):
        self.backend = _make_backend()

    def tearDown(self):
        with patch(f"{_MOD}.MPNowPlayingInfoCenter"):
            self.backend.cancel()

    def _update(self, song, position_ms=0, playing=False, artwork=None):
        """Call update_now_playing and return the dict passed to setNowPlayingInfo_."""
        mock_info_center = MagicMock()
        with (
            patch(f"{_MOD}.MPNowPlayingInfoCenter") as mock_npc,
            patch.object(OSXBackend, "_build_artwork", return_value=artwork),
        ):
            mock_npc.defaultCenter.return_value = mock_info_center
            self.backend.update_now_playing(song, position_ms, playing)
        return mock_info_center.setNowPlayingInfo_.call_args[0][0]

    def test_song_fields_in_now_playing_info(self):
        song = AudioFile(
            {
                "title": "Test Title",
                "artist": "Test Artist",
                "album": "Test Album",
                "~#length": 240,
                "~filename": "/music/test.mp3",
            }
        )
        info = self._update(song, position_ms=30000, playing=True)
        self.assertEqual(info[MPMediaItemPropertyTitle], "Test Title")
        self.assertEqual(info[MPMediaItemPropertyArtist], "Test Artist")
        self.assertEqual(info[MPMediaItemPropertyAlbumTitle], "Test Album")
        self.assertAlmostEqual(info[MPMediaItemPropertyPlaybackDuration], 240.0)
        self.assertAlmostEqual(info[MPNowPlayingInfoPropertyElapsedPlaybackTime], 30.0)

    def test_playing_sets_rate_to_one(self):
        song = AudioFile({"title": "T", "~filename": "/t.mp3"})
        info = self._update(song, playing=True)
        self.assertEqual(info[MPNowPlayingInfoPropertyPlaybackRate], 1.0)

    def test_paused_sets_rate_to_zero(self):
        song = AudioFile({"title": "T", "~filename": "/t.mp3"})
        info = self._update(song, playing=False)
        self.assertEqual(info[MPNowPlayingInfoPropertyPlaybackRate], 0.0)

    def test_position_ms_converted_to_seconds(self):
        song = AudioFile({"title": "T", "~filename": "/t.mp3"})
        info = self._update(song, position_ms=90500)
        self.assertAlmostEqual(info[MPNowPlayingInfoPropertyElapsedPlaybackTime], 90.5)

    def test_none_song_clears_info(self):
        mock_info_center = MagicMock()
        with patch(f"{_MOD}.MPNowPlayingInfoCenter") as mock_npc:
            mock_npc.defaultCenter.return_value = mock_info_center
            self.backend.update_now_playing(None, 0, False)
        info = mock_info_center.setNowPlayingInfo_.call_args[0][0]
        self.assertEqual(info[MPNowPlayingInfoPropertyPlaybackRate], 0.0)
        self.assertNotIn(MPMediaItemPropertyTitle, info)

    def test_artwork_included_when_available(self):
        mock_art = MagicMock()
        song = AudioFile({"title": "T", "~filename": "/t.mp3"})
        info = self._update(song, artwork=mock_art)
        self.assertIs(info[MPMediaItemPropertyArtwork], mock_art)

    def test_artwork_absent_when_none(self):
        song = AudioFile({"title": "T", "~filename": "/t.mp3"})
        info = self._update(song, artwork=None)
        self.assertNotIn(MPMediaItemPropertyArtwork, info)

    def test_artwork_cached_for_same_song(self):
        song = AudioFile({"title": "T", "~filename": "/t.mp3"})
        mock_info_center = MagicMock()
        with (
            patch(f"{_MOD}.MPNowPlayingInfoCenter") as mock_npc,
            patch.object(OSXBackend, "_build_artwork", return_value=None) as mock_build,
        ):
            mock_npc.defaultCenter.return_value = mock_info_center
            self.backend.update_now_playing(song, 0, True)
            self.backend.update_now_playing(song, 1000, True)
        mock_build.assert_called_once()

    def test_artwork_refreshed_on_song_change(self):
        song1 = AudioFile({"title": "A", "~filename": "/a.mp3"})
        song2 = AudioFile({"title": "B", "~filename": "/b.mp3"})
        mock_info_center = MagicMock()
        with (
            patch(f"{_MOD}.MPNowPlayingInfoCenter") as mock_npc,
            patch.object(OSXBackend, "_build_artwork", return_value=None) as mock_build,
        ):
            mock_npc.defaultCenter.return_value = mock_info_center
            self.backend.update_now_playing(song1, 0, True)
            self.backend.update_now_playing(song2, 0, True)
        self.assertEqual(mock_build.call_count, 2)


class TOSXBuildArtwork(TestCase):
    def _make_song(self, dirname, embedded_data=None):
        song = MagicMock()
        song.side_effect = (
            lambda key, default="": dirname if key == "~dirname" else default
        )
        if embedded_data is not None:
            mock_img = MagicMock()
            mock_img.read.return_value = embedded_data
            song.get_primary_image.return_value = mock_img
        else:
            song.get_primary_image.return_value = None
        return song

    def test_returns_none_when_no_image_and_no_cover_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            song = self._make_song(tmpdir)
            result = OSXBackend._build_artwork(song)
        self.assertIsNone(result)

    def test_uses_embedded_image(self):
        mock_ns_image = MagicMock()
        mock_artwork = MagicMock()
        song = self._make_song("/music", embedded_data=b"\xff\xd8")
        with (
            patch(f"{_MOD}.NSImage") as mock_NSImage,
            patch(f"{_MOD}.MPMediaItemArtwork") as mock_MPArtwork,
        ):
            mock_NSImage.alloc.return_value.initWithData_.return_value = mock_ns_image
            artwork_factory = mock_MPArtwork.alloc.return_value
            init_artwork = artwork_factory.initWithBoundsSize_requestHandler_
            init_artwork.return_value = mock_artwork
            result = OSXBackend._build_artwork(song)
        self.assertIs(result, mock_artwork)

    def test_falls_back_to_cover_jpg(self):
        mock_ns_image = MagicMock()
        mock_artwork = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "cover.jpg").touch()
            song = self._make_song(tmpdir)
            with (
                patch(f"{_MOD}.NSImage") as mock_NSImage,
                patch(f"{_MOD}.MPMediaItemArtwork") as mock_MPArtwork,
            ):
                mock_NSImage.alloc.return_value.initWithContentsOfFile_.return_value = (
                    mock_ns_image
                )
                artwork_factory = mock_MPArtwork.alloc.return_value
                init_artwork = artwork_factory.initWithBoundsSize_requestHandler_
                init_artwork.return_value = mock_artwork
                result = OSXBackend._build_artwork(song)
        self.assertIs(result, mock_artwork)

    def test_prefers_embedded_over_cover_file(self):
        mock_artwork = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "cover.jpg").touch()
            song = self._make_song(tmpdir, embedded_data=b"\xff\xd8")
            with (
                patch(f"{_MOD}.NSImage") as mock_NSImage,
                patch(f"{_MOD}.MPMediaItemArtwork") as mock_MPArtwork,
            ):
                mock_NSImage.alloc.return_value.initWithData_.return_value = MagicMock()
                artwork_factory = mock_MPArtwork.alloc.return_value
                init_artwork = artwork_factory.initWithBoundsSize_requestHandler_
                init_artwork.return_value = mock_artwork
                OSXBackend._build_artwork(song)
            # initWithContentsOfFile_ should never have been called
            mock_NSImage.alloc.return_value.initWithContentsOfFile_.assert_not_called()

    def test_returns_none_on_exception(self):
        song = self._make_song("/music", embedded_data=b"\xff\xd8")
        with patch(f"{_MOD}.NSImage") as mock_NSImage:
            mock_NSImage.alloc.side_effect = RuntimeError("ObjC error")
            result = OSXBackend._build_artwork(song)
        self.assertIsNone(result)


class TOSXCommandDispatcher(TestCase):
    def setUp(self):
        self.dispatcher = _CommandDispatcher.alloc().init()
        self.received = []
        self.dispatcher._callback = lambda *args: self.received.append(args)

    def _fire(self, command_key, action, position_time=None):
        self.dispatcher._dispatch[command_key] = action
        mock_event = MagicMock()
        mock_event.command.return_value = command_key
        if position_time is not None:
            mock_event.positionTime.return_value = position_time
        with patch(f"{_MOD}.GLib") as mock_glib:
            mock_glib.idle_add.side_effect = lambda fn, *args: fn(*args)
            self.dispatcher.handle_command_(mock_event)

    def test_dispatches_next(self):
        self._fire(object(), MMKeysAction.NEXT)
        self.assertEqual(self.received, [(MMKeysAction.NEXT,)])

    def test_dispatches_playpause(self):
        self._fire(object(), MMKeysAction.PLAYPAUSE)
        self.assertEqual(self.received, [(MMKeysAction.PLAYPAUSE,)])

    def test_seek_passes_position(self):
        self._fire(object(), MMKeysAction.SEEK, position_time=42.5)
        self.assertEqual(self.received, [(MMKeysAction.SEEK, 42.5)])

    def test_unknown_command_is_ignored(self):
        mock_event = MagicMock()
        mock_event.command.return_value = object()
        with patch(f"{_MOD}.GLib"):
            self.dispatcher.handle_command_(mock_event)
        self.assertEqual(self.received, [])

    def test_no_callback_does_not_raise(self):
        cmd = object()
        self.dispatcher._dispatch[cmd] = MMKeysAction.NEXT
        self.dispatcher._callback = None
        mock_event = MagicMock()
        mock_event.command.return_value = cmd
        with patch(f"{_MOD}.GLib"):
            self.dispatcher.handle_command_(mock_event)
