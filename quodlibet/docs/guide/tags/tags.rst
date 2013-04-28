.. _AudioTags:

An Introduction to Tags
=======================

Overview
--------

Quod Libet supports free-form tags for most of the common audio formats. 
This means you can name your tags in any way you want, but using common tag 
names for common purposes is advised because it helps QL to write the tags 
in a way that other media players can understand them and also helps QL 
understand certain tag values and make use of them.

Quod Libet also supports expressions using "tied tags" in several contexts 
- see :ref:`TiedTags`


Sort Tags
---------

Tags ``artistsort``, ``albumsort``, ``albumartistsort``, ``performersort`` 
(including roles) will be used for sorting if they are present.

Lets say you have a song with an ``artist`` tag *The Beatles* and want it 
to be sorted as if it was named *Beatles, The*, you can add an 
``artistsort`` tag containing *Beatles, The*.

 * QL includes a basic plugin for creating such sort tags automatically.
 * The musicbrainz plugin includes an option to write sort tags if found.


Internal Tags
-------------

Internal tags are tags that start with a ``~`` like ``~people``, ``~length`` or 
``~year``. They are either not stored in files themselves, or are derived 
from the values in the files.

See :ref:`InternalTags` for a complete list.


Album Identification
--------------------

Quod Libet uses various tags to define what songs are in the same album. 

First of all ``album`` (or ``albumsort`` if present) will be used. In case two 
albums have the same name the following tags will be used (ascending 
priority): ``musicbrainz_albumid``, ``labelid``, ``album_grouping_key``.


Common scenarios
^^^^^^^^^^^^^^^^

    ''I have a two disc album and each disc is shown separately.''

Make sure the album tags (and ``albumsort`` if present) are the same 
(remove 'CD1/2' etc.). In case you used the musicbrainz plugin and each 
disc got a different ``musicbrainz_albumid``, add a nonempty ``labelid`` to 
all songs.

    ''Two albums have the same name and are merged.''

Add a nonempty labelid to one of the albums, or use the musicbrainz plugin 
to get a `musicbrainz_albumid` for at least one of them.

Common Questions
^^^^^^^^^^^^^^^^

    ''Why doesn't QL know that my albums are different ones by seeing that they don't have the same artist?''

There are many songs that have multiple artist, so this can't be decided on the basis of artist tags.

Replay Gain Tags
----------------

The following (fairly standard) tags are used for volume adjustment:

  * ``replaygain_track_gain``
  * ``replaygain_track_peak``
  * ``replaygain_album_gain``
  * ``replaygain_album_peak``

See ReplayGain section for further details.
