#!/usr/bin/python -u
# An example of how to use the musepack module.
# This uses ossaudiodev, but whatever works for you is fine.
# public domain.

import os, sys
if len(sys.argv) != 2:
  raise SystemExit("Usage: %s filename.mpc" % sys.argv[0])

try:
  import musepack
except ImportError:
  raise SystemExit("Please compile the musepack.mpc extension!")

mod = musepack.MPCFile(sys.argv[1])

import ossaudiodev
dev = ossaudiodev.open("w")

print "Playing %s" % sys.argv[1]

dev.setfmt(ossaudiodev.AFMT_S16_LE)
dev.channels(2)
dev.speed(mod.frequency)

while True:
  s = mod.read()
  sys.stdout.write("\rPosition: %d:%02d / %d:%02d" %(
     mod.position / 60000, (mod.position % 60000) / 1000,
     mod.length / 60000, (mod.length % 60000) / 1000))
  if s: dev.write(s)
  else: break
