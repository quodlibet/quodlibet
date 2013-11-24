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

|hg-logo| Source
----------------

Quod Libet uses `Mercurial <http://mercurial.selenic.com/>`_ for source
control and is hosted on `Google Code <https://code.google.com/>`_ as well
as `Bitbucket <https://bitbucket.org/>`__:

 * https://code.google.com/p/quodlibet
 * https://bitbucket.org/lazka/quodlibet

To clone the repository::

    hg clone https://code.google.com/p/quodlibet
    hg clone https://bitbucket.org/lazka/quodlibet


|source-logo| Release Tarballs
------------------------------

========================== ===============================
Release                    Filename
========================== ===============================
Quod Libet 3.0.2           quodlibet-3.0.2.tar.gz_
Quod Libet Plugins 3.0.2   quodlibet-plugins-3.0.2.tar.gz_
Quod Libet 2.6.3           quodlibet-2.6.3.tar.gz_
Quod Libet Plugins 2.6.3   quodlibet-plugins-2.6.3.tar.gz_
Quod Libet 2.5.1           quodlibet-2.5.1.tar.gz_
Quod Libet Plugins 2.5.1   quodlibet-plugins-2.5.1.tar.gz_
========================== ===============================

.. _quodlibet-3.0.2.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-3.0.2.tar.gz
.. _quodlibet-plugins-3.0.2.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-plugins-3.0.2.tar.gz
.. _quodlibet-2.6.3.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-2.6.3.tar.gz
.. _quodlibet-plugins-2.6.3.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-plugins-2.6.3.tar.gz
.. _quodlibet-2.5.1.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-2.5.1.tar.gz
.. _quodlibet-plugins-2.5.1.tar.gz: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-plugins-2.5.1.tar.gz


For old releases see the `full file listing <https://bitbucket.org/lazka/quodlibet-files/src/default/releases>`__.

|ubuntu-logo| Ubuntu
--------------------

Stable PPA::

    $ sudo add-apt-repository ppa:lazka/ppa


Unstable PPA::

    $ sudo add-apt-repository ppa:lazka/dumpingplace

.. note::

    Quod Libet 3.x supports **Ubuntu 12.04**, but needs some updated
    dependencies that you'll need to install separately:

    * The `GStreamer Developer PPA
      <https://launchpad.net/~gstreamer-developers/+archive/ppa?field.series_
      filter=precise>`__ for GStreamer 1.0.
    * *(optional)* Ubuntu 12.10 packages of both `gir1.2-keybinder-3.0
      <http://packages.ubuntu.com/quantal/gir1.2-keybinder-3.0>`__ and
      `libkeybinder-3.0-0
      <http://packages.ubuntu.com/quantal/libkeybinder-3.0-0>`__ for
      multimedia key support under non GNOME environments.

|debian-logo| Debian
--------------------

Unstable Repo::

    deb http://www.student.tugraz.at/christoph.reiter/debian/ quodlibet-unstable/


Repo key::

    $ sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0C693B8F


|fedora-logo| Fedora
--------------------

Stable Repo:

  * `Fedora 17 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/Fedora_17/>`__
  * `Fedora 18 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/Fedora_18/>`__
  * `Fedora 19 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/Fedora_19/>`__

Unstable Repo:

  * `Fedora 17 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/Fedora_17/>`__
  * `Fedora 18 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/Fedora_18/>`__
  * `Fedora 19 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/Fedora_19/>`__


|opensuse-logo| openSUSE
------------------------

Stable Repo:

  * `openSUSE 12.1 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_12.1/>`__
  * `openSUSE 12.2 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_12.2/>`__
  * `openSUSE 12.3 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_12.3/>`__
  * `openSUSE 13.1 <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_13.1/>`__
  * `openSUSE Tumbleweed <http://download.opensuse.org/repositories/home:/lazka0:/ql-stable/openSUSE_Tumbleweed>`__

Unstable Repo:

  * `openSUSE 12.1 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_12.1/>`__
  * `openSUSE 12.2 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_12.2/>`__
  * `openSUSE 12.3 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_12.3/>`__
  * `openSUSE 13.1 <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_13.1/>`__
  * `openSUSE Tumbleweed <http://download.opensuse.org/repositories/home:/lazka0:/ql-unstable/openSUSE_Tumbleweed>`__


|windows-logo| Windows
----------------------

=========================== ==============================
Release                     Filename
=========================== ==============================
Quod Libet 2.6.3            quodlibet-2.6.3-installer.exe_
Quod Libet 2.6.3 (portable) quodlibet-2.6.3-portable.exe_
Quod Libet 2.5.1            quodlibet-2.5.1-installer.exe_
Quod Libet 2.4.1            quodlibet-2.4.1-installer.exe_
=========================== ==============================

.. _quodlibet-2.6.3-portable.exe: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-2.6.3-portable.exe
.. _quodlibet-2.6.3-installer.exe: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-2.6.3-installer.exe
.. _quodlibet-2.5.1-installer.exe: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-2.5.1-installer.exe
.. _quodlibet-2.4.1-installer.exe: https://bitbucket.org/lazka/quodlibet-files/raw/default/releases/quodlibet-2.4.1-installer.exe

For old releases see the `full file listing <https://bitbucket.org/lazka/quodlibet-files/src/default/releases>`__.


|arch-logo| Arch Linux
----------------------

::

    $ pacman -S quodlibet


.. _RunFromSource:

|source-logo| Running from Source
---------------------------------

Install mercurial and check out the source::

    $ hg clone https://code.google.com/p/quodlibet/
    $ cd quodlibet

QL/EF expects the plugins to be in "~/.quodlibet/plugins" so
create a symlink::

    $ mkdir ~/.quodlibet
    $ ln -s $(readlink -f plugins) ~/.quodlibet/plugins

Now switch to the real QL folder::

    $ cd quodlibet

If you want translations, you have to create the gettext translation files::

$ ./setup.py build_mo

Run Quod Libet or Ex Falso::

    $ ./quodlibet.py
    $ ./exfalso.py

To update to the latest version, switch to the QL dir and run::

 $ hg pull --update
 $ ./setup.py build_mo # (only if you need translations)

|macosx-logo| Mac OS X
----------------------

::

    sudo port install quodlibet
