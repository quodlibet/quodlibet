from quodlibet.util.collection import Album
from quodlibet.formats._audio import AudioFile
from quodlibet import const
from tests import TestCase, add
from tests.plugin import PluginTestCase

# Allow some debugging
const.DEBUG = False

A1S1 = AudioFile(
        {'album': 'greatness', 'title': 'excellent', 'artist': 'fooman',
         '~#lastplayed': 1234, '~#rating': 0.75})
A1S2 = AudioFile(
        {'album': 'greatness', 'title': 'superlative', 'artist': 'fooman',
         '~#lastplayed': 1234, '~#rating': 1.0})
A1 = Album(A1S1)
A1.songs = set([A1S1, A1S2])

A2S1 = AudioFile({'album': 'mediocrity', 'title': 'blah', 'artist': 'fooman',
                  '~#lastplayed': 1234})
A2S2 = AudioFile({'album': 'mediocrity', 'title': 'meh', 'artist': 'fooman',
                  '~#lastplayed': 1234})
A2 = Album(A2S1)
A2.songs = set([A2S1, A2S2])

A3S1 = AudioFile(
        {'album': 'disappointment', 'title': 'shameful', 'artist': 'poorman',
         '~#lastplayed': 2345, '~#rating': 0.25})
A3S2 = AudioFile(
        {'album': 'disappointment', 'title': 'zero', 'artist': 'poorman',
         '~#lastplayed': 2345, '~#rating': 0.0})
A3S3 = AudioFile(
        {'album': 'disappointment', 'title': 'lame', 'artist': 'poorman',
         '~#lastplayed': 0, '~#rating': 0.25})

A3 = Album(A3S1)
A3.songs = set([A3S1, A3S2, A3S3])

for song in [A1S1, A1S2, A2S1, A2S2, A3S1, A3S2, A3S3]: song["length"] = 100

class TRandomAlbum(PluginTestCase):
    """Some basic tests for the random album plugin algorithm"""
    WEIGHTS = {'rating': 0, 'added': 0, 'laststarted': 0, 'lastplayed': 0,
               'length': 0, 'skipcount': 0, 'playcount': 0}

    def setUp(self):
        self.plugin = self.plugins["Random Album Playback"]()
        self.albums = [A1, A2, A3]

    def get_winner(self, albums):
        print_d("Weights: %s " % self.plugin.weights)
        scores = self.plugin._score(albums)
        print_d("Scores: %s" % scores)
        return max(scores)[1]


    def test_score_rating(self):
        weights = self.plugin.weights = self.WEIGHTS.copy()
        weights['rating'] = 1
        self.failUnlessEqual(A1, self.get_winner(self.albums))

    def test_score_length(self):
        weights = self.plugin.weights = self.WEIGHTS.copy()
        weights['length'] = 1
        self.failUnlessEqual(A3, self.get_winner(self.albums))

    def test_score_lastplayed(self):
        weights = self.plugin.weights = self.WEIGHTS.copy()
        weights['lastplayed'] = 1
        self.failUnlessEqual(A3, self.get_winner(self.albums))

    def test_score_lastplayed_added(self):
        weights = self.plugin.weights = self.WEIGHTS.copy()
        weights['lastplayed'] = 1
        # No data here
        weights['added'] = 1
        self.failUnlessEqual(A3, self.get_winner(self.albums))

    def test_score_mixed(self):
        print_d("Starting.")
        weights = self.plugin.weights = self.WEIGHTS.copy()
        weights['length'] = 1
        weights['lastplayed'] = 2
        weights['rating'] = 1
        # A3 is #3 rating, #1 in lastplayed, #1 in length
        self.failUnlessEqual(A3, self.get_winner(self.albums))
        weights['lastplayed'] = 1
        weights['rating'] = 2
        weights['length'] = 0.5
        # A1 is #1 for Rating, #2 for lastplayed, #2 or 3 length
        self.failUnlessEqual(A1, self.get_winner(self.albums))

add(TRandomAlbum)
