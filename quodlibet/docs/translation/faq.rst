FAQ
===


What do these things in strings mean?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``command|tag``: see `Translation Context`_
* ``This is %s``, ``an %(foobat)s example``, ``for {translators}, {0}``:
  see `String Formatting`_


Why are some strings not translatable?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In case of strings like "Apply" and "Ok" that show up on buttons, these 
come from GTK and are not part of QL. But there is a chance that we have 
forgotten to mark a string translatable, so please contact us.

If anything else is not translatable you can start QL with the following 
variable set::

    QUODLIBET_TEST_TRANS=xx ./quodlibet.py

which will append and prepend "xx" to all translatable strings.


What does `check|titlecase?` mean?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There's a special string `check|titlecase?` which should be translated as 
anything if your language does not use `title casing 
<http://en.wikipedia.org/wiki/Letter_case>`_ (eg *This Is Title Casing*) 
for labels. If it is left untranslated, title-casing will be used.


String Formatting
^^^^^^^^^^^^^^^^^

Some strings include replacement tokens like ``%s`` or ``{foobar}``. These 
mark places where text gets replaces at runtime, so they should be carried 
over to the translation without changing their content.

Some examples showing the strings to translate and the resulting strings 
where the tokens have been replaced:

* ``Hello %s`` -> ``Hello Lou``
* ``The number %d`` -> ``The number 42``
* ``Hello %(name)s`` -> ``Hello Lou``
* ``Hello {name}`` -> ``Hello Lou``
* ``Hello {0}`` -> ``Hello Lou``
* ``Hello {0.name}`` -> ``Hello Lou``
* ``Hello {}`` -> ``Hello Lou``

In the case of ``Hello %(name)s``, a possible German translation and text 
displayed to the user would be ``Hallo %(name)s`` and ``Hallo Lou``.


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


Plural-Forms
^^^^^^^^^^^^

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
