Overview
========

Quod Libet has different ways to browse your library, called *Browsers*, 
which are selectable from the *View* menu. There is always one (primary) 
browser active.

Depending on which browser you're using, different options will be 
available in the *Filters* menu and context menus. For example, the Search 
Bar can filter by anything, but there's no way to get a "top 40" in the 
Album List.


Secondary Browsers
------------------

.. figure:: http://wiki.quodlibet.googlecode.com/hg/images/queue_2browsers.png
    :align: right
    :width: 400px
    :target: http://wiki.quodlibet.googlecode.com/hg/images/queue_2browsers.png

    Multiple Browsers - Search & secondary Album List

You can also browse your library in a separate window (without disturbing 
your current playlist) by selecting one of the options from *Music* → 
*Browse Library*. You can have multiple of these open at once, and they 
will all react to changes to your library underneath.


No Browser
----------

If you select *Disable Browser*, whatever browser you were using just 
disappears. You can still browse your library with the *Filters* menu, but 
you can't search manually.


The Song List
-------------

The *Song List*, as the name implies, presents a list of all the songs that 
the current browser has found, or filtered for you. The columns are 
configurable, and can be any tag, or even combinations of tags from your 
library. For more information on tags, see [AudioTags An Introduction to 
Tags].

Sorting:

  * List columns sorted by "disc" and "track" are actually sorted by "album"
  * All songs are sorted by the column header tag and with a special sort key.
    If there is something wrong with the sort order check the tags used in
    the sort key: *"albumsort or album, album_grouping_key or labelid or
    musicbrainz_albumid, ~#disc, ~#track, artistsort or artist,
    musicbrainz_artistid, title, ~filename"*
    (see [AudioTags An Introduction to Tags])

