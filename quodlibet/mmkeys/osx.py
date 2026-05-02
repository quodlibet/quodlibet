# Copyright 2012 Martijn Pieters <mj@zopatista.com>
# Copyright 2014 Eric Le Lay elelay.fr:dev
# Copyright 2025 Jost Schulte
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
osxmmkey - Mac OS X Media Keys support via MPRemoteCommandCenter
----------------------------------------------------------------

Requires pyobjc-framework-MediaPlayer to be installed.

Media key routing is handled by the system — multiple apps coexist correctly
and no Accessibility permission is required.
"""

from gi.repository import GLib

from ._base import MMKeysBackend, MMKeysAction, MMKeysImportError

try:
    import objc
    from AppKit import NSImage
    from Foundation import NSObject
    from MediaPlayer import (
        MPMediaItemArtwork,
        MPMediaItemPropertyAlbumTitle,
        MPMediaItemPropertyArtist,
        MPMediaItemPropertyArtwork,
        MPMediaItemPropertyPlaybackDuration,
        MPMediaItemPropertyTitle,
        MPNowPlayingInfoCenter,
        MPNowPlayingInfoPropertyElapsedPlaybackTime,
        MPNowPlayingInfoPropertyPlaybackRate,
        MPRemoteCommandCenter,
        MPRemoteCommandHandlerStatusSuccess,
    )
except ImportError as e:
    raise MMKeysImportError from e

# Provide block type metadata that pyobjc-framework-MediaPlayer may not include.
# Arguments: 0=self, 1=SEL, 2=boundsSize, 3=requestHandler (block).
objc.registerMetaDataForSelector(
    b"MPMediaItemArtwork",
    b"initWithBoundsSize:requestHandler:",
    {
        "arguments": {
            3: {
                "callable": {
                    "retval": {"type": b"@"},
                    "arguments": {
                        0: {"type": b"^v"},
                        1: {"type": b"{CGSize=dd}"},
                    },
                }
            }
        }
    },
)


class _CommandDispatcher(NSObject):
    # NSObject subclass used as target for addTarget_action_. One instance is
    # shared across all commands; the fired command is identified via its
    # pointer, looked up in _dispatch.

    def init(self):
        self = objc.super(_CommandDispatcher, self).init()
        if self is None:
            return None
        self._dispatch = {}
        self._callback = None
        return self

    def handle_command_(self, event):
        action = self._dispatch.get(event.command())
        if action is not None and self._callback is not None:
            if action == MMKeysAction.SEEK:
                GLib.idle_add(self._callback, action, event.positionTime())
            else:
                GLib.idle_add(self._callback, action)
        return MPRemoteCommandHandlerStatusSuccess

    # Explicit ObjC selector name preserves the camelCase selector that
    # addTarget_action_ registers against, while keeping the Python name lowercase.
    handle_command_ = objc.selector(
        handle_command_, selector=b"handleCommand:", signature=b"q@:@"
    )


class OSXBackend(MMKeysBackend):
    def __init__(self, name, callback):
        self._dispatcher = _CommandDispatcher.alloc().init()
        self._dispatcher._callback = callback
        center = MPRemoteCommandCenter.sharedCommandCenter()
        self._commands = []
        self._art_song_key = None
        self._art = None

        MPNowPlayingInfoCenter.defaultCenter().setNowPlayingInfo_(
            {MPNowPlayingInfoPropertyPlaybackRate: 0.0}
        )

        self._register(center.togglePlayPauseCommand(), MMKeysAction.PLAYPAUSE)
        self._register(center.nextTrackCommand(), MMKeysAction.NEXT)
        self._register(center.previousTrackCommand(), MMKeysAction.PREV)
        self._register(center.stopCommand(), MMKeysAction.STOP)
        self._register(center.playCommand(), MMKeysAction.PLAY)
        self._register(center.pauseCommand(), MMKeysAction.PAUSE)
        self._register(center.changePlaybackPositionCommand(), MMKeysAction.SEEK)

    def _register(self, command, action):
        command.setEnabled_(True)
        self._dispatcher._dispatch[command] = action
        command.addTarget_action_(self._dispatcher, b"handleCommand:")
        self._commands.append(command)

    @staticmethod
    def _build_artwork(song):
        try:
            embedded = song.get_primary_image()
            if embedded is not None:
                ns_image = NSImage.alloc().initWithData_(embedded.read())
                if ns_image is not None:
                    return (
                        MPMediaItemArtwork.alloc().initWithBoundsSize_requestHandler_(
                            (512.0, 512.0), lambda size: ns_image
                        )
                    )
            from pathlib import Path

            dirname = Path(song("~dirname", ""))
            for name in ("cover.jpg", "cover.png", "folder.jpg", "folder.png"):
                path = dirname / name
                if path.exists():
                    ns_image = NSImage.alloc().initWithContentsOfFile_(str(path))
                    if ns_image is not None:
                        artwork = MPMediaItemArtwork.alloc()
                        return artwork.initWithBoundsSize_requestHandler_(
                            (512.0, 512.0), lambda size, img=ns_image: img
                        )
        except Exception:
            pass
        return None

    def update_now_playing(self, song, position_ms, playing):
        if song is None:
            self._art_song_key = None
            self._art = None
            MPNowPlayingInfoCenter.defaultCenter().setNowPlayingInfo_(
                {MPNowPlayingInfoPropertyPlaybackRate: 0.0}
            )
            return
        key = song("~filename", None)
        if key != self._art_song_key:
            self._art_song_key = key
            self._art = self._build_artwork(song)
        info = {
            MPMediaItemPropertyTitle: song("title", ""),
            MPMediaItemPropertyArtist: song.comma("artist"),
            MPMediaItemPropertyAlbumTitle: song.comma("album"),
            MPMediaItemPropertyPlaybackDuration: float(song("~#length", 0)),
            MPNowPlayingInfoPropertyElapsedPlaybackTime: position_ms / 1000.0,
            MPNowPlayingInfoPropertyPlaybackRate: 1.0 if playing else 0.0,
        }
        if self._art is not None:
            info[MPMediaItemPropertyArtwork] = self._art
        MPNowPlayingInfoCenter.defaultCenter().setNowPlayingInfo_(info)

    def cancel(self):
        for command in self._commands:
            command.removeTarget_(self._dispatcher)
            command.setEnabled_(False)
        self._commands.clear()
        self._dispatcher = None
        self._art = None
        self._art_song_key = None
        MPNowPlayingInfoCenter.defaultCenter().setNowPlayingInfo_(None)
