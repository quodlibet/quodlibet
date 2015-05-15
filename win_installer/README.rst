====================
QL Windows Installer
====================

Requirements:

* 7zip
* wine (tested with 1.6.1)
* QL build deps
* wget
* git
* 1.5GB free space

How To
------

* Run "build_installer.sh $VERSION"
* _bin will be created which contains installers of various dependencies
* _build_env will be created which contains all files created during the
  build process.
* After the build is finished, quodlibet-$VERSION-installer.exe and
  quodlibet-$VERSION-portable.exe will be placed in this directory.


SDK Environment
---------------

After running build_sdk.sh, ./_sdk contains a development environment
including all dependencies and the needed launchers.
