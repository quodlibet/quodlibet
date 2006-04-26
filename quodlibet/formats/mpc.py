# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gst

from formats._apev2 import APEv2File

try:
    import ctypes
    _libc = ctypes.cdll.LoadLibrary("libc.so.6")
    _mpcdec = ctypes.cdll.LoadLibrary("libmpcdec.so.3")
except: extensions = []
else:
    try: gst.element_factory_make('musepackdec')
    except: extensions = []
    else:
        extensions = [".mpc", ".mp+"]
        def _get_errno(): return ctypes.c_int.in_dll(_libc, "errno").value
        mpc_bool_t = ctypes.c_uint8
        mpc_int16_t = ctypes.c_int16
        mpc_int32_t = ctypes.c_int32
        mpc_int64_t = ctypes.c_int64
        mpc_uint16_t = ctypes.c_uint16
        mpc_uint32_t = ctypes.c_uint32
        mpc_streaminfo_off_t = mpc_int32_t

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

        _mpcdec.mpc_streaminfo_get_length.restype = ctypes.c_double

class MPCFile(APEv2File):
    format = "Musepack"

    IGNORE = APEv2File.IGNORE + [
        "replaygain_track_peak", "replaygain_album_peak",
        "replaygain_track_gain", "replaygain_album_gain"]

    def __init__(self, filename):
        super(MPCFile, self).__init__(filename)

        reader = _MPCReaderFile()

        f = _libc.fopen(filename, "r")
        if not f: raise OSError(os.strerror(_get_errno()))
        _mpcdec.mpc_reader_setup_file_reader(
            ctypes.pointer(reader), ctypes.c_void_p(f))
        info = _MPCStreamInfo()

        if _mpcdec.mpc_streaminfo_read(
            ctypes.byref(info), ctypes.byref(reader.reader)):
            raise IOError("not a valid Musepack file")

        self["~#length"] = int(
            _mpcdec.mpc_streaminfo_get_length(ctypes.byref(info)))
        self["~#bitrate"] = int(info.average_bitrate)

        track_g = "%+0.2f dB" % (info.gain_title / 100.0)
        album_g = "%+0.2f dB" % (info.gain_album / 100.0)
        track_p = str(info.peak_title / 32767.0)
        album_p = str(info.peak_album / 32767.0)
        self["replaygain_track_gain"] = track_g
        self["replaygain_track_peak"] = track_p
        self["replaygain_album_gain"] = album_g
        self["replaygain_album_peak"] = album_p
        _libc.fclose(reader.file)

        self.sanitize(filename)

info = MPCFile
