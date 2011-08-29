import gtk
import pango

from quodlibet import config

from quodlibet import qltk
from quodlibet.browsers._base import Browser
from quodlibet.browsers.albums import AlbumList, AlbumTagCompletion

from quodlibet import util

class AlbumIconList(AlbumList):
    name = _("Album Icons")
    accelerated_name = _("Album _Icons")
    priority = 4.5
    __model = None

    @classmethod
    def _init_model(klass, library):
        klass.__model = model = klass._AlbumStore(object, str, gtk.gdk.Pixbuf)
        library.connect('removed', klass._remove_songs, model)
        library.connect('changed', klass._changed_songs, model)
        library.connect('added', klass._add_songs, model)
        klass._add_songs(library, library.values(), model)
        model.append(row=[None, _("All Songs"), None])

    @classmethod
    def _add_songs(klass, library, added, model, update=True):
        albums = model.get_albums()
        changed = set() # Keys of changed albums
        new = [] # Added album instances
        for song in added:
            labelid = song.get("labelid", "")
            mbid = song.get("musicbrainz_albumid", "")
            key = song.album_key
            if key not in albums:
                new_album = klass._Album(song("album"), labelid, mbid)
                albums[key] = new_album
                new.append(new_album)
            albums[key].songs.add(song)
            changed.add(key)
        for album in new:
            model.append(row=[album, album("title"), album.cover])
        if update: klass._update(changed, model)
        else: return changed


    class _Album(AlbumList._Album):
        def refresh(self):
            super(AlbumIconList._Album, self).refresh()
            data = "%s\n<i>%s</i>" % (
                util.escape(self("artist")), util.escape(self("title")))
            self._model[self._iter][1] = data
            self._model[self._iter][2] = self.cover

    def __init__(self, library, player):
        # Intentional use of AlbumList instead if AlbumIconList. We
        # don't want to initialize AlbumList, just its parents.
        super(AlbumList, self).__init__(spacing=6)
        self._register_instance()
        if self.__model is None:
            self._init_model(library)
        self._save = bool(player)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        model_sort = gtk.TreeModelSort(self.__model)
        model_filter = model_sort.filter_new()
        self._view = gtk.IconView(model_filter)

        if isinstance(self._view, gtk.CellLayout):
            # gtk.IconView is a piece of shit; this magic was copied
            # from the Gimmie source, and hopefully works.
            icon_cell = gtk.CellRendererPixbuf()
            self._view.pack_start(icon_cell, expand=False)
            self._view.add_attribute(icon_cell, "pixbuf", 2)

            text_cell = gtk.CellRendererText()
            text_cell.set_property("wrap-mode", pango.WRAP_WORD)
            text_cell.set_property('wrap-width', 90)
            text_cell.set_property('width', 100)
            text_cell.set_property('yalign', 0.0)
            text_cell.set_property('alignment', pango.ALIGN_CENTER)
            text_cell.set_property('ellipsize', pango.ELLIPSIZE_END)
            self._view.pack_start(text_cell, expand=False)
            self._view.add_attribute(text_cell, "markup", 1)
        else:
            self._view.set_text_column(1)
            self._view.set_pixbuf_column(2)
        sw.add(self.view)
        self.view.connect('selection-changed', self.__fill_songs)
        self.view.connect('item-activated', self.__play_selection, player)
        self.view.set_columns(0)
        self.view.set_item_width(0)
        self.view.set_selection_mode(gtk.SELECTION_MULTIPLE)

        self.pack_start(self.SortCombo(model_sort), expand=False)
        self.pack_start(self.FilterEntry(model_filter), expand=False)
        self.pack_start(sw)
        self.show_all()

    def __play_selection(self, view, path, player):
        player.reset()

    view = property(lambda self: self._view)

    def restore(self):
        pass

    def save(self):
        pass

    def activate(self):
        self.view.emit('selection-changed')

    def __fill_songs(self, view):
        albums = self.view.get_selected_items()
        model = self.view.get_model()
        songs = set()
        for path in albums:
            songs.update(model[path][0].songs)
        songs = list(songs)
        self.emit('songs-selected', songs, None)

browsers = [AlbumIconList]
