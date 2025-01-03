# Copyright 2007 Joe Wreschnig
#        2016-17 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import quodlibet.qltk.playorder


class PlayOrderPlugin(quodlibet.qltk.playorder.Order):
    """Play order plugins define alternate play orders for
    Quod Libet, of the two types: Reorder (aka Shuffle) and Repeat.
    Implementations must choose to subclass `RepeatPlugin` or `ShufflePlugin`.

    They appear, when enabled, in the combo boxes in the lower left of the
    main window, as well as in the tray icon context menu.

    If explicit "next song" button presses should be handled
    differently than reaching the end of a song, use:
        def next_implicit(self, playlist, iter): ...
        def next_explicit(self, playlist, iter): ...
        def previous_explicit(self, playlist, iter): ...
        def previous_implicit(self, playlist, iter): ...

    """

    # Note these values unset the base versions, as the plugin handler logic
    # does some auto-setting of these, based on PLUGIN_NAME, if they're None
    name: str | None = None
    display_name = None
    accelerated_name = None

    priority = 200
    """Plugins default to lower priority than built-ins"""


class RepeatPlugin(PlayOrderPlugin, quodlibet.qltk.playorder.Repeat):
    """Repeat plugins add new ways to repeat an existing,
    possibly shuffled playlist.

    Note that they must delegate to the underlying `Order` (typically a
     `Reorder`) in order for the UI to function as intended.
     As such, the only method necessary to implement from `Repeat` is
        def next(self, playlist, iter): ...

    """

    pass


class ShufflePlugin(PlayOrderPlugin, quodlibet.qltk.playorder.Reorder):
    """Shuffle plugins add new ways to reorder a given song list

    Shuffle / plugins must define at least two missing methods from `Reorder`,
    i.e.
        def next(self, playlist, iter): ...
        def previous(self, playlist, iter): ...

    """

    pass
