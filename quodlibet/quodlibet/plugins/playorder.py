# Copyright 2007 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import quodlibet.qltk.playorder

class PlayOrderPlugin(quodlibet.qltk.playorder.Order):
    """Play order plugins define alternate play orders for
    Quod Libet. They appear, when enabled, in the combo box
    in the lower left of the main window, as well as in the
    tray icon context menu.

    Play order plugins must define at least two methods, next
    and previous.
        def next(self, playlist, iter): ...
        def previous(self, playlist, iter): ...

    'playlist' is a GTK+ ListStore containing at least an AudioFile as
    the first element in each row (in the future there may be more
    elements per row), and iter is the GtkTreeIter for the song that
    just finished, if any (if the song is not in the list, this iter
    will be None).

    They can also define 'display_name' and 'accelerated_name'
    attributes which are used as the strings for display in the combo
    box and menu; both default to PLUGIN_NAME.

    Finally, they can specify an integer 'priority' to sort the list,
    and a 'replaygain_profile' list which is a list of Replay Gain
    profile names that this mode should fall back to (e.g. a shuffle
    mode should not use the 'album' Replay Gain profile).

    There is also
        def set(self, playlist, iter): ...
    for when the user manually selects a song from the list. In this
    case, iter is the song they selected, and playlist.current_iter is
    the current iter, if any. If iter is provided and this function
    returns None, the currently-playing song will not be ended.

    If explicit "next song" button presses should be handled
    differently than reaching the end of a song, use:
        def next_implicit(self, playlist, iter): ...
        def next_explicit(self, playlist, iter): ...
        def previous_explicit(self, playlist, iter): ...
        def previous_implicit(self, playlist, iter): ...
    There is also set_explicit, but no set_implicit.

    Finally, there is
        def reset(self, playlist): ...
    which is called when the playlist changes and state should be reset.

    """

    name = None
    display_name = None
    accelerated_name = None
    priority = quodlibet.qltk.playorder.Order.priority

class PlayOrderRememberedMixin(quodlibet.qltk.playorder.OrderRemembered):
    name = None
    display_name = None
    accelerated_name = None
    priority = quodlibet.qltk.playorder.Order.priority

class PlayOrderInOrderMixin(quodlibet.qltk.playorder.OrderInOrder):
    name = None
    display_name = None
    accelerated_name = None
    priority = quodlibet.qltk.playorder.Order.priority

class PlayOrderShuffleMixin(quodlibet.qltk.playorder.OrderShuffle):
    name = None
    display_name = None
    accelerated_name = None
    priority = quodlibet.qltk.playorder.Order.priority
