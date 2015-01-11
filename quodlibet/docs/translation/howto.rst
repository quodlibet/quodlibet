.. _Translating:

How-to
======

If you're fluent in a language other than English, and have some spare
time, you can help us translate Quod Libet. Translation is a continuous
process on an active projects like this - as developers add new features or
modify existing text used, new translations will be needed. Many of the
translations files are missing a lot of strings, so please try the trunk
version in your language.

Of course, there might be mistakes in the English, too! Please let us know
if you find them.


Translation Software
--------------------

To translate, you'll want to have intltool, gettext and mercurial installed::

    apt-get install intltool gettext mercurial


For translating itself you need a PO editor like `Poedit 
<http://www.poedit.net/>`_::

    apt-get install poedit


Translation Process
-------------------

Get the QL code::

    $ hg clone https://quodlibet.googlecode.com/hg/ quodlibet 
    $ cd quodlibet/quodlibet

To translate the last release, update to the stable branch::

    $ hg branches  # to get the list of branches
    $ hg update quodlibet-X.X # for example: quodlibet-2.3

To translate current trunk, update to the default branch::

    $ hg update default

Create the POT file and update translations::

    $ ./setup.py build_mo


In case there's not already a translation for your language::

    $ msginit -i po/quodlibet.pot -l po/<mylang>


Now start translating...

::

    $ poedit ./po/<lang>.po

Test the translation by generating MO files and running Quod Libet and Ex 
Falso. build_mo will create a 'build' directory including the processed 
translations and if 'build' is present QL/EF will use these translations 
instead of the global ones.

::

    $ ./setup.py build_mo
    $ ./quodlibet.py
    $ ./exfalso.py

If your active system language is not the one you are translating, you can 
run them like::

    $ LANG=<mylang> ./quodlibet.py

Finally run our unit tests to make sure the translation will not cause 
programming errors. If it says something else, there's a problem with the 
translation.

::

    $ ./setup.py build_mo
    $ ./setup.py test --to-run PO.<mylang>

And send us the .po file you made! Create a `new issue 
<http://code.google.com/p/quodlibet/issues/entry>`_ and attach the file. 
Feel free to post a comment to the mailing list, so that other people can 
test your work.
