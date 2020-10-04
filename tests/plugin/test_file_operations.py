# Copyright 2021 Michał Kaliński
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from queue import SimpleQueue
from tempfile import TemporaryDirectory
import time
from threading import Event
from typing import NamedTuple
from unittest.mock import patch, create_autospec, Mock

from quodlibet.formats import AudioFile
from quodlibet.util.songwrapper import SongWrapper
from . import PluginTestCase


class _OperationSetup(NamedTuple):
    source: str
    target: str
    body: str


def _make_song(filename: str) -> SongWrapper:
    return SongWrapper(AudioFile({"~filename": filename}))


def _thread_pause() -> None:
    time.sleep(0.001)


class _BaseCases:
    class FOTestCase(PluginTestCase):
        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cls.mod = cls.modules["file-operations"]
            cls.kind = cls.plugins["file-operations"].cls

        @classmethod
        def tearDownClass(cls):
            del cls.mod
            del cls.kind
            super().tearDownClass()

    class OperationTestCase(FOTestCase):
        OPERATION_CLASS_NAME = "Operation"

        @classmethod
        def setUpClass(cls):
            super().setUpClass()
            cls.operations_setups = [
                _OperationSetup("a", "b", "abody\n"),
                _OperationSetup("one", "two", "onebody\n"),
            ]
            cls.operation_class = getattr(cls.mod, cls.OPERATION_CLASS_NAME)

        @classmethod
        def tearDownClass(cls):
            del cls.operations_setups
            del cls.operation_class
            super().tearDownClass()

        def setUp(self):
            super().setUp()
            self.temp_dir = TemporaryDirectory()
            self.temp_dir_name = os.path.basename(self.temp_dir.name)
            self.operations_params = []
            self.source_tails = []
            self.target_tails = []

            for op_setup in self.operations_setups:
                source_path = os.path.join(self.temp_dir.name, op_setup.source)
                self.operations_params.append(
                    self.mod.OperationParams(
                        _make_song(source_path),
                        os.path.join(self.temp_dir.name, op_setup.target),
                    ),
                )
                self.source_tails.append(
                    os.path.join(self.temp_dir_name, op_setup.source)
                )
                self.target_tails.append(
                    os.path.join(self.temp_dir_name, op_setup.target)
                )

                with open(source_path, "w") as source_file:
                    source_file.write(op_setup.body)

        def tearDown(self):
            self.temp_dir.cleanup()
            del self.temp_dir
            del self.temp_dir_name
            del self.operations_params
            del self.source_tails
            del self.target_tails
            super().tearDown()

        def test_operation_yields_success_messages(self):
            operation = self.operation_class(self.operations_params)
            messages = operation.execute()

            for message, source_tail, target_tail in zip(
                messages, self.source_tails, self.target_tails
            ):
                self.assertIs(message.kind, self.mod.MessageKind.INFO)
                self.assertIn(self.operation_class.VERB, message.body)
                self.assertIn(source_tail, message.body)
                self.assertIn(target_tail, message.body)

        def test_operation_yields_error_message_and_stops(self):
            exception_text = "foo bar"

            with patch.object(self.operation_class, "do_operation") as operate_mock:
                operate_mock.side_effect = Exception(exception_text)

                operation = self.operation_class(self.operations_params)
                messages = list(operation.execute())

            self.assertEqual(len(messages), 1)
            message = messages[0]
            self.assertIs(message.kind, self.mod.MessageKind.ERROR)
            self.assertIn(self.source_tails[0], message.body)
            self.assertIn(self.target_tails[0], message.body)
            self.assertIn(exception_text, message.body)


class TFOCopyOperation(_BaseCases.OperationTestCase):
    OPERATION_CLASS_NAME = "CopyOperation"

    def test_creates_copies_of_songs(self):
        operation = self.operation_class(self.operations_params)
        list(operation.execute())

        for op_params in self.operations_params:
            with open(op_params.target, "r") as target_file, \
                    open(op_params.source, "r") as source_file:
                self.assertEqual(target_file.read(), source_file.read())


class TFOMoveOperation(_BaseCases.OperationTestCase):
    OPERATION_CLASS_NAME = "MoveOperation"

    def test_moves_songs(self):
        # Sources must be cached before operation because they change during move
        sources = [op.source for op in self.operations_params]
        operation = self.operation_class(self.operations_params)
        list(operation.execute())

        for op_params, op_source, op_setup in zip(
            self.operations_params,
            sources,
            self.operations_setups,
        ):
            self.assertFalse(os.path.exists(op_source))

            with open(op_params.target, "r") as target_file:
                self.assertEqual(target_file.read(), op_setup.body)


class TFOOperationWorker(_BaseCases.FOTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.operation_messages = [
            cls.mod.MessageKind.INFO.with_body("foo"),
            cls.mod.MessageKind.ERROR.with_body("bar"),
        ]

    @classmethod
    def tearDownClass(cls):
        del cls.operation_messages
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.operation_mock = self.mock_operation()
        self.feedback_queue = SimpleQueue()
        self.abort_event = Event()
        self.finish_callback = Mock()
        self.operation_worker_args = self.mod.OperationWorkerArguments(
            operation=self.operation_mock,
            feedback_queue=self.feedback_queue,
            abort_event=self.abort_event,
            finish_callback=self.finish_callback,
        )

    def tearDown(self):
        del self.operation_mock
        del self.feedback_queue
        del self.abort_event
        del self.finish_callback
        del self.operation_worker_args
        super().tearDown()

    @classmethod
    def mock_operation(cls):
        operation = create_autospec(cls.mod.Operation, instance=True)
        operation.execute.return_value = cls.operation_messages_generator()
        return operation

    @classmethod
    def operation_messages_generator(cls):
        for message in cls.operation_messages:
            _thread_pause()
            yield message

    def drain_queue(self):
        while not self.feedback_queue.empty():
            yield self.feedback_queue.get()

    def test_puts_execute_messages_in_feedback_queue(self):
        thread = self.mod.operation_worker(self.operation_worker_args)
        thread.join()
        messages = list(self.drain_queue())

        self.assertEqual(messages[:-1], self.operation_messages)
        self.assertIs(messages[-1].kind, self.mod.MessageKind.END)

    def test_stops_execution_on_abort_flag(self):
        thread = self.mod.operation_worker(self.operation_worker_args)
        self.abort_event.set()
        thread.join()
        messages = list(self.drain_queue())

        self.assertEqual(messages[:-1], self.operation_messages[:1])
        self.assertIs(messages[-1].kind, self.mod.MessageKind.END)

    def test_calls_finish_callback_after_all_done(self):
        thread = self.mod.operation_worker(self.operation_worker_args)
        self.finish_callback.assert_not_called()

        thread.join()
        self.finish_callback.assert_called()


class TFOFeedbackWorker(_BaseCases.FOTestCase):
    def setUp(self):
        super().setUp()
        self.feedback_queue = SimpleQueue()
        self.feedback_widget = create_autospec(self.mod.FeedbackWidget, instance=True)
        self.feedback_worker_args = self.mod.FeedbackWorkerArguments(
            feedback_queue=self.feedback_queue,
            feedback_widget=self.feedback_widget,
        )

    def tearDown(self):
        del self.feedback_queue
        del self.feedback_widget
        del self.feedback_worker_args
        super().tearDown()

    def test_drains_gueue_unit_end_message_received(self):
        self.feedback_queue.put(self.mod.MessageKind.INFO.with_body("foo"))

        thread = self.mod.feedback_worker(self.feedback_worker_args)
        _thread_pause()

        self.assertTrue(self.feedback_queue.empty())
        self.assertTrue(thread.is_alive())

        self.feedback_queue.put(self.mod.MessageKind.END.with_body("bar"))

        thread.join()

        self.assertTrue(self.feedback_queue.empty())

    def test_calls_feedback_widget_on_messages(self):
        info = self.mod.MessageKind.INFO.with_body("foo")
        self.feedback_queue.put(info)
        error = self.mod.MessageKind.ERROR.with_body("bar")
        self.feedback_queue.put(error)
        end = self.mod.MessageKind.END.with_body("baz")
        self.feedback_queue.put(end)

        thread = self.mod.feedback_worker(self.feedback_worker_args)
        thread.join()

        self.feedback_widget.on_info.assert_called_with(info)
        self.feedback_widget.on_error.assert_called_with(error)
        self.feedback_widget.on_end.assert_called_with(end)
