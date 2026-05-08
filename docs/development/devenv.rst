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



Poetry
------

Across all environments, we now support Virtualenvs with Pip dependencies,
managed by `Poetry <https://python-poetry.org/>`__.
We currently require Poetry 2.

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

Install the native dependencies via Homebrew, then use Poetry for Python packages::

    $ brew install cairo dbus gst-libav gst-plugins-bad gst-plugins-good gst-plugins-ugly \
        gstreamer gtk-mac-integration gtk+3 libsoup pkg-config pygobject3
    $ poetry install
    $ poetry run pip install pyobjc

.. |quodlibet.modules ref| replace:: ``quodlibet.modules`` moduleset file
.. _quodlibet.modules ref: https://github.com/quodlibet/quodlibet/tree/main/dev-utils/osx_bundle/modulesets/quodlibet.modules

The brew list above may be out of date; check the ``quodlibet`` metamodule section of the
|quodlibet.modules ref|_ for the authoritative list.

Running the app
~~~~~~~~~~~~~~~

To run Quod Libet from source on macOS, use the helper script in ``dev-utils/macos/``::

    $ ./dev-utils/macos/run.sh

This is required for ``MPRemoteCommandCenter`` and media key routing to work. Without it,
macOS will not route media keys to the process because it lacks a bundle identity.
See ``dev-utils/macos/run.sh`` for details.

Running tests
~~~~~~~~~~~~~

The test suite does not need a bundle identity — run it directly with Poetry::

    $ poetry run pytest tests/

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
