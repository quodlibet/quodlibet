import sys
import random
import gtk

if sys.version_info < (2, 4): from sets import Set as set

OFF, SHUFFLE, WEIGHTED = range(3)

class PlaylistMux(object):
    def __init__(self, watcher, q, pl):
        self.q = q
        self.pl = pl
        watcher.connect('song-started', self.__check_q)

    def __check_q(self, watcher, song):
        if song is not None:
            iter = self.q.find(song)
            if iter: self.q.remove(iter)
            self.q.go_to(None); self.q.next()

    def get_current(self):
        if self.q.current is not None: return self.q.current
        else: return self.pl.current

    current = property(get_current)

    def is_empty(self):
        return self.q.is_empty() or self.p.is_empty()

    def next(self):
        if self.q.is_empty(): self.pl.next()
        elif self.q.current is None: self.q.next()

    def previous(self):
        self.pl.previous()

    def go_to(self, song):
        self.pl.go_to(song)
        self.q.go_to(None)

    def reset(self):
        self.pl.reset()

    def enqueue(self, songs):
        for song in songs:
            if song not in self.q: self.q.append(row=[song])

class PlaylistModel(gtk.ListStore):
    shuffle = OFF
    repeat = False
    __path = None

    def __init__(self):
        gtk.ListStore.__init__(self, object)
        self.__played = []

    def set(self, songs):
        oldsong = self.current
        self.__played = []
        self.__path = None
        self.clear()
        for song in songs:
            iter = self.append(row=[song])
            if song == oldsong:
                self.__path = self.get_path(iter)[0]

    def remove(self, iter):
        oldpath = self.__path
        song = self.current
        gtk.ListStore.remove(self, iter)
        self.go_to(song)
        if self.__path is None and not self.is_empty():
            self.__path = min(oldpath, len(self) - 1)

    def get(self):
        return [row[0] for row in self]

    def get_current(self):
        if self.__path == None: return None
        elif self.is_empty(): return None
        else: return self[(self.__path,)][0]

    current = property(get_current)

    def next(self):
        if self.shuffle:
            self.__next_shuffle()
            return
        
        # If we're empty, the next song is no song.
        # If the current song is the last song,
        #  - If repeat is off, the next song is no song.
        #  - If repeat is on, the next song is the first song.
        # Else, if the current song is no song, the next song is the first.
        # Else, the next song is the next song.
        if self.is_empty(): self.__path = None
        elif self.__path >= len(self) - 1:
            if self.repeat: self.__path = 0
            else: self.__path = None
        elif self.__path is None: self.__path = 0
        else: self.__path += 1

    def __next_shuffle(self):
        if self.__path is not None:
            self.__played.append(self.__path)

        if self.shuffle == 1: self.__next_shuffle_regular()
        elif self.shuffle == 2: self.__next_shuffle_weighted()
        else: raise ValueError("Invalid shuffle %d" % self.shuffle)

    def __next_shuffle_regular(self):
        played = set(self.__played)
        songs = set(range(len(self)))
        remaining = songs.difference(played)
        if remaining:
            self.__path = random.choice(list(remaining))
        elif self.repeat:
            self.__played = []
            self.__path = random.choice(list(songs))
        else:
            self.__played = []
            self.__path = None

    def __next_shuffle_weighted(self):
        songs = self.get()
        max_score = sum([song.get('~#rating', 2) for song in songs])
        choice = random.random() * max_score
        current = 0.0
        for i, song in enumerate(songs):
            current += song.get("~#rating", 2)
            if current >= choice:
                self.__path = i
                break

        else: self.__path = 0

    def previous(self):
        if self.shuffle:
            self.__previous_shuffle()
            return

        # If we're empty, the last song is no song.
        # Else if the current song is none, the previous is the last.
        # Else the previous song is the previous song.
        if self.is_empty(): self.__path = None
        elif self.__path == 0: pass
        elif self.__path is None: self.__path = len(self) - 1
        else: self.__path  = max(0, self.__path - 1)

    def __previous_shuffle(self):
        try: path = self.__played.pop(-1)
        except IndexError: pass
        else: self.__path = path

    def go_to(self, song):
        if self.shuffle and self.__path is not None:
            self.__played.append(self.__path)

        self.__path = None
        if isinstance(song, gtk.TreeIter):
            self.__path = self.get_path(song)
        else:
            def _find(self, path, iter):
                if self[iter][0] == song:
                    self.__path = path[0]
                    return True
                else: return False
            self.foreach(_find)

    def find(self, song):
        iters = [None]
        def _find(self, path, iter):
            if self[iter][0] == song:
                iters.append(iter)
                return True
            else: return False
        self.foreach(_find)
        return iters[-1]

    def find_all(self, songs):
        iters = []
        def _find(self, path, iter, it):
            if self[iter][0] in songs: it.append(iter)
            return len(it) == len(songs)
        self.foreach(_find, iters)
        return iters

    def __contains__(self, song): return bool(self.find(song))

    def is_empty(self):
        return not bool(len(self))

    def reset(self):
        self.__played = []
        self.go_to(None)
