.. _Requirements:

Requirements
============

Core Dependencies
-----------------

Quod Libet depends on the Python runtime and associated libraries.

 * `Python <http://www.python.org>`__ (>= 2.6)
 * `PyGObject <https://live.gnome.org/PyGObject>`__ (>= 3.2)
 * `GStreamer <http://gstreamer.freedesktop.org/>`__ (>= 1.0) or
   `xine-lib <http://www.xine-project.org/>`__ (>= 1.1): 
 * `Mutagen <https://mutagen.readthedocs.org/>`__ (>= 1.14): 

Particular audio formats depend on various *GStreamer* decoding elements,
as well as other Python modules. GStreamer splits their downlads into
*''good''*, *''bad''*, *''ugly''*, and *''ffmpeg''* packages, each of which
contains elements; you probably want them all.

Additional Features
-------------------

*Audio Feed support* depends on HTTP support and `Universal Feed Parser
<http://www.feedparser.org>`_.

Many parts of Quod Libet benefit from *D-Bus* and its `Python bindings
<http://dbus.freedesktop.org>`_.

*iPod support* depends on `libgpod <http://www.gtkpod.org/>`_.

*Device support* depends on `UDisks 1
<http://www.freedesktop.org/wiki/Software/udisks>`_.

Plugins
-------

Part of Quod Libet's strength is in its rich array of plugins to extend the
base functionality and interface with other systems. Some of these depend
on libraries of their own. If you don't have these, the plugin manager will
catch these errors and disable the plugin to avoid errors in QL itself, and
present them in the plugins error section. Once you've installed the
libraries, the plugins should work as expected.

Some notable examples:

 * The auto library update plugin depends on `pynotify
   <https://github.com/seb-m/pyinotify>`_
 * Zeitgeist plugin depends on the
   `python zeitgeist bindings <http://zeitgeist-project.com/news/python/>`_
