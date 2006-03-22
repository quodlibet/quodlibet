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

    def __init__(self, filename=None, initial=[], count=10, model=None):
        self.count = count
        try: model = self.models[model]
        except KeyError:
            model = self.models[model] = gtk.ListStore(str, str)
        else: model = gtk.ListStore(str, str)

        super(ComboBoxEntrySave, self).__init__(model, 0)
        self.clear()
        render = gtk.CellRendererText()
        self.pack_start(render, True)
        self.add_attribute(render, 'text', 1)

        self.set_row_separator_func(self.__separator_func)

        if len(model) == 0:
            self.__fill(filename, initial)
        self.connect_object('destroy', self.set_model, None)

    def __fill(self, filename, initial):
        model = self.get_model()
        model.append(row=[None, None])

        if filename is None: return

        if os.path.exists(filename):
            for line in file(filename).readlines():
                line = line.strip()
                model.append(row=[line, line])

        for c in initial:
            model.append(row=[c, c])

        self.__shorten()

    def __separator_func(self, model, iter):
        return model[iter][0] is None

    def __shorten(self):
        model = self.get_model()
        for row in model:
            if row[0] is None:
                offset = row.path[0] + 1
                break
        to_remove = (len(model) - offset) - self.count
        while to_remove > 0:
            model.remove(model.get_iter((len(model) - 1,)))
            to_remove -= 1

    def write(self, filename, create=True):
        """Save to a filename. If create is True, any needed parent
        directories will be created."""
        try:
            if create:
                if not os.path.isdir(os.path.dirname(filename)):
                    os.makedirs(os.path.dirname(filename))

            saved = file(filename + ".saved", "wU")
            memory = file(filename, "wU")
            target = saved
            for row in self.get_model():
                if row[0] is None: target = memory
                else:
                    target.write(row[0] + "\n")
                    if target is saved:
                        target.write(row[1] + "\n")
            saved.close()
            memory.close()
        except EnvironmentError: pass

    def __remove_if_present(self, text):
        removable = False
        model = self.get_model()
        for row in model:
            if row[0] is None: removable = True
            elif removable and row[0] == text:
                model.remove(row.iter)
                return

    def prepend_text(self, text):
        model = self.get_model()

        self.__remove_if_present(text)

        for row in model:
            if row[0] is None:
                model.insert_after(row.iter, row=[text, text])
                break
        self.__shorten()
