The Windows installer can now be built mostly automatically from a Windows
host. To do so, you need a few things installed on your Windows system:

 * Python 2.x (2.6 or greater is probably required):
    http://python.org/download/
 * Mercurial: http://mercurial.selenic.com/downloads/
 * NSIS: http://nsis.sourceforge.net/Download

These programs are used in the build process, but aren't bundled into the
installer, so you don't have to worry about keeping them strictly up to date.
The build script looks for these in default locations, which you may need to
adjust (but probably do not).

You'll also need a copy of the Quod Libet Mercurial tree with messages
generated. A simple way to do this is to make a checkout on Linux, 'hg up' to
the revision you want to build an installer for, and run 'setup.py build_mo'.
Once that's done, copy it over to your Windows host, or make it accessible via
a network mount.

From a Windows command prompt in this folder, run:

    > C:\Python26\python.exe win_installer_build.py quodlibet-2.2.1

replacing values as necessary. The script will pull down appropriate
dependencies, unpack and bootstrap a Python distribution, and build the
installer, ideally without touching anything outside of a few temporary
directories.

Near the end, it will pause to let you copy the MSVC runtime, if you have it.
Most people don't need this, but it's nice to have for the official installer.
You can probably skip it.

The original instructions follow because the script is a bit inscrutable.
They will not be kept up to date, but they do follow along approximately.

== Gather Dependencies ==

* Python 2
* GTK+-bundle (unpack into Python 2 directory)
* pyCairo
* pyGObject
* pyGTK
* GStreamer WinBuilds
* pyGst WinBuilds
* Python: (note, if using easy_install you must install with '-Z')
    * mutagen
    * feedparser
    * py2exe
    * python-musicbrainz2
* NSIS

== Build ==

In the usual manner. Use the distutils command 'py2exe'.

== Copy ==

All of these things should go in 'quodlibet/dist':

* From the GTK+-bundle: 'etc', 'lib', 'share/locale', 'share/themes'

* From your GStreamer WinBuilds install dir: dump the contents of 'bin'
  straight into 'quodlibet/dist', but do not overwrite any files when asked.
  Copy 'lib', 'share', and 'etc' over as whole directories.

* From a computer running a real operating system: do a 'build_mo' then copy
  the contents of 'build/share' to 'quodlibet/dist/share'.

== Pack ==

Remove any GTK locale which doesn't have a corresponding QL one:
    $ for i in share/locale/*; do if test \! -e "../build/$i"; then \
        rm -r "$i"; fi; done

Remove any non-DLL from dist/lib:
    $ find lib -type f \! -iname '*dll' -delete

Set the theme:
    $ cp share/themes/MS-Windows/gtk-2.0/gtkrc etc/gtk-2.0/

Run the installer NSI script to write the installer.
