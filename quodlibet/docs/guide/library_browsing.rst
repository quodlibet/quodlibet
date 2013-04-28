Browsing Your Library
=====================

Overview
--------

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


No Browser
----------

If you select *Disable Browser*, whatever browser you were using just 
disappears. You can still browse your library with the *Filters* menu, but 
you can't search manually.


Search Library
--------------

The *Search Library* browser (which is the default one) lets you enter 
search terms and play all matching songs. It also supports 
[SearchingGuide#Complex_Searches complex searches]. Finally, it lets you 
limit the number of results; right-click on the text bar and select *Limit 
Results*. To display your whole library, don't enter any search terms.

The browser remembers the last eight searches you made automatically. If 
you want to save more, you can right-click on the text entry and select 
*Edit Saved Values...*, which will let you name and save searches 
permanently. Saved searches will appear above automatically remembered ones 
in the menu.


File System
-----------

This browser lets you view songs based on the folder they're in. It can 
play and edit songs inside and outside of your song library, and adds an 
item to the context menu to add the selected songs to your library. If you 
try to add songs to a playlist or the play queue that aren't in your 
library, they will be added automatically to it.

Note that since ratings and play counts are usually stored in the library 
rather than the song, play counts and ratings will only be saved if you add 
the song to your library!

Internet Radio
--------------

This browser lets you listen to Internet radio stations (a.k.a. streaming 
audio or Shoutcast). It supports MP3 and Ogg Vorbis streaming, and may 
support other formats (AAC or RealMedia) if you have appropriate GStreamer 
plugins installed. *New Station* accepts either a direct URL to a stream, 
or a URL to a ``.pls`` file with a list of streams.

Radio stations cannot be added to playlists or the play queue. You can edit 
the ``title``, ``artist``, and ``grouping`` tags, but the rest are filled 
in by the station when you listen.

If you don't know any good stations, the *Stations...* button will let you 
select some. If you do know some good stations, you can add them to the 
Stations list.

Audio Feeds
-----------

The *Audio Feeds* browser allows you to subscribe to syndicated feeds with 
attached audio files; these are often called "podcasts" or "blogcasts." 
Feeds are automatically checked for updates every two hours, and bolded if 
new entries are found.

You can right-click on a file in an audio feed, and select *Download*, to 
download it to your hard drive. Currently this has no effect on the feed 
itself (so changes to the local song will not be reflected in the feed list).
