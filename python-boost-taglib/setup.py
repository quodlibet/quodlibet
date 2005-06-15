#!/usr/bin/env python

from distutils.core import setup, Extension

extensions = []

LS = ['boost_python', 'tag']
ECA = ["-I/usr/include/taglib"]

setup(name="python-boost-taglib", version="0",
      url="http://www.sacredchao.net/quodlibet",
      description="Boost-Python wrappers for TagLib",
      author="Joe Wreschnig",
      author_email="piman@sacredchao.net",
      license="GNU GPL v2",
      long_description="""This module wraps TagLib.""",
      ext_modules=[
    Extension('taglib', ['taglib.cpp'], libraries=LS,extra_compile_args=ECA)]
    )
