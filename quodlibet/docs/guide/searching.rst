Searching Your Library
======================

Pretty much every view in Quod Libet contains a search entry where you can 
enter search terms and save them. Quod Libet will search in artist, album, 
title, version, and any other visible columns for what you enter.

If that's enough for you, you can stop reading now. But what if you want
something more powerful?


Combining Searches and Negation
-------------------------------

You can combine search terms using ``&`` ("and") and ``|`` ("or"):

If you want to listen to Electronic music but no Ambient:

::

    &(electro, !ambient)

Or you want to get all songs by `Neutral Milk Hotel 
<http://en.wikipedia.org/wiki/Neutral_Milk_Hotel>`_ including the solo 
performances of `Jeff Mangum <http://en.wikipedia.org/wiki/Jeff_Mangum>`_:

::

    |(mangum, neutral milk)

You can get all songs that don't match the search term using ``!``::

    !electro

Lets say you want to listen to you whole library but are not in the mood 
for classical music or songs by `The Smiths 
<http://en.wikipedia.org/wiki/The_Smiths>`_::

    !|(classical, smiths)

While these searches are easy to type in, they depend on the visible colums
and the active browser, also the last one might exclude some songs wich
happen to contain "smiths" in their album title.


Searching a Specific Tag
------------------------

To search a specific tag, use a search like::

    artist = delerium
    album = bargainville

The search terms can't use quotes (``"``), slashes (``/``), hashes (``#``), 
pipes (``|``), ampersands (``&``), or bangs (``!``); these characters have 
special meanings for advanced searches.

If you want an exact match, use quotes::

    artist = "a girl called eddy"

If you need to put a ``"`` inside the quotes, you can put a ``\`` before it::

    version = "12\" mix"

..

    ''That's great, until I want to hear all my songs by
    `BoA <http://www.avexnet.or.jp/boa/>`_, and not the ones by
    `Boa <http://www.boaweb.co.uk/>`_. ``artist = "boa"`` gives me both!''

You can put a ``c`` after the last " to make the search case-sensitive::

    artist = "BoA"c
    artist = "Boa"c

You can also search :ref:`internal tags <InternalTags>`, e.g.

 * ``~format = Ogg Vorbis``
 * ``~dirname=Greatest Hits`` - search for all songs in Greatest Hits folders.

It's also possible to search in multiple tags at once:

 * `*artist, performer = "Boa"c`*


Combining Searches
------------------

 ''That's cool, but I want something cooler.''

Like before you can combine searches using ``&`` ("and") and ``|`` ("or"); 
either grouping entire searches, or just the tag values. Although the 
examples below use simple keywords, you can also use exact matches or 
regular expressions.

::

    artist = |(Townshend, Who)
    &(artist = Lindsay Smith, album = Vat)

The first one will find anything by `The Who <http://www.thewho.net/>`_ or 
guitarist `Pete Townshend <http://www.petetownshend.co.uk/>`_'s later work. 
The second one will only give you the songs that match both, so you'll find 
songs `Lindsay Smith <http://www.lindsay-smith.com/>`_'s `Tales From The 
Fruitbat Vat <http://www.cdbaby.com/cd/lindsaysmith>`_, but not her other 
albums.

You can also pick out all the songs that ''don't'' match the terms you give,
using ``!``.

::

    genre = !Audiobook

is probably a good idea when playing your whole library on shuffle.


Numeric Searches
----------------

    ''That's pretty cool, but ``year = |("2001", "2002", "2003", "2004", 
    "2005", "2006")`` is pretty unwieldy. And what about everything before 
    2001?''

Using ``#``, you can search your library for numeric values. Quod Libet 
keeps some internal numeric values - ``track``, ``disc``, ``rating``, 
``length``, ``playcount``, ``skipcount``, ``added`` (time added to the 
library), ``mtime`` (time last modified), ``lastplayed``, and 
``laststarted``.

 * ``#(skipcount > 100)`` could find really unpopular songs, or
 * ``#(track > 50)`` to figure out who makes really insane albums

Times like `added` are stored in seconds, which is pretty cumbersome to search
on. Instead, you can search with semi-English, like

 * ``#(added < 1 day)``

to find songs added in the last day (if you think that that's backwards, 
mentally add 'ago' when you read it). Quod Libet knows about seconds, 
minutes, hours, days, months (30 days), and years (365 days), kB 
(Kilobyte), MB (Megabyte), GB (Gigabyte). You can also use ''HH:MM'' 
notation, like

 * ``#(2:00 < length < 3:00)``

to find songs between two and three minutes.

Besides the values QL provides, any tag value that's a number in your files 
can be searched like this. So the solution to the original problem is

 * ``#(year > 2000)`` and
 * ``#(year <= 2000)``

Of course, you can combine these with other kinds of searches.

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


Real Ultimate Power: Regular Expressions
----------------------------------------

Quod Libet also supports searching your library using ''regular 
expressions'', a common way of finding text for Unix applications. Regular 
expressions look like regular searches, except they use / instead of ", and 
some punctuation has special meaning. For more information about regular 
expressions, there are many good tutorials on the web, such as `Kars 
Meyboom's <http://analyser.oli.tudelft.nl/regex/index.html.en>`_.

Some examples:

 * ``artist = !/\sRice/``

or using the default tags

 * ``/^portis/``

like with exact matches append a `c` to make the search case-sensitive

 * ``/Boa/c``

Now you can search anything!
