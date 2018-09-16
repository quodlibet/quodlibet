===============================
Windows Installer Build Scripts
===============================

We use `msys2 <https://msys2.github.io/>`__ for creating the Windows installer
and development on Windows.


Development
-----------

For developing on Windows you have two choices.

1) Just use an existing Quod Libet installation plus a git checkout:

   * Clone the git repo with some git client
   * Download and install the latest installer build:
     https://github.com/quodlibet/quodlibet/releases/download/latest/quodlibet-latest-installer.exe
   * Go to quodlibet.py in the git checkout and run
     ``%PROGRAMFILES(X86)%\Quod Libet\bin\python.exe quodlibet.py``.

2) Use proper msys2 environment


Setting Up the MSYS2 Environment
--------------------------------

* Download msys2 64-bit from https://msys2.github.io/
* Follow instructions on https://msys2.github.io/
* Execute ``C:\msys64\mingw32.exe``
* Run ``pacman -S git`` to install git
* Run ``git clone https://github.com/quodlibet/quodlibet.git``
* Run ``cd quodlibet/win_installer`` to end up where this README exists.
* Execute ``./bootstrap.sh`` to install all the needed dependencies.
* Now go to the application source code ``cd ../quodlibet``
* To run Quod Libet execute ``./quodlibet.py``

If you want to use py.test directly you have to unset the MSYSTEM env var:
``MSYSTEM= py.test tests/test_util.py``


Creating an Installer
---------------------

Simply run ``./build.sh [git-tag]`` and both the installer and the portable
installer should appear in this directory.

You can pass a git tag ``./build.sh release-3.8.0`` to build a specific tag or
pass nothing to build master. Note that it will clone from this repository and
not from github so any commits present locally will be cloned as well.


Updating an Existing Installer
------------------------------

We directly follow msys2 upstream so building the installer two weeks later
might result in newer versions of dependencies being used. To reduce the risk
of stable release breakage you can use an existing installer and just install
a newer Quod Libet version into it and then repack it.

``./rebuild.sh quodlibet-3.8.0-installer.exe [git-tag]``
