# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


class BaseIndicator:
    def remove(self):
        """Remove the indicator"""

        raise NotImplementedError

    def set_paused(self, value):
        """Update the paused state of the indicator"""


    def set_song(self, song):
        """Update the provided state of the indicator using the passed
        song or None if no song is active.
        """


    def set_info_song(self, song):
        """Update the provided information of the indicator using the passed
        song or None if no song is active.
        """


    def popup_menu(self):
        """Show the context menu as if the icon was pressed.

        Mainly for testing
        """

