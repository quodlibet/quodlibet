from tests import TestCase, add

import os
import sys
import shutil
import tempfile
import py_compile

from quodlibet.util.modulescanner import *


class TModuleScanner(TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp("ql-mod")

    def _create_mod(self, name, package=None):
        if package is not None:
            base = os.path.join(self.d, package)
        else:
            base = self.d
        return open(os.path.join(base, name), "wb")

    def _create_pkg(self, name):
        base = os.path.join(self.d, name)
        os.mkdir(base)
        return open(os.path.join(base, "__init__.py"), "wb")

    def tearDown(self):
        shutil.rmtree(self.d)

    def test_importables(self):
        self.failUnlessEqual(list(get_importables(self.d)), [])
        h = self._create_mod("foo.py")
        h.close()
        self.failUnlessEqual(list(get_importables(self.d))[0],
                             (h.name, [h.name]))

    def test_importables_package(self):
        self.failUnlessEqual(list(get_importables(self.d)), [])
        h = self._create_pkg("foobar")
        self.failUnlessEqual(list(get_importables(self.d))[0],
                             (os.path.dirname(h.name), [h.name]))
        h.close()

    def test_load_dir_modules(self):
        h = self._create_mod("x.py")
        h.write("test=42\n")
        h.close()
        mods = load_dir_modules(self.d, "foo.bar")
        self.failUnlessEqual(len(mods), 1)
        self.failUnlessEqual(mods[0].test, 42)

    def test_load_dir_modules_compiled_ignore(self):
        h = self._create_mod("x1.py")
        h.write("test=24\n")
        h.close()
        py_compile.compile(h.name)
        os.unlink(h.name)
        self.failUnlessEqual(os.listdir(self.d), ["x1.pyc"])

        mods = load_dir_modules(self.d, "foo.bar")
        self.failUnlessEqual(len(mods), 0)


    def test_load_dir_modules_compiled(self):
        h = self._create_mod("x1.py")
        h.write("test=99\n")
        h.close()
        py_compile.compile(h.name)
        os.unlink(h.name)
        self.failUnlessEqual(os.listdir(self.d), ["x1.pyc"])

        mods = load_dir_modules(self.d, "foo.bar", load_compiled=True)
        self.failUnlessEqual(len(mods), 1)
        self.failUnlessEqual(mods[0].test, 99)

    def test_scanner_add(self):
        self._create_mod("q1.py").close()
        self._create_mod("q2.py").close()
        s = ModuleScanner([self.d])
        self.failIf(s.modules)
        removed, added = s.rescan()
        self.failIf(removed)
        self.failUnlessEqual(set(added), set(["q1", "q2"]))
        self.failUnlessEqual(len(s.modules), 2)
        self.failUnlessEqual(len(s.failures), 0)

    def test_scanner_remove(self):
        h = self._create_mod("q3.py")
        h.close()
        s = ModuleScanner([self.d])
        s.rescan()
        os.remove(h.name)
        removed, added = s.rescan()
        self.failIf(added)
        self.failUnlessEqual(removed, ["q3"])
        self.failUnlessEqual(len(s.modules), 0)
        self.failUnlessEqual(len(s.failures), 0)

    def test_scanner_error(self):
        h = self._create_mod("q4.py")
        h.write("1syntaxerror\n")
        h.close()
        s = ModuleScanner([self.d])
        removed, added = s.rescan()
        self.failIf(added)
        self.failIf(removed)
        self.failUnlessEqual(len(s.failures), 1)
        self.failUnless("q4" in s.failures)

add(TModuleScanner)
