#!/usr/bin/env python

import glob
import os
import shutil
import sys

from distutils.core import setup, Command
from distutils.dep_util import newer
from distutils.command.build_scripts import build_scripts as distutils_build_scripts

from gdist import GDistribution, GObjectExtension
from gdist.clean import clean as gdist_clean
from gdist.gobject import build_gobject_ext as gdist_build_gobject_ext

PACKAGES = ("browsers devices formats library parse plugins qltk "
            "util player debug").split()

class clean(gdist_clean):
    def run(self):
        gdist_clean.run(self)

        for ext in self.distribution.gobject_modules:
            path = ext.name.replace(".", "/") + ".so"
            if os.path.exists(path):
                os.unlink(path)

        if not self.all:
            return

        def should_remove(filename):
            if (filename.lower()[-4:] in [".pyc", ".pyo"] or
                filename.endswith("~") or
                (filename.startswith("#") and filename.endswith("#"))):
                return True
            else:
                return False
        for pathname, dirs, files in os.walk(os.path.dirname(__file__)):
            for filename in filter(should_remove, files):
                try: os.unlink(os.path.join(pathname, filename))
                except EnvironmentError, err:
                    print str(err)

        for base in ["coverage", "build", "dist"]:
            path = os.path.join(os.path.dirname(__file__), base)
            if os.path.isdir(path):
                shutil.rmtree(path)

class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
        ("suite=", None, "test suite (folder) to run (default 'tests')"),
        ]

    def initialize_options(self):
        self.to_run = []
        self.suite = "tests"

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")

    def run(self):
        tests = __import__(self.suite)
        if tests.unit(self.to_run):
            raise SystemExit("Test failures are listed above.")

class build_scripts(distutils_build_scripts):
    description = "copy scripts to build directory"

    def run(self):
        self.mkpath(self.build_dir)
        for script in self.scripts:
            newpath = os.path.join(self.build_dir, os.path.basename(script))
            if newpath.lower().endswith(".py"):
                newpath = newpath[:-3]
            if newer(script, newpath) or self.force:
                self.copy_file(script, newpath)

class release(Command):
    description = "release a new version of Quod Libet"
    user_options = [
        ("all-the-way", None, "svn commit and copy release tarball to kai")
        ]

    def initialize_options(self):
        self.all_the_way = False

    def finalize_options(self):
        pass

    def run(self):
        from quodlibet.const import VERSION
        self.run_command("test")
        if os.path.exists("../../releases/quodlibet-%s" % VERSION):
            raise 
        target = "../../releases/quodlibet-%s" % VERSION
        if os.path.isdir(target):
            raise SystemExit("Quod Libet %s was already released." % VERSION)

        # This is so fucking weird, SVN refuses to branch
        # trunk/quodlibet with some error about the files already
        # existing. Releasing is more important than proper branch
        # history.
        self.spawn(["svn", "export", os.getcwd(), target])
        self.spawn(["svn", "add", target])

        if self.all_the_way:
            if os.environ.get("USER") != "piman":
                print "You're not Joe, so this might not work."
            self.spawn(
                ["svn", "commit", "-m", "Quod Libet %s." % VERSION, target])
            os.chdir(target)
            if os.environ.get("USER") != "piman":
                print "You're not Joe, so this definitely won't work."
            print "Copying tarball to kai."
            self.run_command("sdist")
            self.spawn(["gpg", "-b", "dist/quodlibet-%s.tar.gz" % VERSION])
            self.spawn(["scp", "dist/quodlibet-%s.tar.gz" % VERSION,
                        "dist/quodlibet-%s.tar.gz.sig" % VERSION,
                        "sacredchao.net:~piman/public_html/software"])
            self.run_command("register")

class coverage_cmd(Command):
    description = "generate test coverage data"
    user_options = []

    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass

    def run(self):
        # Wipe existing modules, to make sure coverage data is properly
        # generated for them.
        for key in sys.modules.keys():
            if key.startswith('quodlibet'):
                del(sys.modules[key])

        import trace
        tracer = trace.Trace(
            count=True, trace=False,
            ignoredirs=[sys.prefix, sys.exec_prefix])
        def run_tests():
            self.run_command("test")
        tracer.runfunc(run_tests)
        results = tracer.results()
        coverage = os.path.join(os.path.dirname(__file__), "coverage")
        results.write_results(show_missing=True, coverdir=coverage)
        map(os.unlink, glob.glob(os.path.join(coverage, "[!q]*.cover")))
        try: os.unlink(os.path.join(coverage, "..setup.cover"))
        except OSError: pass

        total_lines = 0
        bad_lines = 0
        for filename in glob.glob(os.path.join(coverage, "*.cover")):
            lines = file(filename, "rU").readlines()
            total_lines += len(lines)
            bad_lines += len(
                [line for line in lines if
                 (line.startswith(">>>>>>") and
                  "finally:" not in line and '"""' not in line)])
        print "Coverage data written to", coverage, "(%d/%d, %0.2f%%)" % (
            total_lines - bad_lines, total_lines,
            100.0 * (total_lines - bad_lines) / float(total_lines))


class check(Command):
    description = "check installation requirements"
    user_options = []

    NAME = "Quod Libet"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        print "Checking Python version:",
        print ".".join(map(str, sys.version_info[:2]))
        if sys.version_info < (2, 4):
            raise SystemExit("%s requires at least Python 2.4. "
                             "(http://www.python.org)" % self.NAME)

        print "Checking for PyGTK >= 2.10:",
        try:
            import pygtk
            pygtk.require('2.0')
            import gtk
            if gtk.pygtk_version < (2, 10) or gtk.gtk_version < (2, 10):
                raise ImportError
        except ImportError:
            raise SystemExit("not found\n%s requires PyGTK 2.10. "
                             "(http://www.pygtk.org)" % self.NAME)
        else: print "found"

        print "Checking for gst-python >= 0.10.2:",
        try:
            import pygst
            pygst.require("0.10")
            import gst
            if gst.pygst_version < (0, 10, 2):
                raise ImportError
        except ImportError:
            have_pygst = False
            print "not found"
        else:
            have_pygst = True
            print "found"

        print "Checking for xine-lib >= 1.1:",
        try:
            from quodlibet.player._xine import xine_check_version
            if not xine_check_version(1, 1, 0):
                raise ImportError
        except ImportError:
            have_xine = False
            print "not found"
        else:
            have_xine = True
            print "found"

        if not have_pygst and not have_xine:
            raise SystemExit("%s requires gst-python 0.10.2 "
                             "(http://gstreamer.freedesktop.org)"
                             " or xine-lib 1.1 "
                             "(http://www.xinehq.de/)." % self.NAME)

        print "Checking for Mutagen >= 1.10:",
        try:
            import mutagen
            if mutagen.version < (1, 10):
                raise ImportError
        except ImportError:
            raise SystemExit("not found\n%s requires Mutagen 1.10.\n"
                "(http://code.google.com/p/quodlibet/downloads/list)" %
                self.NAME)
        else: print "found"

        print """\n\
Your system meets the installation requirements. Run %(setup)s install to
install it. You may want to make some extensions first; you can do that
with %(setup)s build_gobject.""" % dict(setup=sys.argv[0])

class build_gobject_ext(gdist_build_gobject_ext):
    def run(self):
        gdist_build_gobject_ext.run(self)
        for ext in self.distribution.gobject_modules:
            path = ext.name.replace(".", "/") + ".so"
            self.copy_file(os.path.join(self.build_lib, path), path)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from quodlibet import const
    cmd_classes = {"check": check, 'clean': clean, "test": test_cmd,
                   "coverage": coverage_cmd, "release": release,
                   "build_scripts": build_scripts,
                   "build_gobject_ext": build_gobject_ext}
    setup_kwargs = {
        'distclass': GDistribution,
        'cmdclass': cmd_classes,
        'name': "quodlibet",
        'version': const.VERSION,
        'url': "http://code.google.com/p/quodlibet/",
        'description': "a music library, tagger, and player",
        'author': "Joe Wreschnig, Michael Urman, & others",
        'author_email': "quod-libet-development@googlegroups.com",
        'maintainer': "Steven Robertson and Christoph Reiter",
        'license': "GNU GPL v2",
        'packages': ["quodlibet"] + map("quodlibet.".__add__, PACKAGES),
        'package_data': {"quodlibet": ["images/*.png", "images/*.svg"]},
        'scripts': ["quodlibet.py", "exfalso.py"],
        'po_directory': "po",
        'po_package': "quodlibet",
        'shortcuts': ["quodlibet.desktop", "exfalso.desktop"],
        'man_pages': ["man/quodlibet.1", "man/exfalso.1"],
        'gobject_modules': [
                    GObjectExtension("quodlibet._mmkeys",
                            "mmkeys/mmkeys.defs",
                            "mmkeys/mmkeys.override",
                            ["mmkeys/mmkeys.c", "mmkeys/mmkeysmodule.c"],
                            include_dirs=["mmkeys"]),
                    GObjectExtension("quodlibet._trayicon",
                            "trayicon/trayicon.defs",
                            "trayicon/trayicon.override",
                            ["trayicon/eggtrayicon.c",
                             "trayicon/trayiconmodule.c"],
                            include_dirs=["trayicon"])
                    ],
        }
    if os.name == 'nt':
        import pygst
        pygst.require('0.10')
        from os.path import join

        # suckily, we include 'browsers' and 'formats' twice.
        data_files = [('', ['COPYING']),
                      (join('quodlibet', 'browsers'),
                        glob.glob(join('quodlibet', 'browsers', '*.py'))),
                      (join('quodlibet', 'formats'),
                        glob.glob(join('quodlibet', 'formats', '*.py'))),
                      (join('quodlibet', 'images'),
                        glob.glob(join('quodlibet', 'images', '*.png')) +
                        glob.glob(join('quodlibet', 'images', '*.svg')))]
        for type in ["playorder", "songsmenu", "editing", "events"]:
            data_files.append((join('quodlibet', 'plugins', type),
                glob.glob(join('..', 'plugins', type, '*.py'))))

        includes = (
                    'feedparser').split()

        setup_kwargs.update({
                    'data_files': data_files,
                    'windows': [
                        {
                            "script": "quodlibet.py",
                            "icon_resources": [(0,
                               join('quodlibet', 'images', 'quodlibet.ico'))]
                        },
                        {
                            "script": "exfalso.py",
                            "icon_resources": [(0,
                                join('quodlibet', 'images', 'exfalso.ico'))]
                        }
                    ],
                    'options': {
                        'py2exe': {
                            'packages': 'encodings, feedparser, quodlibet',
                            'includes': ('cairo, pango, pangocairo, atk, '
                                         'gobject, pygst, gst, '
                                         'quodlibet.player.gstbe')
                        }
                    }
                })
    setup(**setup_kwargs)

