Interacting with Quod Libet
===========================


In Python
---------

Quod Libet supports :ref:`plugins written in Python <PluginDev>`. These
plugins can interact with songs more directly than the other interfaces,
changing or reading metadata using dict-like !AudioFile objects. The plugin
interface has not yet stabilized, although we do not expect it to change
drastically in the future.


The Unix Way
------------


Querying the player
^^^^^^^^^^^^^^^^^^^

Quod Libet writes information about the current song to
``~/.quodlibet/current``. The file is in key=value form. Key values are in
UTF-8, except for the ``~filename`` key, which has unknown encoding (but
will point to the file being played when interpreted as a sequence of bytes).

There is a ``--print-playing`` option which can use the same syntax as the
RenamingFiles interface to print information about the current song:
``quodlibet --print-playing '<artist> - <tracknumber~title>'``

``quodlibet --status`` provides player state information. The first word
will be either *playing*, *paused*, or *not-running*, followed by

 * the selected View,
 * volume setting (0.0 - 1.0)
 * Playback order & repeat settings
 * Current song progress (0.0 - 1.0)


Controlling the player
^^^^^^^^^^^^^^^^^^^^^^

Quod Libet understands a number of command line arguments to control a running player. For a full list, see the man page.

  * ``--next``, ``--previous``, ``--play``, and ``--pause`` should
    be self-explanatory; ``--play-pause`` toggles pause on and off.
  * ``--volume n`` sets the volume to anywhere between 0 (muted) or
    100 (full volume)
  * ``--seek <time>`` seeks within the current song.
  * ``--query <search text>`` searches in your library
    (if the current browser supports it).
  * ``--play-file <filename>`` plays that file or directory.

Quod Libet can also be controlled via a `FIFO 
<https://en.wikipedia.org/wiki/Named_pipe>`_ , ``~/.quodlibet/control``. To see 
how the command-line arguments map to FIFO commands, refer to 
``process_arguments()`` in 
https://github.com/quodlibet/quodlibet/blob/master/quodlibet/quodlibet/cli.py; 
as a simple example::

    # Sets volume to 50%
    echo volume 50 > ~/.quodlibet/control


Integration with third party tools
----------------------------------


Quod Libet in Conky
^^^^^^^^^^^^^^^^^^^

`Conky <https://github.com/brndnmtthws/conky>`_ is a lightweight system
monitor for X. It includes builtin objects for many popular music players, but
not quodlibet (yet).  That doesn't mean you can't use conky with quodlibet.
After installing conky, add the following to your```~/.conkyrc`` file::

    ${if_existing /<path to your home directory>/.quodlibet/current}
    ${exec quodlibet --print-playing "<artist>"}
    ${scroll 50 ${exec quodlibet --print-playing "<title~album>"}  }
    ${endif}


will display the current artist on one line with a scrolling display of
song title and album on the next line.  Conky will only attempt to display
this information if quodlibet is playing.


eSpeak: Speech Synthesizer
^^^^^^^^^^^^^^^^^^^^^^^^^^

You can use `eSpeak <http://espeak.sourceforge.net/>`_ to hear the current
playing title.

::

    quodlibet --print-playing "<~~people~title>" | espeak -s 120  -v $(quodlibet --print-playing "<language|<language>|en>")

In this example Quod Libet will use the value of the language tag to tell
eSpeak which language/voice to use for the specific title (Use ``espeak
--voices``` to get a list of all available languages).

You can also lower the volume during speaking::

    VOL=$(echo $(quodlibet --status | head -n1 | cut -d\  -f3)*100 | bc)
    quodlibet --volume=$(echo $VOL/3 | bc)
    quodlibet --print-playing "<~~people~title>" | espeak -s 120 -v $(quodlibet --print-playing "<language|<language>|en>")
    quodlibet --volume=$(echo $VOL/1 | bc)
