.. include:: ../icons.rst

.. _DevEnv:

Creating a Development Environment
==================================

This will show you how to get the latest and freshest Quod Libet running on
your machine and allow you to change it as you wish. The main task here is to
install all the software which Quod Libet uses and depends on.


Nix Flake
---------

To help with consistent tooling across machines and platforms,
we now include a basic `Nix Flake <https://nixos.wiki/wiki/Flakes>`__
which currently provides suitable versions for Python and Poetry (see below)
as well as some linter tooling.
To run a Bash shell with this set up, install Nix (with Flake support),
then run::

    $ nix develop
    $ python --version  # or whatever

You can also run Flake apps directly, e.g.::

    $ nix run .#poetry -- --version



Poetry
------

Across all environments, we now support Virtualenvs with Pip dependencies,
managed by `Poetry <https://python-poetry.org/>`__.

Installation, once cloned is just::

    $ poetry install


If you want all the *optional* dependencies for various plugins::

    $ poetry install -E plugins


|linux-logo| Linux
------------------

The easiest and recommended way to get all the dependencies needed for the
development version is to install one of our unstable repositories. By doing
so all the needed dependencies are automatically installed along the way. See
the :ref:`download section <Downloads>` for a list of available repositories.

In case your distribution is not supported you have to find/install the
dependencies yourself. See the :ref:`PackagingGuide` for a list of
dependencies.

Now clone the Git repository and start Quod Libet::

    $ git clone https://github.com/quodlibet/quodlibet.git
    $ ./quodlibet/quodlibet/quodlibet.py


|macosx-logo| MacOS
-------------------

On MacOS (formerly OS X) all the needed dependencies are included in the provided bundle
itself.
Download the latest bundle, which is guaranteed to work with current
Git ``main``: `QuodLibet-latest.dmg
<https://github.com/quodlibet/quodlibet/releases/download/ci/QuodLibet-latest.dmg>`__.
It contains a ``run`` script which passes all arguments to the included Python with
the right environment set up.

::

    $ git clone https://github.com/quodlibet/quodlibet.git
    $ ./QuodLibet.app/Contents/MacOS/run <path_to_git_repo>/quodlibet/quodlibet.py

On recent MacOS releases, the OS Gatekeeper will complain about the application not being recognised.
It is easiest to just clear the `com.apple.quarantine` extended attribute from all files in the bundle
rather than try and open each and every component that MacOS will refuse to open:

::

    $ xattr -rd com.apple.quarantine ./QuodLibet.app/Contents

The bundle includes `pip`, so you can always install additional packages (such as `flake8`, `pytest` and
`flaky`, which would let you run the test suite):

::

    $ ./QuodLibet.app/Contents/MacOS/run -m pip install flake8 pytest flaky
    $ ./QuodLibet.app/Contents/MacOS/run <path_to_git_repo>/setup.py test

If you want to run the tests with your own Python command, you'll need to install some additonal software
and packages:

::

    $ brew install cairo dbus gst-libav gst-plugins-bad gst-plugins-good gst-plugins-ugly \
        gstreamer gtk-mac-integration gtk+3 libsoup pkg-config pygobject3
    $ poetry install
    $ poetry run pip install pyobjc


.. |quodlibet.modules ref| replace:: ``quodlibet.modules`` moduleset file 
.. _quodlibet.modules ref: https://github.com/quodlibet/quodlibet/tree/main/dev-utils/osx_bundle/modulesets/quodlibet.modules

This will *almost* cover all the dependencies that the bundle will contain; at the time of writing the brew
gstreamer plugins do not include the wavpack (``gst-plugins-good``) or game-music-emu (gme, in ``gst-plugins-bad``)
plugins. The above list may be out of date, check the ``quodlibet`` metamodule section of the |quodlibet.modules ref|_
for a more up-to-date list of dependencies.

If you want to build a bundle yourself or change/add dependencies,
see the `osx_bundle directory
<https://github.com/quodlibet/quodlibet/tree/main/dev-utils/osx_bundle>`__
in the Git repo for further instructions.


|windows-logo| Windows
----------------------

On Windows we use the `msys2 <http://www.msys2.org/>`__ environment for
development.

Check out the `win_installer
<https://github.com/quodlibet/quodlibet/tree/main/dev-utils/win_installer>`__
directory in the Git repo for further instructions.

