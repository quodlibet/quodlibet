# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


"""Various `plugin_handles` helpers"""


def is_a_file(song):
    return song.is_file


def is_writable(song):
    return bool(song.can_change()) and song.is_writable


def is_finite(song):
    return not song.multisong


def can_be_queued(song):
    return not song.can_add


def has_writable_image(song):
    return song.can_change_images


def has_bookmark(song):
    return bool(song.bookmarks)


# Higher order functions

def any_song(*song_funcs):
    return __handles_factory(any, song_funcs)


def each_song(*song_funcs):
    return __handles_factory(all, song_funcs)


def __handles_factory(reducer, song_funcs):
    def handles(_, songs):
        return reducer(all(f(s) for f in song_funcs)
                       for s in songs)
    return handles
