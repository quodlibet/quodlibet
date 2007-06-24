# Copyright 2007 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

global playlist, device, backend
playlist = None
device = None
backend = None

PlaylistPlayer = None

class error(RuntimeError):
    def __init__(self, short_desc, long_desc):
        self.short_desc = short_desc
        self.long_desc = long_desc

def init(backend_name):
    global backend
    modulename = "quodlibet.player." + backend_name

    try:
        backend = __import__(modulename, {}, {}, "quodlibet.player")
    except ImportError:
        raise error(
            _("Invalid audio backend"),
            _("The audio backend %r is not installed.") % backend_name)
    else:
        return backend

def init_device(librarian):
    global playlist, device, PlaylistPlayer
    playlist = device = backend.init(librarian)
    PlaylistPlayer = type(device)
    return device

def can_play_mime(mime):
    """Returns True if the player can play files with specified MIME type."""
    if backend is not None:
        return backend.can_play_mime(mime)
    return True

def can_play_uri(uri):
    """Returns True if the player can play a stream at specified uri."""
    if backend is not None:
        return backend.can_play_uri(uri)
    return True
