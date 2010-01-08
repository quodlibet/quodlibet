== Gather Dependencies ==

* Python 2
* GTK+-bundle (unpack into Python 2 directory)
* pyCairo
* pyGObject
* pyGTK
* GStreamer WinBuilds
* pyGst WinBuilds
* Python:
    * mutagen
    * feedburner
    * py2exe
* NSIS

== Build ==

In the usual manner. Use the distutils command 'py2exe'.

== Copy ==

All of these things should go in 'quodlibet/dist':

* From the GTK+-bundle: 'etc', 'lib', and everything in 'share' except the docs

* From your GStreamer WinBuilds install dir: dump the contents of 'bin'
  straight into 'quodlibet/dist', but do not overwrite any files when asked.
  Copy 'lib', 'share', and 'etc' over as well.

* From a computer running a real operating system: do a 'build_mo' then copy
  the contents of 'build/share' to 'quodlibet/dist'. I have no idea if this
  will actually result in localization for Windows users but it's worth a try.

== Pack ==

Check the version string in the installer MSI, then run it.

