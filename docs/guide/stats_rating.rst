.. _Stats:

Library Statistics
==================

Play Count
----------

The internal ``~#playcount`` tag is incremented when a song ends
or is forced to end by the user and the playback time has exceeded
a certain song duration (in %). This duration can be configured
in the preferences.

In case of radio streams, which don't have a defined duration, the play
count gets incremented whenever the stream is played.

Searching for all songs that where played more than 10 times:

.. code-block:: text

    #(playcount > 10)


Last Played Time
----------------

The ``~#lastplayed`` tag gets updated to the current time whenever
``~#playcount`` gets incremented. See details above.

Searching for all songs played less than 4 days ago:

.. code-block:: text

    #(lastplayed < 4 days)


Last Started Time
-----------------

The ``~#laststarted`` tag gets updated to the current time whenever the
song gets started.


Searching for all songs started less than 1 week ago:

.. code-block:: text

    #(laststarted < 1 week)


Skip Count
----------

The ``~#skipcount`` tag gets incremented whenever the song gets forced to end
by the user and the playing time was less than half of the song's duration.

Searching for songs that where skipped between 5 and 10 times:

.. code-block:: text

    #(5 <= skipcount <= 10)
