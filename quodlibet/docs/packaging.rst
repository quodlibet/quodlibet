.. _PackagingGuide:

Packaging Guide
===============

This page is directed at distributions, packagers and developers. Please
:ref:`contact us <Contact>` if there is anything unclear / out of date /
missing. For license & copyright information see :ref:`license`


Changes
-------

3.6
^^^

* **Mutagen 1.30** required
* **GTK+ 3.10** required
* **PyGObject 3.10** required
* **webkitgtk-3.0** → **webkit2gtk-4.0** (Lyrics Window plugin)
* **sphinx 1.3** required for building the documentation
* New optional plugin dependency: **libappindicator-gtk3** + **typelibs**:
  for the Tray Icon plugin under Ubuntu Unity and KDE Plasma
* **python-musicbrainzngs** instead of **python-musicbrainz2**
* **python-cddb** no longer needed


3.5
^^^

* **Mutagen 1.27** required


3.4
^^^

* The main repo moved from Mercurial (Google Code) to Git (GitHub)
* The build should now be reproducible
* **gtk-update-icon-cache** is no longer a build dependency
* **gettext >= 0.15** is required now at build time
* A complete **icon theme** is now required (this was also partly the case
  with 3.3) and an icon theme including symbolic icons is recommended.
  **adwaita-icon-theme** provides both for example.
* **Mutagen 1.22** required, **Mutagen 1.27** recommended
* New files installed to ``/usr/share/icons/hicolor/scalable/apps/``
* **quodlibet.desktop** now contains a **MimeType** entry, which means
  calling **update-desktop-database** is needed after package installation.


3.3
^^^

* New optional plugin dependency: **webkitgtk-3.0 + typelibs**
* **Mutagen 1.27** recommended

3.2
^^^

* **Plugins got merged** into Quod Libet. This means the quodlibet-plugins
  tarball is gone and plugins will be installed by ``setup.py install``. For
  distros that used to include the plugins in the main package this means all
  plugin related packaging code can simply be removed. For distros that
  offered separate packages the installation can be split by packaging
  ``quodlibet/ext`` in a separate package. Quod Libet can run without it.

* **UDisks2** is supported, in addition to UDisks1

* **Python 2.7** required instead of 2.6 (might still work, but not tested)

3.1
^^^

* **No changes** compared to 3.0


Existing Packaging
------------------

The following distributions package Quod Libet:

* Arch Linux: https://www.archlinux.org/packages/extra/any/quodlibet/
* Debian: https://packages.debian.org/source/sid/quodlibet
* Fedora: https://admin.fedoraproject.org/pkgdb/package/quodlibet/

The Ubuntu PPA / unstable repo builds are automated by the following scripts:

https://github.com/lazka/quodlibet-ppa


.. _Dependencies:

Non-Optional Runtime Dependencies
---------------------------------

The following software is needed to start Ex Falso or Quod Libet.

* **Python** (2.7)
* **PyGObject** including **cairo support** (>= 3.10)
* **pycairo** (>= 1.8)
* **mutagen** (>= 1.30)
* **GTK+** (>= 3.10)
* On Windows only: **pywin32**
* On OS X only: **PyObjC**

For icons a complete **icon theme** is needed, preferably with symbolic icons. 
For example **adwaita-icon-theme** or the older **gnome-icon-theme** + 
**gnome-icon-theme-symbolic**

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

**python-musicbrainzngs**:
    * For the musicbrainz plugin

**GStreamer Plugins Good**:
    * For the replaygain plugin

**GStreamer Plugins Bad**:
    * For the acoustid plugin

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

**webkit2gtk** (== 4.0) + **typelibs**:
    * For the Lyrics Window plugin

**libappindicator-gtk3** + **typelibs**:
    * For the Tray Icon plugin under Ubuntu Unity and KDE Plasma


Build Dependencies
------------------

* **Python** 2.7 (stdlib only)
* **gettext** >= 0.15 and **intltool** for translations.
* (optional) **sphinx** >= 1.3

For user documentation ``setup.py build_sphinx`` can be used to create the
HTML user guide and put it in the build directory in the ``sphinx``
subdirectory. This is not part of the default build process and requires
**sphinx**.
