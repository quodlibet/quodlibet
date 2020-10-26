# Copyright 2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import quodlibet

try:
    from soco import SoCo, SoCoException
    from soco.data_structures import (DidlMusicTrack, DidlPlaylistContainer,
                                      DidlItem)
except ImportError:
    raise quodlibet.plugins.MissingModulePluginException("soco")

from typing import Text, Optional, Dict, Tuple, Collection
from gi.repository import Gtk
from quodlibet import _
from quodlibet import app
from quodlibet import qltk
from quodlibet.formats import AudioFile
from quodlibet.plugins.playlist import PlaylistPlugin
from quodlibet.qltk import Icons, Dialog
from quodlibet.qltk.notif import Task
from quodlibet.util import copool
from quodlibet.util.dprint import print_d, print_w
from quodlibet.util.string.filter import remove_punctuation

try:
    import soco
except ImportError:
    raise quodlibet.plugins.MissingModulePluginException("soco")

PlaylistID = Text
ID = Text
Name = Text
SonosPlaylistDict = Dict[PlaylistID, Name]


class ComboBoxEntry(Gtk.ComboBox):
    def __init__(self, choices: Dict[Text, Text], tooltip_markup=None):
        super().__init__(
            model=Gtk.ListStore(str, str),
            entry_text_column=1,
            has_entry=True)
        self._fill_model(choices)
        if tooltip_markup:
            self.get_child().set_tooltip_markup(tooltip_markup)

    def _fill_model(self, choices: Dict[Text, Text]):
        self.clear()
        render = Gtk.CellRendererText()
        self.pack_start(render, True)
        self.add_attribute(render, 'text', 1)

        model = self.get_model()
        for id_, name in choices.items():
            model.append(row=[id_, name])
        self.set_model(model)

        comp = Gtk.EntryCompletion()
        comp.set_model(self.get_model())
        comp.set_text_column(1)
        self.get_child().set_completion(comp)

    def get_chosen(self) -> Tuple[Optional[ID], Name]:
        tree_iter = self.get_active_iter()
        if tree_iter is not None:
            model = self.get_model()
            id_, name = model[tree_iter][:2]
            return id_, name
        entry = self.get_child()
        return None, entry.get_text()

    def set_text(self, text: Text):
        model = self.get_model()
        for i, (id_, value) in enumerate(model):
            if value == text:
                self.set_active(i)
                print_d(f"Text matched existing playlist: {id_} ({value!r})")
                return

        return self.get_child().set_text(text)


class GetSonosPlaylistDialog(Dialog):

    def __init__(self, choices: SonosPlaylistDict):
        super().__init__(title="Which Sonos Playlist?", transient_for=None)
        self.options = choices

        self.set_border_width(6)
        self.set_resizable(True)
        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(_("OK"), Gtk.ResponseType.OK)
        self.vbox.set_spacing(6)
        self.set_default_response(Gtk.ResponseType.OK)

        box = Gtk.VBox(spacing=6)
        label = Gtk.Label(
            label=_("Type a new playlist name,\n"
                    "or choose an existing Sonos playlist to overwrite"))
        box.set_border_width(6)
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        box.pack_start(label, True, True, 0)

        self._combo = ComboBoxEntry(choices)
        box.pack_start(self._combo, False, False, 0)

        self.vbox.pack_start(box, True, True, 0)
        self.get_child().show_all()

    def run(self, text: Optional[Text] = None) \
            -> Optional[Tuple[Optional[Name], Text]]:
        self.show()
        if text:
            self._combo.set_text(text)
        self._combo.grab_focus()
        resp = super().run()
        try:
            return (self._combo.get_chosen() if resp == Gtk.ResponseType.OK
                    else None)
        finally:
            self.destroy()


class SonosPlaylistPlugin(PlaylistPlugin):
    PLUGIN_ID = "Export to Sonos Playlist"
    PLUGIN_NAME = _(u"Export to Sonos Playlist")
    PLUGIN_DESC = _("Exports a playlist to Sonos playlist, "
                    "provided both share a directory structure.")
    PLUGIN_ICON = Icons.NETWORK_WORKGROUP
    REQUIRES_ACTION = True

    DEBUG = False

    MAX_RESULTS_PER_SEARCH = 10
    """Request this many max results, for each search to then filter in code"""

    def __init__(self, playlists=None, library=None):
        super().__init__(playlists, library)
        self.__cancel = False
        self.device: Optional[SoCo] = None

    def __cancel_add(self):
        """Tell the copool to stop (adding songs)"""
        self.__cancel = True

    @classmethod
    def _score(cls, t: DidlMusicTrack, song: AudioFile) -> float:
        d = t.to_dict()
        try:
            person = song.list("~people")[0]
        except IndexError:
            person = None
        album = song("album")
        score = (int(remove_punctuation(t.title).lower()
                     == remove_punctuation(song("title")).lower())
                 + int(bool(person) and person in d.values())
                 + int(bool(album) and album in d.get("album", "")))
        if cls.DEBUG:
            print_d("%.1f for %s (%s)" % (score, t.title, d))
        return score

    def __add_songs(self, task: Task, songs: Collection[AudioFile],
                    spl: DidlPlaylistContainer):
        """Generator for copool to add songs to the temp playlist"""
        assert self.device
        task_total = float(len(songs))
        print_d("Adding %d song(s) to Sonos playlist. "
                "This might take a while..." % task_total)
        for i, song in enumerate(songs):
            if self.__cancel:
                print_d("Cancelled Sonos export")
                return
            lib = self.device.music_library

            # Exact title gets the best results it seems; some problems with ’
            search_term = song("title")
            assert search_term
            results = lib.get_tracks(search_term=search_term,
                                     max_items=self.MAX_RESULTS_PER_SEARCH)
            yield
            total = len(results)
            if total == 1:
                track = results[0]
            elif total > 1:
                desc = song("~~people~album~title")
                candidates = [(self._score(t, song), t) for t in results]
                in_order = sorted(candidates, reverse=True, key=lambda x: x[0])
                track = in_order[0][1]
                print_d(f"From {len(results)} choice(s) for {desc!r}, "
                        f"chose {self.uri_for(track)}")
            else:
                print_w("No results for \"%s\"" % search_term)
                track = None
            if track:
                try:
                    self.device.add_item_to_sonos_playlist(track, spl)
                except SoCoException as e:
                    print_w(f"Couldn't add {track} ({e}, skipping")
            task.update(float(i) / task_total)
            yield
        task.update((task_total - 2) / task_total)
        yield
        task.finish()
        print_d(f"Finished export to {spl.title!r}")

    @staticmethod
    def uri_for(track: DidlItem) -> Text:
        """More usable elsewhere (on Linux at least)"""
        return track.get_uri().replace("x-file-cifs", "smb")

    def plugin_playlist(self, playlist):
        # TODO - only get coordinator nodes, somehow
        self.device: SoCo = soco.discovery.any_soco()
        device = self.device
        if not device:
            qltk.ErrorMessage(
                app.window,
                _("Error finding Sonos device(s)"),
                _("Error finding Sonos. Please check settings")
            ).run()
        else:
            sonos_pls = device.get_sonos_playlists()
            pl_id_to_name = {pl.item_id: pl.title for pl in sonos_pls}
            print_d("Sonos playlists: %s" % pl_id_to_name)
            ret = GetSonosPlaylistDialog(pl_id_to_name).run(playlist.name)
            if ret:
                spl_id, name = ret
                if spl_id:
                    spl: DidlPlaylistContainer = next(s for s in sonos_pls
                                                      if s.item_id == spl_id)
                    print_w(f"Replacing existing Sonos playlist {spl!r}")
                    device.remove_sonos_playlist(spl)

                print_d(f"Creating new playlist {name!r}")
                spl = device.create_sonos_playlist(name)
                task = Task("Sonos", _("Export to Sonos playlist"),
                            stop=self.__cancel_add)
                copool.add(self.__add_songs, task, playlist.songs, spl,
                           funcid="sonos-playlist-save")
