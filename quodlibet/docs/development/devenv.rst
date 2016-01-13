.. include:: ../icons.rst

.. _DevEnv:

Creating a Development Environment
==================================

This will show you how to get the latest and freshest Quod Libet running on
your machine and allow you to change it as you wish. The main task here is to
install all the software which Quod Libet uses and depends on.


|linux-logo| Linux
------------------

The easiest and recommended way to get all the dependencies needed for the
development version is to install one of our unstable repositories. By doing
so all the needed dependencies are automatically installed along the way. See
the :ref:`download section <Downloads>` for a list of available repositories.

In case your distribution is not supported you have to find/install the
dependencies yourself. See the :ref:`PackagingGuide` for a list of
dependencies.

Now clone the git repository and start Quod Libet::

    $ git clone https://github.com/quodlibet/quodlibet.git
    $ ./quodlibet/quodlibet/quodlibet.py


|macosx-logo| OS X
------------------

On OS X all the needed dependencies are included in :ref:`the provided bundle
<macosx>` itself. The bundle contains a script which passes all arguments to
the included Python with the right environment set up.

::

    $ git clone https://github.com/quodlibet/quodlibet.git
    $ ./QuodLibet.app/Contents/MacOS/run <path_to_git_repo>/quodlibet/quodlibet.py

If you want to build a bundle yourself or change/add dependencies check out
the `"osx_bundle"
<https://github.com/quodlibet/quodlibet/tree/master/osx_bundle>`__ directory
in the git repo for further instructions.


|windows-logo| Windows
----------------------

On Windows we provide a special SDK package which includes all dependencies
and tools for development. Check out the :ref:`Windows download section
<windows>`.

First extract the package and open a console in the sdk directory. Then

#. run env.bat
#. (first time only) run clone.bat
#. cd quodlibet\\quodlibet
#. python quodlibet.py

If you want to build an installer yourself or change/add dependencies check
out the `"win_installer"
<https://github.com/quodlibet/quodlibet/tree/master/win_installer>`__
directory in the git repo for further instructions.
