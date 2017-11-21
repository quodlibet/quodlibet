Album Browsers
==============

Identifying albums
------------------

Throughout Quod Libet, albums are grouped by examining the ``album`` tag on 
individual songs. To support distinct albums with the same name, groups of 
songs with the same 'album' tag are further inspected for the presence of 
one of three tags: ``album_grouping_key``, ``labelid``, and 
``musicbrainz_albumid``, in that order. If a song has any of these, it will 
be used to identify the album it belongs to along with the ``album`` tag. 

In short, if more than one album in your library has the same name, use one 
of the secondary tags to separate them. The MusicBrainz plugin will add 
``musicbrainz_albumid`` tags automatically, and may be the easiest solution 
for adding identically-named albums to your library.

Album List Browser
------------------

.. image:: ../../images/album.png
    :scale: 45%
    :align: left

The *Album List* browser makes it easy to treat your music collection as a 
set of albums, presented on the left, rather than as a set of songs, via 
album-centric enhancements to viewing, sorting, and searching.

You can (configurably) display the album art next to each album to allow 
faster identification of your albums (plus *it's just prettier*...).

Extra features related to searching, sorting and presenting albums are 
detailed below.


Cover Grid Browser
------------------

.. image:: ../../images/covergrid-plus-waveform-2017-08.png
    :scale: 30%
    :align: right

The cover grid is another album-like browser that places more emphasis on the
album art.

It has a search similar to album list (see the section below),
and configuration of its own (including a flexible per-album display area).



Searching
---------

After creating the list of albums using the heuristic described above, the 
Album List browser then computes information across all the songs in an 
album. While the browser uses sensible defaults as to exactly how this 
information is compiled, it also exposes the choice while searching. This 
is most useful with numeric searches. For example, to find the albums with 
an *average* rating of 0.6 or greater, you can search for

  ``#(rating >= .6)``

This works because the Album List averages the values of numeric tags by 
default. To find the albums with *any song* with a rating of .6 or greater, 
though, you have to add something to your search:

  ``#(rating:max >= .6)``

These tag suffixes work for any numeric search.  The options are ``min``, 
``max``, ``sum``, and ``avg`` (the default).

For string tags, the values which get searched are created by joining all 
of the underlying songs' values together. The albums in an Album List also 
have a few tags which are computed in a particular manner. A few of the 
interesting ones:

  * ``~#length`` is computed as the sum of the length of the underlying
    songs.
  * ``~#tracks`` and ``~#discs`` are the total number of songs and discs in
    an album.

Also useful, though not strictly album-only:

  * ``~#filesize`` is the size on disk of a file in bytes
    (but can be formatted for humans)
  * ``~people`` is computed from all underlying tracks, with
    duplicate entries removed.
