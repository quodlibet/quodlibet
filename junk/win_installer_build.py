#!/usr/bin/python
#
# Copyright 2010 Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.


"""A hastily-organized auto-build script to generate the Windows installer."""

from __future__ import with_statement

import re
import os
import sys
import time
import shutil
import shelve
import urllib2
import zipfile
import tarfile
import optparse
import tempfile
import traceback
import subprocess


from os.path import join
from contextlib import contextmanager

# The directory for downloaded files
CACHEDIR=os.path.expanduser(r'~\.ql_winbuild_cache')

# The temporary directory we'll use for virutalenv
TDIR=''
PROG_DIR = os.environ['PROGRAMFILES']
HG_PATH = os.path.join(PROG_DIR, "Mercurial", "hg.exe")
NSIS_PATH = os.path.join(PROG_DIR, "NSIS", "makensis.exe")

# Backport some changesets for specific tags
BACKPORTS = {
    "quodlibet-2.2.1": [4410, 4411, 4412, 4420, 4435, 4436, 4437, 4438, 4444,
                        4445, 4447, 4448]
}

def ccall(cmd, *args, **kwargs):
    """subprocess.check_call wrapper to work around broken PATH."""
    if not cmd[0].endswith('.exe'):
        cmd[0] = cmd[0] + '.exe'
    for i in ['', r'\bin', r'\Scripts']:
        fn = join(TDIR, 'Python'+i, cmd[0])
        if os.path.isfile(fn):
            cmd[0] = fn
            break
    return subprocess.check_call(cmd, *args, **kwargs)

@contextmanager
def chdir(path):
    cwd = os.getcwd()
    os.chdir(path)
    yield
    os.chdir(cwd)

def vsorted(lst):
    return sorted(lst, key=lambda k:
            map(lambda s: not s.isdigit() and s or int(s), k.split('.')))

def urlfetch(url):
    """Generator function for fetching a URL in 32k chunks w/ feedback."""
    print "Fetching URL '%s'" % url
    u = urllib2.urlopen(url)
    while True:
        data = u.read(32768)
        if data:
            sys.stdout.write('.')
            yield data
        else:
            print ''
            return

def copytree2(src, dst):
    """Like shutil.copytree but allows target to exist"""
    names = os.listdir(src)
    if not os.path.isdir(dst):
        os.makedirs(dst)
    errors = []
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if os.path.isdir(srcname):
                copytree2(srcname, dstname)
            else:
                shutil.copy2(srcname, dstname)
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        except shutil.Error, err:
            errors.extend(err.args[0])
    if errors:
        raise Error(errors)

class Page(object):
    """A page cache for doing version lookups and the like."""
    cache = None

    def __init__(self, url):
        if self.cache is None:
            type(self).cache = shelve.open(join(CACHEDIR, 'pages.db'))
        if url in self.cache and time.time() - self.cache[url]['time'] < 24800:
            print "URL '%s' in cache (%d sec old)" % (
                    url, time.time() - self.cache[url]['time'])
            self.text = self.cache[url]['text']
        else:
            self.text = ''.join(urlfetch(url))
            self.cache[url] = {'time': time.time(), 'text': self.text}
            self.cache.sync()

class Dep(object):
    """Download and version information for a dependency."""
    def __init__(self, name, prefix):
        """
        Creates the dependency. 'name' is the project release name. 'prefix'
        is the desired version prefix. If 'prefix' is none, the latest version
        will be used.
        """
        self.name = name
        self.prefix = prefix
        print "Fetching version list for package %s" % name
        self.versions = list(reversed(vsorted(set(self._get_versions()))))
        if prefix:
            best_vers = filter(lambda s: s.startswith(prefix), self.versions)
        else:
            best_vers = self.versions
        if len(best_vers) == 0:
            raise ValueError("No releases of %s %s found." % (name, prefix))

        self.url = self._get_release(best_vers[0])
        # The 'split' removes suffixes like '?download'
        self.filename = os.path.basename(self.url).split('?')[0]
        print "Selected %s" % self.filename

    def _get_versions(self):
        """Returns a list of available versions. Depending on the URL scheme,
        this will either be just major.minor or the full version."""
        raise NotImplementedError

    def _get_release(self, version):
        """Returns the URL of the latest release of the selected version,
        based on whatever _get_versions returns."""
        raise NotImplementedError

    @property
    def fetched(self):
        """Whether the package has been fetched to the cache."""
        return os.path.isfile(join(CACHEDIR, self.filename))

class PythonDep(Dep):
    """Fetcher for the win32 Python MSI."""
    def _get_versions(self):
        url = 'http://www.python.org/download/releases/'
        return re.findall('href="/download/releases/([1234567890.]+)[/]?"',
                          Page(url).text)

    def _get_release(self, version):
        return ('http://www.python.org/ftp/python/%(ver)s/python-%(ver)s.msi' %
                {'ver': version})

class GnomeDep(Dep):
    """Fetcher for files from the Gnome project."""
    def __init__(self, name, prefix, file_re):
        """
        'name' must be identical to the project name. 'file_re' should match
        the binary's name exactly.
        """
        self.url_re = 'href="(%s)"' % file_re
        super(GnomeDep, self).__init__(name, prefix)

    def _get_versions(self):
        self.project_url = (
            'http://ftp.gnome.org/pub/gnome/binaries/win32/%s' % self.name)
        return re.findall('href="([1234567890.]+)[/]?"',
                          Page(self.project_url).text)

    def _get_release(self, version):
        filename = vsorted(re.findall(self.url_re,
                        Page('/'.join((self.project_url, version))).text))[-1]
        return '/'.join((self.project_url, version, filename))

class SFDep(Dep):
    """Fetcher for files from SourceForge."""
    def __init__(self, name, prefix, file_re):
        """
        'name' must be identical to the project name. 'file_re' should match
        the binary's name exactly. SF projects can be a little more scattered,
        so double-check the results of this one.
        """
        self.file_re = file_re
        super(SFDep, self).__init__(name, prefix)

    def _get_versions(self):
        return ['automatic']

    def _get_release(self, version):
        ur="url: '(http://downloads.sourceforge.net/project/%s/[^']*%s[^']*)'"
        ur = ur % (self.name, self.file_re)
        page = Page('http://sourceforge.net/projects/%s/files/' % self.name)
        return vsorted(re.findall(ur, page.text))[-1]

class DirectDep(Dep):
    """Just returns the given URL"""
    def __init__(self, name, prefix, down_url):
        self.down_url = down_url
        super(DirectDep, self).__init__(name, prefix)

    def _get_versions(self):
        return ["Unknown"]

    def _get_release(self, version):
        return self.down_url

class OnePageDep(Dep):
    """Fetcher for projects which have direct download URLs on one page."""

    def __init__(self, name, prefix, page_url, url_re):
        self.page_url = page_url
        self.url_re = url_re
        super(OnePageDep, self).__init__(name, prefix)

    def _get_versions(self):
        return ['automatic']

    def _get_release(self, version):
        # Note: does not catch end quote by design (for pypi compat)
        url = vsorted(re.findall('href="(%s)' % self.url_re,
                                 Page(self.page_url).text))[-1]
        if "://" not in url:
            url = "/".join([self.page_url, url])
        return url

class EasyInstallDep(Dep):
    """Does no work, just here for the sake of appearance"""
    def __init__(self, name):
        self.name = name
        self.versions = ['automatic']
        self.filename = 'automatic'

    @property
    def fetched(self):
        return True

class Installer(object):
    def __init__(self, dest=None):
        """
        'dest' should be a relative path from the temporary directory. If the
        type of install doesn't require a destination, it may be omitted.
        """
        self.dest = dest

    def install(self, dep):
        raise NotImplementedError

class MSIInst(Installer):
    """Does an administrative install (essentially an unpack) to a directory."""
    def install(self, dep):
        subprocess.check_call(['msiexec', '/a', join(CACHEDIR, dep.filename),
            '/qb', 'TARGETDIR=%s' % join(TDIR, self.dest)])

class ZipInst(Installer):
    """Unzips a package to a target directory."""
    def install(self, dep):
        zf = zipfile.ZipFile(join(CACHEDIR, dep.filename))
        zf.extractall(join(TDIR, self.dest))

class TarInst(Installer):
    """Untars a package to a target directory."""
    def install(self, dep):
        tf = tarfile.open(join(CACHEDIR, dep.filename))
        tf.extractall(join(TDIR, self.dest))

class UnrarInst(Installer):
    """Untars a package to a target directory."""
    def install(self, dep):
        with chdir(join(TDIR, self.dest)):
            ccall(['unrar', 'x', join(CACHEDIR, dep.filename)])

class EasyInstallInst(Installer):
    """Uses easy_install to install a package. Does not require a dest."""
    def install(self, dep):
        ccall(['easy_install', '-Z', dep.name])

class EasyInstallExeInst(Installer):
    """Uses easy_install to install a binary. Does not require a dest."""
    def install(self, dep):
        ccall(['easy_install', '-Z', join(CACHEDIR, dep.filename)])

class InnoInst(Installer):
    """Unpacks an Inno Setup installer to a particular location."""
    def install(self, dep):
        dest = join(TDIR, self.dest)
        tmp = tempfile.mkdtemp()
        ccall(['innounp', '-x', '-d%s' % tmp, join(CACHEDIR, dep.filename)])
        with chdir(join(tmp, '{app}')):
            for root, dirs, files in os.walk('.'):
                if not os.path.isdir(join(dest, root)):
                    os.mkdir(join(dest, root))
                for file in files:
                    if not os.path.isfile(join(dest, root, file)):
                        os.rename(join(root, file), join(dest, root, file))

class SetuptoolsInst(Installer):
    """Requirement for bootstrapping the install process."""
    def install(self, dep):
        tf = tarfile.open(join(CACHEDIR, dep.filename))
        tf.extractall(TDIR)
        with chdir(join(TDIR, dep.filename.replace('.tar.gz', ''))):
            ccall(['python', 'setup.py', 'install'])

def do_setup(rev):
    PYVER='2.6'
    deps = [
    (PythonDep('Python', PYVER),
        MSIInst('Python')),
    (OnePageDep('setuptools', None, 'http://pypi.python.org/pypi/setuptools',
                '[^"]*setuptools[^"]*tar.gz[^"#]*'),
        SetuptoolsInst()),
    (SFDep('gnuwin32', None, 'unrar-[1234567890.]*-bin.zip'),
        ZipInst('Python')),
    (SFDep('innounp', None, 'innounp[1234567890.]*.rar'),
        UnrarInst('Python')),
    (GnomeDep('libglade', '2.6', '[^"]*libglade_[^"]*win32.zip'),
        ZipInst('gtk')),
    (OnePageDep('libbzip2', None,
                'http://ftp.gnome.org/pub/gnome/binaries/win32/dependencies/',
                '[^"]*libbzip2_[^"]*.zip[^"#]*'),
        ZipInst('gtk')),
    (GnomeDep('libcroco', '0.6', '[^"]*libcroco_[^"]*win32.zip'),
        ZipInst('gtk')),
    (GnomeDep('libgsf', '1.14', '[^"]*libgsf_[^"]*win32.zip'),
        ZipInst('gtk')),
    (GnomeDep('librsvg', '2.26', '[^"]*librsvg_[^"]*win32.zip'),
        ZipInst('gtk')),
    (GnomeDep('librsvg', '2.26', '[^"]*svg-gdk-pixbuf-loader_[^"]*win32.zip'),
        ZipInst('gtk')),
    (GnomeDep('pycairo', '1.8', '[^"]*win32-py%s.exe' % PYVER),
        EasyInstallExeInst()),
    (GnomeDep('pygobject', '2.20', '[^"]*win32-py%s.exe' % PYVER),
        EasyInstallExeInst()),
    (GnomeDep('pygtk', '2.16', '[^"]*glade.win32-py%s.exe' % PYVER),
        EasyInstallExeInst()),
    (DirectDep('GStreamer', None,
        'http://ossbuild.googlecode.com/files/GStreamer-WinBuilds-GPL-x86.msi'),
        MSIInst('gstreamer')),
    (DirectDep('pygst', None,
        'http://ossbuild.googlecode.com/files/GStreamer-WinBuilds-SDK-GPL-x86.msi'),
        MSIInst('pygst')),
    (SFDep('py2exe', None, 'py2exe-[1234567890.]*.win32-py%s.exe' % PYVER),
        EasyInstallExeInst()),
    (SFDep('pywin32', None, 'pywin32-[1234567890.]*.win32-py%s.exe' % PYVER),
        EasyInstallExeInst()),
    (EasyInstallDep('mutagen'), EasyInstallInst()),
    (EasyInstallDep('feedparser'), EasyInstallInst()),
    (EasyInstallDep('python-musicbrainz2'), EasyInstallInst()),
    (GnomeDep('gtk+', '2.16', '[^"]*-bundle_.*_win32.zip'),
        ZipInst('gtk')), # >2.16 has windows theming disabled.
    (GnomeDep('glib', '2.24', 'glib_[^"]*_win32.zip'),
        ZipInst('gtk')), # current svg deps need a newer glib
    #OnePageStep('NSIS', None, re='[^"]*nsis-[1234567890.]*-setup.exe[^"]*',
    #   page='http://nsis.sourceforge.net/Download', args=['/S']),
    ]

    fmt = '%-20s %-15s %s'
    print
    print fmt % ('Package', 'Newest', 'Selected')

    for (dep, inst) in deps:
        print fmt % (dep.name, dep.versions[0], dep.filename)

    print 'Hit enter to continue...'
    raw_input()

    print '\nFetching unfetched dependencies...'
    for (dep, inst) in deps:
        if not dep.fetched:
            fn = join(CACHEDIR, dep.filename)
            with open(fn + '.tmp', 'wb') as fp:
                [fp.write(data) for data in urlfetch(dep.url)]
            os.rename(fn + '.tmp', fn)

    print '\nStarting installation...'

    new_paths = [join(TDIR, 'Python' + d) for d in ['', r'\bin', r'\scripts']]
    new_paths += [join(TDIR, r'gstreamer\PFiles'),
        join(TDIR, r'gstreamer\PFiles\bin')]
    new_paths += [join(TDIR, 'gtk'), join(TDIR, r'gtk\bin')]
    print os.environ['PATH']
    #subprocess.check_call(['path', ';'.join(new_paths + ['%PATH%'])])
    os.environ['PATH'] = ';'.join(new_paths + [os.environ['PATH']])
    print os.environ['PATH']

    for (dep, inst) in deps:
        print 'Installing %s' % dep.name
        inst.install(dep)

    # pygst -> python
    pygst_path = join(TDIR, r'pygst\PFiles\bindings\python\v2.6')
    pygst_dist = join(TDIR, 'Python')
    copytree2(pygst_path, pygst_dist)

    #Overwrite pyexe code which shows the stderr alert box.
    pyexe_dir = os.path.join(TDIR, r'Python\Lib\site-packages')
    site_dir = filter(lambda x: 'py2exe' in x, os.listdir(pyexe_dir))[0]
    pyexe_boot = os.path.join(pyexe_dir, site_dir, r'py2exe\boot_common.py ')
    with open(pyexe_boot, "rb") as f:
        new_text = f.read().replace("gister(alert", "gister(lambda *x: None")
    with open(pyexe_boot, "wb") as f:
        f.write(new_text)

    old_path = os.getcwd()
    repo_path = join(TDIR, 'ql')

    print 'Cloning this repo into temporary directory'
    ccall([HG_PATH, 'clone', '..', repo_path])
    with chdir(join(repo_path, 'quodlibet')):
        print 'Updating to revision %s' % rev
        ccall([HG_PATH, 'pull'])
        ccall([HG_PATH, 'up', rev])
        print 'Applying backports:'
        if rev in BACKPORTS:
            for bp in sorted(BACKPORTS[rev]):
                patch = '%s.patch' % bp
                process = subprocess.Popen(
                    [HG_PATH, 'diff', '-r%d:%d' % (bp-1, bp)],
                    shell=False, stdout=subprocess.PIPE)
                text = process.communicate()[0]
                f = open(patch, 'wb')
                f.write(text)
                f.close()
                ccall([HG_PATH, 'import', '--no-commit', '-f', patch])
                os.remove(patch)
        print 'Assembling Windows binary'
        ccall(['python', 'setup.py', 'py2exe'])

    dist_path = join(TDIR, r'ql\quodlibet\dist')

    # for pygst: one of the libs is looking for _gst.pyd
    shutil.copyfile(os.path.join(dist_path, 'gst._gst.pyd'),
        os.path.join(dist_path, '_gst.pyd'))

    # You must have a license to restribute the resulting installer
    #for file in ['Microsoft.VC90.CRT.manifest', 'msvcr90.dll']:
    #    shutil.copy(join(TDIR, 'Python', file), dist_path)

    # Copy required files from GStreamer distribution
    gst_path = join(TDIR, r'gstreamer\PFiles')
    for file in filter(lambda f: f.endswith('.dll'),
                       os.listdir(join(gst_path, 'bin'))):
        if not os.path.isfile(join(dist_path, file)):
            shutil.copy(join(gst_path, 'bin', file), dist_path)

    for dir in ['lib', 'share', 'etc']:
        copytree2(join(gst_path, dir), join(dist_path, dir))

    # Copy required files from GTK+
    gtk_path = join(TDIR, 'gtk')

    # Generate pixbuf loaders file
    target = os.path.join(gtk_path, 'etc', 'gtk-2.0', 'gdk-pixbuf.loaders')
    process = subprocess.Popen(['gdk-pixbuf-query-loaders.exe'],
        shell=False, stdout=subprocess.PIPE)
    text = process.communicate()[0]
    text = re.compile('".*\/(.*?)\.dll"').sub('\"lib/gtk-2.0/2.10.0/loaders/\\1.dll\"', text)
    f = open(target, 'wb')
    f.write(text)
    f.close()

    for file in filter(lambda f: f.endswith('.dll'),
                       os.listdir(join(gtk_path, 'bin'))):
        if not os.path.isfile(join(dist_path, file)):
            shutil.copy(join(gtk_path, 'bin', file), dist_path)

    for dir in ['lib/gtk-2.0', 'share/locale', 'share/themes', 'etc']:
        copytree2(join(gtk_path, dir), join(dist_path, dir))

    # Copy stock icon replacements
    copytree2('icons', join(dist_path, 'share', 'icons'))

    built_locales = join(os.getcwd(), r'..\quodlibet\build\share\locale')
    # Prune GTK locales without a corresponding QL one:
    for locale in os.listdir(join(dist_path, r'share\locale')):
        if not os.path.isdir(join(built_locales, locale)):
            shutil.rmtree(join(dist_path, r'share\locale', locale))

    # Copy over QL locales
    for locale in os.listdir(built_locales):
        dest = join(dist_path, r'share\locale', locale, 'LC_MESSAGES')
        if not os.path.isdir(dest):
            os.makedirs(dest)
        shutil.copy(join(built_locales, locale, r'LC_MESSAGES\quodlibet.mo'),
                    dest)

    # Set the theme
    shutil.copy(join(dist_path, r'share\themes\MS-Windows\gtk-2.0\gtkrc'),
                join(dist_path, r'etc\gtk-2.0'))

    print "\n\nIf you have a license for redistributing the MSVC runtime,"
    print "you should drop it in %s now." % join(TDIR, r'ql\quodlibet\dist')
    print "Otherwise just hit enter."
    raw_input()

    # Finally, run that installer script.
    subprocess.check_call([NSIS_PATH,
                           join(TDIR, r'ql\junk\win_installer.nsi')])
    shutil.copy(join(TDIR, r'ql\junk\quodlibet-LATEST.exe'),
                'quodlibet-%s-installer.exe' % rev.replace('quodlibet-', ''))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Run this script with a tag or revision as the only arg."
        sys.exit(1)

    if not os.path.isdir('../quodlibet/build/share/locale'):
        print "You should run 'python setup.py build_mo' from a Linux"
        print "machine, copy the repo over (or use a network mount), and"
        print "run this script from that repo."
        sys.exit(1)

    if not os.path.isdir(CACHEDIR):
        os.mkdir(CACHEDIR)

    TDIR = tempfile.mkdtemp()
    print "Created temporary directory at %s" % TDIR
    try:
        do_setup(sys.argv[1])
        print "Okay, your installer should now be in this directory."
        print "Removing temporary directory at %s" % TDIR
        shutil.rmtree(TDIR)
        print "All done."
    except:
        traceback.print_exc()
        print "Not removing temporary directory %s" % TDIR


