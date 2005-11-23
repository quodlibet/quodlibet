# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gtk

class ComboBoxEntrySave(gtk.ComboBoxEntry):
    """A ComboBoxEntry that remembers the past 'count' strings entered,
    and can save itself to (and load itself from) a filename or file-like."""

    models = {}
    
    def __init__(self, f=None, initial=[], count=10, model=None):
        self.count = count
        if model:
            try:
                gtk.ComboBoxEntry.__init__(self, self.models[model], 0)
            except KeyError:
                gtk.ComboBoxEntry.__init__(self, gtk.ListStore(str), 0)
                self.models[model] = self.get_model()
                self.__fill(f, initial)
        else:
            gtk.ComboBoxEntry.__init__(self, gtk.ListStore(str), 0)
            self.__fill(f, initial)
        self.connect_object('destroy', self.set_model, None)

    def __fill(self, f, initial):
        if f is not None and not hasattr(f, 'readlines'):
            if os.path.exists(f):
                for line in file(f).readlines():
                    self.append_text(line.strip())
        elif f is not None:
            for line in f.readlines():
                self.append_text(line.strip())
        for c in initial: self.append_text(c)

    def prepend_text(self, text):
        try: self.remove_text(self.get_text().index(text))
        except ValueError: pass
        gtk.ComboBoxEntry.prepend_text(self, text)
        while len(self.get_model()) > self.count:
            self.remove_text(self.count)

    def insert_text(self, position, text):
        try: self.remove_text(self.get_text().index(text))
        except ValueError: pass
        if position >= self.count: return
        else:
            gtk.ComboBoxEntry.insert_text(self, position, text)
            while len(self.get_model()) > self.count:
                self.remove_text(self.count)

    def append_text(self, text):
        if text not in self.get_text():
            if len(self.get_model()) < self.count:
                gtk.ComboBoxEntry.append_text(self, text)

    def get_text(self):
        """Return a list of all entries in the history."""
        return [m[0] for m in self.get_model()]

    def write(self, f, create=True):
        """Save to f, a filename or file-like. If create is True, any
        needed parent directories will be created."""
        try:
            if not hasattr(f, 'read'):
                if ("/" in f and create and
                    not os.path.isdir(os.path.dirname(f))):
                    os.makedirs(os.path.dirname(f))
                f = file(f, "w")
            f.write("\n".join(self.get_text()) + "\n")
        except EnvironmentError: pass
