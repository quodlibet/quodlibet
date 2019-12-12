# Copyright 2013 Simonas Kazlauskas
#      2015-2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import glob
import os.path
import re
import sre_constants

from senf import fsn2text

from quodlibet import _
from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.util.dprint import print_w
from quodlibet import config


def get_ext(s):
    return os.path.splitext(s)[1].lstrip('.')


def prefer_embedded():
    return config.getboolean("albumart", "prefer_embedded", False)


class EmbeddedCover(CoverSourcePlugin):
    PLUGIN_ID = "embed-cover"
    PLUGIN_NAME = _("Embedded album covers")
    PLUGIN_DESC = _("Uses covers embedded into audio files.")

    embedded = True

    @classmethod
    def group_by(cls, song):
        # one group per song
        return song.key

    @staticmethod
    def priority():
        return 0.85 if prefer_embedded() else 0.7

    @property
    def cover(self):
        if self.song.has_images:
            image = self.song.get_primary_image()
            return image.file if image else None


class FilesystemCover(CoverSourcePlugin):
    PLUGIN_ID = "filesystem-cover"
    PLUGIN_NAME = _("Filesystem cover")
    PLUGIN_DESC = _("Uses commonly named images found in common directories " +
                    "alongside the song.")

    cover_subdirs = frozenset(
        ["scan", "scans", "images", "covers", "artwork"])
    cover_exts = frozenset(["jpg", "jpeg", "png", "gif"])

    cover_positive_words = ["front", "cover", "frontcover", "jacket",
                            "folder", "albumart", "edited"]
    cover_negative_words = ["back", "inlay", "inset", "inside"]
    cover_positive_regexes = frozenset(
        [re.compile(r'(\b|_)' + s + r'(\b|_)') for s in cover_positive_words])
    cover_negative_regexes = frozenset(
        [re.compile(r'(\b|_|)' + s + r'(\b|_)') for s in cover_negative_words])

    @classmethod
    def group_by(cls, song):
        # in the common case this means we only search once per album
        return song('~dirname'), song.album_key

    @property
    def name(self):
        return "Filesystem"

    def __str__(self):
        return "Filesystem in %s" % (self.group_by(self.song)[0])

    @staticmethod
    def priority():
        return 0.80

    @property
    def cover(self):
        # TODO: Deserves some refactoring
        if not self.song.is_file:
            return None

        base = self.song('~dirname')
        images = []

        # Issue 374: Specify artwork filename
        if config.getboolean("albumart", "force_filename"):
            escaped_path = os.path.join(glob.escape(base),
                                        config.get("albumart", "filename"))
            try:
                for path in glob.glob(escaped_path):
                    images.append((100, path))
            except sre_constants.error:
                # Use literal filename if globbing causes errors
                path = os.path.join(base, config.get("albumart", "filename"))
                images = [(100, path)]
        else:
            entries = []
            try:
                entries = os.listdir(base)
            except EnvironmentError:
                print_w("Can't list album art directory %s" % base)

            fns = []
            for entry in entries:
                lentry = entry.lower()
                if get_ext(lentry) in self.cover_exts:
                    fns.append((None, entry))
                if lentry in self.cover_subdirs:
                    subdir = os.path.join(base, entry)
                    sub_entries = []
                    try:
                        sub_entries = os.listdir(subdir)
                    except EnvironmentError:
                        pass
                    for sub_entry in sub_entries:
                        lsub_entry = sub_entry.lower()
                        if get_ext(lsub_entry) in self.cover_exts:
                            fns.append((entry, sub_entry))

            for sub, fn in fns:
                dec_lfn = fsn2text(fn).lower()

                score = 0
                # check for the album label number
                labelid = self.song.get("labelid", "").lower()
                if labelid and labelid in dec_lfn:
                    score += 20

                # Track-related keywords
                values = self.song.list("~people") + [self.song("album")]
                lowers = [value.lower().strip() for value in values
                          if len(value) > 1]
                score += 2 * sum([value in dec_lfn for value in lowers])

                # Generic keywords
                score += 3 * sum(r.search(dec_lfn) is not None
                                 for r in self.cover_positive_regexes)

                score -= 2 * sum(r.search(dec_lfn) is not None
                                 for r in self.cover_negative_regexes)

                # print("[%s - %s]: Album art \"%s\" scores %d." %
                #         (self.song("artist"), self.song("title"), fn, score))
                if score > 0:
                    if sub is not None:
                        fn = os.path.join(sub, fn)
                    images.append((score, os.path.join(base, fn)))

        images.sort(reverse=True)
        for score, path in images:
            # could be a directory
            if not os.path.isfile(path):
                continue
            try:
                return open(path, "rb")
            except IOError:
                print_w("Failed reading album art \"%s\"" % path)

        return None
