# Copyright 2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import threading
from time import sleep, time
from typing import List, Dict

from quodlibet import config
from quodlibet.ext.events.qlscrobbler import QLSubmitQueue
from quodlibet.formats import AudioFile
from quodlibet.util.picklehelper import pickle_load
from senf import fsnative
from tests import run_gtk_loop, init_fake_app, destroy_fake_app
from tests.plugin import PluginTestCase

A_SONG = AudioFile({"~filename": fsnative("fake.mp3"),
                    "artist": "Foo bar",
                    "title": "The Title"})


class TScrobbler(PluginTestCase):

    @classmethod
    def setUpClass(cls):
        config.init()
        init_fake_app()

    @classmethod
    def tearDownClass(cls):
        destroy_fake_app()
        config.quit()

    def setUp(self):
        self.mod = self.modules["QLScrobbler"]
        self.plugin = self.plugins["QLScrobbler"].cls()
        # It's a class instance, so make sure :(
        self.plugin.queue.queue.clear()
        self.SCROBBLER_CACHE_FILE = self.mod.QLSubmitQueue.SCROBBLER_CACHE_FILE
        try:
            os.unlink(self.SCROBBLER_CACHE_FILE)
        except FileNotFoundError:
            pass

    def tearDown(self):
        del self.mod

    def test_queue(self):
        queue: QLSubmitQueue = self.mod.QLSubmitQueue()
        thread = threading.Thread(target=queue.run, daemon=True)
        thread.start()
        songs = [A_SONG]
        for song in songs:
            queue.submit(song)
        assert len(queue.queue) == 1
        queue.dump_queue()

        loaded = self.load_queue()
        assert all(actual['a'] == expected["artist"]
                   and actual['t'] == expected["title"]
                   for actual, expected in zip(loaded, songs))

    def load_queue(self) -> List[Dict]:
        try:
            with open(self.SCROBBLER_CACHE_FILE, 'rb') as f:
                return pickle_load(f)
        except FileNotFoundError:
            return []

    def test_enabled_disabled(self):
        self.plugin.enabled()
        assert self.plugin._tid
        # Disable
        self.plugin.disabled()
        assert not self.plugin._tid

    def test_autosave(self):
        self.plugin.AUTOSAVE_INTERVAL = 0.1
        self.plugin.enabled()
        assert not self.load_queue()
        assert not self.plugin.queue.queue, "Queue not empty in test"
        self.plugin.queue.submit(A_SONG)
        assert len(self.plugin.queue.queue) == 1, "Song wasn't queued"

        queue = self.retry_queue()
        assert len(queue) == 1, "Queued song didn't get persisted"
        self.plugin.disabled()

    def retry_queue(self):
        """Allows GTK looks, flushing of disk buffers etc"""
        queue = None
        start = time()
        while time() - start < 2:
            run_gtk_loop()
            queue = self.load_queue()
            if queue:
                break
            sleep(0.1)
        return queue
