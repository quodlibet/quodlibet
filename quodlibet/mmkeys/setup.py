#!/usr/bin/env python

import os

from distutils.core import setup, Extension

def capture(cmd):
    return os.popen(cmd).read().strip()

setup(name="pymmkeys", version="3",
      url="http://sacredchao.net/~piman/software/python.shtml",
      description="multimedia key input for PyGTK",
      author="Joe Wreschnig",
      author_email="piman@sacredchao.net",
      license="GNU GPL v2",
      long_description="""\
This module lets you access multimedia keys found on most new keyboards
from PyGTK; most importantly it grabs all input events so your program
doesn't need to be in focus when the key is pressed (which is the
usual behavior of the keys).""",
      ext_modules=[
    Extension(
    "mmkeys", ["mmkeyspy.c", "mmkeys.c", "mmkeysmodule.c"],
    extra_compile_args=capture(
        "pkg-config --cflags gtk+-2.0 pygtk-2.0").split(),
    extra_link_args=capture("pkg-config --libs gtk+-2.0 pygtk-2.0").split()
    ),
         ])
