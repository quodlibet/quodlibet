.. _Translating:

How-to (Legacy Manual Process)
==============================

.. warning::
    The new preferred method to translate is via `Weblate
    <https://hosted.weblate.org/engage/quodlibet>`__. The process described here
    still works and is supported in case you for some reason prefer it.


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

    $ git clone https://github.com/quodlibet/quodlibet.git
    $ cd quodlibet

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

    $ LANGUAGE=<mylang> ./quodlibet.py

Finally run our unit tests to make sure the translation will not cause 
programming errors. If it says something else, there's a problem with the 
translation.

::

    $ ./setup.py test --to-run PO.<mylang>

And as a last step create a pull request with your changes:
https://github.com/quodlibet/quodlibet/pulls
