.. _InternalTags:

Internal Tags
=============

Quod Libet stores a number of tags internally, that are either not stored 
in files themselves, or are derived from the values in the files.


String Tags
-----------

 * ``~basename``: The last component of the full path name
 * ``~errors``: A list of errors that have occured trying to play this file
 * ``~dirname``: Everything but the last component of the file path name
 * ``~filename``: The full path name
 * ``~format``: The file format
 * ``~length``: The length of the file in H:MM:SS format
 * ``~mountpoint``: The component of the full path name that corresponds to the file's immediate parent mount
 * ``~performers``: A list of performers, including :ref:`roles <PerformerRoles>`
 * ``~people``: A list of all people involved in the song
 * ``~rating``: A string representation of the song's rating (e.g. ★★★☆)
 * ``~uri``: The full URI of the song
 * ``~year``: The release year, derived from the ``date`` tag
 * ``~originalyear``: The original year, derived from the ``originaldate`` tag
 * ``~playlist``: Playlist names of which the song is part of
 * ``~filesize``: Human formatted size (e.g. *4.5 MB*)


The ``~people`` Internal Tag
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The internal ``~people`` tag combines the following tags to one: 
``albumartist``, ``artist``, ``author``, ``composer``, ``~performers``, 
``originalartist``, ``lyricist``, ``arranger``, ``conductor`` in this exact 
order.

In case of sorting this means that all album artists come first followed by 
all artists and so on.

In case of song collections and albums the values of each included tag are 
sorted by frequency.


Song Collections / Albums
^^^^^^^^^^^^^^^^^^^^^^^^^

 * ``~length``: The length of all songs in H:MM:SS format
 * ``~long-length``: The length of all songs in "H hours, M minutes, S seconds" format 
 * ``~tracks``: The real number of songs in the collection in "# track(s)" format
 * ``~discs``: The number of different discs in "# disc(s)" format
 * ``~rating``: The average rating in music notes
 * ``~filesize``: Total Human formatted size (e.g. *4.5 MB*)

All other tags return a list of values retrieved from all songs, without 
duplicates, sorted by their number of appearance.

.. _numeric-tags:

Numeric Tags
------------

 * ``~#added``: The date the song was added to the library
 * ``~#bitrate``: The bitrate of the song, in kilo bits per second
 * ``~#disc``: The disc number of the song (the first half of the ``discnumber`` tag)
 * ``~#discs``: The total number of discs in this song's collection
 * ``~#filesize``: The size in bytes of this song
 * ``~#lastplayed``: The time this song was last played through
 * ``~#laststarted``: The time this song was last started
 * ``~#length``: The length of the song, in seconds
 * ``~#mtime``: The time this file was last modified
 * ``~#playcount``: The total number of times you've played the song through
 * ``~#rating``: The rating of the song, as a number between 0 and 1.
 * ``~#skipcount``: The total number of times you've skipped through the song
 * ``~#track``: The track number of the song (the first half of the ``tracknumber`` tag)
 * ``~#tracks``: The total number of tracks in the album
 * ``~#year``: The release year, derived from the ``date`` tag
 * ``~#originalyear``: The original year, derived from the ``originaldate`` tag

Note some numeric tags have string tag equivalents (see above) for 
human-readable format. 


Song Collections / Albums
^^^^^^^^^^^^^^^^^^^^^^^^^

 * ``~#tracks``: The real number of songs in the collection
 * ``~#discs``: The number of different discs in the collection
 * ``~#filesize``: The total filesize of all songs in the collection

For all other numeric tags it is possible to define numeric functions by 
appending ``:numeric_func`` to the tag name (``~#playcount:avg`` for example). 
All internal numeric tags use a default function in case no function is 
given. For user defined numeric tags the average value is returned by 
default.

 * ``avg``: Returns the average value (``~#rating``)
 * ``sum``: Returns the summation of all values (``~#length``, ``~#playcount``, ``~#skipcount``)
 * ``min``: Returns the smallest value (``~#year``)
 * ``max``: Returns the largest value (``~#added``, ``~#lastplayed``, ``~#laststarted``, ``~#mtime``)
