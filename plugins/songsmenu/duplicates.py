#
#    Duplicates songs plugin.
#
#    Copyright (C) 2012, 2011 Nick Boultbee
#
#    Finds "duplicates" of songs selected by searching the library for
#    others with the same user-configurable "key", presenting a browser-like
#    dialog for further interaction with these.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of version 2 of the GNU General Public License as
#    published by the Free Software Foundation.
#

import string
import unicodedata

from gi.repository import Gtk, Pango

from quodlibet import app
from quodlibet import print_d, print_w, util, qltk
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.edittags import AudioFileGroup
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import RCMHintedTreeView


class DuplicateSongsView(RCMHintedTreeView):
    """Allows full tree-like functionality on top of underlying features"""

    def get_selected_songs(self):
        selection = self.get_selection()
        if selection is None:
            return []
        model, rows = selection.get_selected_rows()
        if not rows:
            return []
        selected = []
        for row in rows:
            row = model[row]
            if row.parent is None:
                for child in row.iterchildren():
                    selected.append(child[0])
            else:
                selected.append(row[0])
        return selected

    def Menu(self, library):
        songs = self.get_selected_songs()
        if not songs:
            return

        menu = SongsMenu(
            library, songs, delete=True, parent=self, plugins=False,
            devices=False, playlists=False)
        menu.show_all()
        return menu

    def __select_song(self, player, path, col):
        if len(path) == 1:
            if self.row_expanded(path):
                self.collapse_row(path)
            else:
                self.expand_row(path, False)
        else:
            songs = self.get_selected_songs()
            if songs and player.go_to(songs[0], True):
                player.paused = False
            else:
                print_w("Sorry, can't play song outside current list.")

    def _removed(self, library, songs):
        model = self.get_model()
        if not model:
            return
        for song in songs:
            row = model.find_row(song)
            if row:
                group_row = model.iter_parent(row.iter)
                print_d("Found parent group = %s" % group_row)
                model.remove(row.iter)
                num_kids = model.iter_n_children(group_row)
                if num_kids < Duplicates.MIN_GROUP_SIZE:
                    print_d("Removing group %s" % group_row)
                    model.remove(group_row)
            else:
                # print_w("Couldn't delete song %s" % song)
                pass

    def _added(self, library, songs):
        model = self.get_model()
        if not model:
            return
        for song in songs:
            key = Duplicates.get_key(song)
            model.add_to_existing_group(key, song)
            # TODO: handle creation of new groups based on songs that were
            #       in original list but not as a duplicate

    def _changed(self, library, songs):
        model = self.get_model()
        if not model:  # Keeps happening on next song - bug / race condition?
            return
        for song in songs:
            key = Duplicates.get_key(song)
            row = model.find_row(song)
            if row:
                print_d("Changed duplicated file \"%s\" (Row=%s)" %
                        (song("~artist~title"), row))
                parent = model.iter_parent(row.iter)
                old_key = model[parent][0]
                if old_key != key:
                    print_d("Key changed from \"%s\" -> \"%s\"" %
                            (old_key, key))
                    self._removed(library, [song])
                    self._added(library, [song])
                else:
                    # Still might be a displayable change
                    print_d("Calling model.row_changed(%s, %s)..." %
                            (row.path, row.iter))
                    model.row_changed(row.path, row.iter)
            else:
                model.add_to_existing_group(key, song)

    def __init__(self, model):
        super(DuplicateSongsView, self).__init__(model)
        self.connect_object('row-activated',
                            self.__select_song, app.player)
        # Selecting multiple is a nice feature it turns out.
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        # Handle signals propagated from the underlying library
        self.connected_library_sigs = []
        SIGNAL_MAP = {
            'removed': self._removed,
            'added': self._added,
            'changed': self._changed
        }
        for (sig, callback) in SIGNAL_MAP.items():
            print_d("Listening to library.%s signals" % sig)
            self.connected_library_sigs.append(
                app.library.connect(sig, callback))

        # And disconnect, or Bad Stuff happens.
        self.connect('destroy', self.on_destroy)

    def on_destroy(self, view):
        print_d("Disconnecting from library signals...")
        for sig in self.connected_library_sigs:
            app.library.disconnect(sig)


class DuplicatesTreeModel(Gtk.TreeStore):
    """A tree store to model duplicated song information"""

    # Define columns to display (and how, in lieu of using qltk.browsers)
    def i(x):
        return x
    TAG_MAP = [
        ("artist", i), ("title", i), ("album", i),
        ("~#length", lambda s: util.format_time(int(s))),
        ("~#filesize", lambda s: util.format_size(int(s))), ("~#bitrate", i),
        ("~filename", i)]
    # Now make a dict. This seems clunky.
    tag_functions = {}
    for t, f in TAG_MAP:
        tag_functions[t] = f

    @classmethod
    def group_value(cls, group, tag):
        """Gets a formatted aggregated value/dummy for a set of tag values"""
        try:
            group_val = group[tag].safenicestr()
        except KeyError:
            return ""
        else:
            try:
                group_val = cls.tag_functions[tag](group_val)
            except (ValueError, TypeError):
                pass
        return group_val.replace("\n", ", ")

    def find_row(self, song):
        """Returns the row in the model from song, or None"""
        for parent in self:
            for row in parent.iterchildren():
                if row[0] == song:
                    self.__iter = row.iter
                    self.sourced = True
                    return row
        return None

    def add_to_existing_group(self, key, song):
        """Tries to add a song to an existing group. Returns None if not able
        """
        #print_d("Trying to add %s to group \"%s\"" % (song("~filename"), key))
        for parent in self:
            if key == parent[0]:
                print_d("Found group", self)
                return self.append(parent.iter, self.__make_row(song))
            # TODO: update group
        return None

    @classmethod
    def __make_row(cls, song):
        """Construct GTK row for a song, with all columns"""
        return [song] + [util.escape(str(f(song.comma(tag)))) for
                         (tag, f) in cls.TAG_MAP]

    def add_group(self, key, songs):
        """Adds a new group, returning the row created"""
        group = AudioFileGroup(songs)
        # Add the group first.
        parent = self.append(None,
            [key] +
            [self.group_value(group, tag) for tag, f in self.TAG_MAP])

        for s in songs:
            self.append(parent, self.__make_row(s))

    def go_to(self, song, explicit=False):
        #print_d("Duplicates: told to go to %r" % song, context=self)
        self.__iter = None
        if isinstance(song, Gtk.TreeIter):
            self.__iter = song
            self.sourced = True
        elif not self.find_row(song):
            print_d("Failed to find song", context=self)
        return self.__iter

    def remove(self, itr):
        if self.__iter and self[itr].path == self[self.__iter].path:
            self.__iter = None
        super(DuplicatesTreeModel, self).remove(itr)

    def get(self):
        return [row[0] for row in self]

    @property
    def get_current(self):
        if self.__iter is None:
            return None
        elif self.is_empty():
            return None
        else:
            return self[self.__iter][0]

    @property
    def get_current_path(self):
        if self.__iter is None:
            return None
        elif self.is_empty():
            return None
        else:
            return self[self.__iter].path

    @property
    def get_current_iter(self):
        if self.__iter is None:
            return None
        elif self.is_empty():
            return None
        else:
            return self.__iter

    def is_empty(self):
        return not len(self)

    def __init__(self):
        super(DuplicatesTreeModel, self).__init__(
            object, str, str, str, str, str, str, str)


class DuplicateDialog(Gtk.Window):
    """Main dialog for browsing duplicate results"""

    def __quit(self, widget=None, response=None):
        if response == Gtk.ResponseType.OK or \
                response == Gtk.ResponseType.CLOSE:
            print_d("Exiting plugin on user request...", self)
        self.finished = True
        self.destroy()
        return

    def __songs_popup_menu(self, songlist):
        path, col = songlist.get_cursor()
        menu = songlist.Menu(app.library)
        if menu is not None:
            return songlist.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __init__(self, model):
        songs_text = ngettext("%d duplicate group", "%d duplicate groups",
                len(model)) % len(model)
        super(DuplicateDialog, self).__init__()
        self.set_destroy_with_parent(True)
        self.set_title("Quod Libet - %s (%s)" % (Duplicates.PLUGIN_NAME,
                                                 songs_text))
        self.finished = False
        self.set_default_size(960, 480)
        self.set_border_width(6)
        swin = Gtk.ScrolledWindow()
        swin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        swin.set_shadow_type(Gtk.ShadowType.IN)
        # Set up the browser view
        view = DuplicateSongsView(model)

        def cell_text(column, cell, model, iter_, index):
            text = model[iter_][index]
            cell.markup = text
            cell.set_property("markup", text)

        # Set up the columns
        for i, (tag, f) in enumerate(DuplicatesTreeModel.TAG_MAP):
            e = (Pango.EllipsizeMode.START if tag == '~filename'
                else Pango.EllipsizeMode.END)
            render = Gtk.CellRendererText()
            render.set_property("ellipsize", e)
            col = Gtk.TreeViewColumn(util.tag(tag), render)
            # Numeric columns are better smaller here.
            if tag.startswith("~#"):
                col.set_fixed_width(80)
                col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
            else:
                col.set_expand(True)
                col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            col.set_resizable(True)
            col.set_cell_data_func(render, cell_text, i + 1)
            view.append_column(col)

        view.connect('popup-menu', self.__songs_popup_menu)
        swin.add(view)
        # A basic information area
        hbox = Gtk.HBox(spacing=6)

        def expand_all(*args):
            model = view.get_model()
            for row in model:
                if view.row_expanded(row.path):
                    for row in model:
                        view.collapse_row(row.path)
                    break
            else:
                for row in model:
                    view.expand_row(row.path, False)

        expand = Gtk.Button(_("Collapse / Expand all"))
        expand.connect_object("clicked", expand_all, view)
        hbox.pack_start(expand, False, True, 0)

        label = Gtk.Label(label=_("Duplicate key expression is '%s'") %
                Duplicates.get_key_expression())
        hbox.pack_start(label, True, True, 0)
        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close.connect('clicked', self.__quit)
        hbox.pack_start(close, False, True, 0)

        vbox = Gtk.VBox(spacing=6)
        vbox.pack_start(swin, True, True, 0)
        vbox.pack_start(hbox, False, True, 0)
        self.add(vbox)
        self.show_all()


class Duplicates(SongsMenuPlugin, PluginConfigMixin):
    PLUGIN_ID = 'Duplicates'
    PLUGIN_NAME = _('Duplicates Browser')
    PLUGIN_DESC = _('Find and browse similarly tagged versions of songs.')
    PLUGIN_ICON = Gtk.STOCK_MEDIA_PLAY
    PLUGIN_VERSION = "0.7"

    MIN_GROUP_SIZE = 2
    _CFG_KEY_KEY = "key_expression"
    __DEFAULT_KEY_VALUE = "~artist~title~version"

    _CFG_REMOVE_WHITESPACE = 'remove_whitespace'
    _CFG_REMOVE_DIACRITICS = 'remove_diacritics'
    _CFG_REMOVE_PUNCTUATION = 'remove_punctuation'
    _CFG_CASE_INSENSITIVE = 'case_insensitive'

    # Cached values
    key_expression = None
    __cfg_cache = {}

    # Faster than a speeding bullet
    __trans = string.maketrans("", "")

    @classmethod
    def get_key_expression(cls):
        if not cls.key_expression:
            cls.key_expression = (
                    cls.config_get(cls._CFG_KEY_KEY, cls.__DEFAULT_KEY_VALUE))
        return cls.key_expression

    @classmethod
    def PluginPreferences(cls, window):
        def key_changed(entry):
            #print_d("setting to %s" % entry.get_text().strip())
            cls.config_set(cls._CFG_KEY_KEY, entry.get_text().strip())

        vb = Gtk.VBox(spacing=10)
        vb.set_border_width(0)
        hbox = Gtk.HBox(spacing=6)
        # TODO: construct a decent validator and use ValidatingEntry
        e = UndoEntry()
        e.set_text(cls.get_key_expression())
        e.connect("changed", key_changed)
        e.set_tooltip_markup("Accepts QL tag expressions like "
                "<tt>~artist~title</tt> or <tt>musicbrainz_track_id</tt>")
        lbl = Gtk.Label(label=_("_Group duplicates by:"))
        lbl.set_mnemonic_widget(e)
        lbl.set_use_underline(True)
        hbox.pack_start(lbl, False, True, 0)
        hbox.pack_start(e, False, True, 0)
        frame = qltk.Frame(label=_("Duplicate Key"), child=hbox)
        vb.pack_start(frame, True, True, 0)

        # Matching Option
        toggles = [
            (cls._CFG_REMOVE_WHITESPACE, _("Remove _Whitespace")),
            (cls._CFG_REMOVE_DIACRITICS, _("Remove _Diacritics")),
            (cls._CFG_REMOVE_PUNCTUATION, _("Remove _Punctuation")),
            (cls._CFG_CASE_INSENSITIVE, _("Case _Insensitive")),
        ]
        vb2 = Gtk.VBox(spacing=6)
        for key, label in toggles:
            ccb = ConfigCheckButton(label, 'plugins', cls._config_key(key))
            ccb.set_active(cls.config_get_bool(key))
            vb2.pack_start(ccb, True, True, 0)

        frame = qltk.Frame(label=_("Matching options"), child=vb2)
        vb.pack_start(frame, False, True, 0)

        vb.show_all()
        return vb

    @staticmethod
    def remove_accents(s):
        return filter(lambda c: not unicodedata.combining(c),
                      unicodedata.normalize('NFKD', unicode(s)))

    @classmethod
    def get_key(cls, song):
        key = song(cls.get_key_expression())
        if cls.config_get_bool(cls._CFG_REMOVE_DIACRITICS):
            key = cls.remove_accents(key)
        if cls.config_get_bool(cls._CFG_CASE_INSENSITIVE):
            key = key.lower()
        if cls.config_get_bool(cls._CFG_REMOVE_PUNCTUATION):
            key = str(key).translate(cls.__trans, string.punctuation)
        if cls.config_get_bool(cls._CFG_REMOVE_WHITESPACE):
            key = "_".join(key.split())
        return key

    def plugin_songs(self, songs):
        model = DuplicatesTreeModel()
        self.__cfg_cache = {}

        # Index all songs by our custom key
        # TODO: make this cache-friendly
        print_d("Calculating duplicates...", self)
        groups = {}
        for song in songs:
            key = self.get_key(song)
            if key and key in groups:
                groups[key].add(song._song)
            elif key:
                groups[key] = set([song._song])

        for song in app.library:
            key = self.get_key(song)
            if key in groups:
                groups[key].add(song)

        # Now display the grouped duplicates
        for (key, children) in groups.items():
            if len(children) < self.MIN_GROUP_SIZE:
                continue
            # The parent (group) label
            model.add_group(key, children)

        dialog = DuplicateDialog(model)
        dialog.show()
