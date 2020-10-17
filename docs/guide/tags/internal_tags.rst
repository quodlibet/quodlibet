.. _InternalTags:

Internal Tags
=============

Quod Libet stores a number of tags internally, that are either not stored 
in files themselves, or are derived from the values in the files.


String Tags
-----------

 * ``~basename``: The last component of the full path name
 * ``~dirname``: Everything but the last component of the file path name
 * ``~filename``: The full path name
 * ``~format``: The file format (e.g. "MPEG-4")
 * ``~codec``: The audio codec (e.g. "AAC LC")
 * ``~encoding``: Encoder name, version, settings used (e.g. "LAME 3.97.0, VBR")
 * ``~length``: The length of the file in H:MM:SS format
 * ``~mountpoint``: The component of the full path name that corresponds to the file's immediate parent mount
 * ``~performers``: A list of performers
 * ``~people``: A list of all people involved in the song
 * ``~rating``: A string representation of the song's rating (e.g. ★★★☆). Note that in most formats these are per email address.
 * ``~uri``: The full URI of the song
 * ``~year``: The release year, derived from the ``date`` tag
 * ``~originalyear``: The original year, derived from the ``originaldate`` tag
 * ``~playlists``: Comma-separated playlist names in which the song is included
 * ``~filesize``: Human formatted size (e.g. *4.5 MB*)


The ``~people`` Internal Tag
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The internal ``~people`` tag combines the following tags to one: 
``albumartist``, ``artist``, ``author``, ``composer``, ``~performers``, 
``originalartist``, ``lyricist``, ``arranger``, ``conductor`` in this exact 
order.

For sorting, this means that all album artists come first followed by
all artists and so on. For song collections / albums, the values of
each included tag are sorted by frequency.

Variants:
    ``~people:roles`` includes roles e.g. ``"The Parley of Instruments
    (Orchestra), David Thomas (Bass)"``. The roles are either derived from the
    source tag name (``composer=Joseph Haydn`` → ``Joseph Haydn
    (Composition)``) or from the performer role
    (``performer:composition=Joseph Haydn`` → ``Joseph Haydn (Composition)``).
    For the latter see the ``~performers`` tag.

    ``~people:real`` excludes *Various Artists*, commonly used as a
    placeholder for album artists on compilations, etc.


The ``~performers`` Internal Tag
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The internal ``~performers`` tag combines all the artists specified in the
performer tags to a single one.

Example: ``performer:vocals=Brandon Patton, performer:banjo=Béla Fleck``

``~performers`` will then display ``"Brandon Patton, Béla Fleck"``

Variants:
    ``~performer:roles`` includes the roles as well. For the above example
    it will display ``"Brandon Patton (Vocals), Béla Fleck (Banjo)"``


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
 * ``~#bitdepth``: The bitdepth of this song
 * ``~#bitrate``: The bitrate of the song, in kilo bits per second
 * ``~#disc``: The disc number of the song (the first half of the ``discnumber`` tag)
 * ``~#channels``: The channel count
 * ``~#discs``: The total number of discs in this song's collection
 * ``~#filesize``: The size in bytes of this song
 * ``~#lastplayed``: The time this song was last played through
 * ``~#laststarted``: The time this song was last started
 * ``~#length``: The length of the song, in seconds
 * ``~#mtime``: The time this file was last modified
 * ``~#playcount``: The total number of times you've played the song through
 * ``~#rating``: The rating of the song, as a number between 0 and 1.
 * ``~#samplerate``: The sample rate of this song
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

For all other numeric tags it is possible to define numeric functions by 
appending ``:numeric_func`` to the tag name (``~#playcount:avg`` for example). 
All internal numeric tags use a default function in case no function is 
given. For user defined numeric tags the average value is returned by 
default.

 * ``avg``: Returns the average value (``~#rating``)
 * ``sum``: Returns the summation of all values (``~#length``, ``~#playcount``, ``~#skipcount``, ``~#filesize``)
 * ``min``: Returns the smallest value (``~#year``)
 * ``max``: Returns the largest value (``~#added``, ``~#lastplayed``, ``~#laststarted``, ``~#mtime``)
 * ``bav``: Returns the `Bayesian average <https://en.wikipedia .org/wiki/Bayesian_average>`_ value (``~#rating``)
            Being most appropriate for ratings, the parameter is adjusted
            globally under the preferences for ratings.
