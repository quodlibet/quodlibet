# Copyright 2004 Joe Wreschnig. Licensed under the GNU GPL version 2.

import os
import ctypes

_modplug = ctypes.cdll.LoadLibrary("libmodplug.so.0")
_modplug.ModPlug_GetName.restype = ctypes.c_char_p

class ModFile(object):
    """A loaded MOD file.

    The length and current position in milliseconds are stored
    as ModFile.length and ModFile.position. The title is stored as
    ModFile.title."""

    length = 0
    position = 0
    title = None
    __f = None

    def __init__(self, filename, playback=True):
        """If playback is true, then the file will be kept open
        for further calls to ModFile.read/ModFile.seek. Otherwise, the
        length and title will be read and the file will be closed.

        If no title is found the filename is used instead."""
        size = os.path.getsize(filename)
        data = file(filename).read()
        f = _modplug.ModPlug_Load(data, len(data))
        self.length = _modplug.ModPlug_GetLength(f)
        self.title = _modplug.ModPlug_GetName(f) or os.path.basename(filename)
        if playback: self.__f = f

    def seek(self, ms):
        """Seek to a position in milliseconds."""
        if self.__f is None: raise ArgumentError("not open for playback")
        elif ms <= self.length:
            _modplug.ModPlug_Seek(self.__f, int(ms))
            self.position = int(ms)
        else: raise IOError("attempt to seek past end of file")

    def read(self, size=1024):
        """Read and return audio data, up to ''size'' bytes."""
        if self.__f is None: raise ArgumentError("not open for playback")
        buffer = ctypes.create_string_buffer(size)
        buffer_len = _modplug.ModPlug_Read(self.__f, buffer, size)
        if buffer_len == 0: return ""
        else:
            self.position += buffer_len / 176.4
            return buffer[:buffer_len]
            

    def __del__(self):
        if self.__f is not None: _modplug.ModPlug_Unload(self.__f)

    def __repr__(s):
        return "<%s length=%r name=%r>" % (type(s).__name__, s.length, s.name)
