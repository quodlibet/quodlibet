#!/usr/bin/env python

from distutils.core import setup, Extension
setup(name = "pymp4info", version = "0.1",
      url = "",
      description = "A simple wrapper for some FAAD2 functions",
      author = "Alexey Bobyakov",
      author_email = "claymore.ws@gmail.com",
      license = "GNU GPL v2",
      long_description = """
A simple wrapper for FAAD2 library to get information about audio
track length, average bitrate and frequency. There is also a tagger
for handling iTunes metadata.""",
	  packages = ["mp4info"],
      ext_modules=[
         Extension("mp4info.mp4", ["mp4info/mp4.c"],
                   libraries = ["faad", "mp4v2"]
                   ),
         ])
