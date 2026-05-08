.. _Testing:

=======
Testing
=======

Quod Libet uses the CPython unittest framework for testing and `pytest
<https://docs.pytest.org/en/latest/>`__ as a test runner. All testing related
code can be found under ``tests/``.

To run the full test suite::

    poetry run pytest tests/

For checking code coverage::

    poetry run coverage run -m pytest tests/
    poetry run coverage report


Selecting a Specific Test
-------------------------

Run a single file or a glob of files::

    poetry run pytest tests/test_formats_mp3.py
    poetry run pytest tests/test_formats*

Run a single test class or method::

    poetry run pytest tests/test_formats_mp3.py::TMP3File
    poetry run pytest tests/test_formats_mp3.py::TMP3File::test_title

To just run code quality tests::

    poetry run pytest tests/quality

Some helpful options are ``-s`` for not hiding stdout and ``-x`` for stopping
on the first error. For more information check out
https://docs.pytest.org/en/latest/usage.html


Abort on First Error
--------------------

Pass ``-x`` to abort on the first failure::

    poetry run pytest tests/ -x
