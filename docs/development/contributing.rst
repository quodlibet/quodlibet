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

You can find development packages in the :ref:`download section
<Downloads>` .


.. _BugReports:

Filing bug reports
------------------

Useful Links
    * `List current bugs <https://github.com/quodlibet/quodlibet/issues>`_
    * `Add a new bug <https://github.com/quodlibet/quodlibet/issues/new>`_


Writing a good bug report
    It helps the developers to format bugs in a standard way, with a short
    summary as the Issue title, ideally:

      1. **Steps to reproduce** (how the bug can be demonstrated again)
      2. **Expected output** (what *should* happen)
      3. **Actual output** (what *did* happen)

    Also: the more logs, system details, and insight about the library / files
    the better the chance of a speedy resolution.

    For more general tips see `"How to Report Bugs Effectively"
    <https://www.chiark.greenend.org.uk/~sgtatham/bugs.html>`_.

Look through existing issues
    Quod Libet is a mature project (in its second decade!), and there have been
    a *lot* of features and bugs discussed over the years. It's probable that
    what you're thinking has been discussed at some point, so please search
    through existing open (and to a lesser extent closed) issues before
    creating a new one. This reduces noise and saves the maintainers time.

One bug per ticket
    Please do not create an item (ticket) in the issue tracker which contains
    reports of multiple unrelated issues. Even if you are reporting several
    very minor bugs, each one deserves its own issue. This allows each issue to
    receive independent discussion and analysis, and to be closed separately.


Viewing Debug information
    If the bug you have found does not raise an exception, the debug window
    won't appear and the dump won't be generated. In this case, run quodlibet
    from the command line using the command ``quodlibet --debug``. It will show
    additional information that might be useful.


Testing the latest code
    Some problems are fixed in the development branch which aren't yet fixed in
    the current release. If you can, try to reproduce your bug against a recent
    checkout before filing.


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

As with bugs, please check for existing feature requests first and
refrain from submitting multiple feature requests in the same issue.
If you have related ideas, file them separately and mention
the issue numbers of previous ideas.


Translation
-----------

Help us :ref:`translate Quod Libet into other languages<Translating>`.
You don't need to know how to program in Python to do it.


Getting started as a developer on Quod Libet
--------------------------------------------

On an long-standing project it can be daunting helping out for the first time.
The `newcomer-friendly tag <https://github.com/quodlibet/quodlibet/issues?q=is%3Aopen+is%3Aissue+label%3Anewcomer-friendly>`_
has been added to (some) issues to indicate where the existing developers
feel there is an opportunity to help out without too much background (or risk).
See the discussion around this in `Issue 2516 <https://github.com/quodlibet/quodlibet/issues/2516>`_

The other area perfect for newcomers is in the rich
:ref:`plugins ecosystem <PluginDev>` - at time of writing QL has >80 plugins.
These require less knowledge of Python, GTK+ and the QL architecture / codebase.

It's best to examine existing (and past) PRs, keep an eye on the mailing list,
and especially the Github issues list.
Reading the unit / integration tests is usually instructive too.
IRC can be a good place for more immediate questions.


Submitting changes
------------------

Patches are always welcome, and should be in the form of a pull request or by 
attaching a patch to the issue.
Please work on existing issues where possible (there are a lot),
or at the very least make sure there is an accompanying issue for your PR.

If you follow the :ref:`CodingGuidelines` it will be much easier to get your 
changes included quickly.
