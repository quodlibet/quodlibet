.. _Downloads:

.. include:: icons.rst

Downloads
=========

================ ================================================ ==========================================
**Linux:**       |ubuntu-logo| :ref:`Ubuntu <ubuntu>`             |debian-logo| :ref:`Debian <debian>`
   \             |fedora-logo| :ref:`Fedora <fedora>`             |opensuse-logo| :ref:`openSUSE <opensuse>`
   \             |arch-logo| :ref:`Arch Linux <arch>`
**Windows:**     |windows-logo| :ref:`Windows <windows>`
**Mac OS X:**    |macosx-logo| :ref:`Mac OS X <macosx>`
**Development:** |source-logo| :ref:`Release Tarballs <tarballs>`
================ ================================================ ==========================================

All files are signed with the following key: `0EBF 782C 5D53 F7E5 FB02  A667 46BD 761F 7A49 B0EC <http://keyserver.ubuntu.com/pks/lookup?op=vindex&search=0x46BD761F7A49B0EC&fingerprint=on>`__

----


.. _tarballs:

|source-logo| Release Tarballs
------------------------------

========================== =============================== ================================================== ============================================
Release                    File                            SHA256                                             PGP
========================== =============================== ================================================== ============================================
Quod Libet 3.9.0           quodlibet-3.9.0.tar.gz_         `SHA256 <quodlibet-3.9.0.tar.gz.sha256_>`_         `SIG <quodlibet-3.9.0.tar.gz.sig_>`_
Quod Libet 3.8.1           quodlibet-3.8.1.tar.gz_         `SHA256 <quodlibet-3.8.1.tar.gz.sha256_>`_         `SIG <quodlibet-3.8.1.tar.gz.sig_>`_
Quod Libet 3.7.1           quodlibet-3.7.1.tar.gz_         `SHA256 <quodlibet-3.7.1.tar.gz.sha256_>`_         `SIG <quodlibet-3.7.1.tar.gz.sig_>`_
========================== =============================== ================================================== ============================================

.. _quodlibet-3.9.0.tar.gz: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0.tar.gz
.. _quodlibet-3.9.0.tar.gz.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0.tar.gz.sha256
.. _quodlibet-3.9.0.tar.gz.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0.tar.gz.sig

.. _quodlibet-3.8.1.tar.gz: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1.tar.gz
.. _quodlibet-3.8.1.tar.gz.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1.tar.gz.sha256
.. _quodlibet-3.8.1.tar.gz.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1.tar.gz.sig

.. _quodlibet-3.7.1.tar.gz: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1.tar.gz
.. _quodlibet-3.7.1.tar.gz.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1.tar.gz.sha256
.. _quodlibet-3.7.1.tar.gz.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1.tar.gz.sig

For old releases see the `full file listing <https://github.com/quodlibet/quodlibet/releases>`__.


.. _ubuntu:

|ubuntu-logo| Ubuntu
--------------------

Stable Repo (14.04+):
    ::

        $ sudo add-apt-repository ppa:lazka/ppa


Unstable PPA (16.04+):
    ::

        $ sudo add-apt-repository ppa:lazka/dumpingplace


.. _debian:

|debian-logo| Debian
--------------------

Stable Repo:
    * Debian Stable::

        # deb http://lazka.github.io/ql-debian/stable/ quodlibet-stable/

        sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5A62D0CAB6264964
        sudo apt-get update
        sudo apt-get install quodlibet

Unstable Repo:
    * Debian Testing::

        # deb http://lazka.github.io/ql-debian/testing/ quodlibet-unstable/

        sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 5A62D0CAB6264964
        sudo apt-get update
        sudo apt-get install quodlibet


.. _fedora:

|fedora-logo| Fedora
--------------------

* `Fedora Stable Repo <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-stable&package=quodlibet>`__
* `Fedora Unstable Repo <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-unstable&package=quodlibet>`__

For stable releases check out the `official
repos <https://apps.fedoraproject.org/packages/quodlibet/overview/>`__ first -
they usually contain the latest release:


.. _opensuse:

|opensuse-logo| openSUSE
------------------------

* `openSUSE Stable Repo <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-stable&package=quodlibet>`__
* `openSUSE Unstable Repo <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-unstable&package=quodlibet>`__

.. _arch:

|arch-logo| Arch Linux
----------------------

Stable:
    ::

        $ pacman -S quodlibet


Unstable:
    See `quodlibet-git <https://aur.archlinux.org/packages/quodlibet-git/>`__ in
    the `AUR <https://wiki.archlinux.org/index.php/AUR>`__.


.. _windows:

|windows-logo| Windows
----------------------

=========================== ============================== ================================================= ==========================================
Release                     File                           SHA256                                            PGP
=========================== ============================== ================================================= ==========================================
Quod Libet 3.9.0            quodlibet-3.9.0-installer.exe_ `SHA256 <quodlibet-3.9.0-installer.exe.sha256_>`_ `SIG <quodlibet-3.9.0-installer.exe.sig_>`_
Quod Libet 3.9.0 (portable) quodlibet-3.9.0-portable.exe_  `SHA256 <quodlibet-3.9.0-portable.exe.sha256_>`_  `SIG <quodlibet-3.9.0-portable.exe.sig_>`_
Quod Libet 3.8.1            quodlibet-3.8.1-installer.exe_ `SHA256 <quodlibet-3.8.1-installer.exe.sha256_>`_ `SIG <quodlibet-3.8.1-installer.exe.sig_>`_
Quod Libet 3.8.1 (portable) quodlibet-3.8.1-portable.exe_  `SHA256 <quodlibet-3.8.1-portable.exe.sha256_>`_  `SIG <quodlibet-3.8.1-portable.exe.sig_>`_
Quod Libet 3.7.1            quodlibet-3.7.1-installer.exe_ `SHA256 <quodlibet-3.7.1-installer.exe.sha256_>`_ `SIG <quodlibet-3.7.1-installer.exe.sig_>`_
Quod Libet 3.7.1 (portable) quodlibet-3.7.1-portable.exe_  `SHA256 <quodlibet-3.7.1-portable.exe.sha256_>`_  `SIG <quodlibet-3.7.1-portable.exe.sig_>`_
=========================== ============================== ================================================= ==========================================

The latest development installer: `quodlibet-latest-installer.exe <https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-latest-installer.exe>`__

.. _quodlibet-3.9.0-portable.exe: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0-portable.exe
.. _quodlibet-3.9.0-portable.exe.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0-portable.exe.sha256
.. _quodlibet-3.9.0-portable.exe.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0-portable.exe.sig

.. _quodlibet-3.9.0-installer.exe: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0-installer.exe
.. _quodlibet-3.9.0-installer.exe.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0-installer.exe.sha256
.. _quodlibet-3.9.0-installer.exe.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/quodlibet-3.9.0-installer.exe.sig

.. _quodlibet-3.8.1-portable.exe: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1-portable.exe
.. _quodlibet-3.8.1-portable.exe.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1-portable.exe.sha256
.. _quodlibet-3.8.1-portable.exe.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1-portable.exe.sig

.. _quodlibet-3.8.1-installer.exe: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1-installer.exe
.. _quodlibet-3.8.1-installer.exe.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1-installer.exe.sha256
.. _quodlibet-3.8.1-installer.exe.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/quodlibet-3.8.1-installer.exe.sig

.. _quodlibet-3.7.1-portable.exe: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1-portable.exe
.. _quodlibet-3.7.1-portable.exe.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1-portable.exe.sha256
.. _quodlibet-3.7.1-portable.exe.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1-portable.exe.sig

.. _quodlibet-3.7.1-installer.exe: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1-installer.exe
.. _quodlibet-3.7.1-installer.exe.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1-installer.exe.sha256
.. _quodlibet-3.7.1-installer.exe.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/quodlibet-3.7.1-installer.exe.sig

For old releases see the `full file listing <https://github.com/quodlibet/quodlibet/releases>`__.


.. _macosx:

|macosx-logo| Mac OS X
----------------------

=========================== ============================== ========================================== ==========================================
Release                     Application Bundle             SHA256                                     PGP
=========================== ============================== ========================================== ==========================================
Quod Libet 3.9.0            QuodLibet-3.9.0.dmg_           `SHA256 <QuodLibet-3.9.0.dmg.sha256_>`_    `SIG <QuodLibet-3.9.0.dmg.sig_>`_
Ex Falso 3.9.0              ExFalso-3.9.0.dmg_             `SHA256 <ExFalso-3.9.0.dmg.sha256_>`_      `SIG <ExFalso-3.9.0.dmg.sig_>`_
Quod Libet 3.8.1            QuodLibet-3.8.1.dmg_           `SHA256 <QuodLibet-3.8.1.dmg.sha256_>`_    `SIG <QuodLibet-3.8.1.dmg.sig_>`_
Ex Falso 3.8.1              ExFalso-3.8.1.dmg_             `SHA256 <ExFalso-3.8.1.dmg.sha256_>`_      `SIG <ExFalso-3.8.1.dmg.sig_>`_
Quod Libet 3.7.1            QuodLibet-3.7.1.dmg_           `SHA256 <QuodLibet-3.7.1.dmg.sha256_>`_    `SIG <QuodLibet-3.7.1.dmg.sig_>`_
Ex Falso 3.7.1              ExFalso-3.7.1.dmg_             `SHA256 <ExFalso-3.7.1.dmg.sha256_>`_      `SIG <ExFalso-3.7.1.dmg.sig_>`_
=========================== ============================== ========================================== ==========================================

The latest development bundle: `QuodLibet-latest.dmg <https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-latest.dmg>`__

For old releases see the `full file listing <https://github.com/quodlibet/quodlibet/releases>`__.

.. _QuodLibet-3.9.0.dmg: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/QuodLibet-3.9.0.dmg
.. _QuodLibet-3.9.0.dmg.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/QuodLibet-3.9.0.dmg.sha256
.. _QuodLibet-3.9.0.dmg.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/QuodLibet-3.9.0.dmg.sig

.. _ExFalso-3.9.0.dmg: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/ExFalso-3.9.0.dmg
.. _ExFalso-3.9.0.dmg.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/ExFalso-3.9.0.dmg.sha256
.. _ExFalso-3.9.0.dmg.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.9.0/ExFalso-3.9.0.dmg.sig

.. _QuodLibet-3.8.1.dmg: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/QuodLibet-3.8.1.dmg
.. _QuodLibet-3.8.1.dmg.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/QuodLibet-3.8.1.dmg.sha256
.. _QuodLibet-3.8.1.dmg.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/QuodLibet-3.8.1.dmg.sig

.. _ExFalso-3.8.1.dmg: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/ExFalso-3.8.1.dmg
.. _ExFalso-3.8.1.dmg.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/ExFalso-3.8.1.dmg.sha256
.. _ExFalso-3.8.1.dmg.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.8.1/ExFalso-3.8.1.dmg.sig

.. _QuodLibet-3.7.1.dmg: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/QuodLibet-3.7.1.dmg
.. _QuodLibet-3.7.1.dmg.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/QuodLibet-3.7.1.dmg.sha256
.. _QuodLibet-3.7.1.dmg.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/QuodLibet-3.7.1.dmg.sig

.. _ExFalso-3.7.1.dmg: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/ExFalso-3.7.1.dmg
.. _ExFalso-3.7.1.dmg.sha256: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/ExFalso-3.7.1.dmg.sha256
.. _ExFalso-3.7.1.dmg.sig: https://github.com/quodlibet/quodlibet/releases/download/release-3.7.1/ExFalso-3.7.1.dmg.sig
