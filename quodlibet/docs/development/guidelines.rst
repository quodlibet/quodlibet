.. _CodingGuidelines:

Coding Guidelines
=================

Getting started
---------------

Before you can start making changes to Quod Libet you have to set up a
development environment. See ":ref:`DevEnv`" for further details.

Source Overview
---------------

============ ==========================================
browsers/*    Things in the View menu
ext/*         Extensions to QL / EF (i.e. the plugins)
formats/*     File format support
library/*     Library management code
plugins/*     Base classes and structural enabling plugins
operon/*      Operon, the QL CLI tool
qltk/*        GTK+ widget subclasses/extensions
util/*        General utility functions and setup code
============ ==========================================

If you want to get a full overview of QL's code, good places to start
are ``browsers/_base.py``, ``formats/_audio.py``, and ``library/libraries.py``.


Code Guidelines
---------------

We try to keep Quod Libet's code in pretty good shape; when submitting a
patch, it's much easier to get it included quickly if you run through this
checklist of common-sense code quality items. Make sure your patch:

* Passes existing tests. You can test this by executing ``./setup.py test``
* Is commented.
* Adds your name to the copyright header of every file you touch.
  This helps you get credit and helps us keep track of authorship.


General Guidelines
------------------

We prefer Python to C. We prefer ``ctypes`` to compiled C wrappers. A good way
to get a new feature applied is if you include tests for it. Stock strings 
and string reuse are awesome, but don't make the interface awkward just to 
avoid a new string.


Unit Tests
----------

Quod Libet comes with a lot of tests, which helps us control regression.
To run them, run ``./setup.py test``. Your
patch can't break any unit tests, and if you change tests in a non-obvious 
way (e.g. a patch that removes an entry point and also removes a test for 
it is obvious) you should explain why.

It's possible, indeed encouraged, that a changeset was for no other purpose
than to *improve* the testing / test coverage, as there have been plenty of
bugs that have slipped through. As usual, any fix associated with a confirmed
bug should include tests that would have found the original bug, where possible.

Printing Text
-------------

All terminal output should go through the ``print_``, ``print_w``, 
``print_e``, or ``print_d`` functions. These will handle Unicode recoding. 
They also let us capture all output for debugging purposes.


Translations
------------

All text that could be visible to users (with debugging mode disabled) 
should be marked translatable.

You can do this by simply using the ``_`` function which is globally 
available (through __builtin__)::

    print_w(_("This is translatable"))

To handle plural forms use ``ngettext``::

    text = ngettext("%d second", "%d seconds", time) % time

It is good practice to add a comment for translators if the translation 
depends on the context::

    # Translators: As in "by Artist Name"
    text = _("by %s") % tag
