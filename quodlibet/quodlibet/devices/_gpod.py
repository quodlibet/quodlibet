# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

"""ctypes bindings for libgpod.

Similar to the in libgpod included swig bindings except:
  - Functions for pixbuf handling are missing (itdb_artwork_*)
  - Swig wrappers (sw_*) from the swig bindings are mostly missing

These are needed since the original bindings depend on pygtk which breaks
in combination with pygobject.
"""

from ctypes import *


try:
    _glib = CDLL("libglib-2.0.so.0")
except OSError:
    raise ImportError("Couldn't find libglib-2.0")


try:
    _lib = CDLL("libgpod.so.4")
except OSError:
    raise ImportError("Couldn't find libgpod")


gchar_p = c_char_p
gchar = c_char
guchar = c_uint8
guchar_p = POINTER(c_uint8)
guint = c_uint
gpointer = c_void_p
gint32 = c_int32
guint32 = c_uint32
gint = c_int
gboolean = c_bool
gint8 = c_int8
guint8 = c_uint8
gint16 = c_int16
guint16 = c_uint16
gint64 = c_int64
guint64 = c_uint64
gfloat = c_float
gdouble = c_double
gshort = c_short
gushort = c_ushort
glong = c_long
gulong = c_ulong
gsize = c_size_t
gconstpointer = c_void_p

time_t = c_ulong


g_strdup = _glib.g_strdup
g_strdup.argtypes = [gchar_p]
g_strdup.restype = gpointer

g_free = _glib.g_free
g_free.argtypes = [gpointer]
g_free.restype = None


class StructPointerMixin(object):
    """Access struct fields through the struct pointer"""

    def _get_type(self, name):
        """Returns the type of the field"""

        for n, type_ in self._fields_:
            if name == n:
                return type_
        else:
            raise KeyError

    def __getattr__(self, name):
        if not self:
            raise AttributeError("NULL pointer access")

        return getattr(self.contents, name)

    def __setattr__(self, name, value):
        if not self:
            raise AttributeError("NULL pointer access")

        if not hasattr(self.contents, name):
            raise AttributeError("Invalid attribute: %r" % name)

        # copy c_char_p values and free old ones
        type_ = self._get_type(name)
        if type_ is gchar_p:
            old_value = getattr(self.contents, name)
            g_free(old_value)
            value = g_strdup(value)

        setattr(self.contents, name, value)


class GList(Structure):
    pass


class GListPtr(POINTER(GList), StructPointerMixin):
    _type_ = GList


GList._fields_ = [
    ("data", gpointer),
    ("next", GListPtr),
    ("prev", GListPtr),
]


class GTreePtr(gpointer):
    pass


class Enum(guint):
    def __str__(self):
        for a in (c for c in dir(self) if c.upper() == c):
            if getattr(self, a) == self.value:
                return a
        return "Unkown"

    def __repr__(self):
        return repr(str(self))

    def __int__(self):
        return self.value


class Flags(guint):
    def __str__(self):
        values = []
        for a in (c for c in dir(self) if c.upper() == c):
            if getattr(self, a) & self.value:
                values.append(a)
        return " | ".join(values) or "Unkown"

    def __repr__(self):
        return repr(str(self))

    def __int__(self):
        return self.value


class IpodGeneration(Enum):
    (UNKNOWN, FIRST, SECOND, THIRD, FOURTH, PHOTO, MOBILE, MINI_1, MINI_2,
    SHUFFLE_1, SHUFFLE_2, SHUFFLE_3, NANO_1, NANO_2, NANO_3, NANO_4, VIDEO_1,
    VIDEO_2, CLASSIC_1, CLASSIC_2, TOUCH_1, IPHONE_1, SHUFFLE_4, TOUCH_2,
    IPHONE_2, IPHONE_3, CLASSIC_3, NANO_5, TOUCH_3, IPAD_1, IPHONE_4,
    TOUCH_4, NANO_6) = range(33)


class IpodModel(Enum):
    (INVALID, UNKNOWN, COLOR, COLOR_U2, REGULAR, REGULAR_U2, MINI, MINI_BLUE,
    MINI_PINK, MINI_GREEN, MINI_GOLD, SHUFFLE, NANO_WHITE, NANO_BLACK,
    VIDEO_WHITE, VIDEO_BLACK, MOBILE_1, VIDEO_U2, NANO_SILVER, NANO_BLUE,
    NANO_GREEN, NANO_PINK, NANO_RED, NANO_YELLOW, NANO_PURPLE, NANO_ORANGE,
    IPHONE_1, SHUFFLE_SILVER, SHUFFLE_PINK, SHUFFLE_BLUE, SHUFFLE_GREEN,
    SHUFFLE_ORANGE, SHUFFLE_PURPLE, SHUFFLE_RED, CLASSIC_SILVER,
    CLASSIC_BLACK, TOUCH_SILVER, SHUFFLE_BLACK, IPHONE_WHITE, IPHONE_BLACK,
    SHUFFLE_GOLD, SHUFFLE_STAINLESS, IPAD) = range(43)


class IpodInfo(Structure):
    _fields_ = [
        ("model_number", gchar_p),
        ("capacity", c_double),
        ("ipod_model", IpodModel),
        ("ipod_generation", IpodGeneration),
        ("musicdirs", guint),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gconstpointer),
        ("reserved2", gconstpointer),
    ]


class IpodInfoPtr(POINTER(IpodInfo), StructPointerMixin):
    _type_ = IpodInfo


ITDB_SPL_STRING_MAXLEN = 255
ITDB_SPL_DATE_IDENTIFIER = 0x2dae2dae2dae2dae


class SPLMatch(Enum):
    AND = 0
    OR = 1


class LimitType(Enum):
    MINUTES = 0x01
    MB = 0x02
    SONGS = 0x03
    HOURS = 0x04
    GB = 0x05


class LimitSort(Enum):
    RANDOM = 0x02
    SONG_NAME = 0x03
    ALBUM = 0x04
    ARTIST = 0x05
    GENRE = 0x07
    MOST_RECENTLY_ADDED = 0x10
    LEAST_RECENTLY_ADDED = 0x80000010
    MOST_OFTEN_PLAYED = 0x14
    LEAST_OFTEN_PLAYED = 0x80000014
    MOST_RECENTLY_PLAYED = 0x15
    LEAST_RECENTLY_PLAYED = 0x80000015
    HIGHEST_RATING = 0x17
    LOWEST_RATING = 0x80000017


class SPLAction(Enum):
    IS_INT = 0x00000001
    IS_GREATER_THAN = 0x00000010
    IS_LESS_THAN = 0x00000040
    IS_IN_THE_RANGE = 0x00000100
    IS_IN_THE_LAST = 0x00000200
    BINARY_AND = 0x00000400

    BINARY_UNKNOWN1 = 0x00000800

    IS_STRING = 0x01000001
    CONTAINS = 0x01000002
    STARTS_WITH = 0x01000004
    ENDS_WITH = 0x01000008

    IS_NOT_INT = 0x02000001
    IS_NOT_GREATER_THAN = 0x02000010
    IS_NOT_LESS_THAN = 0x02000040
    IS_NOT_IN_THE_RANGE = 0x02000100
    IS_NOT_IN_THE_LAST = 0x02000200
    NOT_BINARY_AND = 0x02000400
    BINARY_UNKNOWN2 = 0x02000800

    IS_NOT = 0x03000001
    DOES_NOT_CONTAIN = 0x03000002
    DOES_NOT_START_WITH = 0x03000004
    DOES_NOT_END_WITH = 0x03000008


class SPLFieldType(Enum):
    (STRING, INT, BOOLEAN, DATE, PLAYLIST, UNKNOWN, BINARY_AND) = range(1, 8)


class SPLActionType(Enum):
    (STRING, INT, DATE, RANGE_INT, RANGE_DATE, INTHELAST, PLAYLIST, NONE,
    INVALID, UNKNOWN, BINARY_AND) = range(1, 12)


class SPLActionLast(Enum):
    DAYS_VALUE = 86400
    WEEKS_VALUE = 604800
    MONTHS_VALUE = 2628000


class SPLField(Enum):
    SONG_NAME = 0x02
    ALBUM = 0x03
    ARTIST = 0x04
    BITRATE = 0x05
    SAMPLE_RATE = 0x06
    YEAR = 0x07
    GENRE = 0x08
    KIND = 0x09
    DATE_MODIFIED = 0x0a
    TRACKNUMBER = 0x0b
    SIZE = 0x0c
    TIME = 0x0d
    COMMENT = 0x0e
    DATE_ADDED = 0x10
    COMPOSER = 0x12
    PLAYCOUNT = 0x16
    LAST_PLAYED = 0x17
    DISC_NUMBER = 0x18
    RATING = 0x19
    COMPILATION = 0x1f
    BPM = 0x23
    GROUPING = 0x27
    PLAYLIST = 0x28
    PURCHASE = 0x29
    DESCRIPTION = 0x36
    CATEGORY = 0x37
    PODCAST = 0x39
    VIDEO_KIND = 0x3c
    TVSHOW = 0x3e
    SEASON_NR = 0x3f
    SKIPCOUNT = 0x44
    LAST_SKIPPED = 0x45
    ALBUMARTIST = 0x47
    SORT_SONG_NAME = 0x4e
    SORT_ALBUM = 0x4f
    SORT_ARTIST = 0x50
    SORT_ALBUMARTIST = 0x51
    SORT_COMPOSER = 0x52
    SORT_TVSHOW = 0x53
    ALBUM_RATING = 0x5a


class SPLPref(Structure):
    _fields_ = [
        ("liveupdate", guint8),
        ("checkrules", guint8),
        ("checklimits", guint8),
        ("limittype", guint32),
        ("limitsort", guint32),
        ("limitvalue", guint32),
        ("matchcheckedonly", guint8),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gpointer),
        ("reserved2", gpointer),
    ]


class SPLRule(Structure):
    _fields_ = [
        ("field", guint32),
        ("action", guint32),
        ("string", gchar_p),
        ("fromvalue", guint64),
        ("fromdate", guint64),
        ("fromunits", guint64),
        ("tovalue", guint64),
        ("todate", gint64),
        ("tounits", guint64),
        ("unk052", guint32),
        ("unk056", guint32),
        ("unk060", guint32),
        ("unk064", guint32),
        ("unk068", guint32),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gpointer),
        ("reserved2", gpointer),
    ]


class SPLRulePtr(POINTER(SPLRule), StructPointerMixin):
    _type_ = SPLRule


class SPLRules(Structure):
    _fields_ = [
        ("unk004", guint32),
        ("match_operator", guint32),
        ("rules", GListPtr),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gpointer),
        ("reserved2", gpointer),
    ]


class Chapter(Structure):
    _fields_ = [
        ("startpos", guint32),
        ("chaptertitle", gchar_p),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gpointer),
        ("reserved2", gpointer),
    ]


class ChapterPtr(POINTER(Chapter), StructPointerMixin):
    _type_ = Chapter


class Chapterdata(Structure):
    _fields_ = [
        ("chapters", GListPtr),
        ("unk024", guint32),
        ("unk028", guint32),
        ("unk032", guint32),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gpointer),
        ("reserved2", gpointer),
    ]


class ChapterdataPtr(POINTER(Chapterdata), StructPointerMixin):
    _type_ = Chapterdata


ITDB_RATING_STEP = 20


class ThumbPtr(c_void_p):
    pass


UserDataDuplicateFunc = CFUNCTYPE(gpointer, gpointer)
UserDataDestroyFunc = CFUNCTYPE(None, gpointer)


class Artwork(Structure):
    _fields_ = [
        ("thumbnail", ThumbPtr),
        ("id", guint32),
        ("dbid", guint64),
        ("unk028", gint32),
        ("rating", guint32),
        ("unk036", gint32),
        ("creation_date", time_t),
        ("digitized_date", time_t),
        ("artwork_size", guint32),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gpointer),
        ("reserved2", gpointer),
        ("usertype", guint64),
        ("userdata", gpointer),
        ("userdata_duplicate", UserDataDuplicateFunc),
        ("userdata_destroy", UserDataDestroyFunc),
    ]


class ArtworkPtr(POINTER(Artwork), StructPointerMixin):
    _type_ = Artwork


class PhotoDB(Structure):
    _fields_ = [
        ("photos", GListPtr),
        ("photoalbums", GListPtr),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gpointer),
        ("reserved2", gpointer),
        ("usertype", guint64),
        ("userdata", gpointer),
        ("userdata_duplicate", UserDataDuplicateFunc),
        ("userdata_destroy", UserDataDestroyFunc),
    ]


class PhotoDBPtr(POINTER(PhotoDB), StructPointerMixin):
    _type_ = PhotoDB


class DevicePtr(c_void_p):
    pass


class iTunesDB_PrivatePtr(c_void_p):
    pass


class iTunesDB(Structure):
    _fields_ = [
        ("tracks", GListPtr),
        ("playlists", GListPtr),
        ("filename", gchar_p),
        ("device", DevicePtr),
        ("version", guint32),
        ("id", guint64),
        ("tzoffset", gint32),
        ("reserved_int2", gint32),
        ("priv", iTunesDB_PrivatePtr),
        ("reserved2", gpointer),
        ("usertype", guint64),
        ("userdata", gpointer),
        ("userdata_duplicate", UserDataDuplicateFunc),
        ("userdata_destroy", UserDataDestroyFunc),
    ]


class iTunesDBPtr(POINTER(iTunesDB), StructPointerMixin):
    _type_ = iTunesDB


class PhotoAlbum(Structure):
    _fields_ = [
        ("photodb", PhotoDBPtr),
        ("name", gchar_p),
        ("members", GListPtr),
        ("album_type", guint8),
        ("playmusic", guint8),
        ("repeat", guint8),
        ("random", guint8),
        ("show_titles", guint8),
        ("transition_direction", guint8),
        ("slide_duration", gint32),
        ("transition_duration", gint32),
        ("song_id", gint64),
        ("unk024", gint32),
        ("unk028", gint16),
        ("unk044", gint32),
        ("unk048", gint32),
        ("album_id", gint32),
        ("prev_album_id", gint32),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved1", gpointer),
        ("reserved2", gpointer),
        ("usertype", guint64),
        ("userdata", gpointer),
        ("userdata_duplicate", UserDataDuplicateFunc),
        ("userdata_destroy", UserDataDestroyFunc),
    ]


class PhotoAlbumPtr(POINTER(PhotoAlbum), StructPointerMixin):
    _type_ = PhotoAlbum


class Playlist_PrivatePtr(c_void_p):
    pass


class Playlist(Structure):
    _fields_ = [
        ("itdb", iTunesDBPtr),
        ("name", gchar_p),
        ("type", guint8),
        ("flag1", guint8),
        ("flag2", guint8),
        ("flag3", guint8),
        ("num", gint),
        ("members", GListPtr),
        ("is_spl", gboolean),
        ("timestamp", time_t),
        ("id", guint64),
        ("sortorder", guint32),
        ("podcastflag", guint32),
        ("splpref", SPLPref),
        ("splrules", SPLRules),
        ("reserved100", gpointer),
        ("reserved101", gpointer),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("*priv", Playlist_PrivatePtr),
        ("reserved2", gpointer),
        ("usertype", guint64),
        ("userdata", gpointer),
        ("userdata_duplicate", UserDataDuplicateFunc),
        ("userdata_destroy", UserDataDestroyFunc),
    ]


class PlaylistPtr(POINTER(Playlist), StructPointerMixin):
    _type_ = Playlist


class PlaylistSortOrder(Enum):
    MANUAL = 1
    TITLE = 3
    ALBUM = 4
    ARTIST = 5
    BITRATE = 6
    GENRE = 7
    FILETYPE = 8
    TIME_MODIFIED = 9
    TRACK_NR = 10
    SIZE = 11
    TIME = 12
    YEAR = 13
    SAMPLERATE = 14
    COMMENT = 15
    TIME_ADDED = 16
    EQUALIZER = 17
    COMPOSER = 18
    PLAYCOUNT = 20
    TIME_PLAYED = 21
    CD_NR = 22
    RATING = 23
    RELEASE_DATE = 24
    BPM = 25
    GROUPING = 26
    CATEGORY = 27
    DESCRIPTION = 28


class Mediatype(Flags):
    AUDIO = 1 << 0
    MOVIE = 1 << 1
    PODCAST = 1 << 2
    AUDIOBOOK = 1 << 3
    MUSICVIDEO = 1 << 5
    TVSHOW = 1 << 6
    RINGTONE = 1 << 14
    RENTAL = 1 << 15
    ITUNES_EXTRA = 1 << 16
    MEMO = 1 << 20
    ITUNES_U = 1 << 21
    EPUB_BOOK = 1 << 22
    PDF_BOOK = 1 << 23


class Track_PrivatePtr(c_void_p):
    pass


class Track(Structure):
    _fields_ = [
        ("itdb", iTunesDBPtr),
        ("title", gchar_p),
        ("ipod_path", gchar_p),
        ("album", gchar_p),
        ("artist", gchar_p),
        ("genre", gchar_p),
        ("filetype", gchar_p),
        ("comment", gchar_p),
        ("category", gchar_p),
        ("composer", gchar_p),
        ("grouping", gchar_p),
        ("description", gchar_p),
        ("podcasturl", gchar_p),
        ("podcastrss", gchar_p),
        ("chapterdata", ChapterdataPtr),
        ("subtitle", gchar_p),
        ("tvshow", gchar_p),
        ("tvepisode", gchar_p),
        ("tvnetwork", gchar_p),
        ("albumartist", gchar_p),
        ("keywords", gchar_p),
        ("sort_artist", gchar_p),
        ("sort_title", gchar_p),
        ("sort_album", gchar_p),
        ("sort_albumartist", gchar_p),
        ("sort_composer", gchar_p),
        ("sort_tvshow", gchar_p),
        ("id", guint32),
        ("size", guint32),
        ("tracklen", gint32),
        ("cd_nr", gint32),
        ("cds", gint32),
        ("track_nr", gint32),
        ("tracks", gint32),
        ("bitrate", gint32),
        ("samplerate", guint16),
        ("samplerate_low", guint16),
        ("year", gint32),
        ("volume", gint32),
        ("soundcheck", guint32),
        ("time_added", time_t),
        ("time_modified", time_t),
        ("time_played", time_t),
        ("bookmark_time", guint32),
        ("rating", guint32),
        ("playcount", guint32),
        ("playcount2", guint32),
        ("recent_playcount", guint32),
        ("transferred", gboolean),
        ("BPM", gint16),
        ("app_rating", guint8),
        ("type1", guint8),
        ("type2", guint8),
        ("compilation", guint8),
        ("starttime", guint32),
        ("stoptime", guint32),
        ("checked", guint8),
        ("dbid", guint64),
        ("drm_userid", guint32),
        ("visible", guint32),
        ("filetype_marker", guint32),
        ("artwork_count", guint16),
        ("artwork_size", guint32),
        ("samplerate2", c_float),
        ("unk126", guint16),
        ("unk132", guint32),
        ("time_released", time_t),
        ("unk144", guint16),
        ("explicit_flag", guint16),
        ("unk148", guint32),
        ("unk152", guint32),
        ("skipcount", guint32),
        ("recent_skipcount", guint32),
        ("last_skipped", guint32),
        ("has_artwork", guint8),
        ("skip_when_shuffling", guint8),
        ("remember_playback_position", guint8),
        ("flag4", guint8),
        ("dbid2", guint64),
        ("lyrics_flag", guint8),
        ("movie_flag", guint8),
        ("mark_unplayed", guint8),
        ("unk179", guint8),
        ("unk180", guint32),
        ("pregap", guint32),
        ("samplecount", guint64),
        ("unk196", guint32),
        ("postgap", guint32),
        ("unk204", guint32),
        ("mediatype", guint32),
        ("season_nr", guint32),
        ("episode_nr", guint32),
        ("unk220", guint32),
        ("unk224", guint32),
        ("unk228", guint32),
        ("unk232", guint32),
        ("unk236", guint32),
        ("unk240", guint32),
        ("unk244", guint32),
        ("gapless_data", guint32),
        ("unk252", guint32),
        ("gapless_track_flag", guint16),
        ("gapless_album_flag", guint16),
        ("obsolete", guint16),
        ("artwork", ArtworkPtr),
        ("mhii_link", guint32),
        ("reserved_int1", gint32),
        ("reserved_int2", gint32),
        ("reserved_int3", gint32),
        ("reserved_int4", gint32),
        ("reserved_int5", gint32),
        ("reserved_int6", gint32),
        ("priv", Track_PrivatePtr),
        ("reserved2", gpointer),
        ("reserved3", gpointer),
        ("reserved4", gpointer),
        ("reserved5", gpointer),
        ("reserved6", gpointer),
        ("usertype", guint64),
        ("userdata", gpointer),
        ("userdata_duplicate", UserDataDuplicateFunc),
        ("userdata_destroy", UserDataDestroyFunc),
    ]


class TrackPtr(POINTER(Track), StructPointerMixin):
    _type_ = Track


class FileError(Enum):
    SEEK, CORRUPT, NOTFOUND, RENAME, ITDB_CORRUPT = range(5)


class Error(Enum):
    SEEK, CORRUPT, NOTFOUND, RENAME, ITDB_CORRUPT, SQLITE = range(6)


class GErrorPtrPtr(c_void_p):
    pass


_functions = [
    ("itdb_parse", iTunesDBPtr, [gchar_p, GErrorPtrPtr]),
    ("itdb_parse_file", iTunesDBPtr, [gchar_p, GErrorPtrPtr]),
    ("itdb_write", gboolean, [iTunesDBPtr, GErrorPtrPtr]),
    ("itdb_write_file", gboolean, [iTunesDBPtr, gchar_p, GErrorPtrPtr]),
    ("itdb_shuffle_write", gboolean, [iTunesDBPtr, GErrorPtrPtr]),
    ("itdb_shuffle_write_file", gboolean,
     [iTunesDBPtr, gchar_p, GErrorPtrPtr]),
    ("itdb_start_sync", gboolean, [iTunesDBPtr]),
    ("itdb_stop_sync", gboolean, [iTunesDBPtr]),
    ("itdb_new", iTunesDBPtr, []),
    ("itdb_free", None, [iTunesDBPtr]),
    ("itdb_duplicate", iTunesDBPtr, [iTunesDBPtr]),
    ("itdb_tracks_number", guint32, [iTunesDBPtr]),
    ("itdb_tracks_number_nontransferred", guint32, [iTunesDBPtr]),
    ("itdb_playlists_number", guint32, [iTunesDBPtr]),

    ("itdb_musicdirs_number", gint, [iTunesDBPtr]),
    ("itdb_resolve_path", gchar_p, [gchar_p, POINTER(gchar_p)]),
    ("itdb_rename_files", gboolean, [gchar_p, GErrorPtrPtr]),
    ("itdb_cp_get_dest_filename", gchar_p,
     [TrackPtr, gchar_p, gchar_p, GErrorPtrPtr]),
    ("itdb_cp", gboolean, [gchar_p, gchar_p, GErrorPtrPtr]),
    ("itdb_cp_finalize", TrackPtr, [TrackPtr, gchar_p, gchar_p, GErrorPtrPtr]),
    ("itdb_cp_track_to_ipod", gboolean, [TrackPtr, gchar_p, GErrorPtrPtr]),
    ("itdb_filename_fs2ipod", None, [gchar_p]),
    ("itdb_filename_ipod2fs", None, [gchar_p]),
    ("itdb_filename_on_ipod", gchar_p, [TrackPtr]),
    ("itdb_set_mountpoint", None, [iTunesDBPtr, gchar_p]),
    ("itdb_get_mountpoint", gchar_p, [iTunesDBPtr]),
    ("itdb_get_control_dir", gchar_p, [gchar_p]),
    ("itdb_get_itunes_dir", gchar_p, [gchar_p]),
    ("itdb_get_music_dir", gchar_p, [gchar_p]),
    ("itdb_get_artwork_dir", gchar_p, [gchar_p]),
    ("itdb_get_photos_dir", gchar_p, [gchar_p]),
    ("itdb_get_photos_thumb_dir", gchar_p, [gchar_p]),
    ("itdb_get_device_dir", gchar_p, [gchar_p]),
    ("itdb_get_itunesdb_path", gchar_p, [gchar_p]),
    ("itdb_get_itunescdb_path", gchar_p, [gchar_p]),
    ("itdb_get_itunessd_path", gchar_p, [gchar_p]),
    ("itdb_get_artworkdb_path", gchar_p, [gchar_p]),
    ("itdb_get_photodb_path", gchar_p, [gchar_p]),
    ("itdb_get_path", gchar_p, [gchar_p, gchar_p]),

    ("itdb_device_new", DevicePtr, []),
    ("itdb_device_free", None, [DevicePtr]),
    ("itdb_device_set_mountpoint", None, [DevicePtr, gchar_p]),
    ("itdb_device_read_sysinfo", gboolean, [DevicePtr]),
    ("itdb_device_write_sysinfo", gboolean, [DevicePtr, GErrorPtrPtr]),
    ("itdb_device_get_sysinfo", gchar_p, [DevicePtr, gchar_p]),
    ("itdb_device_set_sysinfo", None, [DevicePtr, gchar_p, gchar_p]),
    ("itdb_device_get_ipod_info", IpodInfoPtr, [DevicePtr]),
    ("itdb_info_get_ipod_info_table", IpodInfoPtr, []),
    ("itdb_device_supports_artwork", gboolean, [DevicePtr]),
    ("itdb_device_supports_chapter_image", gboolean, [DevicePtr]),
    ("itdb_device_supports_video", gboolean, [DevicePtr]),
    ("itdb_device_supports_photo", gboolean, [DevicePtr]),
    ("itdb_device_supports_podcast", gboolean, [DevicePtr]),
    ("itdb_info_get_ipod_model_name_string", gchar_p, [IpodModel]),
    ("itdb_info_get_ipod_generation_string", gchar_p, [IpodGeneration]),
    ("itdb_device_get_uuid", gchar_p, [DevicePtr]),

    ("itdb_track_new", TrackPtr, []),
    ("itdb_track_free", None, [TrackPtr]),
    ("itdb_track_add", None, [iTunesDBPtr, TrackPtr, gint32]),
    ("itdb_track_remove", None, [TrackPtr]),
    ("itdb_track_unlink", None, [TrackPtr]),
    ("itdb_track_duplicate", TrackPtr, [TrackPtr]),
    ("itdb_track_by_id", TrackPtr, [iTunesDBPtr, guint32]),
    ("itdb_track_id_tree_create", GTreePtr, [iTunesDBPtr]),
    ("itdb_track_id_tree_destroy", None, [GTreePtr]),
    ("itdb_track_id_tree_by_id", TrackPtr, [GTreePtr, guint32]),

    ("itdb_playlist_new", PlaylistPtr, [gchar_p, gboolean]),
    ("itdb_playlist_free", None, [PlaylistPtr]),
    ("itdb_playlist_add", None, [iTunesDBPtr, PlaylistPtr, gint32]),
    ("itdb_playlist_move", None, [PlaylistPtr, gint32]),
    ("itdb_playlist_remove", None, [PlaylistPtr]),
    ("itdb_playlist_unlink", None, [PlaylistPtr]),
    ("itdb_playlist_duplicate", PlaylistPtr, [PlaylistPtr]),
    ("itdb_playlist_exists", gboolean, [iTunesDBPtr, PlaylistPtr]),
    ("itdb_playlist_add_track", None, [PlaylistPtr, TrackPtr, gint32]),
    ("itdb_playlist_by_id", PlaylistPtr, [iTunesDBPtr, guint64]),
    ("itdb_playlist_by_nr", PlaylistPtr, [iTunesDBPtr, guint32]),
    ("itdb_playlist_by_name", PlaylistPtr, [iTunesDBPtr, gchar_p]),
    ("itdb_playlist_contains_track", gboolean, [PlaylistPtr, TrackPtr]),
    ("itdb_playlist_contain_track_number", guint32, [TrackPtr]),
    ("itdb_playlist_remove_track", None, [PlaylistPtr, TrackPtr]),
    ("itdb_playlist_tracks_number", guint32, [PlaylistPtr]),
    ("itdb_playlist_randomize", None, [PlaylistPtr]),

    ("itdb_playlist_mpl", PlaylistPtr, [iTunesDBPtr]),
    ("itdb_playlist_is_mpl", gboolean, [PlaylistPtr]),
    ("itdb_playlist_set_mpl", None, [PlaylistPtr]),

    ("itdb_playlist_podcasts", PlaylistPtr, [iTunesDBPtr]),
    ("itdb_playlist_is_podcasts", gboolean, [PlaylistPtr]),
    ("itdb_playlist_set_podcasts", None, [PlaylistPtr]),

    ("itdb_playlist_is_audiobooks", gboolean, [PlaylistPtr]),

    ("itdb_splr_get_field_type", SPLFieldType, [SPLRulePtr]),
    ("itdb_splr_get_action_type", SPLActionType, [SPLRulePtr]),
    ("itdb_splr_validate", None, [SPLRulePtr]),
    ("itdb_splr_remove", None, [PlaylistPtr, SPLRulePtr]),
    ("itdb_splr_new", SPLRulePtr, []),
    ("itdb_splr_add", None, [PlaylistPtr, SPLRulePtr, gint]),
    ("itdb_splr_add_new", SPLRulePtr, [PlaylistPtr, gint]),
    ("itdb_spl_copy_rules", None, [PlaylistPtr, PlaylistPtr]),
    ("itdb_splr_eval", gboolean, [SPLRulePtr, TrackPtr]),
    ("itdb_spl_update", None, [PlaylistPtr]),
    ("itdb_spl_update_all", None, [iTunesDBPtr]),
    ("itdb_spl_update_live", None, [iTunesDBPtr]),

    ("itdb_track_set_thumbnails", gboolean, [TrackPtr, gchar_p]),
    ("itdb_track_set_thumbnails_from_data", gboolean,
     [TrackPtr, guchar_p, gsize]),
    ("itdb_track_set_thumbnails_from_pixbuf", gboolean, [TrackPtr, gpointer]),
    ("itdb_track_has_thumbnails", gboolean, [TrackPtr]),
    ("itdb_track_remove_thumbnails", None, [TrackPtr]),
    ("itdb_track_get_thumbnail", gpointer, [TrackPtr, gint, gint]),

    ("itdb_photodb_parse", PhotoDBPtr, [gchar_p, GErrorPtrPtr]),
    ("itdb_photodb_add_photo", ArtworkPtr,
     [PhotoDBPtr, gchar_p, gint, gint, GErrorPtrPtr]),
    ("itdb_photodb_add_photo_from_data", ArtworkPtr,
     [PhotoDBPtr, guchar_p, gsize, gint, gint, GErrorPtrPtr]),
    ("itdb_photodb_add_photo_from_pixbuf", ArtworkPtr,
     [PhotoDBPtr, gpointer, gint, gint, GErrorPtrPtr]),
    ("itdb_photodb_photoalbum_add_photo", None,
     [PhotoDBPtr, PhotoAlbumPtr, ArtworkPtr, gint]),
    ("itdb_photodb_photoalbum_create", PhotoAlbumPtr,
     [PhotoDBPtr, gchar_p, gint]),
    ("itdb_photodb_create", PhotoDBPtr, [gchar_p]),
    ("itdb_photodb_photoalbum_new", PhotoAlbumPtr, [gchar_p]),
    ("itdb_photodb_photoalbum_free", None, [PhotoAlbumPtr]),
    ("itdb_photodb_photoalbum_add", None, [PhotoDBPtr, PhotoAlbumPtr, gint]),
    ("itdb_photodb_free", None, [PhotoDBPtr]),
    ("itdb_photodb_write", gboolean, [PhotoDBPtr, GErrorPtrPtr]),
    ("itdb_photodb_remove_photo", None,
     [PhotoDBPtr, PhotoAlbumPtr, ArtworkPtr]),
    ("itdb_photodb_photoalbum_remove", None,
     [PhotoDBPtr, PhotoAlbumPtr, gboolean]),
    ("itdb_photodb_photoalbum_unlink", None, [PhotoAlbumPtr]),
    ("itdb_photodb_photoalbum_by_name", PhotoAlbumPtr, [PhotoDBPtr, gchar_p]),

    ("itdb_chapterdata_new", ChapterdataPtr, []),
    ("itdb_chapterdata_free", None, [ChapterdataPtr]),
    ("itdb_chapterdata_duplicate", ChapterdataPtr, [ChapterdataPtr]),
    ("itdb_chapterdata_remove_chapter", None, [ChapterdataPtr, ChapterPtr]),
    ("itdb_chapterdata_unlink_chapter", None, [ChapterdataPtr, ChapterPtr]),
    ("itdb_chapterdata_remove_chapters", None, [ChapterdataPtr]),
    ("itdb_chapter_new", ChapterPtr, []),
    ("itdb_chapter_free", None, [ChapterPtr]),
    ("itdb_chapter_duplicate", ChapterPtr, [ChapterPtr]),
    ("itdb_chapterdata_add_chapter", gboolean,
     [ChapterdataPtr, guint32, gchar_p]),

    ("itdb_init_ipod", gboolean, [gchar_p, gchar_p, gchar_p, GErrorPtrPtr]),
]


def wrap_pointer_return(func):
    """If the returned value is a NULL pointer return None instead"""

    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)
        if not ret:
            return None
        return ret
    return wrapper


for name, ret, args in _functions:
    try:
        handle = getattr(_lib, name)
    except AttributeError:
        print_d("symbol not found: %r" % name)
        continue
    handle.argtypes = args
    handle.restype = ret

    # validate pointer return values
    if hasattr(ret, "contents"):
        handle = wrap_pointer_return(handle)

    globals()[name] = handle


def sw_get_tracks(itdb_ptr):
    """Get tracks in itdb."""

    if not itdb_ptr:
        raise ValueError

    tracks = []
    node = itdb_ptr.contents.tracks
    while node:
        entry = node.contents
        track_ptr = cast(entry.data, TrackPtr)
        tracks.append(track_ptr)
        node = node.next
    return tracks


__all__ = []
for key in globals().keys():
    lower = key.lower()
    if lower.startswith("itdb_") or lower.startswith("sw_"):
        __all__.append(key)
