.. _Queue:

The Queue
=========

As described in the :ref:`Overview <Queue_Overview>`, the queue is used to
queue up songs to be played. In recent versions of Quod Libet, some new
features have been introduced to the queue, which is described below.

Ignore and Keep Songs
---------------------

With :ref:`release 4.2.0 <release-4.2.0>`, the queue was updated with
two new checkboxes: *Ignore* and *Keep Songs*.

When the *Keep Songs* checkbox is checked, songs won't be consumed from the
queue anymore when played. In this way, the queue can function as a kind of
temporary playlist.

With the *Ignore* checkbox checked, the queue won't have priority anymore.
This means that if a song is played from the song list, then songs from the
song list will continue playing even if the queue is not empty.

If both *Keep Songs* and *Ignore* are enabled, songs will be kept in the queue
while one at the same time is free to switch between playing songs from the
queue and the song list. If a song in the queue is selected, songs will keep
playing from the queue, while if a song in the song list is selected, then
songs from the song list will be played instead.

Disable and Mode Selection
--------------------------

With :ref:`release 4.3.0 <release-4.3.0>`, the *Ignore* and *Keep Songs*
checkboxes were replaced with a *queue disable* button and a *mode selection*
menu.

The queue can be disabled by clicking the padlock in the queue header. When
disabled, the queue cannot be played from - but you can still add songs to it.

The queue also has two different modes, that can be changed in the queue
preferences.

In the *Ephemeral* mode, the queue consumes songs as described in the
:ref:`Overview <Queue_Overview>`. This is the default behavior.

The other mode is the *Persistent* mode. In this mode, songs will be kept in
the queue even after being played. Furthermore, the queue won't have precedence
over the song list unless it is explicitly being played from by first
double-clicking on a song in it. This allows switching between the queue and
the song list without having to clear or disable the queue.
