#
#    Duplicates songs plugin.
#
#    Copyright (C) 2011 Nick Boultbee
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
from quodlibet.library import library
from quodlibet import config, player, print_d, print_w, util
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.edittags import AudioFileGroup
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import RCMTreeView
import ConfigParser
import gobject
import gtk
import pango


class DuplicateSongsView(RCMTreeView):
    """A modified RCMTreeView allowing full tree-like functionality"""

    def get_selected_songs(self):
        selection = self.get_selection()
        if selection is None: return []
        model, rows = selection.get_selected_rows()
        if not rows: return []
        selected =[]
        for row in rows:
            if model[row][0]: selected.append(model[row][0])
            else:
                # TODO: reflect child-selections in GUI
                for child in model[row].iterchildren():
                    #print_d("Child[0]=%s" % child[0], context=self)
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
        #print_d("Trying to play %s" % songs[0]("~artist~title"), context=self)
        if player.go_to(songs[0], True):
            player.paused = False
        else:
            print_w("Sorry, can't play song outside current list.")
            # This is evil. EVIL. But it half-works.
#            player.setup(self.get_model(), songs[0], 0)
#            if player.go_to(songs[0], True):
#                player.paused = False

    def __removed(self, library, songs):
        model = self.get_model()
        if model:
            for song in songs:
                row = model.find_row(song)
                if row: model.remove(row)
                else: print_w("Couldn't delete song %s" % song)
        else:
            print_d("Null model returned.", context=self)
            print_w("Couldn't delete songs %s" % songs)

    def __init__(self,  model):
        super(DuplicateSongsView, self).__init__(model)
        self.connect_object('row-activated',self.__select_song, player.playlist)
        # Selecting multiple is a nice feature it turns out.
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        # Handle removals propagated from the underlying library
        library.connect('removed', self.__removed)
        
        # TODO: work out if this is really needed
        def reset_activated(*args):
            self._activated = False
        s = player.playlist.connect_after('song-started', reset_activated)
        self.connect_object('destroy', player.playlist.disconnect, s)        


class DuplicatesTreeModel(gtk.TreeStore):
    """A tree store to model duplicated song information"""
    def find_row(self, song):
        for parent in self:
            for row in parent.iterchildren():
                #print_d("Is it: %r ? " % row[0], context=self)
                if row[0] == song:
                    self.__iter = row.iter
                    self.sourced = True
                    return row.iter
        return None

    def go_to(self, song, explicit=False):
        print_d("Duplicates: told to go to %r" % song, context=self)
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
            print_d("Exiting plugin on user request...")
        else:
            print_d("Ignoring GTK response %d!" % response, context=self)
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
        self.set_title("Quod Libet - %s (%s)" % (Duplicates.PLUGIN_NAME, songs_text))
        self.finished = False
        #self.connect('response', self.__quit)
        self.set_default_size(960, 480)
        self.set_border_width(6)
        swin = gtk.ScrolledWindow()
        swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        swin.set_shadow_type(gtk.SHADOW_IN)
        # Set up the browser view
        view = DuplicateSongsView(model)
        # Set up the columns
        for i, (tag,f) in enumerate(Duplicates.TAG_MAP):
            col = gtk.TreeViewColumn(util.tag(tag),
                gobject.new(gtk.CellRendererText,ellipsize=pango.ELLIPSIZE_END),
                markup=i+1)
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
    PLUGIN_VERSION = "0.3"

    MIN_GROUP_SIZE = 2
    _CFG_KEY_KEY = "key_expression"
    __DEFAULT_KEY_VALUE = "~artist~title"

    @classmethod
    def cfg_get(cls, name, default=None):
        try:
            key = __name__ + "_" + name
            return config.get("plugins", key)
        except (ValueError, ConfigParser.Error):
            print_w("Duplicate key config entry not found. Using '%s'" %
                    (default,))
            return default

    @classmethod
    def cfg_set(cls, name, value):
        key = __name__ + "_" + name
        config.set("plugins", key, value)

    @classmethod
    def get_key_expression(cls):
        return cls.cfg_get(cls._CFG_KEY_KEY, cls.__DEFAULT_KEY_VALUE)

    @classmethod
    def PluginPreferences(cls, window):
        def key_changed(entry):
            print_d("setting to %s" % entry.get_text().strip())
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
        vb.pack_start(hbox, expand=True)
        vb.show_all()
        return vb

    def i(x): return x

    # Define columns to display (and how, in lieu of using qltk.browsers)
    TAG_MAP = [
        ("artist",i), ("title",i), ("album",i),
        ("~#length",lambda s: util.format_time(int(s))),
        ("~#filesize",lambda s: util.format_size(int(s))), ("~#bitrate",i),
        ("~filename",i)]
    # Now make a dict. This seems clunky.
    tag_functions = {}
    for t,f in TAG_MAP: tag_functions[t] = f

    @staticmethod
    def group_value(group, tag):
        """Gets a formatted aggregated value/dummy for a set of tag values"""
        try:
            group_val = group[tag].safenicestr()
        except KeyError:
            return ""
        else:
            try:
                return Duplicates.tag_functions[tag](group_val)
            except (ValueError, TypeError), e: return group_val

    def plugin_songs(self, songs):
        self.key_expression = self.get_key_expression()
        model = DuplicatesTreeModel()

        # Index all songs by our custom key
        # TODO: make this cache-friendly
        print_d("Calculating duplicates...", context=self)
        groups = {}
        for song in songs:
            key = song(self.key_expression)
            if key and key in groups:
                groups[key].add(song._song)
            elif key: groups[key] = set([song._song])
        #print_d("Groups found based on '%s': %r" %
        #        (self.key_expression, groups.keys()))

        for song in library:
            key = song(self.key_expression)
            if key in groups:
                groups[key].add(song)

        # Now display the grouped duplicates
        for (key, children) in groups.items():
            if len(children) < self.MIN_GROUP_SIZE: continue
            group = AudioFileGroup(children)

            # The parent (group) label
            parent = model.append(None,
                [None] +
                [self.group_value(group, tag) for tag, f in Duplicates.TAG_MAP])
            for s in children:
                # Construct GTK row for each child, with all columns
                row = [s] + [util.escape(str(f(s(tag)))) for
                             (tag,f) in Duplicates.TAG_MAP]
                model.append(parent, row)

        dialog = DuplicateDialog(model)
        dialog.show()
