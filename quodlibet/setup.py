#!/usr/bin/env python

0 <> 0  # Python 3.x not supported. Use 2.6+ instead.

import glob
import os
import shutil
import sys
import subprocess

# disable translations
os.environ["QUODLIBET_NO_TRANS"] = ""

from distutils.core import setup, Command
from distutils.dep_util import newer
from distutils.command.build_scripts import build_scripts as du_build_scripts
from distutils.dir_util import remove_tree
from distutils.archive_util import make_archive

from gdist import GDistribution
from gdist.clean import clean as gdist_clean

PACKAGES = ("browsers devices formats library parse plugins qltk "
            "util player browsers.albums util.string").split()

# TODO: link this better to the app definitions
MIN_PYTHON_VER = (2, 6)
MIN_PYTHON_VER_STR = ".".join(map(str, MIN_PYTHON_VER))


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
                try:
                    os.unlink(os.path.join(pathname, filename))
                except EnvironmentError as err:
                    print str(err)

        for base in ["coverage", "build", "dist"]:
            path = os.path.join(os.path.dirname(__file__), base)
            if os.path.isdir(path):
                shutil.rmtree(path)


class build_sphinx(Command):
    description = "build sphinx documentation"
    user_options = [
        ("build-dir=", "d", "build directory"),
    ]

    def initialize_options(self):
        self.build_dir = None

    def finalize_options(self):
        self.build_dir = self.build_dir or "build"

    def run(self):
        DOCS_ROOT = "docs"
        GUIDE_ROOT = os.path.join(DOCS_ROOT, "guide")
        TARGET = os.path.join(self.build_dir, "sphinx")

        self.spawn(["sphinx-build", "-b", "html", "-c", DOCS_ROOT,
                    "-n", GUIDE_ROOT, TARGET])


class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)"),
        ("suite=", None, "test suite (folder) to run (default 'tests')"),
        ("strict", None, "make glib warnings / errors fatal"),
        ("all", None, "run all suites"),
        ("exitfirst", "x", "stop after first failing test"),
    ]
    use_colors = sys.stderr.isatty() and os.name != "nt"

    def initialize_options(self):
        self.to_run = []
        self.suite = None
        self.strict = False
        self.all = False
        self.exitfirst = False

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")
        self.strict = bool(self.strict)
        self.all = bool(self.all)
        self.suite = self.suite and str(self.suite)
        self.exitfirst = bool(self.exitfirst)

    @classmethod
    def _red(cls, text):
        from quodlibet.util.dprint import Colorise
        return Colorise.red(text) if cls.use_colors else text

    def run(self):
        mods = sys.modules.keys()
        if "gi" in mods:
            raise SystemExit("E: setup.py shouldn't depend on gi")

        import tests

        main = False
        if not self.suite or self.all:
            main = True

        subdirs = []
        if self.all:
            test_path = tests.__path__[0]
            for entry in os.listdir(test_path):
                if os.path.isdir(os.path.join(test_path, entry)):
                    subdirs.append(entry)
        elif self.suite:
            subdirs.append(self.suite)

        failures, errors = tests.unit(self.to_run, main=main, subdirs=subdirs,
                                      strict=self.strict,
                                      stop_first=self.exitfirst)
        if failures or errors:
            raise SystemExit(self._red("%d test failure(s) and "
                                       "%d test error(s), as detailed above."
                             % (failures, errors)))


class sdist_plugins(Command):
    description = "Build a source distribution of all plugins"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        old_dir = os.getcwd()
        os.chdir("..")

        process = subprocess.Popen(["hg", "locate", "-I", "plugins"],
                                   stdout=subprocess.PIPE)
        out, err = process.communicate()
        assert process.returncode == 0

        files = out.splitlines()

        from quodlibet import const
        dest_name = "quodlibet-plugins-" + const.VERSION

        for f in files:
            parts = f.split(os.path.sep)
            target = os.path.join(dest_name, *parts[1:])
            self.mkpath(os.path.dirname(target))
            self.copy_file(f, target)

        archive_name = make_archive(dest_name, "gztar", base_dir=dest_name)
        remove_tree(dest_name)
        dist_dir = os.path.join("quodlibet", "dist")
        self.mkpath(dist_dir)
        self.move_file(archive_name, dist_dir)

        os.chdir(old_dir)


class build_scripts(du_build_scripts):
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
        try:
            os.unlink(os.path.join(coverage, "..setup.cover"))
        except OSError:
            pass

        # compute coverage
        stats = []
        cov_files = []
        for filename in glob.glob(os.path.join(coverage, "*.cover")):
            cov_files.append(filename)
            lines = file(filename, "rU").readlines()
            lines = filter(None, map(str.strip, lines))
            total_lines = len(lines)
            if not total_lines:
                continue
            bad_lines = len([l for l in lines if l.startswith(">>>>>>")])
            percent = 100.0 * (total_lines - bad_lines) / float(total_lines)
            stats.append((percent, filename, total_lines, bad_lines))
        stats.sort(reverse=True)
        print "#" * 80
        print "COVERAGE"
        print "#" * 80
        total_sum = 0
        bad_sum = 0
        for s in stats:
            p, f, t, b = s
            total_sum += t
            bad_sum += b
            print "%6.2f%% %s" % (p, os.path.basename(f))
        print "-" * 80
        print "Coverage data written to", coverage, "(%d/%d, %0.2f%%)" % (
            total_sum - bad_sum, total_sum,
            100.0 * (total_sum - bad_sum) / float(total_sum))
        print "#" * 80


def recursive_include(base, sub, ext):
    paths = []
    for path, dirs, files in os.walk(os.path.join(base, sub)):
        for f in files:
            if f.split('.')[-1] in ext:
                p = os.path.relpath(os.path.join(path, f), base)
                paths.append(p)
    return paths


if __name__ == "__main__":
    import quodlibet
    from quodlibet import const

    cmd_classes = {
        'clean': clean,
        "test": test_cmd,
        "coverage": coverage_cmd,
        "build_scripts": build_scripts,
        "sdist_plugins": sdist_plugins,
        "build_sphinx": build_sphinx,
    }

    package_path = quodlibet.__path__[0]
    package_data_paths = recursive_include(
        package_path, "images", ("svg", "png", "cache", "theme"))

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
        'package_data': {"quodlibet": package_data_paths},
        'scripts': ["quodlibet.py", "exfalso.py", "operon.py"],
        'po_directory': "po",
        'po_package': "quodlibet",
        'shortcuts': ["data/quodlibet.desktop", "data/exfalso.desktop"],
        'dbus_services': [
            "data/net.sacredchao.QuodLibet.service",
            "data/org.mpris.MediaPlayer2.quodlibet.service",
            "data/org.mpris.quodlibet.service",
        ],
        'man_pages': ["man/quodlibet.1", "man/exfalso.1", "man/operon.1"],
        "search_provider": "data/quodlibet-search-provider.ini",
        }

    setup(**setup_kwargs)
