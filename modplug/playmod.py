#!/usr/bin/env python
# An example of how to use the modplug module.
# This uses ossaudiodev, but whatever works for you is fine.
# public domain.

import os, sys
if len(sys.argv) != 2:
  raise SystemExit("Usage: %s filename.mod" % sys.argv[0])

try:
  import modplug
except ImportError:
  raise SystemExit("Please compile the modplug extension! (make modplug.so)")

mod = modplug.ModFile(sys.argv[1])

import ossaudiodev
dev = ossaudiodev.open("w")

print "Playing %s" % sys.argv[1]

# Not all formats and/or files have titles; if this file doesn't, its
# title is filled in as its basename.
print "Title: %s" % mod.title

# Guessing the lengths of mods is hard.
print "Length: %d:%d" % (mod.length / 60000, (mod.length % 60000) / 1000)

# Currently these are hardcoded into the modplug module; if it actually
# matters an API can be made to change the output settings.
dev.setfmt(ossaudiodev.AFMT_S16_LE)
dev.channels(2)
dev.speed(44100)
while True:
  # read returns no more than the specified number of bytes; it may return
  # less. When it returns 0, the file is done (or your buffer size is too
  # low, seems to be < ~5 bytes).
  s = mod.read(4096)
  if s: dev.write(s)
  else: break
