Audio Backends
==============

Quod Libet currently supports GStreamer and Xine as an audio backend. The 
default backend can be changed in ``~/.quodlibet/config`` by setting the 
``backend`` option (gstbe=GStreamer, xinebe=Xine, nullbe=no backend)

There is also a experimental `Mac OS X NSSound backend (macbe) 
<http://code.google.com/p/quodlibet/issues/detail?id=509>`_ available in 
the issue tracker.


GStreamer
---------

Quod Libet tries  to  read  your GConf  GStreamer  configuration,  but  if  
that fails it falls back to autoaudiosink (which uses pulsesink, alsasink 
or directaudiosink on Windows)

You can change the default pipeline under `Preferences > Player`.

It will automatically add the default sink in case it is missing.

Output Device
^^^^^^^^^^^^^

If you want QL to output to a different device you have to pass the device 
option to the sink. In case of alsa you can get a list of available devices 
by executing::

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


To see the created GStreamer pipeline start quodlibet with the ``--debug`` 
parameter, go to *Preferences* > *Player* and press the *Print pipeline* 
button. All used elements/data formats will be printed to stdout.

RTP Streaming
^^^^^^^^^^^^^

Set the pipeline to::

    audioconvert ! rtpL16pay! udpsink host=224.1.1.1 auto-multicast=true port=5000


And somewhere else::

    gst-launch-0.10 udpsrc multicast-group=224.1.1.1 auto-multicast=true \
            port=5000 do-timestamp=true \
        caps="application/x-rtp,media=audio,clock-rate=44100,payload=96,encoding-name=L16,encoding-params=2" ! \
        rtpL16depay ! decodebin2 ! autoaudiosink

