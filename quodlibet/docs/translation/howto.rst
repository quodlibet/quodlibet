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

To translate, you'll want to have gettext and git installed::

    apt-get install gettext git


For translating itself you need a PO editor like `Poedit 
<https://poedit.net/>`_::

    apt-get install poedit


Translation Process
-------------------

Get the QL code::

    $ git clone https://github.com/quodlibet/quodlibet.git quodlibet 
    $ cd quodlibet/quodlibet

To translate the last release, update to the stable branch::

    $ git branch -a  # to get the list of branches
    $ git checkout quodlibet-X.X # for example: quodlibet-3.3

To translate current trunk, update to the default branch::

    $ git checkout master

You can find the translation file for your chosen language in::

    ./po/<lang>.po

In case there's not already a translation for your language, create one::

    $ ./setup.py create_po --lang=<mylang>

Update translations so all new strings that were added since the last
translation update get included::

    $ ./setup.py update_po --lang=<mylang>

Now start translating...

::

    $ poedit ./po/<lang>.po

Test the translation by generating MO files and running Quod Libet and Ex 
Falso. build_mo will create a 'build' directory including the processed 
translations and if 'build' is present QL/EF will use these translations 
instead of the global ones.

::

    $ ./setup.py build_mo --lang=<mylang>
    $ ./quodlibet.py
    $ ./exfalso.py

If your active system language is not the one you are translating, you can 
run them like::

    $ LANG=<mylang> ./quodlibet.py

Finally run our unit tests to make sure the translation will not cause 
programming errors. If it says something else, there's a problem with the 
translation.

::

    $ ./setup.py test --to-run PO.<mylang>

And send us the .po file you made:

* Create a pull request.
* Or create a `new issue 
  <https://github.com/quodlibet/quodlibet/issues/new>`__ linking to your 
  updated .po file. If you don't have a place for making the file accessible 
  create a `gist <https://gist.github.com/>`__ with the content of the .po 
  file and include the gist URL in the issue description.
