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

* **Python** (2.7)
* **PyGObject** including **cairo support** (>= 3.2)
* **pycairo**
* **mutagen** (>= 1.14)
* **GTK+** (>= 3.2)
* On Windows only: **pywin32**

For playback support in Quod Libet one of the following two is needed:

GStreamer
^^^^^^^^^

Required:
    * **GStreamer** (>= 1.0) + **typelibs**
    * **GStreamer Plugins Base**: Vorbis, Alsa, ...

Optional but recommended:
    * **GStreamer Plugins Good**: Pulseaudio, FLAC, Jack, ...
    * **GStreamer Plugins Ugly**: MP3 (mad), ...
    * **GStreamer Plugins Bad**: MP3 (mpg123), MP4, Opus, ...
    * **GStreamer libav/ffmpeg**: WMA, ...

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

**udisks** or **udisks2**:
    * For detection of DAPs

**python-feedparser**:
    * For the feed browser

**libmodplug1**:
    * For MOD support


Plugin Dependencies
-------------------

All plugin dependencies are optional and will only prevent the corresponding
plugin from loading.

**notification-daemon** (or any other implementation of the dbus spec):
    * For the notification plugin

**python-musicbrainz2**:
    * For the musicbrainz plugin

**GStreamer Plugins Good**:
    * For the replaygain plugin

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

* **Python** 2.7 (stdlib only)
* **intltool** for translations.
* The **gtk-update-icon-cache** executable for creating the
  fallback icon theme cache.

For user documentation ``setup.py build_sphinx`` can be used to create the
HTML user guide and put it in the build directory in the ``sphinx``
subdirectory. This is not part of the default build process and requires
**sphinx**.


Changes
-------

3.0 → 3.1
^^^^^^^^^

* **No changes** compared to 3.0

3.1 → 3.2
^^^^^^^^^

* **Plugins got merged** into Quod Libet. This means the quodlibet-plugins
  tarball is gone and plugins will be installed by ``setup.py install``. For
  distros that used to include the plugins in the main package this means all
  plugin related packaging code can simply be removed. For distros that
  offered separate packages the installation can be split by packaging
  ``quodlibet/ext`` in a separate package. Quod Libet can run without it.

* **UDisks2** is supported, in addition to UDisks1

* **Python 2.7** required instead of 2.6 (might still work, but not tested)
