========
Overview
========

Building and Installing Quod Libet
----------------------------------

While Quod Libet uses distutils/setup.py for building and installing
(``./setup.py build install`` etc.) we don't recommend it, as it doesn't
provide a way to uninstall the application again and it might not do the right
thing by default depending on your distribution/operating system.

Instead we recommend running Quod Libet directly from the git checkout for
development/experiments and use one of our unstable repositories for everyday
use.

See :ref:`DevEnv` on how to proceed, then run ``./exfalso.py`` or
``./quodlibet.py`` 


Testing Changes
---------------

To make sure that your changes don't break any existing feature you should run
the test suite by executing::

    ./setup.py test

For more details and options regarding testing, code quality testing and test
coverage see :ref:`Testing`.
