.. _PluginDev:

Plugin Development
==================

A Quod Libet / Ex Falso Plugin is a simple python module or package which 
contains sub-classes of special plugin classes. These classes can provide
special methods that get used by QL or can take action on certain events.

At the moment the following plugin classes exist:

Plugin Types
^^^^^^^^^^^^

Event Plugins
    * Are instantiated as long as they are enabled or QL is running. They get
      notified when songs start, get added etc.
    * Can also (3.10+) listen to selection changes in the main songlist.
    * Example: Last.fm scrobbler that watches what you play and sends the 
      information to last.fm.

Tag Editing Plugins
    * Can extend many parts of the tag editor.
    * Example: Title case your tags.

GStreamer Plugins
    * Can inject elements into the GStreamer pipeline and configure them on the 
      fly.
    * Example: Tempo adjustment to play music/audio books faster.

Play Order: Shuffle Plugins
    * Can decide which song to play next or what happens if you select one. 
    * Example: weighted shuffle, which prefers higher rated songs.

Play Order: Repeat Plugins:
    * How to repeat the songs
    * Example: repeat each song a set number of times

Songs Menu Plugins
    * Can be accessed through the play list context menu and get passed all 
      selected songs.
    * Example: Album art search, to search album art for all selected songs.

Playlist Plugins
    * Similar to Songs Menu plugin, and in fact derived on the same base class
    * Can be accessed through the playlist context menu in the
      :ref:`Playlist Browser <Playlists>`
    * Example: remove duplicate songs from a playlist.

Cover Source Plugins
    * Fetch covers from external or local resources


Location of Plugins
^^^^^^^^^^^^^^^^^^^

In older versions of Quod Libet, before they were moved into the main
``quodlibet`` module, plugins could be placed in ``~/.config/quodlibet/plugins``
on many Linux systems, and in ``~/.quodlibet/plugins`` on MacOS.

Whilst this still may work,
we recommend installing from source (see :ref:`DevEnv`) for all plugin development,
which will allow a fuller integration experience (debugging, etc).


Creating a new Plugin
^^^^^^^^^^^^^^^^^^^^^

#. Assuming you are running from source, put it in ``quodlibet/ext`` under a
   directory according to its plugin type (``events/`` etc).

#. Write the following into the file::

    from quodlibet.plugins.events import EventPlugin

    class MyPlugin(EventPlugin):
        PLUGIN_ID = "myplugin"
        PLUGIN_NAME = "My Plugin"

#. Restart Quod Libet, or click the ``Refresh`` button in the plugins window.

#. In Quod Libet open ``Music`` ⇒ ``Plugins`` and search the list for "My 
   Plugin"


Tips:
~~~~~

* The best way to find out what is possible is to read the documentation of 
  the `plugin base classes
  <https://github.com/quodlibet/quodlibet/tree/main/quodlibet/plugins>`_ .

* The easiest way to get started creating a new plugin is to look for `existing plugins
  <https://github.com/quodlibet/quodlibet/tree/main/quodlibet/ext>`_ that do
  something similar to what you want.
