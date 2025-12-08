# Copyright 2013 Simonas Kazlauskas
#      2015-2020 Nick Boultbee
#           2019 Joschua Gandert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import glob
import os.path
import re

from senf import fsn2text

from quodlibet import _
from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.util.dprint import print_w, print_d
from quodlibet import config


def prefer_embedded():
    return config.getboolean("albumart", "prefer_embedded", False)


def word_regex(s: str) -> re.Pattern:
    return re.compile(r"(\b|_)" + s + r"(\b|_)")


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
        return None


class FilesystemCover(CoverSourcePlugin):
    PLUGIN_ID = "filesystem-cover"
    PLUGIN_NAME = _("Filesystem cover")
    PLUGIN_DESC = _(
        "Uses commonly named images found in common directories alongside the song."
    )
    DEBUG = False

    cover_subdirs = {"scan", "scans", "images", "covers", "artwork"}
    cover_exts = (".jpg", ".jpeg", ".png", ".gif")

    cover_name_regexes = {re.compile(s) for s in ("^folder$", "^cover$", "^front$")}
    cover_positive_regexes = {
        word_regex(s)
        for s in [".+front", "frontcover", "jacket", "albumart", "edited", ".+cover"]
    }
    cover_negative_regexes = {
        word_regex(s) for s in ["back", "inlay", "inset", "inside"]
    }

    @classmethod
    def group_by(cls, song):
        # in the common case this means we only search once per album
        return song("~dirname"), song.album_key

    @property
    def name(self):
        return "Filesystem"

    def __str__(self):
        return f"Filesystem in {self.group_by(self.song)[0]}"

    @staticmethod
    def priority():
        return 0.80

    @property
    def cover(self):
        # TODO: Deserves some refactoring
        if not self.song.is_file:
            return None
        print_d(f"Searching for local cover for {self.song('~filename')}")
        base = self.song("~dirname")
        images = []

        if config.getboolean("albumart", "force_filename"):
            score = 100
            for filename in config.get("albumart", "filename").split(","):
                # Remove white space to avoid confusion (e.g. "name, name2")
                filename = filename.strip()

                escaped_path = os.path.join(glob.escape(base), filename)
                for path in glob.glob(escaped_path):
                    images.append((score, path))
                    # Adhere to the user-defined filename/pattern order
                    score -= 1

        if not images:
            try:
                entries = os.listdir(base)
            except OSError:
                entries = []
                print_w(f"Can't list album art directory {base}")

            fns = []
            for entry in entries:
                lentry = entry.lower()
                if lentry.endswith(self.cover_exts):
                    fns.append((None, entry))
                if lentry in self.cover_subdirs:
                    try:
                        sub_entries = os.listdir(os.path.join(base, entry))
                    except OSError:
                        sub_entries = []
                    for sub_entry in sub_entries:
                        if sub_entry.lower().endswith(self.cover_exts):
                            fns.append((entry, sub_entry))

            for sub, fn in fns:
                dec_lfn = os.path.splitext(fsn2text(fn))[0].lower()

                score = 0
                # check for the album label number
                labelid = self.song.get("labelid", "").lower()
                if labelid and labelid in dec_lfn:
                    score += 20

                # Track-related keywords
                values = set(self.song.list("~people")) | {self.song("album")}
                lowers = [value.lower().strip() for value in values if len(value) > 1]
                total_terms = sum(len(s.split()) for s in lowers)
                total_words = len([word for word in dec_lfn.split() if len(word) > 1])
                # Penalise for many extra words in filename (wrong file?)
                length_penalty = (
                    -int((total_words - 1) / total_terms) if total_terms else 0
                )

                # Matching tag values are very good
                score += 3 * sum([value in dec_lfn for value in lowers])

                # Well known names matching exactly (folder.jpg)
                score += 4 * sum(
                    r.search(dec_lfn) is not None for r in self.cover_name_regexes
                )

                # Generic keywords
                score += 2 * sum(
                    r.search(dec_lfn) is not None for r in self.cover_positive_regexes
                )

                score -= 3 * sum(
                    r.search(dec_lfn) is not None for r in self.cover_negative_regexes
                )

                sub_text = f" (in {sub!r})" if sub else ""
                if self.DEBUG:
                    print(
                        f"[{self.song('~~people~title')}]: "
                        f"Album art {fn!r}{sub_text} "
                        f"scores {score} ({length_penalty})"
                    )
                score += length_penalty

                # Let's only match if we're quite sure.
                # This allows other sources to kick in
                if score > 2:
                    if sub is not None:
                        fn = os.path.join(sub, fn)
                    images.append((score, os.path.join(base, fn)))

        images.sort(reverse=True)
        for _score, path in images:
            # could be a directory
            if not os.path.isfile(path):
                continue
            try:
                return open(path, "rb")
            except OSError:
                print_w(f'Failed reading album art "{path}"')

        return None
