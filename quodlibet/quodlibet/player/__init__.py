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

def init(backend_name):
    global backend
    modulename = "quodlibet.player." + backend_name
    backend = __import__(modulename, {}, {}, "quodlibet.player")
    return backend

def init_device(librarian):
    global playlist, device, PlaylistPlayer
    playlist = device = backend.init(librarian)
    PlaylistPlayer = type(device)
    return device
