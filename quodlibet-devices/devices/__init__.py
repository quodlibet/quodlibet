# -*- coding: utf-8 -*-
# Copyright 2006 Markus Koller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import traceback

from os.path import dirname, basename, isdir, join
from glob import glob

from devices._base import Device

base = dirname(__file__)
self = basename(base)
modules = [f[:-3] for f in glob(join(base, "[!_]*.py"))]
modules = ["%s.%s" % (self, basename(m)) for m in modules]

devices = []
for _name in modules:
    try: device = __import__(_name, {}, {}, self)
    except NotImplementedError:
        print "W: %s not supported." % _name
        continue
    except Exception, err:
        traceback.print_exc()
        continue

    for klass in device.__dict__.values():
        if type(klass) != type or klass == Device: continue
        if issubclass(klass, Device):
            devices.append(klass)
            break
    else:
        print "W: %s doesn't contain any devices." % device.__name__

devices.sort()

# Return a constructor for a device given by a string
def get(name):
    try: return devices[[d.__name__ for d in devices].index(name)]
    except Exception, err:
        print "W: Removing unsupported device %s." % name
        return Device
