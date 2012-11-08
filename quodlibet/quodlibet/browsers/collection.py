# -*- coding: utf-8 -*-
# Copyright 2010, 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gobject
import gtk
import pango

from quodlibet import config
from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.browsers.albums import AlbumTagCompletion
from quodlibet.browsers._base import Browser
from quodlibet.parse import XMLFromPattern, Query
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.tagscombobox import TagsComboBoxEntry
from quodlibet.qltk.views import AllTreeView, BaseView
from quodlibet.qltk.x import ScrolledWindow, Alignment
from quodlibet.util.collection import Album
from quodlibet.util.library import background_filter
from quodlibet.util.thumbnails import scale


EMPTY = _("Songs not in an album")
ALBUM_PATTERN = r"""\<b\><album|\<i\><album>\</i\>|%s>\</b\><date| \<small\>(<date>)\</small\>>
\<small\><~discs|<~discs> - ><~tracks> - <~long-length>\</small\>""" % EMPTY

UNKNOWN_PATTERN = "<b><i>%s</i></b>" % _("Unknown %s")
MULTI_PATTERN = "<b><i>%s</i></b>" % _("Multiple %s Values")
COUNT_PATTERN = " <span size='small' color='#777'>(%s)</span>"

PAT = XMLFromPattern(ALBUM_PATTERN)
ALBUM_QUERIES = os.path.join(const.USERDIR, "lists", "album_queries")
util.mkdir(os.path.dirname(ALBUM_QUERIES))


def get_headers():
    result = []
    headers = config.get("browsers", "collection_headers", "")
    for h in headers.splitlines():
        values = h.split()
        if len(values) != 2:
            continue
        tag, merge = values
        try:
            result.append((tag, bool(int(merge))))
        except ValueError:
            continue
    return result


def save_headers(headers):
    headers = "\n".join(["%s %d" % (t, m) for (t, m) in headers])
    config.set("browsers", "collection_headers", headers)


class PatternEditor(gtk.HBox):

    PRESETS = [
            [("~people", False)],
            [("~year", False)],
            [("genre", False)],
            [("genre", False), ("artist", False)],
        ]

    COMPLETION = ["genre", "grouping", "~people", "artist", "album", "~year"]

    def __init__(self):
        super(PatternEditor, self).__init__(spacing=12)

        self.__headers = headers = {}
        buttons = []

        group = None
        for tags in self.PRESETS:
            tied = "~" + "~".join([t[0] for t in tags])
            group = gtk.RadioButton(group, "_" + util.tag(tied))
            headers[group] = tags
            buttons.append(group)

        group = gtk.RadioButton(group, _("_Custom"))
        self.__custom = group
        headers[group] = []
        buttons.append(group)

        button_box = gtk.HBox(spacing=6)
        self.__model = model = gtk.ListStore(str, bool)

        radio_box = gtk.VBox(spacing=6)
        for button in buttons:
            radio_box.pack_start(button, expand=False)
            button.connect('toggled', self.__toggled, button_box, model)

        self.pack_start(radio_box, expand=False)

        cb = TagsComboBoxEntry(self.COMPLETION)

        view = BaseView(model)
        view.set_reorderable(True)
        view.set_headers_visible(True)

        ctrl_box = gtk.VBox(spacing=6)

        add = gtk.Button(stock=gtk.STOCK_ADD)
        ctrl_box.pack_start(add, expand=False)
        add.connect('clicked', self.__add, model, cb)

        remove = gtk.Button(stock=gtk.STOCK_REMOVE)
        ctrl_box.pack_start(remove, expand=False)
        remove.connect('clicked', self.__remove, view)

        selection = view.get_selection()
        selection.connect('changed', self.__selection_changed, remove)
        selection.emit('changed')

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)

        edit_box = gtk.VBox(spacing=6)
        edit_box.pack_start(cb, expand=False)
        edit_box.pack_start(sw)

        button_box.pack_start(edit_box)
        button_box.pack_start(ctrl_box, expand=False)
        self.pack_start(button_box)

        render = gtk.CellRendererText()
        render.set_property("editable", True)

        def edited_cb(render, path, text, model):
            model[path][0] = text
        render.connect("edited", edited_cb, model)

        column = gtk.TreeViewColumn(_("Tag"), render, text=0)
        column.set_expand(True)
        view.append_column(column)

        toggle = gtk.CellRendererToggle()
        toggle.connect("toggled", self.__toggeled, model)
        toggle_column = gtk.TreeViewColumn(_("Merge"), toggle, active=1)
        view.append_column(toggle_column)

    def __toggeled(self, render, path, model):
        model[path][1] = not model[path][1]

    def __get_headers(self):
        for button in self.__headers.iterkeys():
            if button.get_active():
                if button == self.__custom:
                    model_headers = [(row[0], row[1]) for row in self.__model]
                    self.__headers[self.__custom] = model_headers
                return self.__headers[button]

    def __set_headers(self, new_headers):
        for button, headers in self.__headers.iteritems():
            if headers == new_headers:
                button.set_active(True)
                button.emit("toggled")
                break
        else:
            self.__headers[self.__custom] = new_headers
            self.__custom.set_active(True)

    headers = property(__get_headers, __set_headers)

    def __selection_changed(self, selection, remove):
        remove.set_sensitive(bool(selection.get_selected()[1]))

    def __add(self, button, model, cb):
        if cb.tag:
            model.append(row=[cb.tag, False])

    def __remove(self, button, view):
        view.remove_selection()

    def __toggled(self, button, edit_widget, model):
        tags = self.__headers[button]

        if tags:
            model.clear()
            for tag, merge in tags:
                model.append(row=[tag, merge])

        edit_widget.set_sensitive(
            button.get_active() and button is self.__custom)


class Preferences(qltk.UniqueWindow):
    def __init__(self, parent=None):
        if self.is_not_unique():
            return
        super(Preferences, self).__init__()

        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_default_size(350, 225)
        self.set_border_width(12)

        self.set_title(_("Album Collection Preferences") + " - Quod Libet")

        vbox = gtk.VBox(spacing=12)

        editor = PatternEditor()
        editor.headers = get_headers()

        apply = gtk.Button(stock=gtk.STOCK_APPLY)
        apply.connect_object("clicked", self.__apply, editor, False)

        cancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        cancel.connect("clicked", lambda x: self.destroy())

        ok = gtk.Button(stock=gtk.STOCK_OK)
        ok.connect_object("clicked", self.__apply, editor, True)

        box = gtk.HButtonBox()
        box.set_spacing(6)
        box.set_layout(gtk.BUTTONBOX_END)
        box.pack_start(apply)
        box.pack_start(cancel)
        box.pack_start(ok)

        vbox.pack_start(editor)
        vbox.pack_start(box, expand=False)

        self.add(vbox)

        ok.grab_focus()
        self.show_all()

    def __apply(self, editor, close):
        if editor.headers != get_headers():
            save_headers(editor.headers)
            CollectionBrowser.set_hierarchy()

        if close:
            self.destroy()


UnknownNode = object()
MultiNode = object()


def build_tree(tags, albums, cache=None):
    if not tags:
        return list(albums)
    tag, merge = tags[0]
    tree = {}
    cache = cache or {}
    for album in albums:
        cache_key = (album, tag)
        if cache_key not in cache:
            cache[cache_key] = album.list(tag)
        values = cache[cache_key]
        if merge and len(values) > 1:
            values = [MultiNode]
        for value in values or [UnknownNode]:
            tree.setdefault(value, []).append(album)
    for key, value in tree.iteritems():
        tree[key] = build_tree(tags[1:], value, cache)
    return tree


class StoreUtils(object):
    """TreeModelFilter can't be subclassed, otherwise this would be a mixin"""

    @staticmethod
    def get_path_for_album(self, album):
        """Returns the path for an album or None"""

        def func(model, path, iter_, result):
            if model[iter_][0] is album:
                result[0] = path
                return True
            return False

        res = [None]
        self.foreach(func, res)
        return res[0]

    @staticmethod
    def get_albums_for_path(self, path):
        return StoreUtils.get_albums_for_iter(self, self[path].iter)

    @staticmethod
    def get_albums_for_iter(self, iter_):
        row = self[iter_]

        if isinstance(row[0], Album):
            return set([row[0]])

        albums = set()
        for child in row.iterchildren():
            obj = child[0]
            if isinstance(obj, Album):
                albums.add(obj)
            else:
                albums.update(
                    StoreUtils.get_albums_for_iter(self, child.iter))
        return albums

    @staticmethod
    def get_markup(self, tags, iter_):
        obj = self[iter_][0]
        if isinstance(obj, Album):
            return PAT % obj

        if isinstance(obj, basestring):
            markup = util.escape(obj)
        else:
            tag = util.tag(tags[len(self.get_path(iter_)) - 1])
            if obj is UnknownNode:
                markup = UNKNOWN_PATTERN % util.escape(tag)
            else:
                markup = MULTI_PATTERN % util.escape(tag)

        num = len(StoreUtils.get_albums_for_iter(self, iter_))
        return markup + COUNT_PATTERN % num

    @staticmethod
    def get_album(self, iter_):
        obj = self[iter_][0]
        if isinstance(obj, Album):
            return obj


class CollectionTreeStore(gtk.TreeStore):
    def __init__(self):
        super(CollectionTreeStore, self).__init__(object)
        self.__tags = []

    def set_albums(self, tags, albums):
        self.clear()
        self.__tags = tags
        self.add_albums(albums)

    @property
    def tags(self):
        return [t[0] for t in self.__tags]

    def add_albums(self, albums):
        def _add(tree, iter_=None):
            # lowest level, add albums
            if isinstance(tree, list):
                for album in tree:
                    self.append(parent=iter_, row=[album])
                return

            # move into existing nodes and remove them from tree
            child = self.iter_children(iter_)
            while child:
                obj = self[child][0]
                if obj in tree:
                    _add(tree[obj], child)
                    del tree[obj]
                child = self.iter_next(child)

            # add missing ones
            for key, value in tree.iteritems():
                _add(value, self.append(parent=iter_, row=[key]))

        _add(build_tree(self.__tags, albums))

    def remove_albums(self, albums):
        # We can't get anything from the albums (they have no songs),
        # so we have to look through everything.

        def _remove_albums(albums, iter_=None):
            child = self.iter_children(iter_)
            while child:
                _remove_albums(albums, child)
                obj = self[child][0]
                if isinstance(obj, Album):
                    # remove albums
                    if obj in albums:
                        if not self.remove(child):
                            child = None
                        continue
                    else:
                        child = self.iter_next(child)
                else:
                    # clean up empty containers
                    if not self.iter_has_child(child):
                        if not self.remove(child):
                            child = None
                        continue
                    else:
                        child = self.iter_next(child)

        _remove_albums(set(albums))

    def change_albums(self, albums):
        def _check_albums(tree, iter_=None, not_found=None):
            if not_found is None:
                not_found = set()

            if isinstance(tree, list):
                # save nodes that are not there anymore
                child = self.iter_children(iter_)
                while child:
                    row = self[child]
                    try:
                        tree.remove(row[0])
                    except ValueError:
                        pass
                    else:
                        # it's still in the same position, trigger a redraw
                        self.row_changed(row.path, row.iter)
                    child = self.iter_next(child)
                not_found.update(tree)
                return not_found

            child = self.iter_children(iter_)
            while child:
                obj = self[child][0]
                if obj in tree:
                    _check_albums(tree[obj], child, not_found)
                    del tree[obj]
                child = self.iter_next(child)

            # everything left over changed
            def _get_all(sub, found=None):
                if found is None:
                    found = set()
                if isinstance(sub, list):
                    found.update(sub)
                    return found
                for v in sub.itervalues():
                    _get_all(v, found)
                return found
            not_found.update(_get_all(tree))

            return not_found

        not_found = _check_albums(build_tree(self.__tags, albums))
        self.remove_albums(not_found)
        self.add_albums(not_found)


class CollectionView(AllTreeView):
    def __init__(self, *args, **kwargs):
        super(CollectionView, self).__init__(*args, **kwargs)
        self.connect_after("row-expanded", self.__expand_helper)

    def __expand_helper(self, view, iter, path):
        model = view.get_model()
        children = list(model[path].iterchildren())
        if len(children) == 1:
            view.expand_row(children[0].path, False)

    def select_album(self, album, unselect=True):
        path = StoreUtils.get_path_for_album(self.get_model(), album)
        if path is not None:
            self.select_path(path, unselect)

    def select_path(self, path, unselect=True):
        for i, x in enumerate(path[:-1]):
            self.expand_row(path[:i + 1], False)
        self.scroll_to_cell(path, use_align=True, row_align=0.5)
        selection = self.get_selection()
        if unselect:
            selection.unselect_all()
            self.set_cursor(path)
        else:
            selection.select_path(path)

    def get_selected_albums(self):
        selection = self.get_selection()
        model, paths = selection.get_selected_rows()
        model = self.get_model()
        albums = set()
        for path in paths:
            albums.update(StoreUtils.get_albums_for_path(model, path))
        return albums


class CollectionBrowser(Browser, gtk.VBox, util.InstanceTracker):
    expand = qltk.RHPaned
    __gsignals__ = Browser.__gsignals__

    name = _("Album Collection")
    accelerated_name = _("Album _Collection")
    priority = 5

    __model = None

    @classmethod
    def _init_model(klass, library):
        klass.__model = model = CollectionTreeStore()
        klass.__albums = albums = library.albums

        albums.load()
        klass.__sigs = [
            albums.connect("added", klass._add_albums, model),
            albums.connect("removed", klass._remove_albums, model),
            albums.connect("changed", klass._change_albums, model),
        ]

        klass.set_hierarchy()

    @classmethod
    def _destroy_model(klass):
        for sig in klass.__sigs:
            klass.__albums.disconnect(sig)
        klass.__model = None
        del klass.__sigs

    def _refilter(self):
        if hasattr(self, "view"):
            self.view.get_model().refilter()

    @classmethod
    def set_hierarchy(klass):
        klass.__model.set_albums(get_headers(), klass.__albums.values())
        for inst in klass.instances():
            inst._refilter()

    @classmethod
    def _add_albums(klass, library, added, model):
        model.add_albums(added)

    @classmethod
    def _remove_albums(klass, library, removed, model):
        model.remove_albums(removed)

    @classmethod
    def _change_albums(klass, library, changed, model):
        model.change_albums(changed)

    def __init__(self, library, main):
        super(CollectionBrowser, self).__init__(spacing=6)
        self._register_instance()
        if self.__model is None:
            self._init_model(library)

        sw = ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.view = view = CollectionView()
        view.set_headers_visible(False)
        model_sort = gtk.TreeModelSort(self.__model)
        model_filter = model_sort.filter_new()
        self.__filter = None
        self.__bg_filter = background_filter()
        model_filter.set_visible_func(self.__parse_query)
        view.set_model(model_filter)

        def sort(model, i1, i2):
            t1, t2 = model[i1][0], model[i2][0]
            if t1 is None or t2 is None:
                # FIXME: why?
                return 0

            # FIXME: order this deterministically
            if t1 is MultiNode or t1 is UnknownNode or \
                    t2 is MultiNode or t2 is UnknownNode:
                return -cmp(t1, t2)

            if not isinstance(t1, Album):
                return cmp(util.human_sort_key(t1), util.human_sort_key(t2))

            a1, a2 = t1, t2
            return (cmp(a1.peoplesort and a1.peoplesort[0],
                        a2.peoplesort and a2.peoplesort[0]) or
                        cmp(a1.date or "ZZZZ", a2.date or "ZZZZ") or
                        cmp((a1.sort, a1.key), (a2.sort, a2.key)))

        model_sort.set_sort_func(0, sort)
        model_sort.set_sort_column_id(0, gtk.SORT_ASCENDING)

        column = gtk.TreeViewColumn("albums")

        def cell_data(column, cell, model, iter_):
            markup = StoreUtils.get_markup(model, self.__model.tags, iter_)
            cell.markup = markup
            cell.set_property('markup', markup)

        def cell_data_pb(column, cell, model, iter_):
            album = StoreUtils.get_album(model, iter_)
            if album is None:
                cell.set_property('stock_id', gtk.STOCK_DIRECTORY)
            else:
                album.scan_cover()
                if album.cover:
                    cell.set_property('pixbuf', scale(album.cover, (25, 25)))
                else:
                    cell.set_property('stock_id', gtk.STOCK_CDROM)

        imgrender = gtk.CellRendererPixbuf()
        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(imgrender, False)
        column.pack_start(render, True)
        column.set_cell_data_func(render, cell_data)
        column.set_cell_data_func(imgrender, cell_data_pb)
        view.append_column(column)

        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(view)

        hbox = gtk.HBox(spacing=6)

        prefs = gtk.Button()
        prefs.add(gtk.image_new_from_stock(
            gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        prefs.connect('clicked', Preferences)

        search = SearchBarBox(button=False, completion=AlbumTagCompletion(),
                              accel_group=self.accelerators)

        search.connect('query-changed', self.__update_filter)

        hbox.pack_start(search)
        hbox.pack_start(prefs, expand=False)

        if main:
            self.pack_start(Alignment(hbox, left=3, top=3), expand=False)
        else:
            self.pack_start(hbox, expand=False)

        self.pack_start(sw, expand=True)

        view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.__sig = view.get_selection().connect('changed',
            self.__selection_changed)
        view.connect('row-activated', self.__play, main)
        view.connect_object('popup-menu', self.__popup, view, library)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        view.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        view.connect("drag-data-get", self.__drag_data_get)

        self.connect("destroy", self.__destroy)

        self.show_all()

    def __parse_query(self, model, iter_):
        f, b = self.__filter, self.__bg_filter
        if f is None and b is None:
            return True

        def check_album(obj):
            if b is None:
                return f(obj)
            if f is None:
                return b(obj)
            return f(obj) and b(obj)

        obj = model[iter_][0]
        if isinstance(obj, Album):
            return check_album(obj)
        else:
            for album in StoreUtils.get_albums_for_iter(model, iter_):
                if check_album(album):
                    return True
            return False

    def __update_filter(self, entry, text):
        self.__filter = None
        if not Query.match_all(text):
            tags = self.__model.tags + ["album"]
            self.__filter = Query(text, star=tags).search
        self.__bg_filter = background_filter()

        self.view.get_model().refilter()

    def __destroy(self, browser):
        klass = type(browser)
        if not klass.instances():
            klass._destroy_model()

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        songs = self.__get_selected_songs()
        if tid == 1:
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
        else:
            sel.set_uris([song("~uri") for song in songs])

    def __popup(self, view, library):
        songs = self.__get_selected_songs(view.get_selection())
        menu = SongsMenu(library, songs, parent=self)
        menu.show_all()
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __play(self, view, path, col, main):
        model = view.get_model()
        if main and isinstance(model[path][0], Album):
            self.emit("activated")
        else:
            if view.row_expanded(path):
                view.collapse_row(path)
            else:
                view.expand_row(path, False)

    def __get_selected_songs(self, sort=True):
        albums = self.view.get_selected_albums()
        songs = []
        if sort:
            for album in albums:
                songs.extend(sorted(album.songs))
        else:
            for album in albums:
                songs.extend(album.songs)
        return songs

    def __selection_changed(self, selection):
        def idle_emit():
            songs = self.__get_selected_songs(False)
            if songs:
                self.emit('songs-selected', songs, None)
        gobject.idle_add(idle_emit)

    def can_filter_albums(self):
        return True

    def filter_albums(self, album_keys):
        albums = filter(None, [self.__albums.get(k) for k in album_keys])
        if albums:
            self.view.select_album(albums[0], unselect=True)
        for album in albums[1:]:
            self.view.select_album(album, unselect=False)

    def unfilter(self):
        model = self.view.get_model()
        root = model.get_iter_root()
        if root:
            self.view.set_cursor(model[root].path)

    def activate(self):
        self.view.get_selection().emit('changed')

    def restore(self):
        paths = config.get("browsers", "collection", "").split("\t")
        paths = [tuple(map(int, path.split())) for path in paths]
        if paths:
            if not paths[0]:
                return
            self.view.select_path(paths[0], unselect=True)
        for path in paths[1:]:
            self.view.select_path(path, unselect=False)

    def scroll(self, song):
        album = self.__albums.get(song.album_key)
        if album:
            self.view.select_album(album)

    def save(self):
        model, paths = self.view.get_selection().get_selected_rows()
        paths = "\t".join([" ".join(map(str, path)) for path in paths])
        config.set("browsers", "collection", paths)

browsers = [CollectionBrowser]
