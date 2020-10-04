# Copyright 2021 Michał Kaliński
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from abc import ABC, abstractmethod
import enum
import functools
import os
from queue import SimpleQueue
import shutil
from threading import Event, Thread
from traceback import format_exc
from typing import (
    Callable,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Type,
)

from gi.repository import GLib, Gtk

from quodlibet.plugins.songshelpers import each_song, is_a_file
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons
from quodlibet.util.i18n import _
from quodlibet.util.songwrapper import SongWrapper


class FileOperationsPlugin(SongsMenuPlugin):
    PLUGIN_ID = "file-operations"
    PLUGIN_NAME = _("File Operations")
    PLUGIN_DESC = _("Adds menu options to copy or move song files. "
                    "Moved songs remain in library.")
    PLUGIN_ICON = Icons.EDIT_COPY

    plugin_handles = each_song(is_a_file)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Set to CopyOperation just to have any non-None value.
        # It will be set to user-requested type when submenu item is activated.
        self.__operation_type: Type[Operation] = CopyOperation

        actions_menu = Gtk.Menu()
        self.set_submenu(actions_menu)

        copy_item = Gtk.MenuItem(_("Copy"))
        copy_item.connect("activate", self.__activate_copy)
        actions_menu.append(copy_item)

        move_item = Gtk.MenuItem(_("Move"))
        move_item.connect("activate", self.__activate_move)
        actions_menu.append(move_item)

    def plugin_songs(self, songs):
        op_params = FileOperationsFileChooser(songs).execute()

        if op_params is None:
            return

        abort_event = Event()
        feedback_widget = FeedbackWidget(abort_event, len(songs))
        feedback_queue = SimpleQueue()

        feedback_worker(
            FeedbackWorkerArguments(
                feedback_widget=feedback_widget,
                feedback_queue=feedback_queue,
            ),
        )

        operation_worker(
            OperationWorkerArguments(
                operation=self.__operation_type(op_params),
                feedback_queue=feedback_queue,
                abort_event=abort_event,
                finish_callback=self.plugin_finish,
            ),
        )

    def __activate_copy(self, _menu_item) -> None:
        self.__operation_type = CopyOperation

    def __activate_move(self, _menu_item) -> None:
        self.__operation_type = MoveOperation


def _song_filename(song: SongWrapper) -> str:
    return song("~filename")


class OperationParams(NamedTuple):
    song: SongWrapper
    target: str

    @property
    def source(self) -> str:
        return _song_filename(self.song)

    def __str__(self) -> str:
        return f"{self.source} --> {self.target}"


class FileOperationsFileChooser:
    def __init__(self, songs: Sequence[SongWrapper]) -> None:
        self._songs = songs

    def execute(self) -> Optional[List[OperationParams]]:
        dialog = self._build_dialog()
        params = None

        try:
            if dialog.run() == Gtk.ResponseType.OK:
                target = dialog.get_filename()
                params = [
                    OperationParams(song, target)
                    for song in self._songs
                ]
        finally:
            dialog.destroy()

        return params

    def _build_dialog(self):
        dialog = Gtk.FileChooserDialog(
            title=_("Select destination"),
            buttons=(
                _("Cancel"),
                Gtk.ResponseType.CANCEL,
                _("Save"),
                Gtk.ResponseType.OK,
            ),
        )

        if len(self._songs) == 1:
            dialog.set_action(Gtk.FileChooserAction.SAVE)
            dialog.set_current_name(os.path.basename(_song_filename(self._songs[0])))
        else:
            dialog.set_action(Gtk.FileChooserAction.SELECT_FOLDER)

        return dialog


class MessageKind(enum.Enum):
    INFO = enum.auto()
    ERROR = enum.auto()
    END = enum.auto()

    def with_body(self, body: str) -> "Message":
        return Message(self, body)


class Message(NamedTuple):
    kind: MessageKind
    body: str


class Operation(ABC):
    VERB = "-"

    def __init__(self, operations_params: Iterable[OperationParams]) -> None:
        self._ops_params = operations_params

    def execute(self) -> Iterator[Message]:
        for op_params in self._ops_params:
            try:
                op_params_str = str(op_params)
                self.do_operation(op_params)
                yield MessageKind.INFO.with_body(f"{self.VERB}: {op_params_str}")
            except Exception:
                yield MessageKind.ERROR.with_body(
                    f"{_('Error')}: {op_params_str}\n{format_exc()}",
                )
                break

    @staticmethod
    @abstractmethod
    def do_operation(op_params: OperationParams) -> None:
        pass


class CopyOperation(Operation):
    VERB = _("Copied")

    @staticmethod
    def do_operation(op_params: OperationParams) -> None:
        shutil.copy(op_params.source, op_params.target)


class MoveOperation(Operation):
    VERB = _("Moved")

    @staticmethod
    def do_operation(op_params: OperationParams) -> None:
        op_params.song.rename(op_params.target)


def _run_in_thread(func):
    @functools.wraps(func)
    def thread_wrapper(*args):
        thread = Thread(target=func, args=args)
        thread.start()
        return thread

    return thread_wrapper


class OperationWorkerArguments(NamedTuple):
    operation: Operation
    feedback_queue: "SimpleQueue[Message]"
    abort_event: Event
    finish_callback: Callable[[], None]


@_run_in_thread
def operation_worker(args: OperationWorkerArguments) -> None:
    for message in args.operation.execute():
        args.feedback_queue.put(message)

        if args.abort_event.is_set():
            break

    args.feedback_queue.put(MessageKind.END.with_body(_("Operations finished")))
    args.finish_callback()


def _run_in_idle(func):
    @functools.wraps(func)
    def idle_wrapper(*args):
        GLib.idle_add(func, *args)

    return idle_wrapper


class FeedbackWidget:
    def __init__(self, abort_event: Event, operations_count: int) -> None:
        self._progress_bar_step = 1 / operations_count
        self._abort_event = abort_event
        self._operations_ended = Event()

        self._window = Gtk.Window(
            type=Gtk.WindowType.TOPLEVEL,
            title=_("File Operations"),
        )
        self._window.set_default_size(800, 600)
        self._window.connect("destroy", lambda _window: self._abort_event.set())

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=3,
            homogeneous=False,
        )
        self._window.add(box)

        self._progress_bar = Gtk.ProgressBar(text=None, show_text=True)
        box.pack_start(self._progress_bar, False, False, 0)

        text_log_scroll = Gtk.ScrolledWindow()
        box.pack_start(text_log_scroll, True, True, 6)

        self._text_log = Gtk.TextView(
            cursor_visible=False,
            editable=False,
            monospace=True,
        )
        text_log_scroll.add(self._text_log)

        self._button = Gtk.Button.new_with_label(_("Abort"))
        self._button.connect("clicked", self.on_button_clicked)
        box.pack_start(self._button, False, False, 0)

        self._window.show_all()

    def on_button_clicked(self, _button) -> None:
        if self._operations_ended.is_set():
            self._window.destroy()
        else:
            self._abort_event.set()

    @_run_in_idle
    def on_info(self, message: Message) -> None:
        self._progress_bar.set_fraction(
            min(self._progress_bar.get_fraction() + self._progress_bar_step, 1),
        )
        self._log_line(message.body)

    @_run_in_idle
    def on_error(self, message: Message) -> None:
        self._log_line(message.body, "")

    @_run_in_idle
    def on_end(self, message: Message) -> None:
        self._operations_ended.set()
        self._progress_bar.set_fraction(1)
        self._log_line(message.body)
        self._button.set_label(_("Close"))

    def _log_line(self, text: str, end: str = "\n") -> None:
        log_buffer = self._text_log.get_buffer()
        log_buffer.insert(log_buffer.get_end_iter(), text + end)


class FeedbackWorkerArguments(NamedTuple):
    feedback_queue: "SimpleQueue[Message]"
    feedback_widget: FeedbackWidget


@_run_in_thread
def feedback_worker(args: FeedbackWorkerArguments) -> None:
    callbacks = {
        MessageKind.INFO: args.feedback_widget.on_info,
        MessageKind.ERROR: args.feedback_widget.on_error,
        MessageKind.END: args.feedback_widget.on_end,
    }

    while True:
        message = args.feedback_queue.get()
        callbacks[message.kind](message)

        if message.kind is MessageKind.END:
            break
