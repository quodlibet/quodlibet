.. _Downloads:

.. include:: icons.rst

Downloads
=========

================ ================================================ ==========================================
**Linux:**       |flatpak-logo| :ref:`Flatpak <flatpak>`
   \             |ubuntu-logo| :ref:`Ubuntu <ubuntu>`             |debian-logo| :ref:`Debian <debian>`
   \             |fedora-logo| :ref:`Fedora <fedora>`             |opensuse-logo| :ref:`openSUSE <opensuse>`
   \             |arch-logo| :ref:`Arch Linux <arch>`
**Windows:**     |windows-logo| :ref:`Windows <windows>`
**macOS:**       |macosx-logo| :ref:`macOS <macosx>`
**Development:** |source-logo| :ref:`Release Tarballs <tarballs>`
================ ================================================ ==========================================

All files are signed with the following key: `0EBF 782C 5D53 F7E5 FB02  A667 46BD 761F 7A49 B0EC <http://keyserver.ubuntu.com/pks/lookup?op=vindex&search=0x46BD761F7A49B0EC&fingerprint=on>`__

----


.. _tarballs:

|source-logo| Release Tarballs
------------------------------

.. include:: tables/default.rst

For old releases see the `full file listing <https://github.com/quodlibet/quodlibet/releases>`__.


.. _flatpak:

|flatpak-logo| Flatpak
----------------------

* `Quod Libet <https://flathub.org/apps/details/io.github.quodlibet.QuodLibet>`__ on Flathub
* `Ex Falso <https://flathub.org/apps/details/io.github.quodlibet.ExFalso>`__ on Flathub

.. _ubuntu:

|ubuntu-logo| Ubuntu
--------------------

::

    $ sudo add-apt-repository ppa:lazka/ppa

.. _debian:

|debian-logo| Debian
--------------------

* Debian Stable::

    # deb http://lazka.github.io/ql-debian/stable/ quodlibet-stable/

    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5A62D0CAB6264964
    sudo apt-get update
    sudo apt-get install quodlibet


.. _fedora:

|fedora-logo| Fedora
--------------------

* `Fedora Stable Repo <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-stable&package=quodlibet>`__

Check out the `official
repos <https://apps.fedoraproject.org/packages/quodlibet/overview/>`__ first -
they usually contain the latest release.


.. _opensuse:

|opensuse-logo| openSUSE
------------------------

* `openSUSE Stable Repo <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-stable&package=quodlibet>`__

.. _arch:

|arch-logo| Arch Linux
----------------------

::

    $ pacman -S quodlibet


.. _windows:

|windows-logo| Windows
----------------------

.. include:: tables/windows.rst

.. include:: tables/windows_portable.rst

For old releases see the `full file listing <https://github.com/quodlibet/quodlibet/releases>`__.


.. _macosx:

|macosx-logo| macOS
-------------------

.. include:: tables/osx_quodlibet.rst

.. include:: tables/osx_exfalso.rst

For old releases see the `full file listing <https://github.com/quodlibet/quodlibet/releases>`__.
