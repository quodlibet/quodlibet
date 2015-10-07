.. _Downloads:

.. |ubuntu-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/ubuntu.png
   :height: 16
   :width: 16
.. |debian-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/debian.png
   :height: 16
   :width: 16
.. |fedora-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/fedora.png
   :height: 16
   :width: 16
.. |opensuse-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/opensuse.png
   :height: 16
   :width: 16
.. |windows-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/windows.png
   :height: 16
   :width: 16
.. |source-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/source.png
   :height: 16
   :width: 16
.. |arch-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/arch.png
   :height: 16
   :width: 16
.. |macosx-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/macosx.png
   :height: 16
   :width: 16


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
Quod Libet 3.5.0           quodlibet-3.5.0.tar.gz_         `SHA256 <quodlibet-3.5.0.tar.gz.sha256_>`_         `SIG <quodlibet-3.5.0.tar.gz.sig_>`_
Quod Libet 3.4.1           quodlibet-3.4.1.tar.gz_         `SHA256 <quodlibet-3.4.1.tar.gz.sha256_>`_         `SIG <quodlibet-3.4.1.tar.gz.sig_>`_
Quod Libet 3.3.1           quodlibet-3.3.1.tar.gz_         `SHA256 <quodlibet-3.3.1.tar.gz.sha256_>`_         `SIG <quodlibet-3.3.1.tar.gz.sig_>`_
========================== =============================== ================================================== ============================================

.. _quodlibet-3.5.0.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.5.0.tar.gz
.. _quodlibet-3.5.0.tar.gz.sha256: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.5.0.tar.gz.sha256
.. _quodlibet-3.5.0.tar.gz.sig: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.5.0.tar.gz.sig

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

Stable PPA (12.04+)::

    $ sudo add-apt-repository ppa:lazka/ppa


Unstable PPA (12.04+)::

    $ sudo add-apt-repository ppa:lazka/dumpingplace


.. note::

    While Ubuntu 12.04 is supported, drag and drop does not work.


.. note::

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

Stable Repo (`OBS <https://build.opensuse.org/project/show/home:lazka0:ql-stable>`__):

  * `Fedora 20 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/Fedora_20/home:lazka0:ql-stable.repo>`__

.. note::

    Check out the official repos first, they usually contain the latest stable release: https://apps.fedoraproject.org/packages/quodlibet/overview/

Unstable Repo (`OBS <https://build.opensuse.org/project/show/home:lazka0:ql-unstable>`__):

  * `Fedora 20 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/Fedora_20/home:lazka0:ql-unstable.repo>`__

Unstable Repo (`COPR <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/>`__):

  * `Fedora 22 <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/fedora-22/lazka-quodlibet-unstable-fedora-22.repo>`__
  * `Fedora 21 <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/fedora-21/lazka-quodlibet-unstable-fedora-21.repo>`__
  * `Fedora 20 <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/fedora-20/lazka-quodlibet-unstable-fedora-20.repo>`__
  * `Fedora Rawhide <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/fedora-rawhide/lazka-quodlibet-unstable-fedora-rawhide.repo>`__
  * `RHEL 7 <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/epel-7/lazka-quodlibet-unstable-epel-7.repo>`__


.. _opensuse:

|opensuse-logo| openSUSE
------------------------

Stable Repo:

  * `openSUSE 13.2 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_13.2/>`__
  * `openSUSE 13.1 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_13.1/>`__
  * `openSUSE Tumbleweed <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_Tumbleweed>`__

Unstable Repo:

  * `openSUSE 13.2 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_13.2/>`__
  * `openSUSE 13.1 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_13.1/>`__
  * `openSUSE Tumbleweed <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_Tumbleweed>`__


.. _arch:

|arch-logo| Arch Linux
----------------------

Stable:

::

    $ pacman -S quodlibet


Unstable:


See `quodlibet-hg <https://aur.archlinux.org/packages/quodlibet-hg>`__ in
the `AUR <https://wiki.archlinux.org/index.php/AUR>`__.


.. _windows:

|windows-logo| Windows
----------------------

Based on `pygi-aio <https://sourceforge.net/projects/pygobjectwin32/>`__ by `Tumagonx
Zakkum <https://github.com/tumagonx>`__

=========================== ============================== ================================================= ==========================================
Release                     File                           SHA256                                            PGP
=========================== ============================== ================================================= ==========================================
Quod Libet 3.5.0            quodlibet-3.5.0-installer.exe_ `SHA256 <quodlibet-3.5.0-installer.exe.sha256_>`_ `SIG <quodlibet-3.5.0-installer.exe.sig_>`_
Quod Libet 3.5.0 (portable) quodlibet-3.5.0-portable.exe_  `SHA256 <quodlibet-3.5.0-portable.exe.sha256_>`_  `SIG <quodlibet-3.5.0-portable.exe.sig_>`_
Quod Libet 3.4.1            quodlibet-3.4.1-installer.exe_ `SHA256 <quodlibet-3.4.1-installer.exe.sha256_>`_ `SIG <quodlibet-3.4.1-installer.exe.sig_>`_
Quod Libet 3.4.1 (portable) quodlibet-3.4.1-portable.exe_  `SHA256 <quodlibet-3.4.1-portable.exe.sha256_>`_  `SIG <quodlibet-3.4.1-portable.exe.sig_>`_
Quod Libet 3.3.1            quodlibet-3.3.1-installer.exe_ `SHA256 <quodlibet-3.3.1-installer.exe.sha256_>`_ `SIG <quodlibet-3.3.1-installer.exe.sig_>`_
Quod Libet 3.3.1 (portable) quodlibet-3.3.1-portable.exe_  `SHA256 <quodlibet-3.3.1-portable.exe.sha256_>`_  `SIG <quodlibet-3.3.1-portable.exe.sig_>`_
=========================== ============================== ================================================= ==========================================

.. _quodlibet-3.5.0-portable.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.0-portable.exe
.. _quodlibet-3.5.0-portable.exe.sha256: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.0-portable.exe.sha256
.. _quodlibet-3.5.0-portable.exe.sig: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.0-portable.exe.sig

.. _quodlibet-3.5.0-installer.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.0-installer.exe
.. _quodlibet-3.5.0-installer.exe.sha256: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.0-installer.exe.sha256
.. _quodlibet-3.5.0-installer.exe.sig: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.5.0-installer.exe.sig

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
Quod Libet 3.5.0            QuodLibet-3.5.0.zip_           `SHA256 <QuodLibet-3.5.0.zip.sha256_>`_    `SIG <QuodLibet-3.5.0.zip.sig_>`_
Ex Falso 3.5.0              ExFalso-3.5.0.zip_             `SHA256 <ExFalso-3.5.0.zip.sha256_>`_      `SIG <ExFalso-3.5.0.zip.sig_>`_
Quod Libet 3.4.1 (v2)       QuodLibet-3.4.1-v2.zip_        `SHA256 <QuodLibet-3.4.1-v2.zip.sha256_>`_ `SIG <QuodLibet-3.4.1-v2.zip.sig_>`_
Ex Falso 3.4.1 (v2)         ExFalso-3.4.1-v2.zip_          `SHA256 <ExFalso-3.4.1-v2.zip.sha256_>`_   `SIG <ExFalso-3.4.1-v2.zip.sig_>`_
Quod Libet 3.4.1            QuodLibet-3.4.1.zip_           `SHA256 <QuodLibet-3.4.1.zip.sha256_>`_    `SIG <QuodLibet-3.4.1.zip.sig_>`_
Ex Falso 3.4.1              ExFalso-3.4.1.zip_             `SHA256 <ExFalso-3.4.1.zip.sha256_>`_      `SIG <ExFalso-3.4.1.zip.sig_>`_
=========================== ============================== ========================================== ==========================================

.. _QuodLibet-3.5.0.zip: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.5.0.zip
.. _QuodLibet-3.5.0.zip.sha256: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.5.0.zip.sha256
.. _QuodLibet-3.5.0.zip.sig: https://bitbucket.org/lazka/quodlibet/downloads/QuodLibet-3.5.0.zip.sig

.. _ExFalso-3.5.0.zip: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.5.0.zip
.. _ExFalso-3.5.0.zip.sha256: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.5.0.zip.sha256
.. _ExFalso-3.5.0.zip.sig: https://bitbucket.org/lazka/quodlibet/downloads/ExFalso-3.5.0.zip.sig

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
