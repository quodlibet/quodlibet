# Copyright 2013 Simonas Kazlauskas
#      2015-2025 Nick Boultbee
#           2019 Joschua Gandert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
from pathlib import Path


from quodlibet import _
from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.util.dprint import print_w, print_d
from quodlibet import config


def get_ext(p: Path) -> str:
    "Gets lowercase extension (no dot)"
    return p.suffix.lower().strip(".")


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
            if image := self.song.get_primary_image():
                print_d(
                    f"Found local embedded cover: {image}",
                    context=self.context,
                )
                return image.file
        return None


class FilesystemCover(CoverSourcePlugin):
    PLUGIN_ID = "filesystem-cover"
    PLUGIN_NAME = _("Filesystem cover")
    PLUGIN_DESC = _(
        "Uses commonly named images found in common directories alongside the song."
    )
    DEBUG = False

    cover_subdirs = {"scan", "scans", "images", "covers", "artwork"}
    cover_exts = {"jpg", "jpeg", "png", "gif"}

    cover_name_regexes = {re.compile(r) for r in (r"^folder$", r"^cover$", r"^front$")}
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
        # TODO: still deserves some more refactoring
        if not self.song.is_file:
            return None
        print_d("Searching for local cover", context=self.context)
        base = Path(self.song("~dirname")).resolve()
        if not (base.exists() and base.is_dir()):
            print_w(f"Directory doesn't exist: {base}", context=self.context)
            return None
        images = []

        if config.getboolean("albumart", "force_filename"):
            score = 100
            fns = config.get("albumart", "filename").split(",")
            for filename in fns:
                # Remove whitespace to avoid confusion (e.g. "name, name2")
                filename = filename.strip()
                for path in base.glob(filename):
                    images.append((score, path))
                    score -= 1
            if not images:
                # See #4488
                print_d(
                    f"No allowed cover files [{' | '.join(fns)}] found, "
                    f"so giving up for {self.song.key}.",
                    context=self.context,
                )
                return None
        else:
            paths = []
            try:
                paths = base.iterdir()
            except OSError:
                print_w(f"Can't list album art directory {base}", context=self.context)

            tuples = []
            for path in paths:
                if get_ext(path) in self.cover_exts:
                    tuples.append((None, path))
                if path.name.lower() in self.cover_subdirs:
                    subdir = base / path
                    sub_entries = []
                    try:
                        sub_entries = subdir.iterdir()
                    except OSError:
                        pass
                    for p in sub_entries:
                        if get_ext(p) in self.cover_exts:
                            tuples.append((path, p))

            for sub, path in tuples:
                dec_lfn = path.stem.lower()

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

                # Well-known names matching exactly (folder.jpg)
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
                        f"Album art {path}{sub_text} "
                        f"scores {score} ({length_penalty})"
                    )
                score += length_penalty

                # Let's only match if we're quite sure.
                # This allows other sources to kick in
                if score > 2:
                    if sub is not None:
                        path = Path(sub) / path
                    images.append((score, path))

        for _score, path in sorted(images, reverse=True):
            # could be a directory
            if not path.is_file():
                continue
            try:
                return path.open("rb")
            except OSError:
                print_w(f'Failed reading album art "{path}"', context=self.context)

        return None
