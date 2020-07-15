Frequently Asked Questions
==========================

Any plans to use Python 3?
--------------------------

Older releases of QL use Python 2. As of :ref:`release 4.0.0 <release-4.0.0>`,
QL is Python 3 only.


Why don't you use SQLite for the song database?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Although the song data Quod Libet stores would benefit from a relational
database, it does not have a predefined schema, and opts to let users define
their own storage keys. This means relational databases based on SQL, which
require predefined schemata, cannot be used directly.


What about <my favourite NoSQL DB> then?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This gets asked fairly often. MongoDB, CouchDB etc are indeed a closer match
to the existing setup, but there is *significant* work porting to any of
these, and each comes with a compatibility / maintenance cost. There has to be
a genuine case for the benefits outweighing the migration cost.


Any environment variables I should know about?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

QUODLIBET_TEST_TRANS
    When set to a string will enclose all translatable strings with that
    string. This is useful for testing how the layout of the user interface
    behaves with longer text as can occur with translations and to see if all
    visible text is correctly marked as translatable.

    ::

        QUODLIBET_TEST_TRANS=XXX

QUODLIBET_DEBUG
    When in the environment gives the same result as if ``--debug`` was passed.


QUODLIBET_BACKEND
    Can be set to the audio backend, overriding the value present in the main
    config file. Useful for quickly testing a different audio backend.

    ::

        QUODLIBET_BACKEND=xinebe ./quodlibet.py

QUODLIBET_USERDIR
    Can be set to a (potentially not existing) directory which will be used as
    the main config directory. Useful to test Quod Libet with a fresh config,
    test the initial user experience, or to try out things without them
    affecting your main library.

    ::

        QUODLIBET_USERDIR=foo ./quodlibet.py
