#!/usr/bin/env python

import os
from distutils.core import setup, Extension

def capture(cmd): return os.popen(cmd).read().strip()

setup(name = "trayicon", version = "1",
      url = "http://sacredchao.net/~piman/software/python.shtml",
      description = "notification area tray icon for PyGTK",
      author = "Joe Wreschnig",
      author_email = "piman@sacredchao.net",
      license = "GNU GPL v2",
      long_description = """
This module lets you put a simple icon in a FreeDesktop.org-compatible
notification area, and receive the 'activate' event when the left button
is pressed, and 'popup-menu' when the right button is pressed.""",
      ext_modules=[
         Extension("trayicon",
                   ["trayicon.c", "trayiconmodule.c", "eggtrayicon.c"],
                   extra_compile_args = capture("pkg-config --cflags gtk+-2.0 pygtk-2.0").split(),
                   extra_link_args = capture("pkg-config --libs gtk+-2.0 pygtk-2.0").split()
                   ),
         ])
