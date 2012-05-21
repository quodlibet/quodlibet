from tests import TestCase, add

from quodlibet.qltk.notif import Task, TaskController

class FakeStatusBar(object):
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
        self.assertEquals(self.c.active_tasks, [])
        self.assertNotEqual(self.c.source, "")
        t1 = Task("src", "desc", controller = self.c)
        self.assertEquals(self.c.source, "src")
        self.assertEquals(self.c.active_tasks, [t1])
        t1.update(0.5)
        self.assertEquals(self.c.frac, 0.5)
        t2 = Task("src2", "desc2", controller = self.c)
        self.assertEquals(self.c.source, _("Active tasks"))
        self.assertEquals(self.c.frac, 0.25)
        Task("src3", "desc3", controller = self.c, known_length=False)
        self.assertAlmostEqual(self.c.frac, 0.5/3)
        t1.finish()
        t2.finish()
        self.assertEquals(self.c.desc, "desc3")
        self.assertEquals(self.c.frac, None)

add(TTaskController)
