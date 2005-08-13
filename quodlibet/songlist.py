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
        if self.__path is not None and self.__path < len(self) - 1:
            self.__path += 1
        elif self.__path is None and len(self):
            self.__path = 0
        else: self.__path = None

    def previous(self):
        if self.__path: self.__path -= 1
        elif self.__path is None and len(self): self.__path = len(self) - 1

    def go_to(self, song):
        def _find(self, path, iter):
            if self[iter][0] == song:
                self.__path = path[0]
                return True
            else: return False
        self.foreach(_find)

    def is_empty(self): return not bool(len(self))
