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
from gettext import ngettext
from quodlibet import config, player, print_d, print_w, util, qltk
from quodlibet.library import library
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.edittags import AudioFileGroup
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import RCMHintedTreeView
import ConfigParser
import gobject
import gtk
import pango
import string
import unicodedata
from quodlibet.qltk.ccb import ConfigCheckButton


class DuplicateSongsView(RCMHintedTreeView):
    """Allows full tree-like functionality on top of underlying features"""

    def get_selected_songs(self):
        selection = self.get_selection()
        if selection is None: return []
        model, rows = selection.get_selected_rows()
        if not rows: return []
        selected = []
        for row in rows:
            if model[row][0]: selected.append(model[row][0])
            else:
                # TODO: reflect child-selections in GUI
                for child in model[row].iterchildren():
                    selected.append(child[0])
        return selected

    def Menu(self, library):
        songs = self.get_selected_songs()
        if not songs: return

        menu = SongsMenu(
            library, songs, delete=True, parent=self, plugins=False,
            devices=False, playlists=False)
        menu.show_all()
        return menu

    def __select_song(self, player, indices, col):
        songs = self.get_selected_songs()
        #print_d("Trying to play %s" % songs[0]("~artist~title~version"), self)
        if player.go_to(songs[0], True):
            player.paused = False
        else:
            print_w("Sorry, can't play song outside current list.")
            # This is evil. EVIL. But it half-works.
#            player.setup(self.get_model(), songs[0], 0)
#            if player.go_to(songs[0], True):
#                player.paused = False

    def _removed(self, library, songs):
        model = self.get_model()
        if not model: return
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
        if not model: return
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
                            self.__select_song, player.playlist)
        # Selecting multiple is a nice feature it turns out.
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        # Handle signals propagated from the underlying library
        self.connected_library_sigs = []
        SIGNAL_MAP = {
            'removed': self._removed,
            'added': self._added,
            'changed': self._changed
        }
        for (sig, callback) in SIGNAL_MAP.items():
            print_d("Listening to library.%s signals" % sig)
            self.connected_library_sigs.append(library.connect(sig, callback))

        # And disconnect, or Bad Stuff happens.
        self.connect('destroy', self.on_destroy)


    def on_destroy(self, view):
        print_d("Disconnecting from library signals...")
        for sig in self.connected_library_sigs:
            library.disconnect(sig)


class DuplicatesTreeModel(gtk.TreeStore):
    """A tree store to model duplicated song information"""

    # Define columns to display (and how, in lieu of using qltk.browsers)
    def i(x): return x
    TAG_MAP = [
        ("artist", i), ("title", i), ("album", i),
        ("~#length", lambda s: util.format_time(int(s))),
        ("~#filesize", lambda s: util.format_size(int(s))), ("~#bitrate", i),
        ("~filename", i)]
    # Now make a dict. This seems clunky.
    tag_functions = {}
    for t, f in TAG_MAP: tag_functions[t] = f

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
            except (ValueError, TypeError), e:
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
        """Tries to add a song to an existing group. Returns None if not able"""
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
        if isinstance(song, gtk.TreeIter):
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
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self[self.__iter][0]

    @property
    def get_current_path(self):
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self[self.__iter].path

    @property
    def get_current_iter(self):
        if self.__iter is None: return None
        elif self.is_empty(): return None
        else: return self.__iter

    def is_empty(self):
        return not len(self)

    def __init__(self):
        super(DuplicatesTreeModel, self).__init__(
            object, str, str, str, str, str, str, str)


class DuplicateDialog(gtk.Window):
    """Main dialog for browsing duplicate results"""

    def __quit(self, widget=None, response=None):
        if response == gtk.RESPONSE_OK or response == gtk.RESPONSE_CLOSE:
            print_d("Exiting plugin on user request...", self)
        self.finished = True
        self.destroy()
        return

    def __songs_popup_menu(self, songlist):
        path, col = songlist.get_cursor()
        menu = songlist.Menu(library)
        if menu is not None:
            return songlist.popup_menu(menu, 0, gtk.get_current_event_time())

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
        swin = gtk.ScrolledWindow()
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        swin.set_shadow_type(gtk.SHADOW_IN)
        # Set up the browser view
        view = DuplicateSongsView(model)
        # Set up the columns
        for i, (tag, f) in enumerate(DuplicatesTreeModel.TAG_MAP):
            e = (pango.ELLIPSIZE_START if tag == '~filename'
                else pango.ELLIPSIZE_END)
            col = gtk.TreeViewColumn(util.tag(tag),
                gobject.new(gtk.CellRendererText, ellipsize=e),
                markup=i + 1)
            # Numeric columns are better smaller here.
            if tag.startswith("~#"):
                col.set_fixed_width(80)
                col.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            else:
                col.set_expand(True)
                col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
            col.set_resizable(True)
            view.append_column(col)

        view.connect('popup-menu', self.__songs_popup_menu)
        swin.add(view)
        # A basic information area
        hbox = gtk.HBox(spacing=6)
        label = gtk.Label(_("Duplicate key expression is '%s'") %
                Duplicates.get_key_expression())
        hbox.pack_start(label)
        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect('clicked', self.__quit)
        hbox.pack_start(close, expand=False)

        vbox = gtk.VBox(spacing=6)
        vbox.pack_start(swin)
        vbox.pack_start(hbox, expand=False)
        self.add(vbox)
        self.show_all()


class Duplicates(SongsMenuPlugin):
    PLUGIN_ID = 'Duplicates'
    PLUGIN_NAME = _('Duplicates Browser')
    PLUGIN_DESC = _('Find and browse similarly tagged versions of songs.')
    PLUGIN_ICON = gtk.STOCK_MEDIA_PLAY
    PLUGIN_VERSION = "0.6"

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
    def _cfg_key(cls, key):
        return "%s_%s" % (__name__, key)

    @classmethod
    def cfg_get(cls, name, default=None):
        try:
            key = cls._cfg_key(name)
            return config.get("plugins", key)
        except (ValueError, ConfigParser.Error):
            print_w("Duplicates config entry for '%s' not found."
                    "Defaulting to  '%s'" % (key, default))
            return default

    @classmethod
    def cfg_get_bool(cls, key, default=True):
        if key in cls.__cfg_cache: return bool(cls.__cfg_cache[key])
        try:
            key = cls._cfg_key(key)
            cls.__cfg_cache[key] = bool
            return bool(config.getboolean("plugins", key))
        except (ValueError, ConfigParser.Error, TypeError):
            print_w("Duplicates config entry for '%s' not found."
                    "Defaulting to  '%s'" % (key, default))
            return default


    @classmethod
    def cfg_set(cls, name, value):
        cls.key_expression = value
        key = cls._cfg_key(name)
        print_d("Setting %s to '%s'" % (key,value))
        config.set("plugins", key, value)

    @classmethod
    def get_key_expression(cls):
        if not cls.key_expression:
            cls.key_expression = (
                    cls.cfg_get(cls._CFG_KEY_KEY, cls.__DEFAULT_KEY_VALUE))
        return cls.key_expression

    @classmethod
    def PluginPreferences(cls, window):
        def key_changed(entry):
            #print_d("setting to %s" % entry.get_text().strip())
            cls.cfg_set(cls._CFG_KEY_KEY, entry.get_text().strip())

        vb = gtk.VBox(spacing=10)
        vb.set_border_width(0)
        hbox = gtk.HBox(spacing=6)
        # TODO: construct a decent validator and use ValidatingEntry
        e = UndoEntry()
        e.set_text(cls.get_key_expression())
        e.connect("changed", key_changed)
        e.set_tooltip_markup("Accepts QL tag expressions like "
                "<tt>~artist~title</tt> or <tt>musicbrainz_track_id</tt>")
        lbl = gtk.Label(_("_Group duplicates by:"))
        lbl.set_mnemonic_widget(e)
        lbl.set_use_underline(True)
        hbox.pack_start(lbl, expand=False)
        hbox.pack_start(e, expand=False)
        frame = qltk.Frame(label=_("Duplicate Key"), child=hbox)
        vb.pack_start(frame, expand=True)

        # Matching Option
        toggles = [
            (cls._CFG_REMOVE_WHITESPACE, _("Remove _Whitespace")),
            (cls._CFG_REMOVE_DIACRITICS, _("Remove _Diacritics")),
            (cls._CFG_REMOVE_PUNCTUATION, _("Remove _Punctuation")),
            (cls._CFG_CASE_INSENSITIVE, _("Case _Insensitive")),
        ]
        vb2=gtk.VBox(spacing=6)
        for key, label in toggles:
            ccb = ConfigCheckButton(label, 'plugins', cls._cfg_key(key))
            ccb.set_active(cls.cfg_get_bool(key))
            vb2.pack_start(ccb)

        frame = qltk.Frame(label=_("Matching options"), child=vb2)
        vb.pack_start(frame, expand=False)

        vb.show_all()
        return vb

    @staticmethod
    def remove_accents(s):
        return filter(lambda c: not unicodedata.combining(c),
                      unicodedata.normalize('NFKD', unicode(s)))

    @classmethod
    def get_key(cls, song):
        key = song(cls.get_key_expression())
        if cls.cfg_get_bool(cls._CFG_REMOVE_DIACRITICS):
            key = cls.remove_accents(key)
        if cls.cfg_get_bool(cls._CFG_CASE_INSENSITIVE):
            key = key.lower()
        if cls.cfg_get_bool(cls._CFG_REMOVE_PUNCTUATION):
            key = str(key).translate(cls.__trans, string.punctuation)
        if cls.cfg_get_bool(cls._CFG_REMOVE_WHITESPACE):
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

        for song in library:
            key = self.get_key(song)
            if key in groups:
                groups[key].add(song)

        # Now display the grouped duplicates
        for (key, children) in groups.items():
            if len(children) < self.MIN_GROUP_SIZE: continue

            # The parent (group) label
            model.add_group(key, children)

        dialog = DuplicateDialog(model)
        dialog.show()

