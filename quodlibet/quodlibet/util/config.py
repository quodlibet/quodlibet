# Copyright 2004-2008 Joe Wreschnig
#           2009-2013 Nick Boultbee
#           2011-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""Simple proxy to a Python ConfigParser."""

import os
from StringIO import StringIO
import csv

# We don't need/want variable interpolation.
from ConfigParser import RawConfigParser as ConfigParser, Error


# In newer RawConfigParser it is possible to replace the internal dict. The
# implementation only uses items() for writing, so replace with a dict that
# returns them sorted. This makes it easier to look up entries in the file.
class _sorted_dict(dict):
    def items(self):
        return sorted(super(_sorted_dict, self).items())


class Config(object):
    """A wrapper around RawConfigParser"""

    def __init__(self):
        self._config = ConfigParser(dict_type=_sorted_dict)
        self._initial = {}

    def set_inital(self, section, option, value):
        """Set an initial value for an option.

        The section must be added with add_section() first.

        Adds the value to the config and calling reset()
        will reset the value to it.
        """

        self.set(section, option, value)

        self._initial.setdefault(section, {})
        self._initial[section].setdefault(option, {})
        self._initial[section][option] = value

    def reset(self, section, option):
        """Reset the value to the initial state"""

        value = self._initial[section][option]
        self.set(section, option, value)

    def options(self, section):
        return self._config.options(section)

    def get(self, *args):
        if len(args) == 3:
            try:
                return self._config.get(*args[:2])
            except Error:
                return args[-1]
        return self._config.get(*args)

    def getboolean(self, *args):
        if len(args) == 3:
            if not isinstance(args[-1], bool):
                raise ValueError
            try:
                return self._config.getboolean(*args[:2])
            # ValueError if the value found in the config file
            # does not match any string representation -> so catch it too
            except (ValueError, Error):
                return args[-1]
        return self._config.getboolean(*args)

    def getint(self, *args):
        if len(args) == 3:
            if not isinstance(args[-1], int):
                raise ValueError
            try:
                return self._config.getint(*args[:2])
            except Error:
                return args[-1]
        return self._config.getint(*args)

    def getfloat(self, *args):
        if len(args) == 3:
            if not isinstance(args[-1], float):
                raise ValueError
            try:
                return self._config.getfloat(*args[:2])
            except Error:
                return args[-1]
        return self._config.getfloat(*args)

    def getstringlist(self, *args):
        """Gets a list of strings, using CSV to parse and delimit"""

        if len(args) == 3:
            if not isinstance(args[-1], list):
                raise ValueError
            try:
                value = self._config.get(*args[:2])
            except Error:
                return args[-1]
        else:
            value = self._config.get(*args)
        parser = csv.reader([value])
        vals = [v.decode('utf-8') for v in parser.next()]
        print_d("%s.%s = %s" % (args + (vals,)))
        return vals

    def setstringlist(self, section, option, values):
        """Sets a config item to a list of quoted strings, using CSV"""

        sw = StringIO()
        values = [unicode(v).encode('utf-8') for v in values]
        writer = csv.writer(sw, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(values)
        self._config.set(section, option, sw.getvalue())

    def set(self, section, option, value):
        # RawConfigParser only allows string values but doesn't
        # scream if they are not (and it only fails before the
        # first config save..)
        if not isinstance(value, str):
            value = str(value)
        self._config.set(section, option, value)

    def setdefault(self, section, option, default):
        if not self._config.has_option(section, option):
            self._config.set(section, option, default)

    def write(self, filename):
        # FIXME: atomic save needed here

        if isinstance(filename, basestring):
            if not os.path.isdir(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            f = file(filename, "w")
        else:
            f = filename
        self._config.write(f)
        f.close()

    def clear(self):
        """Remove all sections and initial values"""

        for section in self._config.sections():
            self._config.remove_section(section)
        self._initial.clear()

    def is_empty(self):
        return not self._config.sections()

    def read(self, filename):
        self._config.read(filename)

    def sections(self):
        return self._config.sections()

    def has_option(self, section, option):
        return self._config.has_option(section, option)

    def remove_option(self, section, option):
        return self._config.remove_option(section, option)

    def add_section(self, section):
        if not self._config.has_section(section):
            self._config.add_section(section)
