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

produces *Has An album* for any song with at least one ``album`` tag value, 
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

In some situations (e.g. the Info area pattern), the result is actually GTK 
markup which uses its own HTML-like patterns with tags like 
``<big>...</big>`` and ``<b>...</b>``, so you have to escape these carefully:

::

    \<span weight='bold' size='large'\><title>\</span\><~length| (<~length>)> : \<b\><~rating>\</b\><version|
    \<small\>\<b\><version>\</b\>\</small\>><~people|
    by <~people>><album|
    <album><tracknumber| : track <tracknumber>>>

Note also the literal newlines.
