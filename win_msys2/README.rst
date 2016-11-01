MSYS2 Based Dev Env
===================

Nothing works, this is just a start.

1) Download msys2 64-bit from https://msys2.github.io/
2) Follow instructions on https://msys2.github.io/
3) Execute ``C:\msys64\mingw32.exe``

::

    pacman -S git mingw-w64-i686-gdk-pixbuf2 mingw-w64-i686-librsvg \
        mingw-w64-i686-gtk3 mingw-w64-i686-python2 \
        mingw-w64-i686-python2-gobject mingw-w64-i686-python2-pip \
        mingw-w64-i686-libsoup
    
    pacman -S mingw-w64-i686-gstreamer mingw-w64-i686-gst-plugins-base \
        mingw-w64-i686-gst-plugins-good mingw-w64-i686-libsrtp \
        mingw-w64-i686-gst-plugins-bad mingw-w64-i686-gst-plugins-ugly

    pip install mutagen futures feedparser certifi pytest pep8 pyflakes
    git clone https://github.com/quodlibet/quodlibet.git

3) Apply this patch to gdk-pixbuf:
   https://bugzilla.gnome.org/show_bug.cgi?id=773760
4) ``cd ./quodlibet/quodlibet``
5) ``MSYSTEM= ./setup.py test``

Notes:

* There are three envs, msys, mingw32 and mingw64. The first is for
  the msys itself (unix tools with compat layer), the latter two for 
  32bit 64bit mingw environs (native compiled using mingw-w64)

* Python 2 changes os.sep, os.path.sep to "/" when MSYSTEM is set (why? 
  wtf). This is the default in the mingXX env. Always unset MSYSTEM for 
  QL. If you forget you have to remove all .pyc or the wrong paths will
  be cached.

* DnD is currently broken in GTK+ 3.20+ (maybe try to switch back to 
  3.18 somehow)

TODO:

* Fix tests
* Figure out how to create an installer out of it (does py2exe work?)
* Make bundling automatic
* Create a SDK for CI
* Build things manually
* Make builds reproducable
