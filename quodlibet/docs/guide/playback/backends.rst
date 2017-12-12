Audio Backends
==============

Quod Libet currently supports GStreamer and Xine as an audio backend. The
default backend can be changed in ``~/.quodlibet/config`` by setting the
``backend`` option (``gstbe`` = GStreamer, ``xinebe`` = Xine, ``nullbe`` =
no backend). Make sure Quod Libet isn't running while you edit the file.


GStreamer Backend
-----------------

Custom Pipelines
^^^^^^^^^^^^^^^^

It's possible to attach a custom GStreamer pipeline to the player backend
under *File* → *Preferences* → *Playback* → *Output Pipeline*. The
pipeline syntax is equivalent to what is used in the *gst-launch* utility.
See ``man gst-launch`` for further information and examples.

In case the custom pipline doesn't contain an audio sink, Quod Libet
will add a default one for you.


Debugging Pipelines
^^^^^^^^^^^^^^^^^^^

In case you are interested in which GStreamer elements and audio formats
are used in the current pipeline, start Quod Libet in debug mode
(``quodlibet --debug``), go to *File* → *Preferences* → *Playback* and
press the *Print Pipeline* button. It will print the whole pipeline used
for the current active song to *stdout*.

For debugging GStreamer related issues see the official GStreamer docs:
`Running and debugging GStreamer Applications
<https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gstreamer/html/gst-
running.html>`__


Gapless Playback
^^^^^^^^^^^^^^^^

Gstreamer supports gapless playback for all common formats except MP3. See
the following bug report for more information:
https://bugzilla.gnome.org/show_bug.cgi?id=620323


Selecting an Output Device
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want QL to output to a different device you have to pass the device
option to the sink by setting a custom pipeline. In case of pulseaudio you can
get a list of available devices by executing::

    #!/usr/bin/env python2
    import gi
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)
    dm = Gst.DeviceMonitor()
    dm.start()
    for device in dm.get_devices():
        if device.get_device_class() == "Audio/Sink":
            props = device.get_properties()
            element = device.create_element(None)
            type_name = element.get_factory().get_name()
            device_name = element.props.device
            print "%s device=%r" % (type_name, device_name)
    dm.stop()

which should give you something like::

    pulsesink device='alsa_output.pci-0000_00_1b.0.analog-stereo'


which you can use as is, as a custom pipeline.


Xine Backend
------------

The Xine backend needs either xine-lib 1.1.x or xine-lib 1.2.x. Since most
distributions make QL only depend on GStreamer, you might have to install
xine-lib manually (*libxine1*, *lixine2* in Debian/Ubuntu).

To enable the backend, set the ``backend`` option in the ``config`` file to
``"xinebe"`` while QL isn't running.
