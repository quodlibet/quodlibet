# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet import _
from quodlibet.qltk.notif import Task, TaskController


class FakeStatusBar:
    def __init__(self):
        self.count = 0

    def update(self):
        self.count += 1


class TTaskController(TestCase):
    def setUp(self):
        self.c = TaskController()
        self.f = FakeStatusBar()
        self.c.parent = self.f

    def test_reparent(self):
        def set_parent(p):
            self.c.parent = p

        set_parent(None)
        set_parent(FakeStatusBar())
        self.assertRaises(ValueError, set_parent, FakeStatusBar())

    def test_multiple_tasks(self):
        self.assertEqual(self.c.active_tasks, [])
        self.assertNotEqual(self.c.source, "")
        t1 = Task("src", "desc", controller=self.c)
        self.assertEqual(self.c.source, "src")
        self.assertEqual(self.c.active_tasks, [t1])
        t1.update(0.5)
        self.assertEqual(self.c.frac, 0.5)
        t2 = Task("src2", "desc2", controller=self.c)
        self.assertEqual(self.c.source, _("Active tasks"))
        self.assertEqual(self.c.frac, 0.25)
        Task("src3", "desc3", controller=self.c, known_length=False)
        self.assertAlmostEqual(self.c.frac, 0.5 / 3)
        t1.finish()
        t2.finish()
        self.assertEqual(self.c.desc, "desc3")
        self.assertEqual(self.c.frac, None)
