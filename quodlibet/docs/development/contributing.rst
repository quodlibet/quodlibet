.. _Contribute:

How to contribute
=================

Testing
-------

One of the most helpful things both regular users and developers can do is
to test others' code. The easiest way to do this is to run the development
version of Quod Libet. Development versions are kept stable, and the
developers generally run the latest code to play their own music, so this
is a safe and helpful way to contribute.

Please keep in mind that Quod Libet is not forward compatible, meaning that 
if you use a newer version, reverting to an older version could lead to 
errors and data loss. So always backup your :ref:`config 
files<ConfigFiles>` if you plan to downgrade at a later point.

You can find find development packages in the :ref:`download section
<Downloads>` .


Trying Patches
--------------

Sometimes developers will post patches on tickets (`try these tickets
<http://code.google.com/p/quodlibet/issues/list?can=2&q=label%3APatch>`_
for a start) for preview or experimental functionality. To install these
over a local checkout, save the patch file e.g. to `123-ql.patch`

::

    $ cd /usr/local/src/quodlibet/    # or wherever you have it
    $ patch -p1 < ql.patch

If you're using mercurial, you can just use ``hg revert --all`` to remove
any patches. Also, for more advanced usage or to test multiple patches
together, you may also like to try `mercurial queues
<http://mercurial.selenic.com/wiki/MqTutorial>`_.

.. _BugReports:

Filing bug reports
------------------

Useful Links
^^^^^^^^^^^^

 * `List current bugs <http://code.google.com/p/quodlibet/issues/list>`_
 * `Add a new bug <http://code.google.com/p/quodlibet/issues/entry>`_


Writing a good bug report
^^^^^^^^^^^^^^^^^^^^^^^^^

The more information provided in a bug report, the more likely a bug can be
reproduced on another system. Good examples of details include:

  * OS, distribution, and version
  * Versions of Python, Quod Libet, Mutagen, GTK, PyGTK, GStreamer, libXine
  * A list of all enabled plugins
  * The current browser
  * Debug log information (dump files)

For more tips see `How to Report Bugs Effectively
<http://www.chiark.greenend.org.uk/~sgtatham/bugs.html>`_.


Isolating the problem(s)
^^^^^^^^^^^^^^^^^^^^^^^^

Misbehaving plugins are a common source of bugs. Try reproducing the bug
with all plugins disabled; if the bug is gone, enable them one by one until
you find the *combination* of plugins that triggers the bug.


Viewing Debug information
^^^^^^^^^^^^^^^^^^^^^^^^^

If the bug you have found does not raise an exception, the debug window
won't appear and the dump won't be generated. In this case, run quodlibet
from the command line using the command ``$ QUODLIBET_DEBUG=1 quodlibet``
(or in newer versions, just ``quodlibet --debug``), and use 'Cause an
error' from the Help menu to produce the dump.


Testing the latest code
^^^^^^^^^^^^^^^^^^^^^^^

Some problems are fixed in the development branch which aren't yet fixed in
the current release. If you can, try to reproduce your bug against a recent
checkout before filing.


One bug per ticket
^^^^^^^^^^^^^^^^^^

Please do not create an item (ticket) in the issue tracker which contains
reports of multiple unrelated issues. Even if you are reporting several
very minor bugs, each one deserves its own issue. This allows each issue to
receive independent discussion and analysis, and to be closed separately.


Filing enhancement requests
---------------------------

The most important component of an enhancement is the *why*. State what it
is Quod Libet doesn't do for you, and give as much information about why
you think adding a feature which accomplished this would be a good thing.
If you have an idea as to how a feature might be implemented, suggestions
are welcome, but be sure to explain why you want a feature before
explaining how you envision it being implemented. Not only does this make
your feature more likely to be supported, it allows others to enhance,
generalize, and refine your ideas.

As with bugs, please refrain from submitting multiple feature requests in
the same issue. If you have related ideas, file them separately and mention
the issue numbers of previous ideas.


Translation
-----------

Help us :ref:`translate Quod Libet into other languages<Translating>`.
You don't need to know how to program in Python to do it.


Submitting patches
------------------

Patches are always welcome, and should be attached to the issue tracker. We
review every issue and tag the ones which include patches, so there's no
need to add "PATCH" to the issue summary.

We try to keep Quod Libet's code in pretty good shape; when submitting a
patch, it's much easier to get it included quickly if you run through this
checklist of common-sense code quality items. Make sure your patch:

  * is `PEP 8 <http://www.python.org/dev/peps/pep-0008/>`_ compliant.
    Yes, this means an 80-character line length.
  * passes existing tests, and includes new ones if at all possible.
  * is commented.
  * adds your name to the copyright header of every file you touch.
    This helps you get credit and helps us keep track of authorship.
