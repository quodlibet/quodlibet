Frequently Asked Questions
==========================

Any plans to use Python 3?
--------------------------

Not immediately, though it's now (May 2015)
`on the development radar <https://github.com/quodlibet/quodlibet/issues/1580>`_.
First, all dependencies (like mutagen) would need to be ported, though this is
largely done now.

That said, at the moment Python 2 does its job well.


I'm using PyCharm and it can't resolve certain functions like ``print_d``. What should I do?
--------------------------------------------------------------------------------------------

QL adds some commonly used functions to `__builtin__` which PyCharm can't
resolve. You can remove the resulting warnings by adding the function names
to the `Ignore references` list under `File > Settings > Project Settings >
Inspections > Python > Unresolved references`.

Add the following names to the list:

* `_`
* `Q_`
* `N_`
* `ngettext`
* `print_`
* `print_d`
* `print_w`
* `print_e`


What format is the song database in?
------------------------------------

It's a pickled list of AudioFile instances. It's easy to edit, if you know a little Python; here's an example session from the Python interactive interpreter which can get you started.

::

    Python 2.6.2 (r262:71600, Jun  4 2009, 15:54:27) 
    [GCC 4.3.2] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import quodlibet
    >>> import cPickle
    >>> with open(".quodlibet/songs", 'r') as songsfile:
    ...     songs = cPickle.load(songsfile)
    ... 
    >>> for k, v in songs[0].items():
    ...     print u'%-26s= %s' % (k, v)
    ... 
    date                      = 2003
    musicbrainz_albumartistid = 2624e8b9-3f77-453d-85e8-6a8c9e5b9d65
    tracknumber               = 1/11
    ~mountpoint               = /opt/media
    musicbrainz_trackid       = 4471cad1-c642-4171-8bca-a8ddf7ac805b
    ~#skipcount               = 0
    album                     = You Are Here
    replaygain_album_gain     = -0.519531 dB
    ~#bitrate                 = 192000
    title                     = Ventriloquist
    ~#length                  = 195
    ~#rating                  = 0.25
    ~filename                 = /opt/media/music/+_-/You Are Here/01 - Ventriloquist.mp3
    replaygain_album_peak     = 0.46560668967
    genre                     = Synthpop
    replaygain_track_peak     = 0.423797607619
    ~#laststarted             = 0
    ~#playcount               = 5
    artist                    = +/-
    musicbrainz_albumid       = d9816797-946e-4d4e-beea-7940fdef57cc
    ~#added                   = 1215625984
    replaygain_track_gain     = +1.960938 dB
    ~#lastplayed              = 1125835201
    ~#mtime                   = 1238344410.0
    >>>
    >>> inrainbows = filter(lambda s: s.get('album') == "In Rainbows", songs)
    >>> for s in inrainbows:
    ...     s['~#rating'] = 1.0
    ... 
    >>> with open('test', 'w') as newsongsfile:
    ...     cPickle.dump(songs, newsongsfile)
    ... 
    >>>


Why don't you use SQLite for the song database?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Although the song data Quod Libet stores would benefit from a relational 
database, it does not have a predefined schema, and opts to let users 
define their own storage keys. This means relational databases based on 
SQL, which require predefined schemata, cannot be used directly.

What about <my favourite NoSQL DB> then?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This gets asked fairly often. MongoDB, CouchDB etc are indeed a closer match to
the existing setup, but there is *significant* work porting an optimised native
pickle-based repository to any of these, and each comes with a compatibility
/ maintenance cost. This doesn't mean it won't happen some day, but there has
to be a genuine case for the benefits outweighing the migration cost.


Any environment variables I should know about?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

QUODLIBET_TEST_TRANS
    When set to a string will enclose all translatable strings with that
    string. This is useful for testing how the layout of the user interface
    behaves with longer text as can occur with translations and to see if all
    visible text is correctly marked as translatable.

    ::

        QUODLIBET_TEST_TRANS=XXX

QUODLIBET_DEBUG
    When in the environment gives the same result as if ``--debug`` was passed.

QUODLIBET_NO_TRANS
    When in the environment disables translations

QUODLIBET_BACKEND
    Can be set to the audio backend, overriding the value present in the main
    config file. Useful for quickly testing a different audio backend.

    ::

        QUODLIBET_BACKEND=xinebe ./quodlibet.py

QUODLIBET_USERDIR
    Can be set to a (potentially not existing) directory which will be used as
    the main config directory. Useful to test Quod Libet with a fresh config,
    test the initial user experience, or to try out things without them
    affecting your main library.

    ::

        QUODLIBET_USERDIR=foo ./quodlibet.py
