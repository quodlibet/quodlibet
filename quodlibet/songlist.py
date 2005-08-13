import gtk

OFF, SHUFFLE, WEIGHTED = range(3)

class PlaylistModel(gtk.ListStore):
    shuffle = OFF
    repeat = False
    __path = None

    def __init__(self):
        gtk.ListStore.__init__(self, object)

    def set(self, songs):
        oldsong = self.current
        self.__path = None
        self.clear()
        for song in songs:
            iter = self.append(row=[song])
            if song == oldsong:
                self.__path = self.get_path(iter)[0]

    def get(self):
        return [row[0] for row in self]

    def get_current(self):
        if self.__path == None: return None
        else: return self[(self.__path,)][0]

    current = property(get_current)

    def next(self):
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

    def previous(self):
        # If we're empty, the last song is no song.
        # Else if the current song is none, the previous is the last.
        # Else the previous song is the previous song.
        if self.is_empty(): self.__path = None
        elif self.__path == 0: pass
        elif self.__path is None: self.__path = len(self) - 1
        else: self.__path  = max(0, self.__path - 1)

    def go_to(self, song):
        if isinstance(song, gtk.TreeIter):
            self.__path = self.get_path(iter)
        else:
            def _find(self, path, iter):
                if self[iter][0] == song:
                    self.__path = path[0]
                    return True
                else: return False
            self.foreach(_find)

    def is_empty(self): return not bool(len(self))
