#!/usr/bin/env python

0<>0 # Python 3.x not supported. Use 2.6+ instead.

import glob
import os
import shutil
import sys

from distutils.core import setup, Command
from distutils.dep_util import newer
from distutils.command.build_scripts import build_scripts as distutils_build_scripts
from distutils.spawn import find_executable

from gdist import GDistribution
from gdist.clean import clean as gdist_clean

PACKAGES = ("browsers devices formats library parse plugins qltk "
            "util player debug").split()

# TODO: link this better to the app definitions
MIN_PYTHON_VER = (2,6)
MIN_PYTHON_VER_STR = ".".join(map(str,MIN_PYTHON_VER))

class clean(gdist_clean):
    def run(self):
        gdist_clean.run(self)

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
        tests = __import__("tests")
        subdir = (self.suite != "tests" and self.suite) or None
        if tests.unit(self.to_run, subdir=subdir):
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

class coverage_cmd(Command):
    description = "generate test coverage data"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
    ]

    def initialize_options(self):
        self.to_run = []

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
            cmd = self.reinitialize_command("test")
            cmd.to_run = self.to_run[:]
            cmd.ensure_finalized()
            cmd.run()
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
        print "Checking Python version >= %s:" % MIN_PYTHON_VER_STR,
        print ".".join(map(str, sys.version_info[:2]))
        if sys.version_info < MIN_PYTHON_VER:
            raise SystemExit("%s requires at least Python %s. "
                             "(http://www.python.org)"
                             % (self.NAME, ".".join(map(str,MIN_PYTHON_VER))))

        print "Checking for PyGTK >= 2.16:",
        try:
            import pygtk
            pygtk.require('2.0')
            import gtk
            if gtk.pygtk_version < (2, 16) or gtk.gtk_version < (2, 16):
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

        print "Checking for Mutagen >= 1.11:",
        try:
            import mutagen
            if mutagen.version < (1, 11):
                raise ImportError
        except ImportError:
            raise SystemExit("not found\n%s requires Mutagen 1.11.\n"
                "(http://code.google.com/p/mutagen/downloads/list)" %
                self.NAME)
        else: print "found"

        print "Checking intltool/gettext:",
        if not find_executable("intltool-update") or \
                not find_executable("msgfmt"):
            raise SystemExit("intltool/gettext not found")
        else: print "found"

        print """\n\
Your system meets the installation requirements. Run %(setup)s install to
install it.""" % dict(setup=sys.argv[0])

def recursive_include(dir, pre, ext):
    all = []
    old_dir = os.getcwd()
    os.chdir(dir)
    for path, dirs, files in os.walk(pre):
        for file in files:
            if file.split('.')[-1] in ext:
                all.append(os.path.join(path, file))
    os.chdir(old_dir)
    return all

def recursive_include_py2exe(dir, pre, ext):
    all = []
    dir = os.path.join(dir, pre)
    for path, dirs, files in os.walk(dir):
        all_path = []
        for file in files:
            if file.split('.')[-1] in ext:
                all_path.append(os.path.join(path, file))
        if all_path: all.append((path, all_path))
    return all

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from quodlibet import const
    cmd_classes = {"check": check, 'clean': clean, "test": test_cmd,
                   "coverage": coverage_cmd, "build_scripts": build_scripts}
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
        'package_data': {"quodlibet": recursive_include("quodlibet", "images",
            ("svg", "png", "cache", "theme"))},
        'scripts': ["quodlibet.py", "exfalso.py"],
        'po_directory': "po",
        'po_package': "quodlibet",
        'shortcuts': ["quodlibet.desktop", "exfalso.desktop"],
        'man_pages': ["man/quodlibet.1", "man/exfalso.1"],
        }
    if os.name == 'nt':
        # (probably) necessary to get the right DLLs pulled in by py2exe
        import pygst
        pygst.require('0.10')
        from os.path import join

        # taken from http://www.py2exe.org/index.cgi/win32com.shell
        # ModuleFinder can't handle runtime changes to __path__, but win32com uses them
        try:
            # py2exe 0.6.4 introduced a replacement modulefinder.
            # This means we have to add package paths there, not to the built-in
            # one.  If this new modulefinder gets integrated into Python, then
            # we might be able to revert this some day.
            # if this doesn't work, try import modulefinder
            try:
                import py2exe.mf as modulefinder
            except ImportError:
                import modulefinder
            import win32com
            for p in win32com.__path__[1:]:
                modulefinder.AddPackagePath("win32com", p)
            for extra in ["win32com.shell"]: #,"win32com.mapi"
                __import__(extra)
                m = sys.modules[extra]
                for p in m.__path__[1:]:
                    modulefinder.AddPackagePath(extra, p)
        except ImportError:
            # no build path setup, no worries.
            pass

        data_files = [('', ['COPYING'])] +  recursive_include_py2exe(
            "quodlibet", "images", ("svg", "png", "cache", "theme"))

        for type in ["playorder", "songsmenu", "editing", "events", "gstreamer"]:
            data_files.append((join('quodlibet', 'plugins', type),
                glob.glob(join('..', 'plugins', type, '*.py'))))

        setup_kwargs.update({
            'data_files': data_files,
            'windows': [
                {
                    "script": "quodlibet.py",
                    "icon_resources": [(0,
                       join('..', 'win_installer', 'quodlibet.ico'))]
                },
                # workaround icon not working under Vista/7
                # exe resource identifiers get incremented and start at 0.
                # and 0 doesn't seem to be valid.
                {
                    "script": "quodlibet.py",
                    "icon_resources": [(0,
                       join('..', 'win_installer', 'quodlibet.ico'))]
                },
                {
                    "script": "exfalso.py",
                    "icon_resources": [(0,
                        join('..', 'win_installer', 'exfalso.ico'))]
                }
            ],
            'options': {
                'py2exe': {
                    'packages': ('encodings, feedparser, quodlibet, '
                                 'HTMLParser, gtk, glib, gobject, '
                                 'musicbrainz2, shelve, json, pyHook'),
                    'includes': ('cairo, pango, pangocairo, atk, gio, '
                                 'pygst, gst, quodlibet.player.gstbe, '
                                 'CDDB'),
                    'excludes': ('ssl_', 'doctest', 'pdb', 'unittest',
                                 'difflib', 'inspect'),
                    'skip_archive': True,
                    'dist_dir': 'dist\\bin'
                }
            }
        })
    setup(**setup_kwargs)

