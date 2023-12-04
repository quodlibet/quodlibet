=========================
OS X Bundle Build Scripts
=========================

**Note:**
    In case you want just want to run Quod Libet from source you can ignore
    all this and use the released bundle as a development environment.
    Download the official bundle, git clone the quodlibet repo and do
    ``./QuodLibet.app/Contents/MacOS/run quodlibet.py``.


The Quod Libet and Ex Falso bundles for OS X contain the application itself
(as both .py and .pyc files), all needed Python packages and machine code
libraries (e.g. GStreamer, GTK+, etc.) and a Python interpreter.  The
only external dependencies are the OS X system libraries.

The machine code libraries are downloaded from their various repositories and
built using `jhbuild <https://git.gnome.org/browse/jhbuild/>`__, a tool 
originally developed for GNOME.  The Python packages are downloaded from
`PyPI https://pypi.python.org/pypi`.


Creating a Bundle
-----------------

Prerequisites:

* `macOS` 10.14+
* Xcode
* Xcode Command Line Tools
* Rust
* Git
* Python3 (see caveats below)

Note: In case you want to target `macOS 10.14` with the resulting bundle you
have to build everything on `10.14`.

1) Go to https://developer.apple.com/download/more/ or the Apple App Store
   and install XCode.
2) Install the command line tools using ``xcode-select --install``.
3) Install rust: https://www.rust-lang.org/tools/install
4) Verify that Xcode and git is installed and in your ``$PATH`` by invoking
   ``git --version``, ``gcc --version``, ``xcodebuild -sdk -version`` and
   ``cargo``. 
5) Make sure that other package managers like homebrew or macports aren't in 
   your ``$PATH`` and that the libraries they install aren't in your
   ``$DYLD_LIBRARY_PATH`` or ``$LD_LIBRARY_PATH``.
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


Caveats and Hints
-----------------

* These instructions are current as of December 2023 and OS X 14.1.  
* No recent attempt has been made to run the Quod Libet test suite on OS X.
* No attempt has been made to build on or for Apple Silicon.
* A complete build takes about two hours on a 2.4 GHz 8-Core Intel Core i9
  with 32 GB RAM and a 1 TB SSD.  Configure scripts consume most of this time.
* The build uses Python distutils, which were removed in Python 3.12.
  Recent development has used Python 3.11.3.  Issue #4442.
* See env.sh for the directories used by jhbuild for the various package's
  source, build and prefix directories.
* If you change or add a patch file, you need to delete the package's 
  source directory to force jhbuild to download the package again and
  reapply patches.
* The pkg_config built by jhbuild has this default search path:
  ``_home/jhbuild_prefix/bin/pkg-config --variable pc_path pkg-config``


Content Description
-------------------

* ``modulesets``: the jhbuild modulesets + patches.
* ``misc``: see each file or directory README for a description.
