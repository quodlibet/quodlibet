#!/usr/bin/python
#
# Copyright 2010 Steven Robertson

"""A hastily-organized auto-build script to generate the Windows installer."""

from __future__ import with_statement

import re
import os
import sys
import shutil
import urllib2
import zipfile
import optparse
import tempfile
import traceback
import subprocess

import BeautifulSoup

from os.path import join

CACHEDIR = os.path.expanduser('~/.ql_winbuild_cache')
DLLS = ['dnsapi.dll', 'imagehlp.dll', 'msimg32.dll', 'powrprof.dll']

def read_url(url):
    u = urllib2.urlopen(url)
    text = u.read()
    u.close()
    return text

def vsorted(lst):
    return sorted(lst, key=lambda k:
            map(lambda s: not s.isdigit() and s or int(s), k.split('.')))

class Step(object):
    """
    The base class for a dependency.

    The idea seemed a *lot* better when I started than when I finished.
    """


    @classmethod
    def setup(cls):
        """Sets up parameters shared by all steps."""
        cls._winedir = tempfile.mkdtemp()
        if not os.path.isdir(CACHEDIR):
            os.makedirs(CACHEDIR)

    @classmethod
    def wine_cmd(cls, cmd):
        """Runs a command in Wine."""
        env = dict(os.environ)
        env['WINEPREFIX'] = cls._winedir
        subprocess.check_call(['wine'] + cmd, env=env)

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

    def install(self):
        """Installs the package as needed to the Wine directory."""
        pass

    def dist_install(self):
        """Does any post-build copying or pruning needed."""
        pass

class MSIInstallMixin (object):
    """Installs an MSI package."""

    def install(self):
        self.wine_cmd(['msiexec', '/q', '/i',
                        join(CACHEDIR, self.filename)])

class ExeInstallMixin (object):
    """Installs an executable, without automation."""

    def __init__(self, *args, **kwargs):
        self.args = []
        if 'args' in kwargs:
            self.args = kwargs.pop('args')

        super(ExeInstallMixin, self).__init__(*args, **kwargs)

    def install(self):
        self.wine_cmd([join(CACHEDIR, self.filename)] + self.args)

class EasyInstallExeMixin (object):
    """Installs a SetupTools executable silently."""

    def install(self):
        self.wine_cmd(['C:/Python26/Scripts/easy_install.exe', '-Z',
                        join(CACHEDIR, self.filename)])

class ZipUnpackInstallMixin (object):
    """
    Unpacks a zip file into a particular directory. The path relative to
    wineroot must be specified as 'unpackpath' to __init__.
    """

    def __init__(self, *args, **kwargs):
        path = kwargs.pop('unpackpath')
        self.path = join(Step._winedir, 'drive_c', path)
        super(ZipUnpackInstallMixin, self).__init__(*args, **kwargs)

    def install(self):
        zf = zipfile.ZipFile(join(CACHEDIR, self.filename))
        # Deal with case-sensitive file paths
        def reduce_func(x, y):
            if not os.path.exists(x):
                os.mkdir(x)
            n = filter(lambda d: y.lower() == d.lower(), os.listdir(x))
            return join(x, n and n[0] or y)
        for item in zf.filelist:
            path = reduce(reduce_func, item.filename.split('/'), self.path)
            with open(path, 'w') as fp:
                fp.write(zf.read(item))

class PythonStep(MSIInstallMixin, Step):

    def _get_versions(self):
        url = 'http://www.python.org/download/releases/'
        return re.findall('href="/download/releases/([1234567890.]+)[/]?"',
                          read_url(url))

    def _get_release(self, version):
        return ('http://www.python.org/ftp/python/%(ver)s/python-%(ver)s.msi' %
                {'ver': version})

class GnomeProjectStep(Step):

    def __init__(self, *args, **kwargs):
        self.url_re = 'href="(%s)"' % kwargs.pop('re')
        super(GnomeProjectStep, self).__init__(*args, **kwargs)

    def _get_versions(self):
        self.project_url = (
            'http://ftp.gnome.org/pub/gnome/binaries/win32/%s' % self.name)
        return re.findall('href="([1234567890.]+)[/]?"',
                          read_url(self.project_url))

    def _get_release(self, version):
        filename = vsorted(re.findall(self.url_re,
                        read_url(join(self.project_url, version))))[-1]
        return join(self.project_url, version, filename)

class GnomePyStep(EasyInstallExeMixin, GnomeProjectStep):
    pass

class GnomeBundleStep(ZipUnpackInstallMixin, GnomeProjectStep):
    pass

class OnePageStep(ExeInstallMixin, Step):

    def __init__(self, *args, **kwargs):
        self.url_re = kwargs.pop('re')
        self.page = kwargs.pop('page')
        super(OnePageStep, self).__init__(*args, **kwargs)

    def _get_versions(self):
        return ['automatic']

    def _get_release(self, version):
        # Note: does not catch end quote by design (for pypi compat)
        return vsorted(re.findall('href="(%s)' % self.url_re,
                                 read_url(self.page)))[-1]

class SFStep(EasyInstallExeMixin, Step):
    def __init__(self, *args, **kwargs):
        self.file_re = kwargs.pop('re')
        super(SFStep, self).__init__(*args, **kwargs)

    def _get_versions(self):
        return ['automatic']

    def _get_release(self, version):
        urls = vsorted(re.findall(
            "url: '(http://downloads.sourceforge.net/project/%s/[^']*%s[^']*)'"
            % (self.name, self.file_re),
            read_url('http://sourceforge.net/projects/%s/files/' % self.name)))
        return urls[-1]

class EasyInstallStep(object):
    versions = ['automatic']
    filename = 'automatic'

    def __init__(self, package):
        self.name = package

    @property
    def fetched(self):
        return True

    def install(self):
        Step.wine_cmd(
                ['C:/Python26/Scripts/easy_install.exe', '-Z', self.name])

    def dist_install(self):
        pass

def do_setup(rev):
    deps = [
    PythonStep('Python', '2.6'),
    GnomeBundleStep('gtk+', '2.20', re='[^"]*-bundle_.*_win32.zip',
                    unpackpath='Python26'),
    GnomeBundleStep('libglade', '2.6', re='[^"]*libglade_[^"]*win32.zip',
                    unpackpath='Python26'),
    OnePageStep('setuptools', None, re='[^"]*setuptools[^"]*py2.6.exe[^"#]*',
        page='http://pypi.python.org/pypi/setuptools'),
    GnomePyStep('pycairo', '1.8', re='[^"]*win32-py2.6.exe'),
    GnomePyStep('pygobject', '2.20', re='[^"]*win32-py2.6.exe'),
    GnomePyStep('pygtk', '2.16', re='[^"]*glade.win32-py2.6.exe'),
    OnePageStep('GStreamer', None,
        re='[^"]*GStreamerWinBuild-[1234567890.]*.exe',
        page='http://www.gstreamer-winbuild.ylatuya.es/doku.php?id=download',
        args=['/VERYSILENT']),
    OnePageStep('pygst', None, re='[^"]*Pygst-[^"]*-Python26[^"]*',
        page='http://www.gstreamer-winbuild.ylatuya.es/doku.php?id=download',
        args=['/VERYSILENT']),
    SFStep('py2exe', None, re='py2exe-[1234567890.]*.win32-py2.6.exe'),
    SFStep('pywin32', None, re='pywin32-[1234567890.]*.win32-py2.6.exe'),
    EasyInstallStep('mutagen'),
    EasyInstallStep('feedparser'),
    EasyInstallStep('python-musicbrainz2'),
    OnePageStep('NSIS', None, re='[^"]*nsis-[1234567890.]*-setup.exe[^"]*',
       page='http://nsis.sourceforge.net/Download', args=['/S']),
    ]

    fmt = '%-20s %-15s %s'
    print
    print fmt % ('Package', 'Newest', 'Selected')

    for dep in deps:
        print fmt % (dep.name, dep.versions[0], dep.filename)

    print 'Hit enter to continue...'
    raw_input()

    print '\nFetching unfetched dependencies...'
    for dep in deps:
        if not dep.fetched:
            print dep.url
            data = read_url(dep.url)
            with open(join(CACHEDIR, dep.filename), 'w') as fp:
                fp.write(data)

    print '\nStarting installation...'
    for dep in deps:
        print 'Installing %s' % dep.name
        dep.install()

    print '\nEditing PATH and adding DLL override'
    reg = r"""REGEDIT4

[HKEY_CURRENT_USER\Environment]
"PATH"="C:\\Python26;C:\\Python26\\bin;C:\\gstreamer;C:\\gstreamer\\bin"

[HKEY_CURRENT_USER\Software\Wine\DllOverrides]
"imagehlp"="native,builtin"
"""
    with tempfile.NamedTemporaryFile(suffix='.reg') as fp:
        fp.write(reg)
        fp.flush()
        Step.wine_cmd(['regedit', fp.name])

    print 'Copying over requisite DLLs'
    for dll in DLLS:
        shutil.copy(join('dlls', dll),
                    join(Step._winedir, 'drive_c/windows/system32'))

    old_path = os.getcwd()
    repo_path = join(Step._winedir, 'drive_c/ql')
    if not os.path.isdir(repo_path):
        print 'Cloning this repo into temporary directory'
        subprocess.check_call(['hg', 'clone', '..', repo_path])
    os.chdir(join(repo_path, 'quodlibet'))
    print 'Updating to revision %s' % rev
    subprocess.check_call(['hg', 'pull'])
    subprocess.check_call(['hg', 'up', rev])

    print 'Generating message catalogs'
    subprocess.check_call(['python', 'setup.py', 'build_mo'])


    print 'Assembling Windows binary'
    #Step.wine_cmd(['python', 'setup.py', 'py2exe', '-b', '1'])


    print 'Nope, building zipfile instead'

    os.chdir(join(Step._winedir, 'drive_c'))
    zf = zipfile.ZipFile(join(old_path, 'build.zip'), 'w')
    for dir in ['ql', 'Python26']:
        for root, dirs, files in os.walk(dir):
            for file in files:
                zf.write(join(root, file))
    zf.writestr('build.cmd', r"""
path %CD%\Python26;%CD%\Python26\bin;%PATH%
cd ql
cd quodlibet
python setup.py py2exe
python pack.py
cd ..
cd ..
""")

    zf.writestr('ql/quodlibet/pack.py', """#!/usr/bin/python
import zipfile
import os
zf = zipfile.ZipFile("../../dist.zip", "w")
for root, dirs, files in os.walk("dist"):
    for file in [os.path.join(root, f) for f in files]:
        print "Adding %s" % file
        zf.write(file)
zf.close()
""")
    zf.close()
    os.chdir(old_path)


    print "Okay, Wine has a few upstream bugs, preventing things from"
    print "being run entirely on it yet. For now, take the file 'build.zip',"
    print "extract it on a Windows host, run 'build.cmd', and copy the"
    print "resulting 'dist.zip' to this directory (%s)." % os.getcwd()
    print "I'll wait.\n\nHit enter when finished."
    raw_input()

    zf = zipfile.ZipFile('dist.zip')
    zf.extractall(join(Step._winedir, 'drive_c/ql/quodlibet'))

    dist_path = join(Step._winedir, 'drive_c/ql/quodlibet/dist')

    # py2exe doesn't catch these files when running in wine
    for file in ['Microsoft.VC90.CRT.manifest', 'msvcr90.dll']:
        shutil.copy(join(Step._winedir, 'drive_c/Python26', file), dist_path)

    # Copy required files from GStreamer distribution
    gst_path = join(Step._winedir, 'drive_c/gstreamer')
    for file in filter(lambda f: f.endswith('.dll'),
                       os.listdir(join(gst_path, 'bin'))):
        if not os.path.isfile(join(dist_path, file)):
            shutil.copy(join(gst_path, 'bin', file), dist_path)

    for dir in ['lib', 'share', 'etc']:
        shutil.copytree(join(gst_path, dir), join(dist_path, dir))

    # Unpack necessities from GTK+ bundle
    bundle = filter(lambda d: d.name == 'gtk+', deps)[0]
    zf = zipfile.ZipFile(join(CACHEDIR, bundle.filename))
    for item in zf.filelist:
        if (item.filename.startswith('lib') and
            item.filename.endswith('.dll')) or filter(
                item.filename.startswith,
                ['etc', 'share/locale', 'share/themes']):
            zf.extract(item, path=dist_path)
        elif item.filename.startswith('bin') and item.filename.endswith('dll'):
            dest = join(dist_path, os.path.basename(item.filename))
            #with open(dest, 'w') as fp:
            #    fp.write(zf.read(item))

    built_locales = join(dist_path, '../build/share/locale')
    # Prune GTK locales without a corresponding QL one:
    for locale in os.listdir(join(dist_path, 'share/locale')):
        if not os.path.isdir(join(built_locales, locale)):
            shutil.rmtree(join(dist_path, 'share/locale', locale))

    # Copy over QL locales
    for locale in os.listdir(built_locales):
        dest = join(dist_path, 'share/locales', locale, 'LC_MESSAGES')
        if not os.path.isdir(dest):
            os.makedirs(dest)
        shutil.copy(join(built_locales, locale, 'LC_MESSAGES/quodlibet.mo'),
                    dest)

    # Set the theme
    shutil.copy(join(dist_path, 'share/themes/MS-Windows/gtk-2.0/gtkrc'),
                join(dist_path, 'etc'))

    # Finally, run that installer script.
    Step.wine_cmd(['C:/Program Files/NSIS/makensis.exe',
                   'C:/ql/junk/win_installer.nsi'])
    shutil.copy(join(Step._winedir, 'drive_c/ql/junk/quodlibet-LATEST.exe'),
                'quodlibet-%s-installer.exe' % rev.replace('quodlibet-', ''))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Run this script with a tag or revision as the only arg."
        sys.exit(1)

    for dll in DLLS:
        if not os.path.isfile(join('dlls', dll)):
            print "You'll need to place copies of the following DLLs from a"
            print "Windows installation into the folder './dlls':"
            print '    %s' % ' '.join(DLLS)
            sys.exit(1)

    Step.setup()
    print "Created temporary wine directory at %s" % Step._winedir
    try:
        do_setup(sys.argv[1])
        print "Okay, your installer should now be in this directory."
    except:
        traceback.print_exc()

    print "Removing temporary wine directory at %s" % Step._winedir
    shutil.rmtree(Step._winedir)

    print "Removing build.zip, dist.zip (if they exist)"
    if os.path.isfile('build.zip'):
        os.unlink('build.zip')
    if os.path.isfile('dist.zip'):
        os.unlink('dist.zip')

    print "All done."

