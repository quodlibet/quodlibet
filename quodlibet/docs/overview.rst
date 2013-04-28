Overview
========

.. image:: images/front.png
    :align: right

**We believe that you know how to organize your music best.**

Quod Libet is a cross-platform music player that supports the features 
you'd expect from a modern media player, like Unicode support, multimedia 
keys, advanced tag editing and Replay Gain. Quod Libet distinguishes itself 
from other media players with its emphasis on simplicity, performance and 
:ref:`search <Searching>`.

Quod Libet uses `GTK+ <http://www.gtk.org/>`_, because GTK+ makes it easy 
to create clean, simple standards compliant user interfaces.  Quod Libet 
uses `Python <http://www.python.org/>`_, because Python makes it easy to 
create clean, simple functional and object-oriented software. Various other 
packages and libraries add to this - see :ref:`Requirements`.

Using the `Mutagen <http://code.google.com/p/mutagen/>`_ tagging library
keeps the rest of Quod Libet as simple as possible and ensures every
tag in your music library is available for your searching pleasure.


Features
--------

Audio Playback
^^^^^^^^^^^^^^

  * Multiple audio back-ends (GStreamer, xine-lib)
  * Replay Gain support
  * Auto-selects between 'track' and 'album' mode based on
    current view and play order
  * Applies clipping prevention whenever available
  * Configurable default (fallback) and pre-amp values to suit any audio setup
  * Multimedia key support
  * Real shuffle mode, that plays the whole playlist before repeating
  * Weighted (by rating) random playback
  * Proper 'Previous' support in shuffle mode
  * A play queue
  * Bookmarks within files (or playlists, with a plugin)


Editing Tags
^^^^^^^^^^^^

  * Full Unicode support
  * Make changes to many files at once
  * Make changes across all supported file formats
  * Tag files based on their filenames with configurable formats
  * Rename files based on their tags
  * No ugly ``%a``, ``%t`` patterns -
    more readable ``<artist>``, ``<title>`` instead
  * Fast track renumbering 
  * See full instructions at :ref:`EditingTags`


Audio Library
^^^^^^^^^^^^^

  * Watch directories and automatically add/remove new music
  * Hide songs on removable devices that may not always be there
  * Save song ratings and play counts
  * Lyrics downloading and saving 
  * Internet Radio ("Shoutcast") support
  * Audio Feeds ("Podcast") support


User Interface
^^^^^^^^^^^^^^

  * Simple user interface to Just Play Music if you want
  * Useful as a small window or maximized, no feeling cramped or wasted space
  * Album cover display
  * Full player control from a tray icon
  * Recognize and display many uncommon tags, as well as any others you want.
    Especially useful for classical music.


Library Browsing
^^^^^^^^^^^^^^^^

  * Simple or regular-expression based search
  * Constructed playlists
  * iTunes/Rhythmbox-like paned browser, but with any tags you want
    (Genre, Date, etc)
  * Album list with cover art
  * By directory, including songs not in your library 


Python-based plugins
^^^^^^^^^^^^^^^^^^^^

  * Automatic tagging via `MusicBrainz <http://musicbrainz.org/>`_ and CDDB
  * On-screen display popups
  * Last.fm/AudioScrobbler submission
  * Tag character encoding conversion
  * Intelligent title-casing of tags
  * Find (and examine / remove) near-duplicate songs across your
    entire collection
  * Audio fingerprinting of music
  * Control Logitech Squeezebox devices.
  * Scan and save Replay Gain values across multiple albums at once
    (using gstreamer)


File Format Support
^^^^^^^^^^^^^^^^^^^

    * MP3, Ogg Vorbis / Speex / Opus, FLAC, Musepack, MOD/XM/IT, Wavpack, 
      MPEG-4 AAC, WMA, MIDI, Monkey's Audio


UNIX-like integration
^^^^^^^^^^^^^^^^^^^^^

  * Player control, status information, and querying of library
    from the command line
  * Can used named pipes to control running instance.
  * Now-playing is available as a fixed file
