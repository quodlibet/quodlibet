Audio Backends
==============

Quod Libet currently supports GStreamer and Xine as an audio backend. The
default backend can be changed in ``~/.quodlibet/config`` by setting the
``backend`` option (``gstbe`` = GStreamer, ``xinebe`` = Xine, ``nullbe`` =
no backend). Make sure Quod Libet isn't running while you edit the file.

There is also an experimental `Mac OS X NSSound backend (macbe)
<http://code.google.com/p/quodlibet/issues/detail?id=509>`_ available in
the issue tracker.


GStreamer Backend
-----------------

Custom Pipelines
^^^^^^^^^^^^^^^^

It's possible to attach a custom GStreamer pipeline to the player backend
under *Music* → *Preferences* → *Playback* → *Output Pipeline*. The
pipeline syntax is equivalent to what is used in the *gst-launch* utility.
See ``man gst-launch`` for further information and examples.

In case the custom pipline doesn't contain an audio sink, Quod Libet
will add a default one for you.


Debugging Pipelines
^^^^^^^^^^^^^^^^^^^

In case you are interested in which GStreamer elements and audio formats
are used in the current pipeline, start Quod Libet in debug mode
(``quodlibet --debug``), go to *Music* → *Preferences* → *Playback* and
press the *Print Pipeline* button. It will print the whole pipeline used
for the current active song to *stdout*.

For debugging GStreamer related issues see the official GStreamer docs:
`Running and debugging GStreamer Applications
<http://gstreamer.freedesktop.org/data/doc/gstreamer/head/gstreamer/html/gst-
running.html>`__


Gapless Playback
^^^^^^^^^^^^^^^^

Gstreamer supports gapless playback for all common formats except MP3. See
the following bug report for more information:
https://bugzilla.gnome.org/show_bug.cgi?id=620323


Selecting an Output Device
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want QL to output to a different device you have to pass the device
option to the sink by setting a custom pipeline. In case of alsa you can get
a list of available devices by executing::

    python -c 'import gst; sink = gst.element_factory_make("alsasink");sink.probe_property_name("device"); print "\n".join(sink.probe_get_values_name("device"))'

which should give you something like::

    hw:0,0
    hw:0,1
    hw:2,0

and a pipeline using hw:2,0 looks like::

    alsasink device=hw:2,0


And similar for pulseaudio::

    python -c 'import gst; sink = gst.element_factory_make("pulsesink");sink.probe_property_name("device"); print "\n".join(sink.probe_get_values_name("device"))'


which outputs something like::

    alsa_output.pci-0000_00_1b.0.analog-stereo

and the pipeline should look like::

    pulsesink device=alsa_output.pci-0000_00_1b.0.analog-stereo


Xine Backend
------------

The Xine backend needs either xine-lib 1.1.x or xine-lib 1.2.x. Since most
distributions make QL only depend on GStreamer, you might have to install
xine-lib manually (*libxine1*, *lixine2* in Debian/Ubuntu).

To enable the backend, set the ``backend`` option in the ``config`` file to
``"xinebe"`` while QL isn't running.
