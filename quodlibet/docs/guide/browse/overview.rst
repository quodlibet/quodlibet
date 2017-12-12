Overview
========

Quod Libet has different ways to browse your library, called *Browsers*, 
which are selectable from the *View* menu. There is always one (the *primary*)
browser active.


Secondary Browsers
------------------

.. figure:: ../../images/queue_2browsers.png
    :align: right
    :scale: 30%

    Multiple Browsers - Search & secondary Album List

You can also browse your library in a separate window (without disturbing 
your current playlist) by selecting one of the options from *Browse* →
*Open Browser*. You can have multiple of these open at once, and they
will all react to changes to your library underneath.


The Song List
-------------

The *Song List*, as the name implies, presents a list of all the songs that 
the current browser has found, or filtered for you. The columns are 
configurable, and can generally be any tag, or even combinations of tags
from your library.
For more information on tags, see :ref:`AudioTags`.

Sorting:

  * List columns sorted by "disc" and "track" are actually sorted by "album"
  * All songs are sorted by the column header tag and with a special sort key.
    If there is something wrong with the sort order check the tags used in
    the sort key: *"albumsort or album, album_grouping_key or labelid or
    musicbrainz_albumid, ~#disc, ~#track, artistsort or artist,
    musicbrainz_artistid, title, ~filename"*
    (see :ref:`AudioTags`)


Filters
-------

Filters allow you to remove all but a subset of songs that from a browser's
 song list, typically based on a tag.

Different browsers implement these accordingly; in the Search browser,
these become searches
e.g. filtering by Artist might produce a search ``artist='Beethoven'c``

Some filters are not available on all browsers. For example, the Search
Bar can filter by anything, but there's no way to get a "top 40" in the
Album List.

Note also that when using the song context menu (a.k.a. "songsmenu"), QL
notices which *column* the mouse is in when you right-click on a song selection,
and will offer this column as a quick filter too, if possible.
