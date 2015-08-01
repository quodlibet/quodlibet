from .util import iter_to_list
from quodlibet.util.dprint import print_d


class GStreamerSource(object):
    def __init__(self, player, playbin):
        self._player = player
        self._playbin = playbin

    def source_setup():
        pass

    def play_song(self, song):
        raise NotImplementedError()


# this is the most basic of sources; it lets the playbin do everything.
class PlaybinHandler(GStreamerSource):

    # find the (uri)decodebin after setup and use autoplug-sort
    # to sort elements like decoders
    def source_setup(self, pipeline, source):
        print_d('setting up default source')

        def autoplug_sort(decode, pad, caps, factories):
            def set_prio(x):
                i, f = x
                i = {
                    "mad": -1,
                    "mpg123audiodec": -2
                }.get(f.get_name(), i)
                return (i, f)
            return zip(*sorted(map(set_prio, enumerate(factories))))[1]

        for e in iter_to_list(self._playbin.iterate_recurse):
            try:
                e.connect("autoplug-sort", autoplug_sort)
            except TypeError:
                pass
            else:
                break

    def play_song(self, song):
        print_d('setting song to %s' % song)
        if song is not None:
            uri = song('~uri')
        else:
            uri = None
        self._playbin.set_property('uri', uri)
