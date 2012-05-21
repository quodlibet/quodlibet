# Copyright 2007 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

global device, backend
backend = None
playlist = None

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

def quit(dev):
    global backend, device, playlist
    dev.destroy()
    del(backend)
    del(device)
    del(playlist)

def init_device(librarian):
    global playlist, device
    playlist = device = backend.init(librarian)
    return device

def can_play_uri(uri):
    """Returns True if the player can play a stream at specified uri."""
    if backend is not None:
        return backend.can_play_uri(uri)
    return True
