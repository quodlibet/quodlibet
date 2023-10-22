# Copyright 2018 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import enum
import ctypes

from gi.repository import GLib, GObject


try:
    h = ctypes.cdll.LoadLibrary("libSM.so.6")
except OSError as e:
    raise ImportError(e) from e


@ctypes.POINTER
class SmcConn(ctypes.Structure):
    pass

SmPointer = ctypes.c_void_p
Bool = ctypes.c_int

SmcSaveYourselfProc = ctypes.CFUNCTYPE(
    None, SmcConn, SmPointer, ctypes.c_int, Bool, ctypes.c_int, Bool)
SmcDieProc = ctypes.CFUNCTYPE(None, SmcConn, SmPointer)
SmcSaveCompleteProc = ctypes.CFUNCTYPE(None, SmcConn, SmPointer)
SmcShutdownCancelledProc = ctypes.CFUNCTYPE(None, SmcConn, SmPointer)


class save_yourself(ctypes.Structure):
    _fields_ = [
        ("callback", SmcSaveYourselfProc),
        ("client_data", SmPointer),
    ]


class die(ctypes.Structure):
    _fields_ = [
        ("callback", SmcDieProc),
        ("client_data", SmPointer),
    ]


class save_complete(ctypes.Structure):
    _fields_ = [
        ("callback", SmcSaveCompleteProc),
        ("client_data", SmPointer),
    ]


class shutdown_cancelled(ctypes.Structure):
    _fields_ = [
        ("callback", SmcShutdownCancelledProc),
        ("client_data", SmPointer),
    ]


class SmcCallbacks(ctypes.Structure):
    _fields_ = [
        ("save_yourself", save_yourself),
        ("die", die),
        ("save_complete", save_complete),
        ("shutdown_cancelled", shutdown_cancelled),
    ]

SmProtoMajor = 1
SmProtoMinor = 0

SmcSaveYourselfProcMask = 1 << 0
SmcDieProcMask = 1 << 1
SmcSaveCompleteProcMask = 1 << 2
SmcShutdownCancelledProcMask = 1 << 3

SmcCloseStatus = ctypes.c_int
SmcClosedNow = 0
SmcClosedASAP = 1
SmcConnectionInUse = 2

SmcOpenConnection = h.SmcOpenConnection
SmcOpenConnection.argtypes = [
    ctypes.c_char_p, SmPointer, ctypes.c_int, ctypes.c_int, ctypes.c_ulong,
    ctypes.POINTER(SmcCallbacks), ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, ctypes.c_char_p]
SmcOpenConnection.restype = SmcConn

SmcCloseConnection = h.SmcCloseConnection
SmcCloseConnection.argtypes = [
    SmcConn, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
SmcCloseConnection.restype = SmcCloseStatus

SmcSaveYourselfDone = h.SmcSaveYourselfDone
SmcSaveYourselfDone.argtypes = [SmcConn, Bool]
SmcSaveYourselfDone.restype = None


@ctypes.POINTER
class IceConn(ctypes.Structure):
    pass

IcePointer = ctypes.c_void_p
IceWatchProc = ctypes.CFUNCTYPE(
    None, IceConn, IcePointer, Bool, ctypes.POINTER(IcePointer))

Status = ctypes.c_int

IceAddConnectionWatch = h.IceAddConnectionWatch
IceAddConnectionWatch.argtypes = [IceWatchProc, IcePointer]
IceAddConnectionWatch.restype = Status

IceRemoveConnectionWatch = h.IceRemoveConnectionWatch
IceRemoveConnectionWatch.argtypes = [IceWatchProc, IcePointer]
IceRemoveConnectionWatch.restype = None

IceConnectionNumber = h.IceConnectionNumber
IceConnectionNumber.argtypes = [IceConn]
IceConnectionNumber.restype = ctypes.c_int

IceProcessMessagesStatus = ctypes.c_int
IceProcessMessagesSuccess = 0
IceProcessMessagesIOError = 1
IceProcessMessagesConnectionClosed = 2


@ctypes.POINTER
class FIXMEPtr(ctypes.Structure):
    pass

IceProcessMessages = h.IceProcessMessages
IceProcessMessages.argtypes = [IceConn, FIXMEPtr, FIXMEPtr]
IceProcessMessages.restype = IceProcessMessagesStatus

IceSetShutdownNegotiation = h.IceSetShutdownNegotiation
IceSetShutdownNegotiation.argtypes = [IceConn, Bool]
IceSetShutdownNegotiation.restype = None

IceCloseStatus = ctypes.c_int

IceCloseConnection = h.IceCloseConnection
IceCloseConnection.argtypes = [IceConn]
IceCloseConnection.restype = IceCloseStatus


class SaveType(enum.IntEnum):
    GLOBAL = 0
    LOCAL = 1
    BOTH = 2


class InteractStyle(enum.IntEnum):
    NONE = 0
    ERRORS = 1
    ANY = 2


class XSMPError(Exception):
    pass


class XSMPSource:
    """Dispatches SM messages in the glib mainloop"""

    def __init__(self):
        self._watch_id = None
        self._watch_proc = None

    def open(self):
        if self._watch_proc is not None:
            raise XSMPError("already open")

        @IceWatchProc
        def watch_proc(conn, client_data, opening, watch_data):
            if opening:
                fd = IceConnectionNumber(conn)
                channel = GLib.IOChannel.unix_new(fd)
                self._watch_id = GLib.io_add_watch(
                    channel,
                    GLib.PRIORITY_DEFAULT,
                    (GLib.IOCondition.ERR | GLib.IOCondition.HUP |
                     GLib.IOCondition.IN),
                    self._process_func, conn)
            else:
                if self._watch_id is not None:
                    GObject.source_remove(self._watch_id)
                    self._watch_id = None

        self._watch_proc = watch_proc
        status = IceAddConnectionWatch(watch_proc, None)
        if status == 0:
            raise XSMPError(
                "IceAddConnectionWatch failed with %d" % status)

    def close(self):
        if self._watch_proc is not None:
            IceRemoveConnectionWatch(self._watch_proc, None)
            self._watch_proc = None

        if self._watch_id is not None:
            GObject.source_remove(self._watch_id)
            self._watch_id = None

    def _process_func(self, channel, condition, conn):
        status = IceProcessMessages(conn, None, None)
        if status != IceProcessMessagesSuccess:
            if status != IceProcessMessagesConnectionClosed:
                IceCloseConnection(conn)
            self._watch_id = None
            return False
        return True


class XSMPClient(GObject.Object):

    __gsignals__ = {
        "save-yourself":
            (GObject.SignalFlags.RUN_LAST, None,
             (object, object, object, object)),
        "die": (GObject.SignalFlags.RUN_LAST, None, ()),
        "save-complete": (GObject.SignalFlags.RUN_LAST, None, ()),
        "shutdown-cancelled": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super().__init__()

        self._source = None
        self._callbacks = SmcCallbacks()
        self._conn = None
        self._id = None

        def wrap_cb(func_type, cb):
            def c_callback(*args):
                return cb(self, func_type, *args[2:])
            return func_type(c_callback)

        self._callbacks.save_yourself.callback = wrap_cb(
            SmcSaveYourselfProc, self._on_save_yourself)
        self._callbacks.die.callback = wrap_cb(SmcDieProc, self._on_die)
        self._callbacks.save_complete.callback = wrap_cb(
            SmcSaveCompleteProc, self._on_save_complete)
        self._callbacks.shutdown_cancelled.callback = wrap_cb(
            SmcShutdownCancelledProc, self._on_shutdown_cancelled)

    def _on_save_yourself(self, conn, client_data, save_type, shutdown,
                          interact_style, fast):
        self.emit(
            "save-yourself", SaveType(save_type), bool(shutdown),
            InteractStyle(interact_style), bool(fast))

    def _on_die(self, conn, client_data):
        self.emit("die")

    def _on_save_complete(self, conn, client_data):
        self.emit("save-complete")

    def _on_shutdown_cancelled(self, conn, client_data):
        self.emit("shutdown-cancelled")

    @property
    def client_id(self):
        if self._conn is None:
            raise XSMPError("connection closed")
        return self._id

    def open(self):
        if self._conn is not None:
            raise XSMPError("connection already open")

        self._source = XSMPSource()
        self._source.open()

        error_string = ctypes.create_string_buffer(250)
        id_ = ctypes.c_char_p()
        self._conn = SmcOpenConnection(
            None, None, SmProtoMajor, SmProtoMinor,
            (SmcDieProcMask | SmcSaveCompleteProcMask |
             SmcSaveYourselfProcMask | SmcShutdownCancelledProcMask),
            ctypes.byref(self._callbacks), None, ctypes.byref(id_),
            len(error_string), error_string)
        # null ptr still returns an object, but its falsy
        if not self._conn:
            self._conn = None

        if self._conn is None:
            self._conn = None
            self._source.close()
            self._source = None
            raise XSMPError("open failed: %r" %
                error_string.value.decode("utf-8"))

        # FIXME: id_ should be freed with free()
        self._id = id_.value.decode("utf-8")

    def save_yourself_done(self, success):
        if self._conn is None:
            raise XSMPError("connection closed")
        SmcSaveYourselfDone(self._conn, success)

    def close(self):
        if self._conn is not None:
            SmcCloseConnection(self._conn, 0, None)
            self._conn = None
        if self._source is not None:
            self._source.close()
            self._source = None

    def __del__(self):
        self.close()
        self._callbacks = None
