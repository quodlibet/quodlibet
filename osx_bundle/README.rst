=========================
OS X Bundle Build Scripts
=========================

**Note:**
    In case you want just want to run Quod Libet from source you can ignore
    all this and use the released bundle as a development environment.
    Download the official bundle, git clone the quodlibet repo and do
    ``./QuodLibet.app/Contents/MacOS/run quodlibet.py``.


Uses jhbuild [3] and the stable module set provided by gtk-osx [2] with a Quod
Libet specific module set overlay to build all needed dependencies for Quod
Libet. Everything will be downloaded/installed into this directory and your
user directory will not be touched.


Creating a Bundle
-----------------

Prerequisites: `OS X` 10.7+ and a working `Xcode` [0] and `git` [1]

Verify that Xcode and git is installed and in your ``$PATH`` by invoking ``git
--version`` and ``gcc --version``. Also make sure that other pacakge managers
like homebrew or macports aren't in your ``$PATH``.

(Tested on OS X 10.9)

1) Call ``bootstrap.sh`` to install jhbuild and set up dummy ``$HOME`` as base.
2) Call ``build.sh`` to download and build all the dependencies.
   This should not lead to errors; if it does please file a bug.
3) Call ``bundle.sh`` to create the finished bundles for QL and EF in
   ``_build``.


Development
-----------

* After ``bootstrap.sh`` has finished executing ``source env.sh`` will put you
  in the build environment. After that jhbuild can be used directly or the
  Quod Libet test suite can be executed.
* ``fetch_modules()`` downloads the git master of the gtk-osx module set
  and replaces the modules under "modulessets" and the
  ``misc/gtk-osx-jhbuildrc`` file. Doing so so should ideally be followed by a
  review of the quodlibet module to reduce duplication and a rebuilt to verify
  that everything still works.


Content Description
-------------------

* ``modulesets`` contains the gtk-osx stable module set and a quodlibet module
  which adds new packages replaces existing ones.
* ``misc``: see each file or directory README for a description.


| [0] https://developer.apple.com/xcode/downloads/
| [1] https://git-scm.com/download/mac
| [2] https://git.gnome.org/browse/gtk-osx/
| [3] https://git.gnome.org/browse/jhbuild/
