import gobject

class BasePlayer(gobject.GObject):
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
    _eq_values = []

    _gsignals_ = {
        'song-started':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'song-ended':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, bool)),
        'seek':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, int)),
        'paused': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'unpaused': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'error': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, str)),
        }

    _gproperties_ = {
        'volume': (float, 'player volume', 'the volume of the player',
                   0.0, 1.0, 1.0, gobject.PARAM_READWRITE)
        }

    def __init__(self, *args, **kwargs):
        super(BasePlayer, self).__init__()

    def destroy(self):
        pass

    def do_get_property(self, property):
        if property.name == 'volume':
            return self._volume
        else: raise AttributeError

    def _set_volume(self, v):
        self.props.volume = min(1.0, max(0.0, v))
    volume = property(lambda s: s._volume, _set_volume)

    def setup(self, source, song, seek_pos):
        """Connect to a PlaylistModel, and load a song."""
        self._source = source
        self.go_to(song)
        if seek_pos:
            self.seek(seek_pos)

    def remove(self, song):
        if self.song is song:
            self._source.next()
            self._end(True)

    def stop(self):
        self.paused = True
        self.seek(0)

    def reset(self):
        self._source.reset()
        if self._source.current is not None:
            self._end(True)
            if self.song:
                self.paused = False

    def next(self):
        self._source.next()
        self._end(True)
        if self.song:
            self.paused = False

    def previous(self, force=False):
        # Go back if standing at the beginning of the song,
        # otherwise restart the current song.
        if force or self.get_position() < 1500:
            self._source.previous()
            self._end(True)
        else:
            self.seek(0)
        if self.song:
            self.paused = False

    def go_to(self, song, explicit=False):
        print_d("Going to %r" % getattr(song, "key", song))
        res = self._source.go_to(song, explicit)
        if explicit and not res:
            return False
        self._end(True)
        return self.song is not None

    @property
    def eq_bands(self):
        """
        A read-only list of equalizer bands (in Hz) supported by this backend.
        """
        # For backwards compatibility, do a hasattr() before calling this.
        return []

    def _get_eq_values(self):
        """
        The list of equalizer values, in the range (-24dB, 12dB).
        """
        return self._eq_values

    def _set_eq_values(self, value):
        self._eq_values[:] = value
        if hasattr(self, 'update_eq_values'):
            self.update_eq_values()

    eq_values = property(_get_eq_values,_set_eq_values)
