#!/usr/bin/env python

from distutils.core import setup, Extension
setup(name = "modplug", version = "0.1",
      description = "ModPlug decoder",
      author = "Joe Wreschnig",
      author_email = "piman@sacredchao.net",
      ext_modules=[
         Extension("modplug",
                   ["modplug.c"],
                   libraries = ["modplug"]
                   ),
         ])
