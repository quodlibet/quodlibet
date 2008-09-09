import gobject
import gtk

class BasePlayer(gtk.Object):
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

    _paused = False
    paused = False
    song = None
    info = None
    # Replay Gain profiles are a list of values to be tried in order;
    # Three things can set them: play order, browser, and a default.
    replaygain_profiles = [None, None, ["none"]]
    _length = 1
    _volume = 1.0

    _gsignals_ = {
        'song-started':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'song-ended':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, bool)),
        'seek':
        (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object, int)),
        'paused': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'unpaused': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'error': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                  (object, str, bool)),
        }

    _gproperties_ = {
        'volume': (float, 'player volume', 'the volume of the player',
                   0.0, 1.0, 1.0, gobject.PARAM_READWRITE)
        }

    def __init__(self, *args, **kwargs):
        super(BasePlayer, self).__init__()

    def do_song_started(self, song):
        # Reset Replay Gain levels based on the new song.
        self.volume = self.volume

    def do_song_ended(self, song, stopped):
        self.volume = self.volume

    def do_get_property(self, property):
        if property.name == 'volume':
            return self._volume
        else: raise AttributeError

    def _set_volume(self, v):
        self.props.volume = min(1.0, max(0.0, v))
    volume = property(lambda s: s._volume, _set_volume)

    def setup(self, source, song):
        """Connect to a PlaylistModel, and load a song."""
        self._source = source
        self.go_to(song)

    def remove(self, song):
        if self.song is song:
            self._end(False)

    def stop(self):
        if not self.paused:
            self._paused = True
            if self.song:
                self.emit('paused')
                self.bin.set_state(gst.STATE_NULL)
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

    def previous(self):
        # Go back if standing at the beginning of the song,
        # otherwise restart the current song.
        if self.get_position() < 500:
            self._source.previous()
            self._end(True)
        else:
            self.seek(0)
        if self.song:
            self.paused = False

    def go_to(self, song):
        print_d("Going to %r" % song, context=self)
        self._source.go_to(song)
        self._end(True)

    def destroy(self):
        self.go_to(None)
        super(BasePlayer, self).destroy()
