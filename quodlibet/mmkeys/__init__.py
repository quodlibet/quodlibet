# Copyright 2014 Christoph Reiter
#           2018 Ludovic Druette
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import config
from quodlibet.util import print_d

from ._base import MMKeysAction, MMKeysImportError


def iter_backends():
    if config.getboolean("settings", "disable_mmkeys"):
        return

    try:
        from .gnome import GnomeBackend, GnomeBackendOldName, MateBackend
    except MMKeysImportError:
        pass
    else:
        yield GnomeBackend
        yield GnomeBackendOldName
        yield MateBackend

    try:
        from .keybinder import KeybinderBackend
    except MMKeysImportError:
        pass
    else:
        yield KeybinderBackend

    try:
        from .winhook import WinHookBackend
    except MMKeysImportError:
        pass
    else:
        yield WinHookBackend

    try:
        from .osx import OSXBackend
    except MMKeysImportError:
        pass
    else:
        yield OSXBackend


def find_active_backend():
    print_d("Trying to find a mmkeys backend")
    for backend in iter_backends():
        if backend.is_active():
            print_d(f"Found {backend.__name__!r}")
            return backend
    return None


class MMKeysHandler:
    """Manages multiple keybinding backends and translates the generated
    events to actions on the player backend.
    """

    def __init__(self, app):
        self._backend = None
        self._window = app.window
        self._player = app.player
        self._player_options = app.player_options
        self._app_name = app.name

    def start(self):
        kind = find_active_backend()
        if not kind:
            return
        self._backend = kind(self._app_name, self._callback)
        # grab on start for cases when the window is hidden on start
        self._backend.grab()

        self._window.connect("notify::is-active", self._focus_event)

    def quit(self):
        if self._backend:
            self._backend.cancel()
            self._backend = None
            self._window = None
            self._player = None

    def _focus_event(self, window, param):
        if window.get_property(param.name) and self._backend:
            self._backend.grab()

    def _callback(self, action):
        print_d(f"Event {action!r} from {type(self._backend).__name__!r}")

        def seek_relative(seconds):
            current = player.get_position()
            current += seconds * 1000
            current = min(player.song("~#length") * 1000 - 1, current)
            current = max(0, current)
            player.seek(current)

        player = self._player
        player_options = self._player_options
        if action == MMKeysAction.PREV:
            player.previous(force=True)
        elif action == MMKeysAction.NEXT:
            player.next()
        elif action == MMKeysAction.STOP:
            player.stop()
        elif action == MMKeysAction.PLAY:
            player.play()
        elif action == MMKeysAction.PLAYPAUSE:
            player.playpause()
        elif action == MMKeysAction.PAUSE:
            player.paused = True
        elif action == MMKeysAction.FORWARD:
            if player.song:
                seek_relative(10)
        elif action == MMKeysAction.REWIND:
            if player.song:
                seek_relative(-10)
        elif action == MMKeysAction.REPEAT:
            player_options.repeat = not player_options.repeat
        elif action == MMKeysAction.SHUFFLE:
            player_options.shuffle = not player_options.shuffle
        else:
            assert 0, "unhandled event"
