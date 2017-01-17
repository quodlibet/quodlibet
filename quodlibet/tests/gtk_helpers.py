# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


class MockSelData(object):
    # Gtk.SelectionData is missing a constructor

    def set(self, type, format, data):
        self.type = type
        self.format = format
        self.data = data

    def get_data_type(self):
        return self.type

    def get_data(self):
        return self.data
