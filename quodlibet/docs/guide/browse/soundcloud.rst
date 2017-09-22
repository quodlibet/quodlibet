Soundcloud Browser
==================

*From v3.7*

Overview
--------

This browser lets you interact with `Soundcloud <https://soundcloud.com>`_
and play tracks from the millions on offer.
Where possible it aims to keep the look and feel as familiar and integrated to
the Quod Libet experience as possible.


.. image:: ../../images/soundcloud-browser-2017-08.png
    :scale: 50%
    :align: right


Connecting your account
-----------------------
If you have a Soundcloud account, you can also:

 * access your favorites
 * rate (like / unlike) songs.
 * list your own tracks (QL 3.10+)

To do so, click the Soundcloud connect button at the bottom right.

This will then take you to. If your operating system is configured to process
``quodlibet://`` URLs with Quod Libet (see `the instructions <https://quodlibet.github.io/callbacks/soundcloud.html?code=CODE_GOES_HERE>`_ given to you there) then
this process will happen automatically.
If not, you can enter the code manually using the same button.

If not, you can copy the code from the web page that appears and click the QL button again to enter it.

Once you are logged, in you can log out by clicking the same button again,
now a disconnect button (seen in the screenshot).


Features
--------

Higher quality streams
^^^^^^^^^^^^^^^^^^^^^^

The Soundcloud browser will use the download URL, where available, for the highest quality stream.
Note this may require that you are logged in, and is usually *not* available.

Support for Quod Libet queries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the more interesting features of the soundcloud browser is that it can
*translate* simpler queries in standard QL syntax to something that can work
across the web to a library that isn't yours.

Obviously, there are many limitations to this approach both conceptually and
due to its implementation, but nonetheless queries like ``&(#(length>300), title=dubstep)``
get (roughly) what you might expect.


Favorites
^^^^^^^^^

These are supported as ``~rating`` (see below), and unrating a track
will unfavorite it in Soundcloud, if you are logged in.


Tags
^^^^

Supported tags
 * ``artist``, ``genre``, and ``title`` translate as you might imagine
 * ``website`` translates to Soundcloud's current URL for that track
 * ``genre`` holds the genres (plural) tagged in Soundcloud (these are rarely useful but YMMV)
 * ``date`` is the *creation* date in Soundcloud
 * ``~#rating`` is translated to 0.0 (not a Soundcloud favourite) or 1.0 (a Soundcloud favourite)
 * ``~#bitrate`` is the highest bitrate available when playing the track (normally 128)
 * ``~comments`` translates to the track details in Soundcloud.
 * ``bpm`` is the Soundcloud BPM if provided.

New tags
 * ``~#favoritings_count`` and ``~#likes_count`` etc represent how often these tracks have been favorited / liked
   (note that there currently seem to be inconsistencies within Soundcloud itself as to how these are populated)
 * ``soundcloud_track_id`` is the Soundcloud ID for the track.
 * ``soundcloud_user_id`` is the Soundcloud ID for the user.
 * ``artwork_url`` is the (remote) image URL for the track artwork on Soundcloud.
   This works well with the corresponding ``Artwork URL Cover Source`` plugin.


Comments
^^^^^^^^
Comments in Soundcloud have been integrated to QL as read-only bookmarks, as
they are also time-specific text to do with a particular song. Unlike bookmarks
they have a lot more metadata (notably the user), so this is rendered as text.

To see them, access as you normally would bookmarks (e.g. view info, right-click the time widget or edit the bookmarks).
