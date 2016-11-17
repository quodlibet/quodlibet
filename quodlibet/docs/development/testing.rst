.. _Testing:

=======
Testing
=======

Quod Libet uses the CPython unittest framework for testing. All testing related
code can be found under ``quodlibet/quodlibet/tests``.

To run the full tests suite simply execute::

    ./setup.py test

We also provide a test for checking code quality using ``pep8`` and
``pyflakes``. To run it simply execute::

    ./setup.py quality

For checking the code coverage of the test suite run::

    ./setup.py coverage


Selecting a Specific Test
-------------------------

To only test a subset of the test suite, pass a comma separated list of test
class names to setup.py via the ``--to-run`` option. For example::

    ./setup.py test --to-run=TMP3File,TAPICType

Similarly the coverage report can also be generated for a subset of tests::

    ./setup.py coverage --to-run=TMP3File,TAPICType


Abort on First Error
--------------------

By passing ``-x`` to ``setup.py test`` the test suite will abort once it
sees the first error instead of printing a summary of errors at the end::

    ./setup.py test -x
