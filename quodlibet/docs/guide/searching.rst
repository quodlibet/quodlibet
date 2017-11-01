.. _Searching:

Searching Your Library
======================

Pretty much every view in Quod Libet contains a search entry where you can
enter search terms and save them. Quod Libet will search in artist, album,
title, version, and any other visible columns for what you enter.

If that's enough for you, you can stop reading now. But what if you want
something more powerful?


Combining Searches and Negation
-------------------------------

You can combine search terms using ``&`` ("and") and ``|`` ("or").

If you want to listen to Electronic music but no Ambient::

    &(electro, !ambient)

Or you want to get all songs by `Neutral Milk Hotel
<https://en.wikipedia.org/wiki/Neutral_Milk_Hotel>`_ including the solo
performances of `Jeff Mangum <https://en.wikipedia.org/wiki/Jeff_Mangum>`_::

    |(mangum, neutral milk)

You can get all songs that don't match the search term using ``!``::

    !electro

Lets say you want to listen to you whole library but are not in the mood
for classical music or songs by `The Smiths
<https://en.wikipedia.org/wiki/The_Smiths>`_::

    !|(classical, smiths)

While these searches are easy to type in, they depend on the visible columns
and the active browser, also the last one might exclude some songs which
happen to contain "smiths" in their album title
- see below for how to perform more targeted searching.


Searching a Specific Tag
------------------------

To search a specific tag, use a search like::

    artist = delerium
    album = bargainville

The search terms can't use quotes (``"``), slashes (``/``), hashes (``#``),
pipes (``|``), ampersands (``&``), or bangs (``!``); these characters have
special meanings for advanced searches.

In QL 3.9 onwards, you can also use `!=` to search for things not equal::

    artist != delerium
    genre != /.+ Jazz/


You can also search :ref:`internal tags <InternalTags>`, e.g.

 * ``~format = Ogg Vorbis``
 * ``~dirname=Greatest Hits`` - search for all songs in Greatest Hits folders.

It's also possible to search in multiple tags at once:

 * ``artist, performer = "Boa"c``


Exact Matching
--------------

If you want an exact match, use quotes::

    artist = "a girl called eddy"

If you need to put a ``"`` inside the quotes, you can put a ``\`` before it::

    version = "12\" mix"

You can put a ``c`` after the last " to make the search case-sensitive::

    artist = "BoA"c
    artist = "Boa"c
    artist != "Boa"c

Combining Tag Searches
----------------------

As with free-text searches, you can combine searches using ``&`` ("and") and
``|``  ("or"); either grouping entire searches, or just the tag values.
Although the examples below use simple keywords, you can also use exact
matches or regular expressions::

    artist = |(Townshend, Who)
    &(artist = Lindsay Smith, album = Vat)

The first finds anything by `The Who <https://en.wikipedia.org/wiki/The_Who>`_
or guitarist `Pete Townshend <https://en.wikipedia.org/wiki/Pete_Townshend>`_
. The second gives the songs that match both, so you'll find songs `Lindsay
Smith <http://www.lindsay-smith.com/>`_'s `Tales From The Fruitbat Vat
<http://www.cdbaby.com/cd/lindsaysmith>`_, but not her other albums.

You can also pick out all the songs that *don't* match the terms you give,
using ``!``::

    genre = !Audiobook

is probably a good idea when playing your whole library on shuffle.
Note again that in QL 3.9 onwards you can use the alternative syntax of::

    genre != Audiobook


More complex searches are of course possible. For example, to select all
Disco and Jazz related (_containing_, technically) genres,
but avoiding Acid Jazz, you could use:

    genre = &(|(Disco, Jazz), !Acid Jazz)


Numeric Searches
----------------

Using ``#``, you can search your library using numeric values. Quod Libet 
keeps some internal numeric values including ``track``, ``disc``, 
``rating``, ``length`` etc. See :ref:`numeric-tags` for full details. You 
can also search any other tag as long as the values have a number format 
like ``1234`` or ``-42.42``, for example ``year`` or ``bpm``.

For comparisons you can then use typical binary operators like ``=``, 
``<``, ``>``, ``<=``, ``>=`` and ``!=``.

 * ``#(skipcount > 100)`` could find really unpopular songs, or
 * ``#(track > 50)`` to figure out who makes really insane albums, or
 * ``#(bpm > 160)`` to find really fast songs

You can also use chained comparisons:
 * ``#(10 <= track < 100)`` to find all two-digit tracks.

Times like ``added`` are stored in seconds, which is pretty cumbersome to
search on. Instead, you can search with semi-English,
like:

 * ``#(added < 1 day)`` for very recently added tracks

to find songs added in the last day (if you think that that's backwards,
mentally add 'ago' when you read it). Quod Libet knows about seconds,
minutes, hours, days, months (30 days), and years (365 days), kB
(Kilobyte), MB (Megabyte), GB (Gigabyte). You can also use ''HH:MM''
notation, like:

 * ``#(2:00 < length < 3:00)`` for songs between two and three minutes long.

Of course, you can combine numeric with other kinds of searches.

 * ``&(genre = classical, #(lastplayed > 3 days))``
 * ``&(artist = "Rush", #(year <= 1996))``


Playlists
---------

You can use the ``~playlists`` internal tag to search by playlists. It is
populated with a list of all the playlists that song appears in. This is
surprisingly powerful if you're a playlist user.

 * ``~playlists=chilled`` will return all songs included in any playlist
   with "chilled" in its name.
 * ``~playlists=|("Chilled", "Jazzy")`` for all songs in either (or both)
   of those playlists.
 * ``&(#(rating>=0.75), ~playlists="")`` will return all high-rated songs
   *not* in any playlist


Regular Expressions
-------------------

Quod Libet also supports searching your library using ''regular
expressions'', a common way of finding text for Unix applications. Regular
expressions look like regular searches, except they use / instead of ", and
some punctuation has special meaning. There are many good tutorials on the
web, and useful online regex testers (such as `Regex Pal <http://www.regexpal
.com/>`_)

Some examples:

 * ``artist = !/\sRice/`` (or in 3.9+: ``artist != /\sRice/``)

or using the default tags

 * ``/^portis/``

like with exact matches append a `c` to make the search case-sensitive

 * ``/Boa/c``


Ignore Accents and Umlauts
--------------------------

Appending a ``d`` after searches makes it's characters match variants with
accents, umlauts etc.

Both ``/Sigur Ros/d`` and ``"Sigur Ros"d`` will match songs with the artist
name ``"Sigur Rós"``.


Now you can search anything!

Pluggable query expressions
---------------------------

More recent versions of Quod Libet allow queries to include pluggable expressions.
This uses the format ``@(plugin: body)`` where plugin is the ID of the query
plugin (e.g. ``saved``, ``python``) - see ``quodlibet/ext/query/*``.

From QL 3.10 onwards, the Python query plugin allows some use of external modules,
notably `time` and `random`, as well as a few useful variables.

For example, here is a way of simulating an album Spotlight in an album browser:

``@(python: Random((int(_ts / 60), a)).random() < 0.01)``

Here ``_ts`` is a current timestamp, and ``a`` is the album data.
So this generates a random number seeded on the current minute and the album key,
so we randomly select 1% of our albums to look at.

Reusing queries
---------------

Complex queries can be split into simpler ones.  Also, a query can be reused 
in other ones.  This way it is easier to change and administer your searches.

In order to do so, the ``Include Saved Search`` query plugin (see above) must be activated.
If you create a saved search named ``Unrated`` you can search for unrated songs from the Beatles
like this:

``&(@(saved: Unrated), Beatles)``

For creating saved searches, use the "Edit saved searches..." item in the drop-down 
at the right of the query text box.
