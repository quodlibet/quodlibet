# -*- coding: utf-8 -*-
# Copyright 2007-2008 Joe Wreschnig
#           2014 Christoph Reiter
#      2014-2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.compat import iteritems

"""Database of all known tags, their translations and how they are used"""


class TagName(object):
    """
    Text:
        desc -- translated description
        plural -- translated plural description or None
        role -- translated role description (for people tags)

    Types:
        user -- user editable tag e.g. "foo"
            hidden -- if user tag should only be shown in the tag editor (e.g.
                      tracknumber is hidden, since ~#track/~#tracks are more
                      useful for displaying)
            has_sort -- has a sort user variant e.g. "foosort"
            machine -- user tag is not human readable. Something people might
                       want to hide in the tag editor.

        internal -- generated by QL e.g. "~foo"
            hidden -- if it is replaced by another tag (for backwards compat)
            has_sort -- has a sort user variant e.g. "~foosort"
            has_roles -- has a roles variant e.g. "~foo:roles"

        numeric -- e.g. "~#foo"
    """

    def __init__(self, name, options, desc, plural=None, role=None):
        # I don't think this categorization is any good.. but at least
        # there is any..
        self.name = name
        self.desc = desc
        self.plural = plural
        self.user = "u" in options
        self.internal = "i" in options
        self.numeric = "n" in options
        self.machine = "m" in options
        self.has_sort = "s" in options
        self.has_roles = "r" in options
        self.hidden = "h" in options
        self.role = role

        # some sanity checks
        assert self.user or self.internal or self.numeric
        assert not (set(options) - set("uinmshr"))

        if self.has_roles:
            assert self.internal
        if self.has_sort:
            assert self.user or self.internal
        if self.machine:
            assert self.user
        if self.hidden:
            assert self.user + self.internal == 1

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, vars(self))


def _get_role_map(tags):
    roles = {}
    for (name, tag) in iteritems(tags):
        if tag.role:
            roles[name] = tag.role
            if tag.has_sort:
                roles[name + "sort"] = tag.role
    return roles


T = TagName
_TAGS = dict((t.name, t) for t in [
    T("album", "us", _("album"), _("albums")),
    T("arranger", "u", _("arranger"), _("arrangers"), _("arrangement")),
    T("artist", "us", _("artist"), _("artists")),
    T("author", "u", _("author"), _("authors")),
    T("comment", "u", _("comment")),
    T("composer", "us", _("composer"), _("composers"), _("composition")),
    # Translators: conducting as in conducting a musical performance
    T("conductor", "u", _("conductor"), _("conductors"), _("conducting")),
    T("contact", "u", _("contact")),
    T("copyright", "u", _("copyright")),
    T("date", "u", _("date")),
    T("description", "u", _("description")),
    T("genre", "u", _("genre"), _("genres")),
    T("performer", "uisr", _("performer"), _("performers"), _("performance")),
    T("grouping", "u", _("grouping")),
    T("language", "ui", _("language")),
    T("license", "u", _("license")),
    T("location", "u", _("location")),
    T("lyricist", "u", _("lyricist"), _("lyricists"), _("lyrics")),
    # Translators: Also e.g. "record label", "publisher"
    T("organization", "u", _("organization")),
    T("title", "u", _("title")),
    T("version", "u", _("version")),
    T("website", "u", _("website")),

    T("albumartist", "us", _("album artist")),
    T("bpm", "u", _("BPM")),
    T("isrc", "u", "ISRC"),
    # Translators: This used to be called "part".
    T("discsubtitle", "u", _("disc subtitle")),
    T("part", "u", _("disc subtitle")),
    T("discnumber", "uh", _("disc")),
    T("tracknumber", "uh", _("track")),
    T("labelid", "u", _("label ID")),
    T("originaldate", "u", _("original release date")),
    T("originalalbum", "u", _("original album")),
    T("originalartist", "u", _("original artist")),
    T("recordingdate", "u", _("recording date")),
    T("releasecountry", "u", _("release country")),

    # for backwards compat
    T("performers", "ishr", _("performers")),

    # http://musicbrainz.org/doc/MusicBrainzTag
    # Note: picard has changed musicbrainz_trackid to mean release track.
    # We can't do that because of existing libraries, so use a new
    # musicbrainz_releastrackid instead.
    T("musicbrainz_trackid", "um", _("MusicBrainz recording ID")),
    T("musicbrainz_releasetrackid", "um", _("MusicBrainz release track ID")),
    T("musicbrainz_albumid", "um", _("MusicBrainz release ID")),
    T("musicbrainz_artistid", "um", _("MusicBrainz artist ID")),
    T("musicbrainz_albumartistid", "um", _("MusicBrainz release artist ID")),
    T("musicbrainz_trmid", "um", _("MusicBrainz TRM ID")),
    T("musicip_puid", "um", _("MusicIP PUID")),
    T("musicbrainz_albumstatus", "um", _("MusicBrainz album status")),
    T("musicbrainz_albumtype", "um", _("MusicBrainz album type")),
    T("musicbrainz_releasegroupid", "um", _("MusicBrainz release group ID")),

    # Translators: "gain" means a volume adjustment, not "to acquire".
    T("replaygain_track_gain", "umn", _("track gain")),
    T("replaygain_track_peak", "umn", _("track peak")),
    # Translators: "gain" means a volume adjustment, not "to acquire".
    T("replaygain_album_gain", "umn", _("album gain")),
    T("replaygain_album_peak", "umn", _("album peak")),
    T("replaygain_reference_loudness", "umn", _("reference loudness")),

    T("added", "n", _("added")),
    T("lastplayed", "n", _("last played")),
    T("disc", "n", _("disc")),
    T("discs", "n", _("discs")),
    T("track", "n", _("track")),
    T("tracks", "n", _("tracks")),
    T("laststarted", "n", _("last started")),
    T("filename", "i", _("full name")),
    T("basename", "i", _("filename")),
    T("dirname", "i", _("directory")),
    T("mtime", "n", _("modified")),
    T("playcount", "n", _("plays")),
    T("skipcount", "n", _("skips")),
    T("uri", "i", "URI"),
    T("mountpoint", "i", _("mount point")),
    T("length", "n", _("length")),
    T("people", "isr", _("people")),
    T("rating", "in", _("rating")),
    T("year", "in", _("year")),
    T("originalyear", "in", _("original release year")),
    T("bookmark", "i", _("bookmark")),
    T("bitrate", "in", _("bitrate")),
    T("filesize", "n", _("file size")),
    T("format", "i", _("file format")),
    T("codec", "i", _("codec")),
    T("encoding", "i", _("encoding")),
    T("playlists", "i", _("playlists")),
    T("channels", "n", _("channel count")),
])


def _get_sort_map(tags):
    """See TAG_TO_SORT"""

    tts = {}
    for name, tag in iteritems(tags):
        if tag.has_sort:
            if tag.user:
                tts[name] = "%ssort" % name
            if tag.internal:
                tts["~%s" % name] = "~%ssort" % name
    return tts


def _get_standard_tags(tags, machine=False):
    stags = []
    for name, tag in iteritems(tags):
        if tag.user and tag.machine == machine:
            stags.append(name)
            if tag.has_sort:
                stags.append("%ssort" % name)
    return stags


TAG_TO_SORT = _get_sort_map(_TAGS)
"""A mapping of tag -> sorttag. e.g. artist -> artistsort"""

MACHINE_TAGS = _get_standard_tags(_TAGS, machine=True)
"""A sequence of editable tags that are not human-readable.
e.g. musicbrainz_albumid
"""

USER_TAGS = _get_standard_tags(_TAGS, machine=False)
"""A sequence of tags that are human-readable and can be edited.
e.g. album
"""

TAG_ROLES = _get_role_map(_TAGS)
"""A mapping from tags to their translated role description.
e.g. conductor -> conducting
"""


def readable(tag, plural=False):
    """Gives a translated description for a tag.

    Also supports internal, numeric tags.
    If plural is True, will return a plural description if possible.

    album -> album
    albumsort -> album (sort)
    ~foo -> foo
    ~people:roles -> people (roles)
    """

    try:
        if tag[0] == "~":
            if tag[1] == "#":
                tag = tag[2:]
            else:
                tag = tag[1:]
    except IndexError:
        return _("Invalid tag")

    def desc(tag):
        if plural:
            plural_desc = _TAGS[tag].plural
            if plural_desc:
                return plural_desc
        return _TAGS[tag].desc

    if tag in _TAGS:
        return desc(tag)
    elif tag == 'people:real':
        return desc('people')
    else:
        roles = False
        if tag.endswith(":roles"):
            roles = True
            tag = tag[:-6]

        parts = []
        if tag.endswith("sort"):
            v = _TAGS.get(tag[:-4])
            if v is not None and v.has_sort:
                tag = tag[:-4]
                # Translators: e.g. "artist (sort)"
                parts.append(_("sort"))
        else:
            v = _TAGS.get(tag[:-4])

        if roles:
            v = _TAGS.get(tag)
            if v is not None and v.has_roles:
                # Translators: e.g. "performer (roles)"
                parts.append(_("roles"))

        if tag in _TAGS:
            desc = desc(tag)
            if parts:
                desc += " (%s)" % ", ".join(parts)
            return desc

    return tag


def sortkey(tag):
    """Sort key for sorting tag names by importance.

    tags.sort(key=sortkey)
    """

    # last one -> most important
    order = [
        "album",
        "artist",
        "title",
    ]

    try:
        return (-order.index(tag), tag)
    except ValueError:
        if tag in MACHINE_TAGS:
            return (2, tag)
        else:
            return (1, tag)
