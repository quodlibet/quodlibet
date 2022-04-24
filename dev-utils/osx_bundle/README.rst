=========================
OS X Bundle Build Scripts
=========================

**Note:**
    In case you want just want to run Quod Libet from source you can ignore
    all this and use the released bundle as a development environment.
    Download the official bundle, git clone the quodlibet repo and do
    ``./QuodLibet.app/Contents/MacOS/run quodlibet.py``.


Uses `jhbuild <https://git.gnome.org/browse/jhbuild/>`__ with a Quod Libet
specific moduleset to build all needed dependencies for Quod Libet. Everything
will be downloaded/installed into this directory and your user directory will
not be touched.


Creating a Bundle
-----------------

Prerequisites:

* `macOS` 10.13+
* Xcode
* Xcode Command Line Tools
* Rust

Note: In case you want to target `macOS 10.13` with the resulting bundle you
have to build everything on `10.13`.
(see https://github.com/quodlibet/quodlibet/issues/2069)

1) Install the command line tools using ``xcode-select --install``.
2) Go to https://developer.apple.com/download/more/ and download the "XCode" matching your macOS version and install it.
3) (optional) On the same page download "Graphics Tools" and enable HiDPI
   debug mode in the "Quartz Debug" tool, so you can test HiDPI on a LowDPI
   screen.
4) Install rust: https://www.rust-lang.org/tools/install
5) Verify that Xcode and git is installed and in your ``$PATH`` by invoking
   ``git --version``, ``gcc --version``, ``xcodebuild -sdk -version`` and
   ``cargo``. Also make sure that other package managers like homebrew or
   macports aren't in your ``$PATH``.
6) Call ``bootstrap.sh`` to install jhbuild and and copy files into place.
7) Call ``build.sh`` to download and build all the dependencies.
   This should not lead to errors; if it does please file a bug.
8) Call ``bundle.sh`` to create the finished bundles for QL and EF in
   ``_build``.

Call ``clean.sh`` to remove everything created above again and get back to
the initial state.


Development
-----------

* After ``bootstrap.sh`` has finished executing ``source env.sh`` will put you
  in the build environment. After that jhbuild can be used directly (Enter the
  jhbuild environment using ``jhbuild shell``) or the Quod Libet test suite
  can be executed.
* ``bootstrap.sh`` can be called again to update the build environment while
  keeping any build packages.


Content Description
-------------------

* ``modulesets``: the jhbuild modulesets + patches.
* ``misc``: see each file or directory README for a description.
