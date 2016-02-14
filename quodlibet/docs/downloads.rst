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
Quod Libet 3.5.3           quodlibet-3.5.3.tar.gz_         `SHA256 <quodlibet-3.5.3.tar.gz.sha256_>`_         `SIG <quodlibet-3.5.3.tar.gz.sig_>`_
Quod Libet 3.4.1           quodlibet-3.4.1.tar.gz_         `SHA256 <quodlibet-3.4.1.tar.gz.sha256_>`_         `SIG <quodlibet-3.4.1.tar.gz.sig_>`_
Quod Libet 3.3.1           quodlibet-3.3.1.tar.gz_         `SHA256 <quodlibet-3.3.1.tar.gz.sha256_>`_         `SIG <quodlibet-3.3.1.tar.gz.sig_>`_
========================== =============================== ================================================== ============================================

.. _quodlibet-3.5.3.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.5.3.tar.gz
.. _quodlibet-3.5.3.tar.gz.sha256: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.5.3.tar.gz.sha256
.. _quodlibet-3.5.3.tar.gz.sig: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.5.3.tar.gz.sig

.. _quodlibet-3.4.1.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.4.1.tar.gz
.. _quodlibet-3.4.1.tar.gz.sha256: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.4.1.tar.gz.sha256
.. _quodlibet-3.4.1.tar.gz.sig: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.4.1.tar.gz.sig

.. _quodlibet-3.3.1.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.3.1.tar.gz
.. _quodlibet-3.3.1.tar.gz.sha256: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.3.1.tar.gz.sha256
.. _quodlibet-3.3.1.tar.gz.sig: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.3.1.tar.gz.sig

For old releases see the `full file listing <https://bitbucket.org/lazka/quodlibet-files/src/default/releases>`__.


.. _ubuntu:

|ubuntu-logo| Ubuntu
--------------------

Stable Repo (14.04+):
    ::

        $ sudo add-apt-repository ppa:lazka/ppa


Unstable PPA (14.04+):
    ::

        $ sudo add-apt-repository ppa:lazka/dumpingplace


To remove the PPAs and revert back to the old version::

    $ sudo apt-get install ppa-purge
    $ sudo ppa-purge ppa:lazka/ppa
    $ sudo ppa-purge ppa:lazka/dumpingplace


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

Stable Repo:
    `Fedora 20, 21, 22 <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-stable&package=quodlibet>`__

Unstable Repo :
    `Fedora 20, 21, 22 <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-unstable&package=quodlibet>`__

For stable releases check out the `official
repos <https://apps.fedoraproject.org/packages/quodlibet/overview/>`__ first -
they usually contain the latest release:


.. _opensuse:

|opensuse-logo| openSUSE
------------------------

Stable Repo:
    `openSUSE 13.1, 13.2, Tumbleweed, Leap 42.1 <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-stable&package=quodlibet>`__

Unstable Repo:
    `openSUSE 13.1, 13.2, Tumbleweed, Leap 42.1 <https://software.opensuse.org/download.html?project=home%3Alazka0%3Aql-unstable&package=quodlibet>`__

.. _arch:

|arch-logo| Arch Linux
----------------------

Stable:
    ::

        $ pacman -S quodlibet


Unstable:
    See `quodlibet-git <https://aur4.archlinux.org/packages/quodlibet-git/>`__ in
    the `AUR <https://wiki.archlinux.org/index.php/AUR>`__.


.. _windows:

|windows-logo| Windows
----------------------

Based on `pygi-aio <https://sourceforge.net/projects/pygobjectwin32/>`__ by `Tumagonx
Zakkum <https://github.com/tumagonx>`__

=========================== ============================== ================================================= ==========================================
Release                     File                           SHA256                                            PGP
=========================== ============================== ================================================= ==========================================
Quod Libet 3.5.2            quodlibet-3.5.2-installer.exe_ `SHA256 <quodlibet-3.5.2-installer.exe.sha256_>`_ `SIG <quodlibet-3.5.2-installer.exe.sig_>`_
Quod Libet 3.5.2 (portable) quodlibet-3.5.2-portable.exe_  `SHA256 <quodlibet-3.5.2-portable.exe.sha256_>`_  `SIG <quodlibet-3.5.2-portable.exe.sig_>`_
Quod Libet 3.4.1            quodlibet-3.4.1-installer.exe_ `SHA256 <quodlibet-3.4.1-installer.exe.sha256_>`_ `SIG <quodlibet-3.4.1-installer.exe.sig_>`_
Quod Libet 3.4.1 (portable) quodlibet-3.4.1-portable.exe_  `SHA256 <quodlibet-3.4.1-portable.exe.sha256_>`_  `SIG <quodlibet-3.4.1-portable.exe.sig_>`_
Quod Libet 3.3.1            quodlibet-3.3.1-installer.exe_ `SHA256 <quodlibet-3.3.1-installer.exe.sha256_>`_ `SIG <quodlibet-3.3.1-installer.exe.sig_>`_
Quod Libet 3.3.1 (portable) quodlibet-3.3.1-portable.exe_  `SHA256 <quodlibet-3.3.1-portable.exe.sha256_>`_  `SIG <quodlibet-3.3.1-portable.exe.sig_>`_
=========================== ============================== ================================================= ==========================================

.. _quodlibet-3.5.2-portable.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.2-portable.exe
.. _quodlibet-3.5.2-portable.exe.sha256: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.2-portable.exe.sha256
.. _quodlibet-3.5.2-portable.exe.sig: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.2-portable.exe.sig

.. _quodlibet-3.5.2-installer.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.2-installer.exe
.. _quodlibet-3.5.2-installer.exe.sha256: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.2-installer.exe.sha256
.. _quodlibet-3.5.2-installer.exe.sig: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.2-installer.exe.sig

.. _quodlibet-3.4.1-portable.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.4.1-portable.exe
.. _quodlibet-3.4.1-portable.exe.sha256: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.4.1-portable.exe.sha256
.. _quodlibet-3.4.1-portable.exe.sig: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.4.1-portable.exe.sig

.. _quodlibet-3.4.1-installer.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.4.1-installer.exe
.. _quodlibet-3.4.1-installer.exe.sha256: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.4.1-installer.exe.sha256
.. _quodlibet-3.4.1-installer.exe.sig: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.4.1-installer.exe.sig

.. _quodlibet-3.3.1-portable.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.3.1-portable.exe
.. _quodlibet-3.3.1-portable.exe.sha256: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.3.1-portable.exe.sha256
.. _quodlibet-3.3.1-portable.exe.sig: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.3.1-portable.exe.sig

.. _quodlibet-3.3.1-installer.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.3.1-installer.exe
.. _quodlibet-3.3.1-installer.exe.sha256: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.3.1-installer.exe.sha256
.. _quodlibet-3.3.1-installer.exe.sig: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.3.1-installer.exe.sig

For old releases see the `full file listing <https://bitbucket.org/lazka/quodlibet/downloads/>`__.

There is also an SDK for developing under Windows: `quodlibet-win-sdk.tar.gz <https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-win-sdk.tar.gz>`__


.. _macosx:

|macosx-logo| Mac OS X
----------------------

Based on the `OS X bundles <https://github.com/elelay/quodlibet-osx-bundle>`__
created by `Eric Le Lay <https://github.com/elelay>`__

=========================== ============================== ========================================== ==========================================
Release                     Application Bundle             SHA256                                     PGP
=========================== ============================== ========================================== ==========================================
Quod Libet 3.5.2-v2         QuodLibet-3.5.2-v2.zip_        `SHA256 <QuodLibet-3.5.2-v2.zip.sha256_>`_ `SIG <QuodLibet-3.5.2-v2.zip.sig_>`_
Ex Falso 3.5.2-v2           ExFalso-3.5.2-v2.zip_          `SHA256 <ExFalso-3.5.2-v2.zip.sha256_>`_   `SIG <ExFalso-3.5.2-v2.zip.sig_>`_
Quod Libet 3.4.1 (v2)       QuodLibet-3.4.1-v2.zip_        `SHA256 <QuodLibet-3.4.1-v2.zip.sha256_>`_ `SIG <QuodLibet-3.4.1-v2.zip.sig_>`_
Ex Falso 3.4.1 (v2)         ExFalso-3.4.1-v2.zip_          `SHA256 <ExFalso-3.4.1-v2.zip.sha256_>`_   `SIG <ExFalso-3.4.1-v2.zip.sig_>`_
=========================== ============================== ========================================== ==========================================

For old releases see the `full file listing <https://bitbucket.org/lazka/quodlibet/downloads/>`__.

.. _QuodLibet-3.5.2-v2.zip: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.5.2-v2.zip
.. _QuodLibet-3.5.2-v2.zip.sha256: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.5.2-v2.zip.sha256
.. _QuodLibet-3.5.2-v2.zip.sig: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.5.2-v2.zip.sig

.. _ExFalso-3.5.2-v2.zip: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.5.2-v2.zip
.. _ExFalso-3.5.2-v2.zip.sha256: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.5.2-v2.zip.sha256
.. _ExFalso-3.5.2-v2.zip.sig: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.5.2-v2.zip.sig

.. _QuodLibet-3.4.1-v2.zip: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.4.1-v2.zip
.. _QuodLibet-3.4.1-v2.zip.sha256: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.4.1-v2.zip.sha256
.. _QuodLibet-3.4.1-v2.zip.sig: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.4.1-v2.zip.sig

.. _ExFalso-3.4.1-v2.zip: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.4.1-v2.zip
.. _ExFalso-3.4.1-v2.zip.sha256: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.4.1-v2.zip.sha256
.. _ExFalso-3.4.1-v2.zip.sig: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.4.1-v2.zip.sig

.. _QuodLibet-3.4.1.zip: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.4.1.zip
.. _QuodLibet-3.4.1.zip.sha256: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.4.1.zip.sha256
.. _QuodLibet-3.4.1.zip.sig: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.4.1.zip.sig

.. _ExFalso-3.4.1.zip: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.4.1.zip
.. _ExFalso-3.4.1.zip.sha256: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.4.1.zip.sha256
.. _ExFalso-3.4.1.zip.sig: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.4.1.zip.sig
