VLC Backend
===========

VLC is an open source media player with a reputation for reliability, high
quality algorithms, and robust support for audio and video formats. The VLC
project automatically generates bindings which permits VLC to be embedded within
other applications. These bindings permit VLC to act as a backend player to the
Quod Libet application by simply ignoring the video fuctionality.

Benefits of using VLC
=====================

Using VLC as a backend has numerous potential benefits.  The driving benefits
behind the creation of this new backend for Quod Libet include:

- Lower CPU utilization
- Improved sound quality in some situations
- Automatic detection of new audio output devices on MacOS


Using the VLC Backend
=====================

Using the backend has two setup requirements:

1. Install the VLC media player:
   - https://github.com/videolan/vlc/releases

2. Setup Quod Libet to use the VLC backend:
   - Edit the VLC configuration file (e.g. `~/.quodlibet/config`)
   - Find the section marked `[player]`
   - Set the backend as follows (change an existing line or add a new line as necessary):
     - `backend=vlcbe`


VLC Links
=========

VLC Project: https://github.com/videolan/vlc
VLC C Bindings API: https://www.olivieraubert.net/vlc/python-ctypes/doc/
VLC Python Bindings Wiki: https://wiki.videolan.org/python_bindings

In order to interface with the VLC libraries, this code relies on the
auomatically generated python bindings for VLC which are available at these
locations:

PyPi: https://pypi.org/project/python-vlc/
Videolan: http://git.videolan.org/?p=vlc/bindings/python.git;a=tree;f=generated;b=HEAD

