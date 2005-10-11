#!/usr/bin/env python

from distutils.core import setup, Extension
setup(name="pymusepack", version="1.0",
      url="http://www.sacredchao.net/quodlibet",
      description="Musepack decoder and tagger",
      author="Joe Wreschnig",
      author_email="piman@sacredchao.net",
      license="GNU GPL v2",
      long_description="""
This Python module lets you load and decode Musepack (MPC/MP+)
files using libmpcdec. It resembles the Python MAD, Vorbis,
and ModPlug interfaces. It also lets you read and edit APEv2 tags.

It requires python-ctypes.""",
      packages = ["musepack"]
    )
