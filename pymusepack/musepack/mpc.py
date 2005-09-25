# A Musepack (MPC) decoder wrapper for Python
# Uses libmpcdec, http://www.musepack.net/index.php?pg=src
# Copyright 2005 Joe Wreschnig, Wim Speekenbrink

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

# $Id$

import os
import ctypes
from ctypes import byref

_libc = ctypes.cdll.LoadLibrary("libc.so.6")
_mpcdec = ctypes.cdll.LoadLibrary("libmpcdec.so.3")

mpc_bool_t = ctypes.c_ubyte
mpc_int16_t = ctypes.c_short
mpc_int32_t = ctypes.c_int
mpc_int64_t = ctypes.c_longlong
mpc_uint16_t = ctypes.c_ushort
mpc_uint32_t = ctypes.c_uint
mpc_streaminfo_off_t = mpc_int32_t

def _get_errno(): return ctypes.c_int.in_dll(_libc, "errno").value

class _MPCReader(ctypes.Structure):
    _fields_ = [('read', ctypes.c_void_p),
                ('seek', ctypes.c_void_p),
                ('tell', ctypes.c_void_p),
                ('get_size', ctypes.c_void_p),
                ('canseek', ctypes.c_void_p),
                # Actually, all the above are function pointers
                ('data', ctypes.c_void_p)
                ]

class _MPCReaderFile(ctypes.Structure):
    _fields_ = [("reader", _MPCReader),
                ("file", ctypes.c_void_p), # actually FILE*
                ("file_size", ctypes.c_long),
                ("is_seekable", mpc_bool_t)]

class _MPCStreamInfo(ctypes.Structure):
    _fields_ = [("sample_freq", mpc_uint32_t),
                ("channels", mpc_uint32_t),
                ("header_position", mpc_streaminfo_off_t),
                ("stream_version", mpc_uint32_t),
                ("bitrate", mpc_uint32_t),
                ("average_bitrate", ctypes.c_double),
                ("frames", mpc_uint32_t),
                ("pcm_samples", mpc_int64_t),
                ("max_band", mpc_uint32_t),
                ("istereo", mpc_uint32_t), # 'is' is a Python keyword
                ('ms', mpc_uint32_t),
                ("block_size", mpc_uint32_t),
                ("profile", mpc_uint32_t),
                ("profile_name", ctypes.c_char_p),
                ("gain_title", mpc_int16_t),
                ("gain_album", mpc_int16_t),
                ("peak_title", mpc_uint16_t),
                ("peak_album", mpc_uint16_t),

                ("is_true_gapless", mpc_uint32_t),
                ("last_frame_samples", mpc_uint32_t),
                ("encoder_version", mpc_uint32_t),
                ("encoder", ctypes.c_char * 256),
                ("tag_offset", mpc_streaminfo_off_t),
                ("total_file_length", mpc_streaminfo_off_t),
                ]

_mpcdec.mpc_reader_setup_file_reader.argtypes = [
    ctypes.POINTER(_MPCReaderFile), ctypes.c_void_p]

_mpcdec.mpc_streaminfo_read.argtypes = [
    ctypes.POINTER(_MPCStreamInfo), ctypes.POINTER(_MPCReader)]

class MPCFile(ctypes.Structure):
    position = 0
    __reader = None

    def __init__(self, filename):
        reader = _MPCReaderFile()
        f = _libc.fopen(filename, "r")
        if not f: raise OSError(os.strerror(_get_errno()))
        _mpcdec.mpc_reader_setup_file_reader(
            ctypes.pointer(reader), ctypes.c_void_p(f))

        self.__reader = reader

        info = _MPCStreamInfo()

        if _mpcdec.mpc_streaminfo_read(
            ctypes.byref(info), ctypes.byref(reader.reader)):
            raise IOError("not a valid Musepack file")

        self.frequency = info.sample_freq
        self.channels = info.channels
        self.frames = info.frames
        self.bitrate = info.average_bitrate
        self.samples = info.pcm_samples
        self.stream_version = info.stream_version
        self.encoder = info.encoder
        self.encoder_version = info.encoder_version
        self.profile = info.profile
        self.profile_name = info.profile_name
        self.gain_radio = info.gain_title
        self.gain_audiophile = info.gain_album
        self.peak_radio = info.peak_title
        self.peak_audiophile = info.peak_album
        self.length = int(self.samples / (self.frequency / 1000.0))
        #self.length = _mpcdec.mpc_streaminfo_get_length(ctypes.byref(info))
        #self.length *= 1000

    def __del__(self):
        if self.__reader and self.__reader.file:
            _libc.fclose(self.__reader.file)
