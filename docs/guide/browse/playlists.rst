.. _Playlists:

Playlists
=========

The Playlist Browser
--------------------

.. image:: ../images/playlist-browser.png
    :scale: 50%
    :align: right

Choose the *Playlists* browser by clicking on *View* -> *Playlists*. The 
usage is fairly simple - a list of songs in the right pane, and a list of 
playlists (with summary information) in the right.

Any file in your library can belong to any playlist or many playlists -
it's up to you how you want to organize them...

Playlist store
--------------
Playlists are stored as files on disk, typically under
``~/.quodlibet/playlists``, depending on your home / XDG directories.

Format
~~~~~~
:new: Playlists are now stored in `XSPF format <http://xspf.org/>`_.
The names are partially URL-encoded - that is, they can and should be URL-unencoded,
but efforts are taken to make them human-friendly names where reasonable.

As before, these playlists are editable but it's recommended to leave them to Quod Libet.
It's good to back them up (``git`` etc works well here too).


Creating playlists
------------------

There are several ways to create playlists in Quod Libet. Choose whichever suits you best:

  * To create a blank playlist, select the Playlist Browser and click *New*.
  * To create a new playlist with songs in it, select the songs in any other
    browser, right click, and select *Add to Playlist* → *New Playlist*.
  * To add songs to an existing playlist, either use *Add to Playlist* in the
    right click menu, or drag them to the playlist name on the sidebar.
  * To import playlists from `pls` or `m3u` /` m3u8` files, use the *Import* button.
    In addition to creating the playlist, any files in it will be added to
    your library.

Context menu support
--------------------

The "songs menu", a context menu presented when you right-click on a song 
(or songs), has in-built support for playlists. Just right-click on a song, 
and select *Add to Playlist*. This is a convenient way of adding a song to 
a playlist from almost *any* browser, and even better, seeing *every* 
playlist that song features in (they will be ticked). 

Library Changes
---------------

The Playlists Browser, like many other browsers, listens to changes in your 
library. This means that any changes in tags will be reflected in the song 
list for each. Playlist entries are indexed by file path though, so *any 
changes of name or directory will remove a song from its playlists* (There 
are, however, discussions to changes this: Issue 708). Please be careful 
with mounted media (e.g. USB / network disks) as when the library is 
rescanned, these files not existing is taken as deletion, which will 
provoke a removal from their playlists. Please keep backups if playlists 
are important.

Drag and Drop
-------------

Quod Libet has extensive drag-and-drop support in the playlists browser. 
You can drag and drop songs from other browsers (eg the search browser) 
onto an existing playlist, or songs from one playlist to another. When you 
drop a song into the left-hand pane in the playlist browser, but not onto a 
playlist, a new playlist is created, named after that song.

Importing and Exporting Playlists
---------------------------------

As outlined above, you can import playlists from `pls` or `m3u`/`m3u8` files
using the _Import_ button. In addition to creating the playlist, any files in
it will be added to your library. You can also drag and drop an `m3u` playlist
file from an external browser onto the left-hand pane in the playlist 
browser to import a playlist.

To export playlists to `m3u`, you first need to install the Export playlist 
export plugin. Once installed, you can export playlists to M3U or PLS 
format by right clicking on the playlist, then *Plugins* -> *Export 
Playlist*.

Dynamic Playlists
-----------------

You may wonder whether Quod Libet doesn't have so-called "dynamic" or 
"smart" playlists as you may know them from other music players, that is, 
playlists that automatically update themselves for example to always 
contain all songs from a certain artist that you have in your library.

In fact, QL does have this functionality, but it is implemented via the 
search functionality and hence located in the search browser, not in the 
playlists browser.

Creating a dynamic playlist:

  * Go to the search browser, (either using *View* or *Music* ->
    *Browse Library*).
  * Enter what you want to search for
    (see :ref:`the section about searching<Searching>` for QL's powerful
    search options), for example `artist = radiohead`. Optionally, click
    on search to test your search and modify it until you're happy.
  * Click the arrow next to the search box on the right, to open the
    drop-down menu. You will see a history of some recent searches (if
    you have searched before), followed by *Edit saved values...* ."
    Clicking on this, you will be presented with a dialogue box. The *Value*
    field has been pre-filled with your current search. If you wish,
    enter a name in the *Name* field (if you leave it blank, QL will
    name it for you). Click *Add*.

You have now created a dynamic playlist, via a saved search. To play, just 
go to the search browser, click on the arrow to the right of the field and 
select your saved search from the list. 

If you want to create several of such saved searches at once, you may find 
it more convenient to edit a text file instead of clicking through the GUI. 
To do so, you can :ref:`edit the configuration text file <ConfigFiles>` 
``~/.quodlibet/lists/queries.saved``.
