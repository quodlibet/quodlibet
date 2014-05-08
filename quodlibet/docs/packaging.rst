.. _PackagingGuide:

Packaging Guide
===============

This page is directed at distributions, packagers and developers.

Please :ref:`contact us <Contact>` if there is anything unclear / out of date / 
missing.

For license & copyright information see :ref:`license`


Existing Packaging
------------------

The following distributions package Quod Libet:

* Arch Linux: https://www.archlinux.org/packages/extra/any/quodlibet/
* Debian: https://packages.debian.org/source/sid/quodlibet
* Fedora: https://admin.fedoraproject.org/pkgdb/acls/name/quodlibet

The Ubuntu PPA / unstable repo builds are automated by the following scripts:

https://github.com/lazka/quodlibet-ppa


.. _Dependencies:

Non-Optional Runtime Dependencies
---------------------------------

The following software is needed to start Ex Falso or Quod Libet.

* **Python** (>= 2.6)
* **PyGObject** including **cairo support** (>= 3.2)
* **pycairo**
* **mutagen** (>= 1.14)
* **GTK+** (>= 3.2)
* On Windows only: **pywin32**

For playback support in Quod Libet one of the following two is needed:

GStreamer
^^^^^^^^^

* **GStreamer** (>= 1.0) + **typelibs**
* **GStreamer Plugins Good**

Particular audio formats depend on various *GStreamer* decoding elements, as 
well as other Python modules. GStreamer splits their downloads into *''good''*, 
*''bad''*, *''ugly''*, and *''ffmpeg/av''* packages, each of which contains 
elements; you probably want them all.

Xine
^^^^

* **xine-lib** 1.1 or 1.2 (the shared library, no Python bindings)


Optional Runtime Dependencies
-----------------------------

**gnome-symbolic-icon-theme**:

    * For symbolic icons; QL will fall back to colored ones if needed.

**dbus-python**:

    * Enables the DBus interface
    * Multimedia key support under GNOME

**pyhook** (Windows only):

    * Multimedia key support under Windows

**libkeybinder-3.0** + **typelib**:

    * Multimedia key support under non Gnome setups

**libgpod4** (the shared library, no Python bindings):

    * iPod support

**libgtksourceview-3** + **typelib**:

    * Undo/Redo support for multiline text fields

**media-player-info**:

    * For detection of DAPs

**udisks** (not udisks2):

    * For detection of DAPs

**python-feedparser**:

    * For the feed browser

**libmodplug1**:

    * For MOD support


Plugin Dependencies
-------------------

All plugin dependencies are optional and will only prevent the corresponding 
plugin from loading.

**notification-deamon** (or any other implementation of the dbus spec):

    * For the notification plugin

**python-musicbrainz2**:

    * For the musicbrainz plugin

**GStreamer Plugins Bad**:

    * For the acoustid plugin

**python-cddb**:

    * For the CDDB plugin

**python-dbus**:

    * "Browse Folders"
    * Screensaver plugins
    * uPnP server
    * Gnome search provider
    * gajim status updater
    * MPRIS
    * ...

**rygel**:

    * The uPnP media server

**Zeitgeist Python bindings**:

    * For the zeitgeist plugin

**pynotify**:

    * For the auto library update plugin


Build Dependencies
------------------

* **Python** 2.6+ (stdlib only)
* **intltool** for translations.
* The **gtk-update-icon-cache** executable for creating the
  fallback icon theme cache.

For user documentation ``setup.py build_sphinx`` can be used to create the 
HTML user guide and put it in the build directory in the ``sphinx`` 
subdirectory. This is not part of the default build process and requires 
**sphinx**.


Changes
-------

3.1.x
^^^^^

    No changes compared to 3.0
