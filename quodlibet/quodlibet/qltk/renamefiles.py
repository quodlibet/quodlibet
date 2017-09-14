# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import unicodedata
import glob
import shutil

from gi.repository import Gtk, Gdk
from senf import fsn2text, text2fsn

import quodlibet
from quodlibet import qltk
from quodlibet import util
from quodlibet import config
from quodlibet import _

from quodlibet.plugins import PluginManager
from quodlibet.pattern import FileFromPattern
from quodlibet.pattern import ArbitraryExtensionFileFromPattern
from quodlibet.qltk._editutils import FilterPluginBox, FilterCheckButton
from quodlibet.qltk._editutils import EditingPluginHandler
from quodlibet.qltk.views import TreeViewColumn
from quodlibet.qltk.cbes import ComboBoxEntrySave
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk import Icons, Button
from quodlibet.qltk.wlw import WritingWindow
from quodlibet.util import connect_obj, gdecode
from quodlibet.util.path import strip_win32_incompat_from_path
from quodlibet.util.dprint import print_d
from quodlibet.compat import itervalues


NBP = os.path.join(quodlibet.get_user_dir(), "lists", "renamepatterns")
NBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber|<tracknumber>. ><title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
/path/<artist> - <album>/<tracknumber>. <title>
~/<artist>/<album>/<tracknumber> - <title>
<albumartist|<albumartist>|<artist>>/(<~year>) <album>\
/<tracknumber|<tracknumber> - ><title>"""


class SpacesToUnderscores(FilterCheckButton):
    _label = _("Replace spaces with _underscores")
    _section = "rename"
    _key = "spaces"
    _order = 1.0

    def filter(self, original, filename):
        return filename.replace(" ", "_")


class StripWindowsIncompat(FilterCheckButton):
    _label = _("Strip _Windows-incompatible characters")
    _section = "rename"
    _key = "windows"
    _order = 1.1

    def __init__(self):
        super(StripWindowsIncompat, self).__init__()
        # If on Windows, force this to be inactive (and hidden)
        if os.name == 'nt':
            self.set_active(False)
            self.set_sensitive(False)
            self.set_no_show_all(True)

    def filter(self, original, filename):
        return strip_win32_incompat_from_path(filename)


class StripDiacriticals(FilterCheckButton):
    _label = _("Strip _diacritical marks")
    _section = "rename"
    _key = "diacriticals"
    _order = 1.2

    def filter(self, original, filename):
        return u"".join(filter(lambda s: not unicodedata.combining(s),
                               unicodedata.normalize('NFKD', filename)))


class StripNonASCII(FilterCheckButton):
    _label = _("Strip non-_ASCII characters")
    _section = "rename"
    _key = "ascii"
    _order = 1.3

    def filter(self, original, filename):
        return u"".join(map(lambda s: (s <= "~" and s) or u"_", filename))


class Lowercase(FilterCheckButton):
    _label = _("Use only _lowercase characters")
    _section = "rename"
    _key = "lowercase"
    _order = 1.4

    def filter(self, original, filename):
        return filename.lower()


class RenameFilesPluginHandler(EditingPluginHandler):
    from quodlibet.plugins.editing import RenameFilesPlugin
    Kind = RenameFilesPlugin


class Entry(object):

    def __init__(self, song):
        self.song = song

    new_name = None
    """new name as unicode or None if not set"""

    @property
    def name(self):
        return fsn2text(self.song("~basename"))


class RenameFiles(Gtk.VBox):
    title = _("Rename Files")
    FILTERS = [SpacesToUnderscores, StripWindowsIncompat, StripDiacriticals,
               StripNonASCII, Lowercase]
    handler = RenameFilesPluginHandler()
    IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'bmp']

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.handler)

    def __init__(self, parent, library):
        super(RenameFiles, self).__init__(spacing=6)
        self.set_border_width(12)

        hbox = Gtk.HBox(spacing=6)
        cbes_defaults = NBP_EXAMPLES.split("\n")
        self.combo = ComboBoxEntrySave(NBP, cbes_defaults,
            title=_("Path Patterns"),
            edit_title=_(u"Edit saved patterns…"))
        self.combo.show_all()
        hbox.pack_start(self.combo, True, True, 0)
        self.preview = qltk.Button(_("_Preview"), Icons.VIEW_REFRESH)
        self.preview.show()
        hbox.pack_start(self.preview, False, True, 0)
        self.pack_start(hbox, False, True, 0)
        self.combo.get_child().connect('changed', self._changed)

        model = ObjectStore()
        self.view = Gtk.TreeView(model=model)
        self.view.show()

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.view)
        self.pack_start(sw, True, True, 0)

        self.pack_start(Gtk.VBox(), False, True, 0)

        filter_box = FilterPluginBox(self.handler, self.FILTERS)
        filter_box.connect("preview", self.__filter_preview)
        filter_box.connect("changed", self.__filter_changed)
        self.filter_box = filter_box
        self.pack_start(filter_box, False, True, 0)

        # move art
        moveart_box = Gtk.VBox()
        self.moveart = ConfigCheckButton(
             _('_Move album art'),
             "rename", "move_art", populate=True)
        self.moveart.set_tooltip_text(
             _("See '[albumart] filenames' config entry " +
               "for image search strings"))
        self.moveart.show()
        moveart_box.pack_start(self.move_art, False, True, 0)
        self.moveart_overwrite = ConfigCheckButton(
             _('_Overwrite album art at target'),
             "rename", "move_art_overwrite", populate=True)
        self.moveart_overwrite.show()
        moveart_box.pack_start(self.moveart_overwrite, False, True, 0)
        self.pack_start(moveart_box, False, True, 0)

        # remove empty
        removeemptydirs_box = Gtk.VBox()
        self.removeemptydirs = ConfigCheckButton(
             _('_Remove empty directories'),
             "rename", "remove_empty_dirs", populate=True)
        self.removeemptydirs.show()
        removeemptydirs_box.pack_start(self.removeemptydirs, False, True, 0)
        self.pack_start(removeemptydirs_box, False, True, 0)

        # Save button
        self.save = Button(_("_Save"), Icons.DOCUMENT_SAVE)
        self.save.show()
        bbox = Gtk.HButtonBox()
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.pack_start(self.save, True, True, 0)
        self.pack_start(bbox, False, True, 0)

        render = Gtk.CellRendererText()
        column = TreeViewColumn(title=_('File'))
        column.pack_start(render, True)

        def cell_data_file(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("text", entry.name)

        column.set_cell_data_func(render, cell_data_file)

        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.view.append_column(column)

        render = Gtk.CellRendererText()
        render.set_property('editable', True)
        column = TreeViewColumn(title=_('New Name'))
        column.pack_start(render, True)

        def cell_data_new_name(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("text", entry.new_name or u"")
        column.set_cell_data_func(render, cell_data_new_name)

        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.view.append_column(column)

        connect_obj(self.preview, 'clicked', self.__preview, None)

        connect_obj(parent, 'changed', self.__class__.__preview, self)
        connect_obj(self.save, 'clicked', self.__rename, library)

        render.connect('edited', self.__row_edited)

        for child in self.get_children():
            child.show()

    def __filter_preview(self, *args):
        Gtk.Button.clicked(self.preview)

    def __filter_changed(self, *args):
        self._changed(self.combo.get_child())

    def _changed(self, entry):
        self.save.set_sensitive(False)
        self.preview.set_sensitive(bool(entry.get_text()))

    def __row_edited(self, renderer, path, new):
        path = Gtk.TreePath.new_from_string(path)
        model = self.view.get_model()
        entry = model[path][0]
        new = gdecode(new)
        if entry.new_name != new:
            entry.new_name = new
            self.preview.set_sensitive(True)
            self.save.set_sensitive(True)
            model.path_changed(path)

    def __rename(self, library):
        model = self.view.get_model()
        win = WritingWindow(self, len(model))
        win.show()
        was_changed = set()
        skip_all = False
        self.view.freeze_child_notify()
        should_move_art = config.getboolean("rename", "move_art")
        moveart_sets = {}
        remove_empty_dirs = config.getboolean("rename", "remove_empty_dirs")

        for entry in itervalues(model):
            if entry.new_name is None:
                continue
            song = entry.song
            old_name = entry.name
            old_pathfile = song['~filename']
            new_name = entry.new_name
            new_pathfile = ""
            # ensure target is a full path
            if os.path.abspath(new_name) != \
                   os.path.abspath(os.path.join(os.getcwd(), new_name)):
                new_pathfile = new_name
            else:
                # must be a relative pattern, so prefix the path
                new_pathfile = \
                    os.path.join(os.path.dirname(old_pathfile), new_name)

            try:
                library.rename(song, text2fsn(new_name), changed=was_changed)
            except Exception:
                util.print_exc()
                if skip_all:
                    continue
                RESPONSE_SKIP_ALL = 1
                msg = qltk.Message(
                    Gtk.MessageType.ERROR, win, _("Unable to rename file"),
                    _("Renaming <b>%(old-name)s</b> to <b>%(new-name)s</b> "
                      "failed. Possibly the target file already exists, "
                      "or you do not have permission to make the "
                      "new file or remove the old one.") % {
                        "old-name": util.escape(old_name),
                        "new-name": util.escape(new_name),
                      },
                    buttons=Gtk.ButtonsType.NONE)
                msg.add_button(_("Ignore _All Errors"), RESPONSE_SKIP_ALL)
                msg.add_icon_button(_("_Stop"), Icons.PROCESS_STOP,
                                    Gtk.ResponseType.CANCEL)
                msg.add_button(_("_Continue"), Gtk.ResponseType.OK)
                msg.set_default_response(Gtk.ResponseType.OK)
                resp = msg.run()
                skip_all |= (resp == RESPONSE_SKIP_ALL)
                # Preserve old behavior: shift-click is Ignore All
                mods = Gdk.Display.get_default().get_pointer()[3]
                skip_all |= mods & Gdk.ModifierType.SHIFT_MASK
                library.reload(song, changed=was_changed)
                if resp != Gtk.ResponseType.OK and resp != RESPONSE_SKIP_ALL:
                    break

            if should_move_art:
                self.__moveart(moveart_sets, old_pathfile, new_pathfile, song)

            if remove_empty_dirs:
                path_old = os.path.dirname(old_pathfile)
                if not os.listdir(path_old):
                    try:
                        os.rmdir(path_old)
                        print_d("Removed empty directory: %r" % path_old, self)
                    except Exception:
                        util.print_exc()

            if win.step():
                break

        self.view.thaw_child_notify()
        win.destroy()
        library.changed(was_changed)
        self.save.set_sensitive(False)

    def __moveart(self, art_sets, pathfile_old, pathfile_new, song):

        path_old = os.path.dirname(os.path.realpath(pathfile_old))
        path_new = os.path.dirname(os.path.realpath(pathfile_new))
        if os.path.samefile(path_old, path_new):
            return
        if (path_old in art_sets.keys() and len(art_sets[path_old]) == 0):
            return

        # get art set for path
        images = []
        if path_old in art_sets.keys():
            images = art_sets[path_old]
        else:
            def glob_escape(s):
                for c in ['[', '*', '?']:
                    s = s.replace(c, '[' + c + ']')
                return s

            # generate art set for path
            art_sets[path_old] = images
            path_old_escaped = glob_escape(path_old)
            for suffix in self.IMAGE_EXTENSIONS:
                images.extend(glob.glob(os.path.join(path_old_escaped,
                                                     "*." + suffix)))
        if len(images) > 0:
            # set not empty yet, (re)process
            filenames = config.getstringlist("albumart", "search_filenames")
            moves = []
            for fn in filenames:
                fn = os.path.join(path_old, fn)
                if "<" in fn:
                    # resolve path
                    fnres = ArbitraryExtensionFileFromPattern(fn).format(song)
                    if fnres in images and fnres not in moves:
                        moves.append(fnres)
                elif "*" in fn:
                    moves.extend(f for f in glob.glob(fn)
                                     if f in images and f not in moves)
                elif fn in images and fn not in moves:
                    moves.append(fn)
            if len(moves) > 0:
                overwrite = config.getboolean("rename", "move_art_overwrite")
                for fnmove in moves:
                    try:
                        # existing files safeguarded until move successful,
                        # then deleted if overwrite set
                        fnmoveto = os.path.join(path_new,
                                                os.path.split(fnmove)[1])
                        fnmoveto_orig = ""
                        if os.path.exists(fnmoveto):
                            fnmoveto_orig = fnmoveto + ".orig"
                            if not os.path.exists(fnmoveto_orig):
                                os.rename(fnmoveto, fnmoveto_orig)
                            else:
                                suffix = 1
                                while os.path.exists(fnmoveto_orig +
                                                     "." + str(suffix)):
                                    suffix += 1
                                fnmoveto_orig = (fnmoveto_orig +
                                                 "." + str(suffix))
                                os.rename(fnmoveto, fnmoveto_orig)
                        print_d("Renaming image %r to %r" %
                                   (fnmove, fnmoveto), self)
                        shutil.move(fnmove, fnmoveto)
                        if overwrite and fnmoveto_orig:
                            os.remove(fnmoveto_orig)
                        images.remove(fnmove)
                    except Exception:
                        util.print_exc()

    def __preview(self, songs):
        model = self.view.get_model()
        if songs is None:
            songs = [e.song for e in itervalues(model)]

        pattern_text = gdecode(self.combo.get_child().get_text())

        try:
            pattern = FileFromPattern(pattern_text)
        except ValueError:
            qltk.ErrorMessage(
                self, _("Path is not absolute"),
                _("The pattern\n\t<b>%s</b>\ncontains / but "
                  "does not start from root. To avoid misnamed "
                  "folders, root your pattern by starting "
                  "it with / or ~/.") % (
                util.escape(pattern_text))).run()
            return
        else:
            if pattern:
                self.combo.prepend_text(pattern_text)
                self.combo.write(NBP)

        # native paths
        orignames = [song["~filename"] for song in songs]
        newnames = [fsn2text(pattern.format(song)) for song in songs]
        for f in self.filter_box.filters:
            if f.active:
                newnames = f.filter_list(orignames, newnames)

        model.clear()
        for song, newname in zip(songs, newnames):
            entry = Entry(song)
            entry.new_name = newname
            model.append(row=[entry])

        self.preview.set_sensitive(False)
        self.save.set_sensitive(bool(pattern_text))
        for song in songs:
            if not song.is_file:
                self.set_sensitive(False)
                break
        else:
            self.set_sensitive(True)
