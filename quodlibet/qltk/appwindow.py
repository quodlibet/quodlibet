# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


class AppWindow:
    """The shared interface provided by both QL and EF"""

    def open_file(self, filename):
        """Open the specified file and play it.

        The file can be missing or a directory..

        Args:
            filename (fsnative)
        Returns:
            bool: If opening worked
        """

        return False

    def get_is_persistent(self):
        """If closing this window should shut down the application

        Returns:
            bool
        """

        return True

    def set_as_osx_window(self, osx_app):
        """Set up the passed in osx app instance

        FIXME: split this into getters..

        Args:
            osx_app (GtkosxApplication.Application)
        """

