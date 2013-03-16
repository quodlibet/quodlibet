# Copyright 2007-2008 Joe Wreschnig
#           2009,2010 Steven Robertson
#           2009-2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import GObject


class Equalizer(object):
    _eq_values = []

    @property
    def eq_bands(self):
        """read-only list of equalizer bands (in Hz) supported."""

        return []

    @property
    def eq_values(self):
        """The list of equalizer values, in the range (-24dB, 12dB)."""

        return self._eq_values

    @eq_values.setter
    def eq_values(self, value):
        self._eq_values[:] = value
        self.update_eq_values()

    def update_eq_values(self):
        """Override to apply equalizer values"""

        pass


class BasePlayer(GObject.GObject, Equalizer):
    """Interfaces between a QL PlaylistModel and a GSt playbin.

    Attributes:
    paused -- True or False, set to pause/unpause the player
    volume -- current volume, 0.0 to 1.0

    song -- current song, or None if not playing
    info -- current stream information, or None if not playing. This is
            usually the same as song, unless the user is listening to
            a stream with multiple songs in it.

    If you're going to show things, use .info. If you're going to
    change things, use .song.
    """

    name = ""
    version_info = ""

    paused = None
    song = None
    info = None
    volume = None

    # Replay Gain profiles are a list of values to be tried in order;
    # Four things can set them: rg menu, browser, play order, and a default.
    replaygain_profiles = [None, None, None, ["none"]]
    _volume = 1.0
    _paused = True

    _gsignals_ = {
        'song-started':
        (GObject.SignalFlags.RUN_LAST, None, (object,)),
        'song-ended':
        (GObject.SignalFlags.RUN_LAST, None, (object, bool)),
        'seek':
        (GObject.SignalFlags.RUN_LAST, None, (object, int)),
        'paused': (GObject.SignalFlags.RUN_LAST, None, ()),
        'unpaused': (GObject.SignalFlags.RUN_LAST, None, ()),
        'error': (GObject.SignalFlags.RUN_LAST, None, (object, str)),
        }

    _gproperties_ = {
        'volume': (float, 'player volume', 'the volume of the player',
                   0.0, 1.0, 1.0, GObject.PARAM_READWRITE)
        }

    def __init__(self, *args, **kwargs):
        super(BasePlayer, self).__init__()

    def destroy(self):
        """Free resources"""

        self._source = None

    def do_get_property(self, property):
        if property.name == 'volume':
            return self._volume
        else:
            raise AttributeError

    def _set_volume(self, v):
        self.props.volume = min(1.0, max(0.0, v))
    volume = property(lambda s: s._volume, _set_volume)

    def setup(self, source, song, seek_pos):
        """Connect to a PlaylistModel, and load a song."""

        self._source = source
        self.go_to(song)
        if seek_pos:
            self.seek(seek_pos)

    def seek(self, position):
        """Seek to absolute position in milliseconds.
        If position is larger than the duration start the next song
        """

        raise NotImplementedError

    def get_position(self):
        """The current position in milliseconds"""

        raise NotImplementedError

    def remove(self, song):
        """Make sure the song isn't played anymore"""

        if song and self.song is song:
            self._source.next()
            self._end(True)

    def stop(self):
        """Stop playback and reset the position.
        Might release the audio device
        """

        self.paused = True
        self.seek(0)

    def reset(self):
        """Reset the source and start playing if possible"""

        self._source.reset()
        if self._source.current is not None:
            self._end(True)
            if self.song:
                self.paused = False

    def next(self):
        """Move to the next song"""

        self._source.next()
        self._end(True)
        if self.song:
            self.paused = False

    def previous(self, force=False):
        """Go back if standing at the beginning of the song
        otherwise restart the current song.

        If force is True always go back.
        """

        if force or self.get_position() < 1500:
            self._source.previous()
            self._end(True)
        else:
            self.seek(0)
        if self.song:
            self.paused = False

    def go_to(self, song, explicit=False):
        """Activate the song in the playlist and play it.
        explicit if the action comes from the user
        """

        print_d("Going to %r" % getattr(song, "key", song))
        res = self._source.go_to(song, explicit)
        if explicit and not res:
            return False
        self._end(True)
        return self.song is not None

    def can_play_uri(self, uri):
        """Whether the player supports playing te given URI scheme"""

        raise NotImplementedError
