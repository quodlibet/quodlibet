import tempfile
from quodlibet.formats._audio import AudioFile as Fakesong
from quodlibet.util.collection import Playlist
from tests import TestCase, add
from random import randint
from timeit import timeit,default_timer
from quodlibet import const

PLAYLISTS = tempfile.gettempdir()

const.DEBUG = True

class TPlaylistPerformance(TestCase):
    def test_playlists_featuring_performance(s):
        """Basic performance tests for `playlists_featuring()`

        Initial tests indicate that:
        For 100,000 songs with 20 Playlists (each of 1000 songs):
        -> The cache is ~= 6MB in size, delivers a 250x speed increase once warm

        For 10,000 songs with 20 Playlists (each of 100 songs):
        -> The cache is ~= 770 KB in size, 6.4x speed increase once warm

        For 10,000 songs with 2 Playlists (each of 5000 songs)
        -> The cache is ~= 770 KB in size, 180x speed increase once warm

        TODO: Reporting, debugging.
        """

        # Basic sizes
        NUM_PLAYLISTS = 10
        NUM_SONGS = 10000

        # Every nth song is playlisted
        SONGS_TO_PLAYLIST_SIZE_RATIO = 10

        PLAYLISTS_PER_PLAYLISTED_SONG = 3

        ARTISTS = ["Mr Foo", "Bar", "Miss T Fie", "Dr Death"]
        pls = []
        library = []

        def setup():
            Playlist._remove_all()
            for i in xrange(NUM_PLAYLISTS):
                pls.append(Playlist(PLAYLISTS, "List %d" % (i+1)))
            for i in xrange(NUM_SONGS):
                a = ARTISTS[randint(0,2)]
                t = "Song %d" % i
                data = {"title": t, "artist":a, "~#tracknumber": i % 20,
                        "~filename": "%s.mp3" % t,
                        "~#filesize":randint(1000000,100000000)}
                song = Fakesong(data)
                library.append(song)
                if not (i % SONGS_TO_PLAYLIST_SIZE_RATIO):
                    song["~included"] = "yes"
                    for j in range(PLAYLISTS_PER_PLAYLISTED_SONG):
                        pls[(i+j) % NUM_PLAYLISTS].append(song)

        print_d("\nSetting up %d songs and %d playlists... " % (
            NUM_SONGS, NUM_PLAYLISTS))
        print_d("took %.1f ms" % (timeit(setup, "pass", default_timer, 1)*1000.0))

        def get_playlists():
            for song in library:
                #song = library[randint(0,len(library)-1)]
                playlists = func(song)
                s.failUnlessEqual(len(playlists),
                    PLAYLISTS_PER_PLAYLISTED_SONG if
                    song("~included") else 0)
                # Spot sanity check
                # s.failUnless(song in list(playlists)[0])

        REPEATS = 2
        func = Playlist._uncached_playlists_featuring
        print_d("Using %d songs and %d playlists, with 1 in %d songs "
              "in %d playlist(s) => each playlist has %d songs. "
              %  (NUM_SONGS, NUM_PLAYLISTS,
                  SONGS_TO_PLAYLIST_SIZE_RATIO,
                  PLAYLISTS_PER_PLAYLISTED_SONG,
                  PLAYLISTS_PER_PLAYLISTED_SONG * NUM_SONGS
                  / (SONGS_TO_PLAYLIST_SIZE_RATIO * NUM_PLAYLISTS)))
        print_d("Timing basic get_playlists_featuring()... ")
        duration = timeit(get_playlists, "pass", default_timer, REPEATS)
        print_d("averages %.1f ms" % (duration * 1000.0 / REPEATS))

        # Now try caching version
        func = Playlist._cached_playlists_featuring
        print_d("Timing cached get_playlists_featuring()...")
        cold = timeit(get_playlists, "pass", default_timer, 1)
        # And now it's warmed up...
        print_d("cold: averages %.1f ms" % (cold* 1000.0))
        warm = timeit(get_playlists, "pass", default_timer, REPEATS -1)
        print_d("warm: averages %.1f ms (speedup = %.1f X)"
              % (warm * 1000.0 / (REPEATS-1), cold/warm))
        print_d("Cache hits = %d, misses = %d (%d%% hits). Size of cache=%.2f KB"
              % (Playlist._hits, Playlist._misses,
                 Playlist._hits * 100 / (Playlist._misses + Playlist._hits),
                 Playlist._get_cache_size()))

add(TPlaylistPerformance)
