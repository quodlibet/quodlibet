.. _Testing:

=======
Testing
=======

Quod Libet uses the CPython unittest framework for testing and `pytest
<https://docs.pytest.org/en/latest/>`__ as a test runner. All testing related
code can be found under ``quodlibet/tests``.

To run the full tests suite simply execute::

    ./setup.py test

For checking the code coverage of the test suite run::

    ./setup.py coverage


Selecting a Specific Test
-------------------------

To only test a subset of the test suite, pass a comma separated list of test
class names to setup.py via the ``--to-run`` option. For example::

    ./setup.py test --to-run=TMP3File,TAPICType

Similarly the coverage report can also be generated for a subset of tests::

    ./setup.py coverage --to-run=TMP3File,TAPICType

Selecting by class name can take a long time because it needs to import all
tests first. To speed things up you can just use pytest directly::

    py.test tests/test_formats_mp3.py
    py.test tests/test_formats*
    py.test tests/test_formats_mp3.py::TMP3File

To just run code quality tests::

    py.test tests/quality

Some helpful ``py.test`` options are ``-s`` for not hiding stdout and ``-x``
for stopping on the first error. For more information check out
https://docs.pytest.org/en/latest/usage.html


Abort on First Error
--------------------

By passing ``-x`` to ``setup.py test`` the test suite will abort once it
sees the first error instead of printing a summary of errors at the end::

    ./setup.py test -x
