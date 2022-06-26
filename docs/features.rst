.. _Features:

Features
========

Audio Playback
^^^^^^^^^^^^^^

  * Multiple audio back-ends (GStreamer, xine-lib).
  * JACK output is also supported explicitly (via GStreamer)
  * Rich Replay Gain support. Auto-selects between 'track' and 'album'
    mode based on current view and play order
  * Applies clipping prevention whenever available
  * Configurable default (fallback) and pre-amp values to suit any audio setup
  * Multimedia key support
  * Real shuffle mode, that plays the whole playlist before repeating
  * Weighted (by rating) random playback
  * Proper 'Previous' support in shuffle mode
  * A configurable play queue


Editing Tags
^^^^^^^^^^^^

  * Full Unicode support
  * Make changes to many files at once
  * Make changes across all supported file formats
  * Tag files based on their filenames with configurable formats
  * Rename files based on their tags, with various filters for
    troublesome characters (especially on Windows)
  * No ugly ``%a``, ``%t`` patterns -
    more readable ``<artist>``, ``<title>`` instead
  * Fast track renumbering
  * Add / edit bookmarks within files
  * See full instructions at :ref:`EditingTags`


Audio Library
^^^^^^^^^^^^^

  * Hide songs on removable devices that may not always be there
  * Watch library for external changes, additions and deletions
  * Save song ratings and play counts
  * Internet Radio support
  * Audio Feeds ("Podcast") support
  * Deep playlist support with import / export (XSPF, M3U, PLS)
  * Soundcloud browsing and streaming, with login and native favorites support


User Interface
^^^^^^^^^^^^^^

  * Simple user interface to Just Play Music if you want
  * Themeable, modern, Gnome-friendly UI (dark and light modes supported)
  * Useful as a small window or maximized, no feeling cramped or wasted space
  * Optional high-resolution waveform seekbar (via WaveForm Plugin)
  * Paned View to group / funnel library data with arbitrary tags
    (e.g. Year -> Genre -> People -> Album)
  * Album cover display in variety of rich layouts
  * Full player control from a tray icon
  * Recognize and display many uncommon tags, as well as any others you want.
    Especially useful for classical music.
  * Rich CLI support (with ``quodlibet`` but also ``operon``)


Library Browsing
^^^^^^^^^^^^^^^^

  * Simple text-searches (unicode-aware)
  * Or... regular expression searches across tag values or free text
  * Or even... complex structured boolean logic and arbitrary Python code
  * Constructed playlists
  * iTunes/Rhythmbox-like paned browser, but with any tags you want
    (Genre, Date, etc)
  * Album list with cover art
  * By directory, including songs not in your library 


Python-based plugins
^^^^^^^^^^^^^^^^^^^^
Quod Libet has over 80 plugins contributed by devs and users, including:

  * Download high-quality cover art from pluggable sources
  * Automatic tagging via `MusicBrainz <http://musicbrainz.org/>`_ and CDDB
  * Configurable on-screen display notifications when songs change
  * Last.fm / AudioScrobbler submission
  * Plugins for web lyrics and synchronised (``.lrc`) lyrics viewing
  * A selection of audio-processing (pitch adjust, stereo downmix, EQ)
  * Custom Commands to run shell (think ``xargs`` for Quod Libet)
  * Find and remove duplicate / similar tracks across your entire library
  * Intelligent title-casing of tags
  * Find (and examine / remove) near-duplicate songs across your
    entire collection
  * Audio fingerprinting of music
  * Sync playlists to Sonos devices or Logitech Squeezebox devices.
  * Interface with dBus, MQTT, and other desktop apps too.
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
  * Rich DBus support (once enabled)
