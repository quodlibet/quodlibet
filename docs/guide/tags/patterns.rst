.. _TagPatterns:

Tag Patterns
============

Tag patterns allow more complex string representation of tags, with a
notion of if-null defaulting; whilst this sounds complex (and it can be!)
it's very useful where libraries have wildly varying tags.

Tag patterns can include strings (e.g. tag names) enclosed in angled
brackets like this

``<artist> - <title> (<album>)``

Which might produce:

``The Beatles - Drive My Car (Rubber Soul)``

Usage
-----

Tag patterns in QL can be used to change the information displayed in various
places, like the playing song area, columns in the song list and the album list
in the album browser.

They can be used to group songs in the paned and the album collection
browser in more complex ways.

And, of course, tag renaming based on tags uses tag patterns to create
the file names and folder structure.

Conditional Tags
----------------

A simple if-then-else concept can be used in tag patterns, testing if a tag
is non-empty. The syntax uses the pipe (``|``) character as a delimiter, in
either of these formats:

 * ``<tag-expression|non-empty-value>`` or
 * ``<tag-expression|non-empty-value|empty-value>``

So using the full (second) form, a Pattern of:

    ``<album|Has An Album|No Album>``

produces *Has An Album* for any song with at least one ``album`` tag value,
else *No Album*.

Note that these can be recursive, i.e. both `non-empty-value` and
`empty-value` are themselves tag patterns, which could contain a
conditional. A more useful example now:

    ``<albumartist|<albumartist>|<artist>>``

This will look for the ``albumartist`` tag and display that if available,
else use ``artist`` (nearly always available).


Examples:

  * ``<~year|<~year>. <album>|<album>>``: *2011. This is an album title*
  * ``<title>, by <albumartist|<albumartist>|<composer|<composer>|<artist>>>``:
    *Liebstraum no. 3, (by Franz Liszt)*


Conditional Tags With Comparisons
---------------------------------

In addition to checking if a tag value is empty, the "if" expression can also
contain a value comparison using the same syntax as the :ref:`search
<Searching>`:

    ``<sometag=test|the value was test|it was something different>``

or more complex ones (note the needed escaping):

    ``<artist=\|(Townshend, Who)|foo|bar>``


.. _TextMarkup:

Text Markup
-----------

In some situations the resulting text will be displayed in the user
interface like for example the album list or the area which displays
information about the currently playing song. To style the resulting text
you can use the following tags in combination with the tag patterns.

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
``[span size='small' color='blue']..[/span]``. See the `Pango Markup
Language`_ page for a complete list of available attributes and values.

A complete example might look like this:

::

    [span weight='bold' size='large']<title>[/span]<~length| (<~length>)> : [b]<~rating>[/b]<version|
    [small][b]<version>[/b][/small]><~people|
    by <~people>><album|
    <album><tracknumber| : track <tracknumber>>>

Note also the literal newlines.

.. _`Pango Markup Language`: https://developer.gnome.org/pango/stable/PangoMarkupFormat.html
