# Copyright 2021 Joschua Gandert
#           2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import os.path
import json
import uuid
from pathlib import Path

from gi.repository import Gtk

from senf import path2fsn

from typing import NamedTuple, Any
from collections.abc import Callable, MutableMapping

from quodlibet.plugins import PluginConfig, BoolConfProp, FloatConfProp
from quodlibet.qltk.matchdialog import ColumnSpec, MatchListsDialog
from quodlibet.qltk.showfiles import show_files

from quodlibet.util.matcher import ObjectListMatcher

from quodlibet.formats._audio import MIGRATE, AudioFile

from quodlibet.util import connect_obj, print_exc

import quodlibet
from quodlibet.util.path import (join_path_with_escaped_name_of_legal_length,
                                 stem_of_file_name, extension_of_file_name)

from quodlibet.util.songwrapper import SongWrapper, check_wrapper_changed

from quodlibet import _, app, print_e, qltk, util, print_d

from quodlibet.plugins.songshelpers import each_song, is_writable, is_finite
from quodlibet.qltk.msg import ErrorMessage, WarningMessage
from quodlibet.qltk import Icons, SeparatorMenuItem
from quodlibet.plugins.songsmenu import SongsMenuPlugin

__all__ = ["ImportExportTagsAndTrackUserDataPlugin"]

_PLUGIN_ID = "ImportExportTagsAndTrackUserData"

# We use this instead of ~playlists, since we want to store playlists in a list
PLAYLISTS_KEY = "//playlists"
IDENTIFIER_KEY = "//identifier"
FILE_STEM_KEY = "//file_stem"

USER_DATA_KEYS = " ".join(MIGRATE | {PLAYLISTS_KEY})

# Could be made configurable in the future, but these likely suffice
# "tag1 tag2" will result in only tag1 and tag2 being exported
# * means all tags (so tags like 'title' and internal (user data) "tags" like ~#added)
# * tag1 tag2 means all except tag1 and tag2
EXPORT_OPTIONS = [(_("Export User Data"), USER_DATA_KEYS),
                  (_("Export Tags"), f"* {USER_DATA_KEYS} {FILE_STEM_KEY}"),
                  (_("Export Tags and User Data"), f"* {FILE_STEM_KEY}"),
                  (_("Export File Stems and User Data"), f"{USER_DATA_KEYS} "
                                                         f"{FILE_STEM_KEY}"),
                  (_("Export File Stems and Tags"), f"* {USER_DATA_KEYS}"),
                  (_("Export File Stems, Tags and User Data"), "*")]

EXPORT_DIR_PATH = Path(quodlibet.get_cache_dir(), "tags_and_track_user_data")
os.makedirs(EXPORT_DIR_PATH, exist_ok=True)

EXPORT_EXTENSION = "json"
TAGS_AND_USERDATA_INDEX_FILE_PATH = EXPORT_DIR_PATH / f"index.{EXPORT_EXTENSION}"


def move_export_to_used(export_path: Path):
    used_path = EXPORT_DIR_PATH / "used"
    used_path.mkdir(exist_ok=True)

    export_path.rename(used_path / export_path.name)


class AlbumId(NamedTuple):
    id_value: str
    title: str
    artist: str
    discs: int
    tracks: int
    last_directory_parts: str

    @classmethod
    def of_song(cls, s: SongWrapper):
        # We're using the last two parts, since sometimes albums have disc folders
        # below the folder that's named after the album
        parts = s("~dirname").rsplit(os.path.sep, maxsplit=2)[-2:]

        return AlbumId(s.album_key[0], s("albumsort", "") or s("album"),
                       s("albumartistsort", "") or s("albumartist") or s("artist"),
                       s("~#discs", 1), s("~#tracks", 1), os.path.join(*parts))


class TrackId(NamedTuple):
    """
    A TrackId is class that's used to identify and match tracks. In theory, almost
    all metadata could be useful for that, but some things are far more relevant than
    others (title vs bpm), and for performance reasons we have to limit it anyway.
    """
    artist: str
    title: str
    disc: int
    discs: int
    track: int
    tracks: int
    file_name: str

    @classmethod
    def of_song(cls, s: SongWrapper | AudioFile):
        return TrackId(s("artist"), s("title"), s("~#disc", 1), s("~#discs", 1),
                       s("~#track", 1), s("~#tracks", 1), s("~basename"))

    @property
    def file_stem(self):
        return os.path.splitext(self.file_name)[0]

    @property
    def track_text(self):
        if self.tracks <= 1:
            return str(self.track)
        return f"{self.track}/{self.tracks}"

    @property
    def disc_text(self):
        if self.discs <= 1:
            return str(self.disc)
        return f"{self.disc}/{self.discs}"


class Config:
    _config = PluginConfig(_PLUGIN_ID)

    need_user_check_if_number_of_albums_differs = BoolConfProp(
        _config, "need_user_check_if_number_of_albums_differs", True)

    need_user_check_if_number_of_tracks_differs = BoolConfProp(
        _config, "need_user_check_if_number_of_tracks_differs", True)

    max_track_similarity_to_need_user_check = FloatConfProp(
        _config, "max_track_similarity_to_need_user_check", 0.76)

    max_album_similarity_to_need_user_check = FloatConfProp(
        _config, "max_album_similarity_to_need_user_check", 0.80)

    delete_exports_after_importing = BoolConfProp(
        _config, "delete_exports_after_importing", True)

    pretty_print_json = BoolConfProp(_config, "pretty_print_json", False)


CONFIG = Config()


class ImportExportTagsAndTrackUserDataPlugin(SongsMenuPlugin):
    PLUGIN_ID = _PLUGIN_ID
    PLUGIN_NAME = _("Import / Export")
    PLUGIN_DESC = _("Imports and exports tags and track user data.")
    PLUGIN_ICON = Icons.EDIT_COPY

    plugin_handles = each_song(is_finite)

    _album_id_to_export_path: MutableMapping[AlbumId, Path]

    def PluginPreferences(self, *args):
        vbox = Gtk.VBox(spacing=6)

        def asd_toggled(button, *args):
            CONFIG.need_user_check_if_number_of_albums_differs = button.get_active()

        def tsd_toggled(button, *args):
            CONFIG.need_user_check_if_number_of_tracks_differs = button.get_active()

        def de_toggled(button, *args):
            CONFIG.delete_exports_after_importing = button.get_active()

        def pp_toggled(button, *args):
            CONFIG.pretty_print_json = button.get_active()

        def mt_scale_changed(scale):
            CONFIG.max_track_similarity_to_need_user_check = scale.get_value()

        def ma_scale_changed(scale):
            CONFIG.max_album_similarity_to_need_user_check = scale.get_value()

        info_box = Gtk.VBox(spacing=6)
        info_frame = qltk.Frame(_("Further information"), child=info_box)
        vbox.pack_start(info_frame, False, True, 0)

        meta_markup = util.monospace(", ".join(MIGRATE))
        info_text = _("The term 'track user data' includes the playlists in which the "
                      "selected tracks are and the following metadata:\n\n%s\n"
                      "\nBe aware that whatever you chose to export will be imported. "
                      "If you exported the file stems (file names without extension), "
                      "then, on import, the selected files will be renamed.\n\nAfter "
                      "exporting an album you can import the data into another version "
                      "of the album. Order and number of tracks can be different. "
                      "The plugin matches the exported data to the new tracks, even if "
                      "the names of the tracks are slightly different. The automatic "
                      "matching is not always correct, so it is better to not reduce "
                      "the following similarity values too much.") % meta_markup

        info_lbl = Gtk.Label(label=info_text, use_markup=True, wrap=True)
        info_box.pack_start(info_lbl, True, True, 0)

        manual_box = Gtk.VBox(spacing=6)
        manual_frame = qltk.Frame(_("User interaction on import"), child=manual_box)
        vbox.pack_start(manual_frame, False, True, 0)

        tsd = Gtk.CheckButton(
            label=_("Require confirmation if number of tracks differs"))
        tsd.set_active(CONFIG.need_user_check_if_number_of_tracks_differs)
        tsd.connect("toggled", tsd_toggled)
        manual_box.pack_start(tsd, True, True, 0)

        asd = Gtk.CheckButton(
            label=_("Require confirmation if number of albums differs"))
        asd.set_active(CONFIG.need_user_check_if_number_of_albums_differs)
        asd.connect("toggled", asd_toggled)
        manual_box.pack_start(asd, True, True, 0)

        desc = _("Percentage below which the user will have to manually check and "
                 "optionally change which track is matched with which.")

        perc_table = Gtk.Table(n_rows=2, n_columns=2)
        perc_table.set_col_spacings(6)
        perc_table.set_row_spacings(6)
        manual_box.pack_start(perc_table, True, True, 0)

        def format_perc(scale, value):
            return _("%d %%") % (value * 100)

        def add_perc_scale_with_label(ratio, col, lbl_text, tooltip_text, on_change):
            scale = Gtk.HScale(adjustment=Gtk.Adjustment.new(0, 0, 1, 0.01, 0.01, 0))
            scale.set_digits(2)
            scale.set_tooltip_text(tooltip_text)
            scale.set_value_pos(Gtk.PositionType.RIGHT)
            scale.set_value(ratio)
            scale.connect("format-value", format_perc)
            scale.connect("value-changed", on_change)

            label = Gtk.Label(label=lbl_text)
            label.set_alignment(0.0, 0.5)
            label.set_padding(0, 6)
            label.set_mnemonic_widget(scale)

            xoptions = Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK
            perc_table.attach(label, 0, 1, col, col + 1, xoptions=xoptions)
            perc_table.attach(scale, 1, 2, col, col + 1)

        add_perc_scale_with_label(CONFIG.max_track_similarity_to_need_user_check, 0,
                                  _("Track similarity:"), desc, mt_scale_changed)

        add_perc_scale_with_label(CONFIG.max_album_similarity_to_need_user_check, 1,
                                  _("Album similarity:"), desc, ma_scale_changed)

        export_box = Gtk.VBox(spacing=6)
        export_frame = qltk.Frame(_("Export files"), child=export_box)
        vbox.pack_start(export_frame, False, True, 0)

        pp = Gtk.CheckButton(label=_("Write pretty and clear JSON (slower)"))
        pp.set_active(CONFIG.pretty_print_json)
        pp.connect("toggled", pp_toggled)
        export_box.pack_start(pp, True, True, 0)

        de = Gtk.CheckButton(label=_("Delete export files after they've been imported"))
        de.set_active(CONFIG.delete_exports_after_importing)
        de.connect("toggled", de_toggled)
        export_box.pack_start(de, True, True, 0)

        return vbox

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._export_collectors = []
        self._import_or_export_option_index = None

        self._album_id_matcher: ObjectListMatcher[AlbumId] = ObjectListMatcher({  #
            lambda a: a.title: 9,  # title is the most reliable
            lambda a: a.artist: 4.5,  #
            lambda a: a.tracks: 1.2,  #
            lambda a: a.last_directory_parts: 1,  # needed in case the album has no tags
            lambda a: a.discs: 0.8,  # multi disc albums sometimes become single disc
            lambda a: a.id_value: 0.5,  # is likely to change unless exact same album
        })
        # We want check similarity afterwards, so it needs be as accurate as possible
        self._album_id_matcher.should_store_similarity_matrix = True
        self._album_id_matcher.should_go_through_every_attribute = True

        self._track_id_matcher: ObjectListMatcher[TrackId] = ObjectListMatcher({  #
            lambda t: t.title: 8,  #
            lambda t: t.artist: 3.5,  #
            lambda t: t.track: 1.2,  #
            lambda t: t.file_stem: 1,  # needed in case the track has no tags
            lambda t: t.disc: 0.8,  #
        })
        self._track_id_matcher.should_store_similarity_matrix = True
        self._album_id_matcher.should_go_through_every_attribute = True

        self._album_id_to_export_path = {}

        submenu = Gtk.Menu()
        self._init_collectors_and_menu(submenu)

        if submenu.get_children():
            self.set_submenu(submenu)
        else:
            self.set_sensitive(False)

    def _init_collectors_and_menu(self, submenu):
        import_item = Gtk.MenuItem(label=_("Import"))
        connect_obj(import_item, "activate", self.__set_import_export_option_index, -1)

        submenu.append(import_item)
        submenu.append(SeparatorMenuItem())

        for idx, (name, query) in enumerate(EXPORT_OPTIONS):
            collector = track_data_collector_for(query)
            self._export_collectors.append(collector)

            item = Gtk.MenuItem(label=name)
            connect_obj(item, "activate", self.__set_import_export_option_index, idx)
            submenu.append(item)

        submenu.append(SeparatorMenuItem())
        open_dir_item = Gtk.MenuItem(label=_("Open Export Directory"))

        def open_export_dir(_):
            show_files(path2fsn(EXPORT_DIR_PATH),
                       [path2fsn(TAGS_AND_USERDATA_INDEX_FILE_PATH.name)])

        connect_obj(open_dir_item, "activate", open_export_dir, None)
        submenu.append(open_dir_item)

    def __set_import_export_option_index(self, index):
        self._import_or_export_option_index = index

    def _error_msg(self, message):
        title = _("Error in %s") % self.PLUGIN_NAME
        ErrorMessage(app.window, title, message).run()

    def plugin_albums(self, albums):
        index = self._import_or_export_option_index

        if index is None or index >= len(self._export_collectors):
            return

        if index < 0:
            self.import_data_to_albums(albums)
        else:
            collect_data = self._export_collectors[index]
            self.export_albums(albums, collect_data)

        self._rewrite_index()
        self._import_or_export_option_index = None

    def import_data_to_albums(self, albums):
        if not self._try_load_exports():
            return

        for exp_album_id, songs in self._iter_export_album_id_matched_to_songs(albums):
            if exp_album_id is not None:
                self.import_data(exp_album_id, songs)

    def _iter_export_album_id_matched_to_songs(self, albums):
        album_ids = [AlbumId.of_song(songs[0]) for songs in albums]
        exp_album_ids = list(self._album_id_to_export_path.keys())

        exp_indices = self._album_id_matcher.get_indices(album_ids, exp_album_ids)
        size_differs = len(exp_album_ids) != len(exp_album_ids)
        need_check = CONFIG.need_user_check_if_number_of_albums_differs and size_differs

        need_check = need_check or self._does_match_need_manual_check(
            self._album_id_matcher, exp_indices,
            CONFIG.max_album_similarity_to_need_user_check)

        if need_check:
            columns = [  #
                ColumnSpec(_("Discs"), lambda a: str(a.discs), False),
                ColumnSpec(_("Tracks"), lambda a: str(a.tracks), False),
                ColumnSpec(_("Title"), lambda a: a.title, True),
                ColumnSpec(_("Artist(s)"), lambda a: a.artist, True),
                ColumnSpec(_("End of path"), lambda a: a.last_directory_parts, True),  #
            ]
            prompt = MatchListsDialog(album_ids, exp_album_ids, exp_indices, columns,
                                      _("Match Albums"), _("Continue"),
                                      id_for_window_tracking=self.PLUGIN_ID)
            exp_indices = prompt.run()

        for exp_idx, songs in zip(exp_indices, albums, strict=False):
            if exp_idx is not None:
                yield exp_album_ids[exp_idx], songs

    def _try_load_exports(self) -> bool:
        """:return: Whether we could load the exports"""

        index_path = TAGS_AND_USERDATA_INDEX_FILE_PATH

        if not index_path.exists():
            self._warning_nothing_to_import()
            return False

        try:
            with index_path.open(encoding="utf-8") as f:
                album_json_key_to_export_file_name = json.load(f)
        except ValueError:
            self._handle_broken_index()
            return False

        if not album_json_key_to_export_file_name:
            self._warning_nothing_to_import()
            return False

        self._load_exports_in_index(album_json_key_to_export_file_name)
        return True

    def _warning_nothing_to_import(self):
        WarningMessage(app.window, _("Nothing to import"),
                       _("You have to export something before you can import."))

    def _load_exports_in_index(self, album_json_key_to_export_file_name):
        for key, file_name in album_json_key_to_export_file_name.items():
            path = EXPORT_DIR_PATH / file_name
            if not path.exists():
                continue

            try:
                # album_id needed to be stored as a json string, since it's a tuple
                album_id = AlbumId(*json.loads(key))
            except ValueError:
                continue

            self._album_id_to_export_path[album_id] = path

    def _handle_broken_index(self):
        index_path = TAGS_AND_USERDATA_INDEX_FILE_PATH

        now = cur_datetime_as_str()
        new_path = index_path.with_name(f"index-broken-{now}.{EXPORT_EXTENSION}")
        index_path.rename(new_path)

        self._error_msg(_("The index was corrupt."))

    def import_data(self, export_album_id: AlbumId, songs: list[SongWrapper]):
        songs = [s for s in songs if is_writable(s)]
        if not songs:
            return
        songs.sort(key=sort_key_for_song)

        export_path = self._album_id_to_export_path[export_album_id]
        changed_songs = self.import_data_and_get_changed(songs, export_path)
        if changed_songs:
            check_wrapper_changed(app.library, changed_songs)

            # Remove used up export
            del self._album_id_to_export_path[export_album_id]
            if CONFIG.delete_exports_after_importing:
                try:
                    export_path.unlink()
                except FileNotFoundError:
                    pass
            else:
                move_export_to_used(export_path)

    def import_data_and_get_changed(self, songs: list[SongWrapper],
                                    source_path: Path) -> list[SongWrapper]:
        """:return: List of changed songs"""

        exported = self._try_read_source_json(source_path)
        if exported is None:
            return []

        # removes TrackId from exported
        exported_indices = self._get_exported_indices_matched_to_songs(exported, songs)
        if not exported_indices:
            return []

        changed_songs = []
        for song, exp_idx in zip(songs, exported_indices, strict=False):
            if exp_idx is None:
                continue

            self._update_song(exported[exp_idx], song)

            if song._needs_write:
                changed_songs.append(song)

        return changed_songs

    def _try_read_source_json(self, path: Path):
        try:
            print_d(f"Loading from {str(path)!r}")
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        except ValueError:
            print_e(f"Couldn't parse JSON in {path}.")
            self._error_msg(_("Couldn't parse JSON in %s") % path)
            return None
        except OSError:
            print_e(f"Couldn't read {path}")
            self._error_msg(_("Couldn't read %s") % path)
            return None

    def _update_song(self, exported_data, song):
        file_stem = exported_data.pop(FILE_STEM_KEY, None)

        if file_stem is not None:
            file_ext = extension_of_file_name(song("~basename"))

            new_name = f"{file_stem}{file_ext}"
            new_song_path = os.path.join(song("~dirname"), new_name)
            try:
                app.library.rename(song._song, new_song_path)
            except ValueError:
                print_e(f"Could not rename {song._song} to {new_song_path}.")

        for pl_name in exported_data.pop(PLAYLISTS_KEY, []):
            add_song_to_playlist(pl_name, song)

        for tag_key, tag_value in exported_data.items():
            if tag_key in song and song[tag_key] == tag_value:
                continue

            song[tag_key] = tag_value
            song._needs_write = True

    def _rewrite_index(self):
        # AlbumId's are tuples, so we need to serialize them to a string for json
        obj = {json.dumps(k): p.name for k, p in self._album_id_to_export_path.items()}
        self._rewrite_json(obj, TAGS_AND_USERDATA_INDEX_FILE_PATH)

    def _rewrite_json(self, obj, path):
        try:
            print_d(f"Writing to {str(path)!r}")
            with path.open("w+", encoding="utf-8") as f:
                json.dump(obj, f, indent=self._get_json_indent())
        except (ValueError, OSError):
            self._error_msg(_("Couldn't write '%s'") % path)
            print_e(f"Couldn't write {path} due to:")
            print_exc()

    def _get_exported_indices_matched_to_songs(self, exported, songs):
        songs_ids = [TrackId.of_song(s) for s in songs]
        export_ids = [TrackId(*md.pop(IDENTIFIER_KEY)) for md in exported]

        export_ids_indices = self._track_id_matcher.get_indices(songs_ids, export_ids)

        size_differs = len(exported) != len(songs)
        need_check = CONFIG.need_user_check_if_number_of_tracks_differs and size_differs

        need_check = need_check or self._does_match_need_manual_check(
            self._track_id_matcher, export_ids_indices,
            CONFIG.max_track_similarity_to_need_user_check)

        if need_check:
            columns = [  #
                ColumnSpec(_("Disc"), lambda t: t.disc_text, False),
                ColumnSpec(_("Track"), lambda t: t.track_text, False),
                ColumnSpec(_("Title"), lambda t: t.title, True),
                ColumnSpec(_("Artist(s)"), lambda t: t.artist, True),
                ColumnSpec(_("File name"), lambda t: t.file_name, True),  #
            ]
            prompt = MatchListsDialog(songs_ids, export_ids, export_ids_indices,
                                      columns, _("Match Tracks"), _("Import"),
                                      id_for_window_tracking=self.PLUGIN_ID)
            return prompt.run()

        return export_ids_indices

    def _does_match_need_manual_check(self, matcher, b_indices,
                                      max_similarity_to_need_manual_check):
        if max_similarity_to_need_manual_check <= 0.0:
            return False
        if max_similarity_to_need_manual_check >= 1.0:
            return True

        sim_matrix = matcher.similarity_matrix
        for a_idx, b_idx in enumerate(b_indices):
            if b_idx is None:
                continue

            sim = sim_matrix[a_idx][b_idx]
            if sim <= max_similarity_to_need_manual_check:
                return True
        return False

    def _get_json_indent(self):
        return 4 if CONFIG.pretty_print_json else None

    def export_albums(self, albums, collect_data):
        self._try_load_exports()

        for songs in albums:
            self.extract_data_and_export(songs, collect_data)

    def extract_data_and_export(self, songs, collect_data):
        songs.sort(key=sort_key_for_song)
        songs_data = [collect_data(s._song) for s in songs]

        album_id = AlbumId.of_song(songs[0])

        prev_path = self._album_id_to_export_path.get(album_id)

        # this overrides export data with the same album key by design, so a user
        # can simply rerun the export on an album they've modified
        path = new_export_path_for_album(album_id) if prev_path is None else prev_path
        self._album_id_to_export_path[album_id] = path

        self._rewrite_json(songs_data, path)


def cur_datetime_as_str():
    return f'{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'


def sort_key_for_song(s: SongWrapper):
    return s("~#disc", 0), s("~#track", 0), s("~basename"), s


def add_song_to_playlist(pl_name, song):
    pl_lib = app.library.playlists
    try:
        pl_lib[pl_name].append(song)
    except KeyError:
        try:
            pl = pl_lib.create(pl_name)
            pl.append(song)
        except ValueError:
            print_e(f"tried to add {song} to playlist {pl_name} but could not due to:")
            print_exc()


TrackData = MutableMapping[str, Any]
"""The term data here includes tags and track user data."""

TrackDataCollector = Callable[[AudioFile], TrackData]


def track_data_collector_for(query: str) -> TrackDataCollector:
    """Creates a callable that returns the track data selected by the query."""
    keys = query.strip().split()

    if keys[0] == "*":
        func = excluding_track_data_collector(set(keys[1:]))
    else:
        func = including_track_data_collector(keys)

    return func


def excluding_track_data_collector(excluded_keys: set[str]) -> TrackDataCollector:
    include_playlist = PLAYLISTS_KEY not in excluded_keys
    include_file_stem = FILE_STEM_KEY not in excluded_keys

    def func(track: AudioFile) -> TrackData:
        md = basic_track_data(track, include_playlist, include_file_stem)
        for key in track:
            if key not in excluded_keys and (key[:1] != "~" or key in MIGRATE):
                md[key] = track[key]

        return md

    return func


def including_track_data_collector(keys: list[str]) -> TrackDataCollector:
    include_playlist = was_removed(keys, PLAYLISTS_KEY)
    include_file_stem = was_removed(keys, FILE_STEM_KEY)

    def func(track: AudioFile) -> TrackData:
        md = basic_track_data(track, include_playlist, include_file_stem)
        for key in keys:
            if key in track:
                md[key] = track[key]
        return md

    return func


def was_removed(elements: list, o: Any) -> bool:
    """:return: whether o was in elements and thus removed from elements"""
    for idx, e in enumerate(elements):
        if e == o:
            del elements[idx]
            return True
    return False


def basic_track_data(track: AudioFile, include_playlist: bool,
                     include_file_stem: bool) -> TrackData:
    md = {IDENTIFIER_KEY: TrackId.of_song(track)}
    if include_playlist:
        if app.library is None:
            raise ValueError("app.library was None - plugin needs it")

        pl_lib = app.library.playlists
        playlist_names = [pl.name for pl in pl_lib.playlists_featuring(track)]
        if playlist_names:
            md[PLAYLISTS_KEY] = playlist_names

    if include_file_stem:
        md[FILE_STEM_KEY] = stem_of_file_name(track("~basename"))
    return md


def new_export_path_for_album(album_id: AlbumId) -> Path:
    stem = f"{album_id.title} - {album_id.artist}"
    path = Path(join_path_with_escaped_name_of_legal_length(str(EXPORT_DIR_PATH), stem,
                                                            EXPORT_EXTENSION))
    trim_count = 1
    while path.exists():
        new_stem = path.stem[:-trim_count] + uuid.uuid4().hex[:trim_count]
        trim_count += 1
        path = path.with_name(f"{new_stem}.{EXPORT_EXTENSION}")

    return path
