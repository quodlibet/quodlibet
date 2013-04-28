Translating
===========

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

Translation FAQ
---------------

Why are some strings not translatable?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In case of strings like "Apply" and "Ok" that show up on buttons, these 
come from GTK and are not part of QL. But there is a chance that we have 
forgotten to mark a string translatable, so please contact us.

If anything else is not translatable you can start QL with the following 
variable set::

    QUODLIBET_TEST_TRANS=xx ./quodlibet.py

which will append and prepend "xx" to all translatable strings.


Translation Context
^^^^^^^^^^^^^^^^^^^

Some strings have a "|" character in them (for example, 
"command|filename"). This is used to separate strings with the same text 
but different contexts. The filename string is used to describe the 
filename tag, and should be translated in a style appropriate for users to 
read in a GUI (for example, "nome de arquivo"). The "command|filename" is 
used to describe a command-line argument, and should be translated 
appropriate for that (for example, "nome_de_arquivo"). The comments in the 
PO file should describe the context if there is any.

Do not translate or include the text before the "|". For example, 
"command|tag" should be translated as "etiqueta" in Galician, not 
"command|etiqueta".


What does `check|titlecase?` mean?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There's a special string `check|titlecase?` which should be translated as 
anything if your language does not use `title casing 
<http://en.wikipedia.org/wiki/Letter_case>`_ (eg *This Is Title Casing*) 
for labels. If it is left untranslated, title-casing will be used.

Plural-Forms
^^^^^^^^^^^^

If you used KBabel or Emacs, you've already translated the plural forms, so
you can skip this.

GTranslator doesn't support "plural" messages (for example, *0 songs*, *1
song*, *2 songs*, *3 songs*...). After you do the translation with
GTranslator you'll need to open up the PO file in your favorite text editor
(`GEdit <http://live.gnome.org/Gedit>`_ is good for this, as is
`vim <http://www.vim.org/>`_) and manually edit the plural forms.

The first thing you need is a Plural-Forms line for your language. The GNU
gettext manual has a chapter on plural forms with examples for many
languages. This should go after the "Content-Transfer-Encoding" line.

The Plural-Forms line tells gettext how many plural forms there are in the
language and how to use them. For example:

::

    msgid "artist"
    msgid_plural "artists"
    msgstr[0] "artist"
    msgstr[1] "artists"

The English plural expression, "n != 1" means to use msgstr[0] if the count
is 1, otherwise use msgstr[1]. If your language has 3 plural forms, you'll
need msgstr[0], msgstr[1], and msgstr[2], and so on.

Sometimes (usually, even) the English strings will be the same. For 
example, ``%d selected`` doesn't change whether it stands for *1 selected* or 
*99 selected*. If it does in your language, you should translate them 
differently. There are further difficulties for the many languages that 
have gender agreement and an unspecified noun in the phrase, but these are 
often translated with brackets (eg in French: *1 sélectionné(e)*, *99 
sélectionné(e)s* perhaps)


Fuzzy translations
^^^^^^^^^^^^^^^^^^

A translation marked *fuzzy* is (usually) one that has been matched to a
similar previous translation, often by `gettext` itself. Note that fuzzy
translations are not treated as accurate translations so will not be used.

Common reasons for strings being marked as fuzzy include:
 * A contributor corrects a typo in the source (English) text 
 * A developer changes the `Mnemonic Label
   <http://developer.gnome.org/gtk/2.24/GtkLabel.html#id727933>`_ -
   This is the underscore you see in many translation strings.
 * The English has changed, but not much
 * sometimes it *just happens*...

For example::

    #: ../quodlibet/browsers/albums.py:425
    #, fuzzy
    msgid "Sort _by:"
    msgstr "Ordina per data"

Here, in the Italian `.po` file, you can see this message has been matched,
presumably used from a "Sort by date" translation previously entered. This
explains why this string was missing in the Italian build.

As a translator please make sure there are no translations left marked as
fuzzy. In `poedit`, you can click the cloud (!) icon, or in a text editor
you should simply remove the `fuzzy` string above the `msgid`.

Other resources
---------------

The `GNOME Translation Project <http://live.gnome.org/TranslationProject>`_ 
has many good resources on how to translate programs properly. When 
possible we try to share English terms and phrases with other GTK+/GNOME 
applications, and we'd like to share non-English ones, too.
