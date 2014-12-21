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
.. |hg-logo| image:: http://bitbucket.org/lazka/quodlibet-files/raw/default/icons/mercurial.png
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

================ ========================================== ================================================
**Linux:**       |ubuntu-logo| :ref:`Ubuntu <ubuntu>`       |debian-logo| :ref:`Debian <debian>`
   \             |fedora-logo| :ref:`Fedora <fedora>`       |opensuse-logo| :ref:`openSUSE <opensuse>`
   \             |arch-logo| :ref:`Arch Linux <arch>`
**Windows:**     |windows-logo| :ref:`Windows <windows>`
**Mac OS X:**    |macosx-logo| :ref:`Mac OS X <macosx>`
**Development:** |hg-logo| :ref:`Source <source>`           |source-logo| :ref:`Release Tarballs <tarballs>`
================ ========================================== ================================================

----

.. _source:

|hg-logo| Source
----------------

Quod Libet uses `Mercurial <http://mercurial.selenic.com/>`_ for source
control and is hosted on `Google Code <https://code.google.com/>`_ as well
as `Bitbucket <https://bitbucket.org/>`__:

 * https://code.google.com/p/quodlibet (primary)
 * https://bitbucket.org/lazka/quodlibet (mirror)

To clone the repository::

    hg clone https://code.google.com/p/quodlibet
    hg clone https://bitbucket.org/lazka/quodlibet

.. _tarballs:

|source-logo| Release Tarballs
------------------------------

========================== ===============================
Release                    Filename
========================== ===============================
Quod Libet 3.2.2           quodlibet-3.2.2.tar.gz_
Quod Libet 3.1.2           quodlibet-3.1.2.tar.gz_
Quod Libet Plugins 3.1.2   quodlibet-plugins-3.1.2.tar.gz_
Quod Libet 3.0.2           quodlibet-3.0.2.tar.gz_
Quod Libet Plugins 3.0.2   quodlibet-plugins-3.0.2.tar.gz_
Quod Libet 2.6.3           quodlibet-2.6.3.tar.gz_
Quod Libet Plugins 2.6.3   quodlibet-plugins-2.6.3.tar.gz_
========================== ===============================

.. _quodlibet-3.2.2.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.2.2.tar.gz
.. _quodlibet-3.1.2.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.1.2.tar.gz
.. _quodlibet-plugins-3.1.2.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-plugins-3.1.2.tar.gz
.. _quodlibet-3.0.2.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.0.2.tar.gz
.. _quodlibet-plugins-3.0.2.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-plugins-3.0.2.tar.gz
.. _quodlibet-2.6.3.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-2.6.3.tar.gz
.. _quodlibet-plugins-2.6.3.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-plugins-2.6.3.tar.gz

For old releases see the `full file listing <https://bitbucket.org/lazka/quodlibet-files/src/default/releases>`__.

.. note::

    Since 3.2 all plugins are included in the main tarball


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

        $ sudo add-get install ppa-purge
        $ sudo ppa-purge ppa:lazka/ppa
        $ sudo ppa-purge ppa:lazka/dumpingplace


.. _debian:

|debian-logo| Debian
--------------------

Stable Repo:

* Wheezy (Debian stable)::

    # deb http://lazka.github.io/ql-debian/stable/ quodlibet-stable/
    # deb http://http.debian.net/debian wheezy-backports main

    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0C693B8F
    sudo apt-get update
    sudo apt-get -t wheezy-backports -t quodlibet-stable install qudlibet gstreamer1.0-pulseaudio

Unstable Repo:

* Jessie (Debian testing)::

    # deb http://lazka.github.io/ql-debian/testing/ quodlibet-unstable/

    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0C693B8F
    sudo apt-get update
    sudo apt-get -t quodlibet-unstable install qudlibet


.. _fedora:

|fedora-logo| Fedora
--------------------

Stable Repo (`OBS <https://build.opensuse.org/project/show/home:lazka0:ql-stable>`__):

  * `Fedora 19 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/Fedora_19/home:lazka0:ql-stable.repo>`__
  * `Fedora 20 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/Fedora_20/home:lazka0:ql-stable.repo>`__

Unstable Repo (`OBS <https://build.opensuse.org/project/show/home:lazka0:ql-unstable>`__):

  * `Fedora 19 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/Fedora_19/home:lazka0:ql-unstable.repo>`__
  * `Fedora 20 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/Fedora_20/home:lazka0:ql-unstable.repo>`__

Unstable Repo (`COPR <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/>`__):

  * `Fedora 19 <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/fedora-19/lazka-quodlibet-unstable-fedora-19.repo>`__
  * `Fedora 20 <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/fedora-20/lazka-quodlibet-unstable-fedora-20.repo>`__
  * `Fedora Rawhide <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/fedora-rawhide/lazka-quodlibet-unstable-fedora-rawhide.repo>`__
  * `RHEL 7 <http://copr.fedoraproject.org/coprs/lazka/quodlibet-unstable/repo/epel-7/lazka-quodlibet-unstable-epel-7.repo>`__


.. _opensuse:

|opensuse-logo| openSUSE
------------------------

Stable Repo:

  * `openSUSE 12.3 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_12.3/>`__
  * `openSUSE 13.1 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_13.1/>`__
  * `openSUSE Tumbleweed <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_Tumbleweed>`__

Unstable Repo:

  * `openSUSE 12.3 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_12.3/>`__
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

=========================== ==============================
Release                     Filename
=========================== ==============================
Quod Libet 3.2.2            quodlibet-3.2.2-installer.exe_
Quod Libet 3.2.2 (portable) quodlibet-3.2.2-portable.exe_
Quod Libet 3.1.2            quodlibet-3.1.2-installer.exe_
Quod Libet 3.1.2 (portable) quodlibet-3.1.2-portable.exe_
Quod Libet 2.6.3            quodlibet-2.6.3-installer.exe_
Quod Libet 2.6.3 (portable) quodlibet-2.6.3-portable.exe_
=========================== ==============================

.. _quodlibet-3.2.2-portable.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.2.2-portable.exe
.. _quodlibet-3.2.2-installer.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.2.2-installer.exe
.. _quodlibet-3.1.2-portable.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.1.2-portable.exe
.. _quodlibet-3.1.2-installer.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-3.1.2-installer.exe
.. _quodlibet-2.6.3-portable.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-2.6.3-portable.exe
.. _quodlibet-2.6.3-installer.exe: https://bitbucket.org/lazka/quodlibet/downloads/quodlibet-2.6.3-installer.exe

For old releases see the `full file listing <https://bitbucket.org/lazka/quodlibet/downloads/>`__.


.. _macosx:

|macosx-logo| Mac OS X
----------------------

.. note::

    Mac OS X support is still experimental; please report any issue you 
    encounter.

Newest bundle (OSX 10.6 - 10.9 x86_64): http://kerik-sf.users.sourceforge.net/quodlibet-osx-bundle/


.. _RunFromSource:

|source-logo| Running from Source
---------------------------------

Install mercurial and check out the source::

    $ hg clone https://code.google.com/p/quodlibet/
    $ cd quodlibet/quodlibet


If you want translations, you have to create the gettext translation files::

$ ./setup.py build_mo

Run Quod Libet or Ex Falso::

    $ ./quodlibet.py
    $ ./exfalso.py

To update to the latest version, switch to the QL dir and run::

 $ hg pull --update
 $ ./setup.py build_mo # (only if you need translations)
