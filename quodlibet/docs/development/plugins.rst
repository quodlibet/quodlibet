.. _PluginDev:

Plugin Development
==================

A Quod Libet / Ex Falso Plugin is a simple python module that contains 
sub-classes of special plugin classes and is placed anywhere in 
``~/.quodlibet/plugins`` so it can be found by QL. These classes can 
provide special methods that get used by QL or can take action on certain 
events.

At the moment the following plugin classes exist:

**Event plugins:**

  * Are instantiated as long as they are enabled or QL is running. They get notified when songs start, get added etc.
  * Example: Last.fm scrobbler that watches what you play and sends the information to last.fm.

**Tag Editing plugins:**

  * Can extend many parts of the tag editor.
  * Example: Title case your tags.

**GStreamer plugins:**

  * Can inject elements into the GStreamer pipeline and configure them on the fly.
  * Example: Tempo adjustment to play music/audio books faster.

**Play order plugins:**

  * Can decide which song to play next or what happens if you select one. 
  * Example: Follow cursor, which plays the selected song next.

**Song menu plugins:**

  * Can be accessed through the play list context menu and get passed all selected songs.
  * Example: Album art search, to search album art for all selected songs.

.. note::

    The best way to find out what is possible is to read the documentation of 
    the `plugin base classes 
    <http://code.google.com/p/quodlibet/source/browse/#hg%2Fquodlibet%2Fquodlibet
    %2Fplugins>`_ .


Let's make a new plugin!
------------------------

First we start with a minimal event plugin::

    from quodlibet.plugins.events import EventPlugin

    class MyPlugin(EventPlugin):
        PLUGIN_ID = "myplugin"
        PLUGIN_NAME = _("My Plugin")

..

 * PLUGIN_ID should be something unique so QL can remember the plugin
   even if it changes its name or class.
 * PLUGIN_NAME is the display name of the plugin (in the plugin
   manager, context menus etc.)

After you place it in ``~/.quodlibet/plugins`` it will show up ind the 
plugin manager and you can enable and disable it.

----

Now we want to display when the plugin gets enabled and disabled by providing
enabled and disabled methods.

::

    class MyPlugin(EventPlugin):
        PLUGIN_ID = "myplugin"
        PLUGIN_NAME = _("My Plugin")
        
        def enabled(self):
            print "enabled!"

        def disabled(self):
            print "disabled!"


As you can see, these get called when you enabled/disable the plugin in the
plugin manager or when you launch or shut down the application. They should
be used to connect to external things, or initialisation. Make sure
you get rid of all references in disabled so the plugin can be deleted properly.

----

Now we want to do something useful and take some action when a song 
starts playing.

::

    class MyPlugin(EventPlugin):
        PLUGIN_ID = "myplugin"
        PLUGIN_NAME = _("My Plugin")
        
        def plugin_on_song_started(self, song):
            if song is not None:
                print song("title")

``plugin_on_song_started`` gets called whenever a new song starts. When no 
song is active (the playlist has reached its end) the song will be `None`.

The plugin now prints the song title on each song change.

----

Instead of printing the song title we now want the song title to be spoken 
on every new song.

::

    import gobject
    import subprocess

    from quodlibet import app
    from quodlibet.plugins.events import EventPlugin

    class MyPlugin(EventPlugin):
        PLUGIN_ID = "myplugin"
        PLUGIN_NAME = _("My Plugin")
        
        def plugin_on_song_started(self, song):
            if song is None:
                return

            old_volume = app.player.volume
            app.player.volume /= 3
            def done(pid, cond):
                app.player.volume = old_volume

            pid = gobject.spawn_async(
                ["/usr/bin/espeak", song("~artist~title").encode("utf-8")],
                flags = gobject.SPAWN_DO_NOT_REAP_CHILD)[0]
            gobject.child_watch_add(pid, done)


Whenever a new song starts we save the current volume, execute ``espeak``
and pass the artist and title of the new song to it and let it speak the text.

Once the espeak process terminates our 'done' callback gets called and
we restore the volume.

.. note:: 

    The easies way to get started is to look for `existing plugins 
    <http://code.google.com/p/quodlibet/source/browse/#hg%2Fplugins>`_ that do 
    something similar to what you want.
