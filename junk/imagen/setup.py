#!/usr/bin/env python

import glob
import os
import shutil
import sys

from distutils.core import setup, Command

from distutils.command.clean import clean as distutils_clean
from distutils.command.sdist import sdist as distutils_sdist

class release(Command):
    description = "release a new version of Imagen"
    user_options = [
        ("all-the-way", None, "svn commit and copy release tarball to kai")
        ]

    def initialize_options(self):
        self.all_the_way = False

    def finalize_options(self):
        pass

    def rewrite_version(self, target, version):
        filename = os.path.join(target, "imagen", "__init__.py")
        lines = file(filename, "rU").readlines()
        fileout = file(filename, "w")
        for line in lines:
            if line.startswith("version ="):
                fileout.write("version = %s\n" % repr(version))
            else:
                fileout.write(line)
        fileout.close()

    def run(self):
        from imagen import version, version_string as sversion
        self.run_command("test")
        if version[-1] >= 0:
            raise SystemExit("%r: version number to release." % version)
        target = "../../releases/imagen-%s" % sversion
        if os.path.isdir(target):
            raise SystemExit("%r was already released." % sversion)
        self.spawn(["svn", "cp", os.getcwd(), target])

        self.rewrite_version(target, version[:-1])

        if self.all_the_way:
            if os.environ.get("USER") != "piman":
                print "You're not Joe, so this might not work."
            self.spawn(
                ["svn", "commit", "-m", "Imagen %s." % sversion, target])
            os.chdir(target)
            if os.environ.get("USER") != "piman":
                print "You're not Joe, so this definitely won't work."
            print "Copying tarball to kai."
            self.run_command("sdist")
            self.spawn(["scp", "dist/imagen-%s.tar.gz" % sversion,
                        "sacredchao.net:~piman/public_html/software"])
            self.run_command("register")

class clean(distutils_clean):
    def run(self):
        # In addition to what the normal clean run does, remove pyc
        # and pyo files from the source tree.
        distutils_clean.run(self)
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

        try: os.unlink("MANIFEST")
        except OSError: pass

        for base in ["coverage", "build", "dist"]:
             path = os.path.join(os.path.dirname(__file__), base)
             if os.path.isdir(path):
                 shutil.rmtree(path)

class sdist(distutils_sdist):
    def run(self):
        import imagen
        if imagen.version[-1] < 0:
            raise SystemExit(
                "Refusing to create a source distribution for a prerelease.")
        else:
            self.run_command("test")
            distutils_sdist.run(self)

class test_cmd(Command):
    description = "run automated tests"
    user_options = [
        ("to-run=", None, "list of tests to run (default all)")
        ]

    def initialize_options(self):
        self.to_run = []

    def finalize_options(self):
        if self.to_run:
            self.to_run = self.to_run.split(",")

    def run(self):
        import tests
        if tests.unit(self.to_run):
            raise SystemExit("Test failures are listed above.")

class coverage_cmd(Command):
    description = "generate test coverage data"
    user_options = []

    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass

    def run(self):
        import trace
        tracer = trace.Trace(
            count=True, trace=False,
            ignoredirs=[sys.prefix, sys.exec_prefix])
        def run_tests():
            import imagen
            reload(imagen)
            self.run_command("test")
        tracer.runfunc(run_tests)
        results = tracer.results()
        coverage = os.path.join(os.path.dirname(__file__), "coverage")
        results.write_results(show_missing=True, coverdir=coverage)
        map(os.unlink, glob.glob(os.path.join(coverage, "[!i]*.cover")))
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

if os.name == "posix":
    data_files = [('share/man/man1', glob.glob("man/*.1"))]
else:
    data_files = []

if __name__ == "__main__":
    from imagen import version_string
    setup(cmdclass={'clean': clean, 'test': test_cmd, 'coverage': coverage_cmd,
                    "sdist": sdist, "release": release},
          name="imagen", version=version_string,
          url="http://www.sacredchao.net/quodlibet/wiki/Development/Imagen",
          description="read and write audio tags for many formats",
          author="Joe Wreschnig",
          author_email="quodlibet@lists.sacredchao.net",
          license="GNU GPL v2",
          packages=["imagen"],
          data_files=data_files,
          scripts=glob.glob("tools/*[!~]"),
          long_description="""\
Imagen is a Python module to handle image metadata.
"""
          )
