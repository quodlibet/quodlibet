#!/usr/bin/env python

from distutils.core import setup, Extension
setup(name="pymodplug", version="1.2",
      url="http://www.sacredchao.net/quodlibet/wiki/Download",
      description="ModPlug decoder",
      author="Joe Wreschnig",
      author_email="piman@sacredchao.net",
      license="GNU GPL v2",
      long_description="""\
This Python module lets you load and decode files supported by
the ModPlug library (which includes MODs, ITs, XMs, and so on).""",
      py_modules=["modplug"]
         )
