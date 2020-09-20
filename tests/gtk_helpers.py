# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


class MockSelData:
    # Gtk.SelectionData is missing a constructor

    def set(self, type, format, data):
        self.type = type
        self.format = format
        self.data = data

    def get_data_type(self):
        return self.type

    def get_data(self):
        return self.data
