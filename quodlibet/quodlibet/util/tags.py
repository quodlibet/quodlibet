# Important constants for tag handling.

# Every tag should be listed here, as the canonical translation copy.
# If machine is true, then the tag will not appear in some contexts,
# as it is not intended to be human-readable.  If internal is true,
# the tag will not show up for editing, as it is generated internally
# by Quod Libet.

def T(name, translation, machine=False, internal=False):
    return (name, (translation, machine, internal))

def MT(name, translation, internal=False):
    return T(name, translation, machine=True, internal=internal)

def IT(name, translation, machine=False):
    return T(name, translation, machine=machine, internal=True)

# Fake out gettext for some convenience.
def N_(name):
    return T(name, _(name))

TAGS = dict([
    N_("album"),
    N_("arranger"),
    N_("artist"),
    N_("author"),
    N_("composer"),
    N_("conductor"),
    N_("contact"),
    N_("copyright"),
    N_("date"),
    N_("description"),
    N_("genre"),
    N_("grouping"),
    N_("language"),
    N_("license"),
    N_("location"),
    N_("lyricist"),
    # Translators: Also e.g. "record label", "publisher"
    N_("organization"),
    N_("performer"),
    N_("title"),
    N_("version"),
    N_("website"),

    T("albumartist", _("album artist")),
    T("bpm", _("BPM")),
    T("isrc", "ISRC"),
    # Translators: This used to be called "part".
    T("discsubtitle", _("disc subtitle")),
    T("part", _("disc subtitle")),
    T("discnumber", _("disc")),
    T("tracknumber", _("track")),
    T("labelid", _("label ID")),
    T("originaldate", _("original release date")),
    T("originalalbum", _("original album")),
    T("originalartist", _("original artist")),
    T("recordingdate", _("recording date")),
    T("releasecountry", _("release country")),
    T("albumartistsort", _("album artist (sort)")),
    T("artistsort", _("artist (sort)")),
    T("albumsort", _("album (sort)")),
    T("performersort", _("performer (sort)")),
    T("performerssort", _("performers (sort)")),

    # http://musicbrainz.org/doc/MusicBrainzTag

    MT("musicbrainz_trackid", _("MusicBrainz track ID")),
    MT("musicbrainz_albumid", _("MusicBrainz release ID")),
    MT("musicbrainz_artistid", _("Musicbrainz artist ID")),
    MT("musicbrainz_albumartistid", _("MusicBrainz album artist ID")),
    MT("musicbrainz_trmid", _("MusicBrainz TRM ID")),
    MT("musicip_puid", _("MusicIP PUID")),
    MT("musicbrainz_albumstatus", _("MusicBrainz album status")),
    MT("musicbrainz_albumtype", _("MusicBrainz album type")),

    # Translators: "gain" means a volume adjustment, not "to acquire".
    MT("replaygain_track_gain", _("track gain")),
    MT("replaygain_track_peak", _("track peak")),
    # Translators: "gain" means a volume adjustment, not "to acquire".
    MT("replaygain_album_gain", _("album gain")),
    MT("replaygain_album_peak", _("album peak")),
    MT("replaygain_reference_loudness", _("reference loudness")),

    IT("added", _("added")),
    IT("lastplayed", _("last played")),
    IT("disc", _("disc")),
    IT("discs", _("discs")),
    IT("track", _("track")),
    IT("tracks", _("tracks")),
    IT("laststarted", _("last started")),
    IT("filename", _("full name")),
    IT("basename", _("filename")),
    IT("dirname", _("directory")),
    IT("mtime", _("modified")),
    IT("playcount", _("plays")),
    IT("skipcount", _("skips")),
    IT("uri", "URI"),
    IT("mountpoint", _("mount point")),
    IT("errors", _("errors")),
    IT("length", _("length")),
    IT("people", _("people")),
    IT("performers", _("performers")),
    IT("rating", _("rating")),
    IT("year", _("year")),
    IT("originalyear", _("original release year")),
    IT("bookmark", _("bookmark")),
    IT("bitrate", _("bitrate")),
    IT("filesize", _("file size")),
    IT("format", _("file format")),
    ])

def add(tag, translation):
    TAGS[tag] = (translation, False, False)

def readable(tag):
    try:
        if tag[0] == "~":
            if tag[1] == "#": tag = tag[2:]
            else: tag = tag[1:]
    except IndexError: return _("Invalid tag")
    else: return TAGS.get(tag, (tag,))[0]

STANDARD_TAGS = [key for key in TAGS if not (TAGS[key][1] or TAGS[key][2])]
MACHINE_TAGS = [key for key in TAGS if TAGS[key][1]]
del(key)

# Other things put here as a canonical translated copy.

_("lyricists")
_("arrangers")
_("composers")
_("conductors")
_("authors")
_("artists")
_("albums")

ngettext("%d second", "%d seconds", 1)
ngettext("%d minute", "%d minutes", 1)
ngettext("%d hour", "%d hours", 1)
ngettext("%d day", "%d days", 1)
ngettext("%d year", "%d years", 1)
