#!/usr/bin/env python

from distutils.core import setup, Extension
setup(name = "pymodplug", version = "1.1",
      url = "http://sacredchao.net/~piman/software/python.shtml",
      description = "ModPlug decoder",
      author = "Joe Wreschnig",
      author_email = "piman@sacredchao.net",
      license = "GNU GPL v2",
      long_description = """
This Python module lets you load and decode files supported by
the ModPlug library (which includes MODs, ITs, XMs, and so on).
Its API has been chosen to mostly match pyvorbis and pymad.""",
      ext_modules=[
         Extension("modplug",
                   ["modplug.c"],
                   libraries = ["modplug"]
                   ),
         ])
