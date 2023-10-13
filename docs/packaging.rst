.. _PackagingGuide:

Packaging Guide
===============

This page is directed at distributions, packagers and developers. Please
:ref:`contact us <Contact>` if there is anything unclear / out of date /
missing. For license & copyright information see :ref:`license`

Existing Packaging
------------------

The following distributions package Quod Libet:

* Arch Linux: https://www.archlinux.org/packages/extra/any/quodlibet/
* Debian: https://packages.debian.org/source/sid/quodlibet
* Fedora: https://admin.fedoraproject.org/pkgdb/package/rpms/quodlibet/

The Ubuntu PPA / unstable repo builds are automated by the following scripts:

https://github.com/quodlibet/ppa-scripts


.. _Dependencies:

Mandatory Runtime Dependencies
------------------------------

The following software is needed to start Ex Falso or Quod Libet.

* **Python** (>= 3.8)
* **PyGObject** including **cairo support** (>= 3.18)
* **pycairo** (>= 1.8)
* **mutagen** (>= 1.34)
* **GTK+** (>= 3.18)
* **libsoup** (>= 3.0)
* **gir1.2-soup-3.0**
* On OS X only: **PyObjC**
* **feedparser**

For icons a complete **icon theme** is needed, preferably with symbolic icons. 
For example **adwaita-icon-theme**.

For playback support in Quod Libet one of the following two is needed:

GStreamer
^^^^^^^^^

Required:
    * **GStreamer** (>= 1.8) + **typelibs**
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

**dbus-python**:
    * Enables the DBus interface
    * Multimedia key support under GNOME

**libkeybinder-3.0** + **typelib**:
    * Multimedia key support under non Gnome setups

**libgtksourceview-4** + **typelib**:
    * Undo/Redo support for multiline text fields

**libmodplug1**:
    * For MOD support


Plugin Dependencies
-------------------

All plugin dependencies are optional and will only prevent the corresponding
plugin from loading.

**notification-daemon** (or any other implementation of the dbus spec):
    * For the notification plugin

**GStreamer Plugins Good**:
    * For the replaygain plugin

**GStreamer Plugins Bad**:
    * For the acoustid plugin

**rygel**:
    * The uPnP media server

**webkit2gtk** (== 4.0) + **typelibs**:
    * For the Lyrics Window plugin

**libappindicator-gtk3** + **typelibs**:
    * For the Tray Icon plugin under Ubuntu Unity and KDE Plasma

Python libraries
^^^^^^^^^^^^^^^^
These can be installed with pip (as well as OS-level packages in some places).

**dbus-python**:
    * "Browse Folders"
    * Screensaver plugins
    * uPnP server
    * Gnome search provider
    * gajim status updater
    * MPRIS
    * ...

**paho-mqtt**
    * For the MQTT plugin

**musicbrainzngs** (>= 0.6):
    * For the Musicbrainz plugin

**soco** (>0.27):
    * For the Sonos plugins

**pypresence**:
    * For the Discord plugin

Build Dependencies
------------------

* **Python** >= 3.8 (stdlib only)
* **gettext** >= 0.19.8 for translations.
* (optional) **sphinx** >= 1.3

For user documentation ``setup.py build_sphinx`` can be used to create the
HTML user guide and put it in the build directory in the ``sphinx``
subdirectory. This is not part of the default build process and requires
**sphinx**.


Testing Dependencies
--------------------

* The build dependencies
* **pytest**
* **flake8**
* **polib**
