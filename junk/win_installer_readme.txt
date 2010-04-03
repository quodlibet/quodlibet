The Windows installer can now be built mostly automatically. There are a ton
of quirks, but the script will prompt you through most of them, and since they
are expected to change as new versions of Wine come out it's not worth
documenting them here.

In short, run

    python win_installer_build.py quodlibet-2.2.1

on a Linux computer with Wine, and follow the prompts.

The original instructions follow because the script is a bit inscrutable.

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
