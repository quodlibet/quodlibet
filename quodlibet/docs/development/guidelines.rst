Workflow & Guidelines
=====================

.. seealso::

    This page contains information on contributing code and patches to Quod 
    Libet. If you want to contribute in another way please see 
    :ref:`Contribute` for many ways to help.


Getting started
---------------

Quod Libet now provides its code through Google Code's Mercurial hosting
service. Click the "Source" tab at the top of the screen to view the current
history, or pull a copy using the
`checkout instructions <http://code.google.com/p/quodlibet/source/checkout>`_.

If you have a recent GTK+ version installed and don't need translations you
can simply run QL directly from source without building/installing.
All you need are the :ref:`dependencies<Dependencies>`. Since QL does not
depend on recent versions of them, the ones shipping with your
distribution should work.

See :ref:`RunFromSource` on how to get started.


Source Overview
---------------

============ ==========================================
browsers/*    Things in the View menu
formats/*     File format support
library/*     Library management code
qltk/*        GTK+ widget subclasses/extensions
util/*        General utility functions and setup code
============ ==========================================

If you want to get a full overview of QL's code, good places to start
are browsers/_base.py, formats/_audio.py, and library/libraries.py.


Tags & Branches
---------------

At the point where no new functionality will be added before a release, a 
new branch gets created. All bugfix changes should get commited there and 
merged back in the default branch where new functionality can be added. In 
case a bugfix was commited to the default branch or an unplanned stable 
release is needed use the hg graft extension to copy those changes to the 
stable branch(es).

::

     /|\     /|\
      |       |
      |    2.4.91
    2.5.-1   /   <--- quodlibet-2.5 branch
      |_____/
      |       /|\
      |        |
      |      2.4.1  <--- quodlibet-2.4.1 tag
      |        |
      |      2.4.0.-1
      |        |
      |      2.4  <--- quodlibet-2.4.0 tag
      |        |
      |      2.3.91.-1
      |        |
      |      2.3.91
    2.4.-1    /
      |______/   <--- quodlibet-2.4 branch
      |
      |  <--- default branch
    2.3.-1
      |
     /|\



Code Guidelines
---------------

We try to keep Quod Libet's code in pretty good shape; when submitting a
patch, it's much easier to get it included quickly if you run through this
checklist of common-sense code quality items. Make sure your patch:

  * is `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`_ compliant.
    Yes, this means an 80-character line length.
  * passes existing tests, and includes new ones if at all possible.
  * is commented.
  * adds your name to the copyright header of every file you touch.
    This helps you get credit and helps us keep track of authorship.


General Guidelines
------------------

We prefer Python to C. We prefer ctypes to compiled C wrappers. A good way 
to get a new feature applied is if you include tests for it. Stock strings 
and string reuse are awesome, but don't make the interface awkward just to 
avoid a new string.


Unit Tests
----------

Quod Libet comes with tests. To run them, run ``./setup.py test``. Your 
patch can't break any unit tests, and if you change tests in a non-obvious 
way (e.g. a patch that removes an entry point and also removes a test for 
it is obvious) you should explain why.


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


Submitting
----------

If your patch fixes a known bug with a ticket, you should attach it to
the ticket directly. If it is a bug fix but doesn't have a ticket, you
can either make a ticket to attach it to, or send it to the mailing list,
quod-libet-development@googlegroups.com.

The ticket tracker is at http://code.google.com/p/quodlibet/issues/list
and at http://code.google.com/p/quodlibet/issues/entry.
