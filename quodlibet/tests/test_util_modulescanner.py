# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import imp
import sys
import shutil

from quodlibet.util.modulescanner import ModuleScanner
from quodlibet.util.importhelper import get_importables, load_dir_modules

from tests import TestCase, mkdtemp


class TModuleScanner(TestCase):

    def setUp(self):
        self.d = mkdtemp("ql-mod")
        sys.modules["qlfake"] = imp.new_module("qlfake")

    def tearDown(self):
        del sys.modules["qlfake"]
        shutil.rmtree(self.d)

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

    def test_importables(self):
        self.failUnlessEqual(list(get_importables(self.d)), [])
        h = self._create_mod("foo.py")
        h.close()
        self.failUnlessEqual(list(get_importables(self.d))[0],
                             ("foo", h.name, [h.name]))

    def test_importables_ignore_init(self):
        h = self._create_mod("foo7.py")
        h.close()
        self._create_mod("__init__.py").close()
        self.failUnlessEqual(list(get_importables(self.d))[0],
                             ("foo7", h.name, [h.name]))

    def test_importables_package(self):
        h = self._create_pkg("foobar")
        self.failUnlessEqual(list(get_importables(self.d))[0],
                             ("foobar", os.path.dirname(h.name), [h.name]))
        h.close()

    def test_importables_package_deps(self):
        h = self._create_pkg("foobar3")
        h2 = self._create_mod("sub.py", "foobar3")
        name, path, deps = list(get_importables(self.d))[0]
        self.failUnlessEqual(name, "foobar3")
        self.failUnlessEqual(path, os.path.dirname(h.name))
        self.failUnlessEqual(set(deps), {h.name, h2.name})
        h2.close()
        h.close()

    def test_load_dir_modules(self):
        h = self._create_mod("x.py")
        h.write(b"test=42\n")
        h.close()
        mods = load_dir_modules(self.d, "qlfake")
        self.failUnlessEqual(len(mods), 1)
        self.failUnlessEqual(mods[0].test, 42)

    def test_load_dir_modules_packages(self):
        h = self._create_pkg("somepkg2")
        h2 = self._create_mod("sub.py", "somepkg2")
        h2.write(b"test=456\n")
        h2.close()
        h.write(b"from .sub import *\nmain=654\n")
        h.close()
        mods = load_dir_modules(self.d, "qlfake")
        self.failUnlessEqual(len(mods), 1)
        self.failUnlessEqual(mods[0].test, 456)

    def test_scanner_add(self):
        self._create_mod("q1.py").close()
        self._create_mod("q2.py").close()
        s = ModuleScanner([self.d])
        self.failIf(s.modules)
        removed, added = s.rescan()
        self.failIf(removed)
        self.failUnlessEqual(set(added), {"q1", "q2"})
        self.failUnlessEqual(len(s.modules), 2)
        self.failUnlessEqual(len(s.failures), 0)

    def test_unimportable_package(self):
        self._create_pkg("_foobar").close()
        s = ModuleScanner([self.d])
        self.failIf(s.modules)
        removed, added = s.rescan()
        self.failIf(added)
        self.failIf(removed)

    def test_scanner_remove(self):
        h = self._create_mod("q3.py")
        h.close()
        s = ModuleScanner([self.d])
        s.rescan()
        os.remove(h.name)
        try:
            os.remove(h.name + "c")
        except OSError:
            pass
        removed, added = s.rescan()
        self.failIf(added)
        self.failUnlessEqual(removed, ["q3"])
        self.failUnlessEqual(len(s.modules), 0)
        self.failUnlessEqual(len(s.failures), 0)

    def test_scanner_error(self):
        h = self._create_mod("q4.py")
        h.write(b"1syntaxerror\n")
        h.close()
        s = ModuleScanner([self.d])
        removed, added = s.rescan()
        self.failIf(added)
        self.failIf(removed)
        self.failUnlessEqual(len(s.failures), 1)
        self.failUnless("q4" in s.failures)

    def test_scanner_add_package(self):
        h = self._create_pkg("somepkg")
        h2 = self._create_mod("sub.py", "somepkg")
        h2.write(b"test=123\n")
        h2.close()
        h.write(b"from .sub import *\nmain=321\n")
        h.close()
        s = ModuleScanner([self.d])
        removed, added = s.rescan()
        self.failUnlessEqual(added, ["somepkg"])
        self.failUnlessEqual(s.modules["somepkg"].module.main, 321)
        self.failUnlessEqual(s.modules["somepkg"].module.test, 123)
