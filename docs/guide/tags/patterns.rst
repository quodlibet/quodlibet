.. _TagPatterns:

Tag Patterns
============

Tag patterns can be used to change the information displayed in various places
like the playing song area, columns in the song list, and the album list in the
album browser.

They can also be used to group songs in the paned and album collection browsers
in more complex ways.

The file renaming tool uses tag patterns to determine the file names and folder
structure to be used for the moved files.

Usage
-----

A tag pattern is a string (piece of text) in which certain symbols receive
special meaning.
Parts of the string that carry no special meaning will be printed as-is when
the tag pattern is rendered by Quod Libet.

To indicate that part of a tag pattern is to be given special meaning in Quod
Libet, it is surrounded by angle brackets,
as in ``<artist>``.
The portion of a tag pattern surrounded by brackets is called a tag
*expression*.

Let's consider a simple example:

``<artist> - <title> (<album>)``

Which might produce:

``The Beatles - Drive My Car (Rubber Soul)``

This example illustrates the most basic form of a tag expression.
In this case, each tag expression is simply the name of a tag.
In a tag expression, a tag name signifies the *contents* of the tag,
or nothing (if the tag is absent or empty).
If the file used in the example did not have the album tag set, the tag pattern
would produce:

``The Beatles - Drive My Car ()``

Tag expressions are not arbitrary strings like tag patterns.
If you write a tag expression with incorrect syntax,
it is likely that Quod Libet will not print anything at all,
so it is important to be careful.

Let's consider some more sophisticated tag expressions.

Fallback Tags
-------------

🆕 `from QL 4.7 onwards`

It's useful to be able to print the contents of a tag only if it exists,
as shown above.
However, you might want to print a tag if it exists,
and fall back to printing some other tag if it does not.
The fallback tag expression allows you to do this with a convenient piece of
syntax,
the double pipe (``||``).

The syntax for this expression is as follows:

 * ``<tag-pattern||tag-pattern>``

This tag expression will print the result of the tag pattern on the left,
if it is non-empty,
and otherwise print the tag pattern on the right (even if it is empty).

Because fallback tag expressions can contain arbitrary tag patterns,
they are extremely flexible.
Since tag patterns can contain a piece of text *or* a valid tag expression,
both of the following are valid examples of fallback tag expressions:

 * ``<<albumartist>||<artist>>``
 * ``<<albumartist>||no album artist>``

The former will fall back to printing the contents of the ``artist``
tag, if the ``albumartist`` tag does not exist.
The latter will instead print the text "no album artist".

Fallback tag expressions are also chainable:
you can use an arbitrary number of tag patterns
and only the first non-empty pattern will be printed.
For instance:

 * ``<<composer>||<albumartist>||<artist>>``

Conditional Tags
----------------

Sometimes you want to print something if a tag exists,
but you don't want to print the content of the tag.
In this case the conditional tag expression syntax comes in handy.

This is a simple if-then-else concept,
which tests if a tag is non-empty,
and prints one of two patterns based on the result of the test.
The syntax for this expression uses the pipe (``|``) character as a delimiter,
in either of these formats:

 * ``<tag-expression|tag-pattern-if-non-empty>``
 * ``<tag-expression|tag-pattern-if-non-empty|tag-pattern-if-empty>``

Using the second form, a pattern of:

    ``<album|Has An Album|No Album>``

produces ``Has An Album`` for any song with at least one ``album`` tag value,
else producing ``No Album``.

Boolean Tag Expressions
-----------------------

The conditional tag expression is not limited to testing for the existence of a
tag.
Quod Libet supports more complicated tag expressions that test for other
conditions.
These expressions do not print anything.
Instead, they produce a true or false condition that is interpreted by the
conditional tag expression.

Conveniently, these expressions reuse the same syntax as search queries,
which is described in :ref:`Searching`.
For example, to check that the contents of a tag match a particular search
string, one could do this:

    ``<sometag=test|the tag contained test|it was something different>``

Or to take a more complicated example:

    ``<artist=\|(Townshend, Who)|foo|bar>``

In this case, notice that any piece of syntax that would normally be
interpreted as a piece of tag expression syntax needs to be escaped for it to
be interpreted as search query syntax.
This is done by preceding it with a ``\\`` character.

Nested Tag Expressions
-------------------------

The syntax for both fallback and conditional tag expressions allows for the
use of arbitrary tag patterns as possible outputs of the expression.
In both cases, this means that tag expressions can contain other tag
expressions.

For example,
suppose you wanted to print the ``composer`` tag for classical music,
and print the ``artist`` tag for anything else.
You could do it like this:

    ``<genre=classical|<composer>|<artist>``

If you wanted to print the ``composer`` tag for classical music only if it
exists, and print the ``artist`` in all other cases, you could do this:

    ``<<genre=classical|<composer>>||<artist>``

As you can see, this makes use of a conditional expression and a fallback
expression at once.
Their syntax allows them to be nested arbitrarily.

Additional Examples
-------------------

  * ``<~year|<~year>. <album>|<album>>``: *2011. This is an album title*
  * ``<title>, by <<albumartist>||<composer>||<artist>>``:
    *Liebstraum no. 3, by Franz Liszt*

.. _TextMarkup:

Text Markup
-----------

In some situations the text generated by a tag pattern will be displayed in the
user interface ---
for example, the currently playing song information is an editable tag pattern,
as is the list of albums.
To style this text,
you can use the following markup in combination with the tag patterns.

===================== ==========
Tag                   Result
===================== ==========
``[b]..[/b]``         Bold
``[big]..[/big]``     Bigger
``[i]..[/i]``         Italic
``[small]..[/small]`` Smaller
``[tt]..[/tt]``       Monospace
``[u]..[/u]``         Underline
``[span][/span]``     see below
===================== ==========

The ``span`` tag can define many more text attributes like size and color:
``[span size='small' color='blue']..[/span]``.
See the `Pango Markup Language`_ page for a complete list of available
attributes and values.

A complete example might look like this:

::

    [span weight='bold' size='large']<title>[/span]<~length| (<~length>)> : [b]<~rating>[/b]<version|
    [small][b]<version>[/b][/small]><~people|
    by <~people>><album|
    <album><tracknumber| : track <tracknumber>>>

Note also the literal newlines.

.. _`Pango Markup Language`: https://developer.gnome.org/pango/stable/PangoMarkupFormat.html
