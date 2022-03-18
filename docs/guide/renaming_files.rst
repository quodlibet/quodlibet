.. _RenamingFiles:

Renaming files
==============

Basic Syntax
------------

Quod Libet allows you to rename files based on their :ref:`tags<AudioTags>`. In
some cases you may wish to alter the filename depending on whether some tags
are present or missing, in addition to their values.

Quod Libet allows _pattern_ syntax for this interaction, as well as plain text.
A pattern is some text surrounded by angle brackets, typically containing tags.

A common pattern might be::

    <tracknumber>. <title~version>


You can use a ``|`` to only insert text when a tag is present::

    <tracknumber|<tracknumber>. ><title~version>


You could also specify literal text to use if the tag is missing by adding
another `|`::

    <album|<album>|No Album> - <title>

A reasonable use of albumartist would be::

    <albumartist|<albumartist>|<artist|<artist>|No artist>>


..which uses the first of the following: Albumartist, Artist or "No artist".

You can also move (rename) files across your filesystem to another
directory by mixing path elements and ``<pattern>`` syntax::

    /home/*username*/Music/<artist>/<album>/...


Simple Renames
--------------

Like tagging by filename, renaming by tags uses tag names enclosed by
``<...>`` to substitute values. To rename songs as their artist followed
by their title, use ``<artist> - <title>`` (The file extension, .ogg, .mpc,
and so on, is automatically added). Other common patterns include

 * ``<tracknumber>. <title>``
 * ``<tracknumber>. <artist> - <title>``
 * ``~/music/<artist> - <album>/<tracknumber>. <title>``
 * ``~/music/<artist>/<album>/<tracknumber>. <title>``

You can also use tied tags to rename, e.g. ``<artist~title>``.


Creating Directories
--------------------

Note that if you use ``/`` (a directory separator) in your filename, you
''must'' start the pattern with a ``/`` (or a ``~/``, which expands to your
home directory). To see why, consider what would happen if you tried to
rename the same file twice with ``<artist>/<title>``. The first time it
would go under ``Artist/Title.ogg``, the second time,
``Artist/Artist/Title.ogg``. When you specify the full path, this can't
happen.

If you don't use a `/` in the pattern, the file gets put in the same directory.


Conditional Renaming
--------------------

Consider the ``<tracknumber>. <title>`` pattern.

When the file is missing a track number, you get a filename that starts
with ., which isn't good. So Quod Libet lets you use ''conditional
renaming'' to avoid that.

To use conditional text, after the tag name (but inside the ``<...>``) put
a ``|`` (a pipe). Then after the pipe, place all the text you want,
including other tag names inside ``<...>``. That text will only be added when
that tag isn't empty.

To avoid the original problem, only display the track number, period, and
space when the track number tag exists:

``<tracknumber|<tracknumber>. ><title>``.

Quod Libet also lets you change the text if a tag ''doesn't'' exist: Use a
second pipe. ``<tracknumber|<tracknumber>|00>. <title>`` will use the
track number at the start of the filename if it exists, or *00* if it
doesn't.


Conditional tagging example
---------------------------

Remember that the format for conditionals is
``<condition|<conditional tag>|<else tag>>``.
You can also embed conditions inside each other::

    /mnt/musik/<genre|<genre>/><artist|<artist>|Unknown>/<album|<album>/><tracknumber|<tracknumber> - ><title>

Let's dissect this:

 * ``/mnt/musik``: A music partition
 * ``<genre|<genre>/>``: If there is a "genre" value, put the song into that
   folder (creating the folder if necessary). If there is no tag genre,
   skip this level in the folder hierarchy (note that the trailing slash
   of ``<genre>/`` is inside the < > that delineate the conditional "block".
 * ``<artist>|<artist>|Unknown>/``: If there's a tag artist, put everything
   into that folder, else put into a folder called "Unknown". Note that the
   trailing slash is outside the < > that delineate the conditional block,
   since we always want that folder level.
 * ``<album|<album>/>``: Album folder as needed, else skip
 * ``<tracknumber|<tracknumber> - >``: Prepend tracknumber if it exists
 * ``<title>``: The track title (or empty string)


Nested Conditional example
--------------------------

For songs that don't have a genre tag, perhaps we'd want to use
the "language" tag and sort into that folder instead.
But many songs would have a genre *and* language tag values,
and those songs should only go into the genre folder (i.e. the language folder should be ignored)

QL can do this, by expanding the ``<genre>`` conditional
block from the expression above to ``<genre|<genre>/|<language|<language>/>>``.

The pipe after the second ``<genre>/`` introduces what should be
done if the first condition *isn't* met (i.e. no genre tag),
but here instead of putting plain text,
we introduce a second conditional block, ``<language|<language/>>``,
which adds a language tag folder, if the song has a tag "language".

The full expression now looks like this::

    /mnt/musik/<genre|<genre>/|<language|<language>/>><artist|<artist>|Unknown>/<album|<album>/><tracknumber|<tracknumber> - ><title>
