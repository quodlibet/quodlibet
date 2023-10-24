# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# TODO:
# RenameCommand
# FillTracknumberCommand

import ast
import os
import re
import shutil
import subprocess
import tempfile

from senf import fsn2text, text2fsn

from quodlibet import _
from quodlibet import util
from quodlibet.formats import EmbeddedImage, AudioFileError
from quodlibet.util.path import mtime
from quodlibet.pattern import Pattern, Error as PatternError
from quodlibet.util.tags import USER_TAGS, sortkey, MACHINE_TAGS
from quodlibet.util.tagsfrompath import TagsFromPattern

from .base import Command, CommandError
from .util import print_terse_table, copy_mtime, list_tags, print_table, \
    get_editor_args


@Command.register
class ListCommand(Command):
    NAME = "list"
    DESCRIPTION = _("List tags")
    USAGE = "[-a] [-t] [-c <c1>,<c2>...] <file>"

    def _add_options(self, p):
        p.add_option("-t", "--terse", action="store_true",
                     help=_("Print terse output"))
        p.add_option("-c", "--columns", action="store", type="string",
                     help=_("Columns to display and order in terse mode (%s)")
                     % "desc,value,tag")
        p.add_option("-a", "--all", action="store_true",
                     help=_("Also list programmatic tags"))

    def _execute(self, options, args):
        if len(args) < 1:
            raise CommandError(_("Not enough arguments"))
        elif len(args) > 1:
            raise CommandError(_("Too many arguments"))

        path = args[0]
        headers = [_("Description"), _("Value"), _("Tag")]
        nicks = ["desc", "value", "tag"]

        if not options.columns:
            order = nicks
        else:
            order = [n.strip() for n in options.columns.split(",")]

        song = self.load_song(path)
        tags = list_tags(song, machine=options.all, terse=options.terse)

        if options.terse:
            print_terse_table(tags, nicks, order)
        else:
            print_table(tags, headers, nicks, order)


@Command.register
class TagsCommand(Command):
    NAME = "tags"
    DESCRIPTION = _("List all common tags")
    USAGE = "[-t] [-c <c1>,<c2>...]"

    def _add_options(self, p):
        p.add_option("-t", "--terse", action="store_true",
                     help=_("Print terse output"))
        p.add_option("-c", "--columns", action="store", type="string",
                     help=_("Columns to display and order in terse mode (%s)")
                     % "tag,desc")
        p.add_option("-a", "--all", action="store_true",
                     help=_("Also list programmatic tags"))

    def _execute(self, options, args):
        if len(args) != 0:
            raise CommandError(_("Too many arguments"))

        headers = [_("Tag"), _("Description")]
        nicks = ["tag", "desc"]

        if not options.columns:
            order = nicks
        else:
            order = [n.strip() for n in options.columns.split(",")]

        tag_names = list(USER_TAGS)
        if options.all:
            tag_names.extend(MACHINE_TAGS)

        tags = []
        for key in tag_names:
            tags.append((key, util.tag(key)))
        tags.sort()

        if not options.terse:
            print_table(tags, headers, nicks, order)
        else:
            print_terse_table(tags, nicks, order)


@Command.register
class CopyCommand(Command):
    NAME = "copy"
    DESCRIPTION = _("Copy tags from one file to another")
    USAGE = "[--dry-run] [--ignore-errors] <source> <dest>"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help=_("Show changes, don't apply them"))
        p.add_option("--ignore-errors", action="store_true",
                     help=_("Skip tags that can't be written"))

    def _execute(self, options, args):
        if len(args) < 2:
            raise CommandError(_("Not enough arguments"))
        elif len(args) > 2:
            raise CommandError(_("Too many arguments"))

        if options.dry_run:
            self.verbose = True

        source_path = args[0]
        dest_path = args[1]

        source = self.load_song(source_path)
        dest = self.load_song(dest_path)

        for key in source.realkeys():
            self.log("Copy %r" % key)
            if not options.ignore_errors and not dest.can_change(key):
                raise CommandError(
                    _("Can't copy tag {tagname} to file: {filename}").format(
                        tagname=repr(key), filename=repr(dest_path)))
            for value in source.list(key):
                dest.add(key, value)

        if not options.dry_run:
            self.save_songs([dest])


@Command.register
class EditCommand(Command):
    NAME = "edit"
    DESCRIPTION = _("Edit tags in a text editor")
    USAGE = "[--dry-run] <file> [<files>]"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help=_("Show changes, don't apply them"))

    def _song_to_text(self, song):
        # to text
        lines = [
            u"File: %r" % fsn2text(song("~filename")),
            u"",
        ]
        for key in sorted(song.realkeys(), key=sortkey):
            for value in song.list(key):
                lines.append(u"  %s=%s" % (key, value))

        return u"\n".join(lines + [u""])

    def _songs_to_text(self, songs):
        header = [
            u"# Lines before the first 'File:' statement, or"
            u" lines that are empty or start with '#' will be ignored.",
            u"",
        ]
        return u"\n".join(header + [self._song_to_text(song) for song in songs])

    def _text_to_song(self, text, song):
        assert isinstance(text, str)

        # parse
        tags = {}
        for line in text.splitlines():
            if not line.strip() or line.startswith(u"#"):
                continue
            try:
                key, value = line.strip().split(u"=", 1)
            except ValueError:
                continue

            tags.setdefault(key, []).append(value)

        # apply changes, sort to always have the same output
        for key in sorted(song.realkeys(), key=sortkey):
            new = tags.pop(key, [])
            old = song.list(key)
            for value in old:
                if value not in new:
                    self.log("Remove %s=%s" % (key, value))
                    song.remove(key, value)
            for value in new:
                if value not in old:
                    self.log("Add %s=%s" % (key, value))
                    song.add(key, value)

        for key, values in tags.items():
            if not song.can_change(key):
                raise CommandError(
                    "Can't change key '%(key-name)s'." % {"key-name": key})
            for value in values:
                self.log("Add %s=%s" % (key, value))
                song.add(key, value)

    def _text_to_songs(self, text, songs):
        # remove comments
        text = re.sub(r"^#.*", "", text, count=0, flags=re.MULTILINE)
        # remove empty lines
        text = re.sub(r"(\r?\n){2,}", "\n", text.strip())
        _, *texts = re.split(r"^File:\s+", text, maxsplit=0, flags=re.MULTILINE)

        for text in texts:
            filename, *lines = text.splitlines()
            filename = text2fsn(ast.literal_eval(filename))
            text = u"\n".join(lines)

            song = next((song for song in songs if song("~filename") == filename), None)
            if not song:
                raise CommandError("No match for %r." % (filename))

            self.log("Update song: %r" % (filename))
            self._text_to_song(text, song)

    def _execute(self, options, args):
        if len(args) < 1:
            raise CommandError(_("Not enough arguments"))

        songs = [self.load_song(path) for path in args]
        dump = self._songs_to_text(songs).encode("utf-8")

        # write to tmp file
        fd, path = tempfile.mkstemp(suffix=".txt")

        try:
            try:
                os.write(fd, dump)
            finally:
                os.close(fd)

            # XXX: copy mtime here so we can test for changes in tests by
            # setting a out of date mtime on the source song file
            copy_mtime(args[0], path)

            # only parse the result if the editor returns 0 and the mtime has
            # changed
            old_mtime = mtime(path)

            editor_args = get_editor_args()
            self.log("Using editor: %r" % editor_args)

            try:
                subprocess.check_call(editor_args + [path])
            except subprocess.CalledProcessError as e:
                self.log(str(e))
                raise CommandError(_("Editing aborted")) from e
            except OSError as e:
                self.log(str(e))
                raise CommandError(
                    _("Starting text editor '%(editor-name)s' failed.") % {
                        "editor-name": editor_args[0]}) from e

            was_changed = mtime(path) != old_mtime
            if not was_changed:
                raise CommandError(_("No changes detected"))

            with open(path, "rb") as h:
                data = h.read()

        finally:
            os.unlink(path)

        try:
            text = data.decode("utf-8")
        except ValueError as e:
            raise CommandError(f"Invalid data: {e!r}") from e

        if options.dry_run:
            self.verbose = True
        self._text_to_songs(text, songs)

        if not options.dry_run:
            self.save_songs(songs)


@Command.register
class SetCommand(Command):
    NAME = "set"
    DESCRIPTION = _("Set a tag and remove existing values")
    USAGE = "[--dry-run] <tag> <value> <file> [<files>]"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help=_("Show changes, don't apply them"))

    def _execute(self, options, args):
        if len(args) < 3:
            raise CommandError(_("Not enough arguments"))

        tag = fsn2text(args[0])
        value = fsn2text(args[1])
        paths = args[2:]

        songs = []
        for path in paths:
            song = self.load_song(path)

            if not song.can_change(tag):
                vars = {"tag": tag, "format": type(song).format,
                        "file": song("~filename")}
                raise CommandError(
                    _("Can not set %(tag)r for %(format)s file %(file)r") % vars)

            self.log("Set %r to %r" % (value, tag))
            if tag in song:
                del song[tag]
            song.add(tag, value)
            songs.append(song)

        if not options.dry_run:
            self.save_songs(songs)


@Command.register
class ClearCommand(Command):
    NAME = "clear"
    DESCRIPTION = _("Remove tags")
    USAGE = "[--dry-run] [-a | -e <pattern> | <tag>] <file> [<files>]"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help=_("Show changes, don't apply them"))
        p.add_option("-e", "--regexp", action="store", type="string",
                     help=_("Value is a regular expression"))
        p.add_option("-a", "--all", action="store_true",
                     help=_("Remove all tags"))

    def _execute(self, options, args):
        if options.all and options.regexp is not None:
            raise CommandError(_("Can't combine '--all' with '--regexp'"))

        if options.regexp is not None or options.all:
            if len(args) < 1:
                raise CommandError(_("Not enough arguments"))
            paths = args
        else:
            if len(args) < 2:
                raise CommandError(_("Not enough arguments"))
            paths = args[1:]

        if options.dry_run:
            self.verbose = True

        songs = []
        for path in paths:
            song = self.load_song(path)

            tags = []
            realkeys = song.realkeys()
            if options.all:
                tags.extend(realkeys)
            elif options.regexp is not None:
                e = re.compile(options.regexp)
                tags.extend(filter(e.match, realkeys))
            else:
                tag = args[0]
                if tag in realkeys:
                    tags.append(tag)

            for tag in tags:
                self.log("Remove tag %r" % tag)
                if not song.can_change(tag):
                    raise CommandError(
                        _("Can't remove {tagname} from {filename}").format(
                            tagname=repr(tag), filename=repr(path)))
                del song[tag]

            if tags:
                songs.append(song)

        if not options.dry_run:
            self.save_songs(songs)


@Command.register
class RemoveCommand(Command):
    NAME = "remove"
    DESCRIPTION = _("Remove a tag value")
    USAGE = "[--dry-run] <tag> [-e <pattern> | <value>] <file> [<files>]"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help=_("Show changes, don't apply them"))
        p.add_option("-e", "--regexp", action="store", type="string",
                     help=_("Value is a regular expression"))

    def _execute(self, options, args):
        if options.regexp is None:
            if len(args) < 3:
                raise CommandError(_("Not enough arguments"))
        else:
            if len(args) < 2:
                raise CommandError(_("Not enough arguments"))

        if options.dry_run:
            self.verbose = True

        tag = args[0]
        if options.regexp is not None:
            match = re.compile(options.regexp).match
            paths = args[1:]
        else:
            value = args[1]
            paths = args[2:]
            def match(v):
                return v == value

        songs = []
        for path in paths:
            song = self.load_song(path)

            if tag not in song:
                continue

            for v in song.list(tag):
                if match(v):
                    self.log("Remove %r from %r" % (v, tag))
                    song.remove(tag, v)
            songs.append(song)

        if not options.dry_run:
            self.save_songs(songs)


@Command.register
class AddCommand(Command):
    NAME = "add"
    DESCRIPTION = _("Add a tag value")
    USAGE = "<tag> <value> <file> [<files>]"

    def _execute(self, options, args):
        if len(args) < 3:
            raise CommandError(_("Not enough arguments"))

        tag = fsn2text(args[0])
        value = fsn2text(args[1])
        paths = args[2:]

        songs = []
        for path in paths:
            song = self.load_song(path)

            if not song.can_change(tag):
                raise CommandError(_("Can not set %r") % tag)

            self.log("Add %r to %r" % (value, tag))
            song.add(tag, value)
            songs.append(song)

        self.save_songs(songs)


@Command.register
class InfoCommand(Command):
    NAME = "info"
    DESCRIPTION = _("List file information")
    USAGE = "[-t] [-c <c1>,<c2>...] <file>"

    def _add_options(self, p):
        p.add_option("-t", "--terse", action="store_true",
                     help=_("Print terse output"))
        p.add_option("-c", "--columns", action="store", type="string",
                     help=_("Columns to display and order in terse mode (%s)")
                     % "desc,value")

    def _execute(self, options, args):
        if len(args) < 1:
            raise CommandError(_("Not enough arguments"))
        elif len(args) > 1:
            raise CommandError(_("Too many arguments"))

        path = args[0]
        song = self.load_song(path)

        headers = [_("Description"), _("Value")]
        nicks = ["desc", "value"]

        if not options.columns:
            order = nicks
        else:
            order = [n.strip() for n in options.columns.split(",")]

        if not options.terse:
            tags = []
            for key in ["~format", "~codec", "~encoding", "~length",
                        "~bitrate", "~filesize"]:
                tags.append((util.tag(key), str(song.comma(key))))

            print_table(tags, headers, nicks, order)
        else:
            tags = []
            for key in ["~format", "~codec", "~encoding", "~#length",
                        "~#bitrate", "~#filesize"]:
                tags.append((key.lstrip("#~"), str(song(key))))

            print_terse_table(tags, nicks, order)


@Command.register
class ImageSetCommand(Command):
    NAME = "image-set"
    DESCRIPTION = _("Set the provided image as primary embedded image and "
                    "remove all other embedded images")
    USAGE = "<image-file> <file> [<files>]"

    def _execute(self, options, args):
        if len(args) < 2:
            raise CommandError(_("Not enough arguments"))

        image_path = args[0]
        paths = args[1:]

        image = EmbeddedImage.from_path(image_path)
        if not image:
            raise CommandError(_("Failed to load image file: %r") % image_path)

        songs = [self.load_song(p) for p in paths]

        for song in songs:
            if not song.can_change_images:
                raise CommandError(
                    _("Image editing not supported for %(file_name)s "
                      "(%(file_format)s)") % {
                      "file_name": song("~filename"),
                      "file_format": song("~format")
                    })

        for song in songs:
            try:
                song.set_image(image)
            except AudioFileError as e:
                raise CommandError(e) from e


@Command.register
class ImageClearCommand(Command):
    NAME = "image-clear"
    DESCRIPTION = _("Remove all embedded images")
    USAGE = "<file> [<files>]"

    def _execute(self, options, args):
        if len(args) < 1:
            raise CommandError(_("Not enough arguments"))

        paths = args
        songs = [self.load_song(p) for p in paths]

        for song in songs:
            if not song.can_change_images:
                raise CommandError(
                    _("Image editing not supported for %(file_name)s "
                      "(%(file_format)s)") % {
                      "file_name": song("~filename"),
                      "file_format": song("~format")
                    })

        for song in songs:
            try:
                song.clear_images()
            except AudioFileError as e:
                raise CommandError(e) from e


@Command.register
class ImageExtractCommand(Command):
    NAME = "image-extract"
    DESCRIPTION = (
        _("Extract embedded images to %(filepath)s") % {
            "filepath": "<destination>/<filename>-<index>.(jpeg|png|..)"
        }
    )
    USAGE = "[--dry-run] [--primary] [-d <destination>] <file> [<files>]"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help="don't save images")
        p.add_option("--primary", action="store_true",
                     help="only extract the primary image")
        p.add_option("-d", "--destination", action="store", type="string",
                     help=_("Path to where the images will be saved to "
                            "(defaults to the working directory)"))

    def _execute(self, options, args):
        if len(args) < 1:
            raise CommandError(_("Not enough arguments"))

        # dry run implies verbose
        if options.dry_run:
            self.verbose = True

        paths = args
        for path in paths:
            song = self.load_song(path)

            # get the primary one or all of them
            if options.primary:
                image = song.get_primary_image()
                images = [image] if image else []
            else:
                images = song.get_images()

            self.log("Images for %r: %r" % (path, images))

            if not images:
                continue

            # get the basename from the song without the extension
            basename = os.path.basename(path)
            name = os.path.splitext(basename)[0]

            # at least two places, but same length for all images
            number_pattern = "%%0%dd" % (max(2, len(images) - 1))

            for i, image in enumerate(images):
                # get a appropriate file extension or use fallback
                extensions = image.extensions
                ext = extensions[0] if extensions else ".image"

                if options.primary:
                    # mysong.mp3 -> mysong.jpeg
                    filename = "%s.%s" % (name, ext)
                else:
                    # mysong.mp3 -> mysong-00.jpeg
                    pattern = "%s-" + number_pattern + ".%s"
                    filename = pattern % (name, i, ext)

                if options.destination is not None:
                    filename = os.path.join(options.destination, filename)

                self.log("Saving image %r" % filename)
                if not options.dry_run:
                    with open(filename, "wb") as h:
                        shutil.copyfileobj(image.file, h)


# @Command.register
class RenameCommand(Command):
    NAME = "rename"
    DESCRIPTION = _("Rename files based on tags")
    USAGE = "[--dry-run] <pattern> <file> [<files>]"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help="show changes, don't apply them")

    def _execute(self, options, args):
        if len(args) < 1:
            raise CommandError("Not enough arguments")


@Command.register
class FillCommand(Command):
    NAME = "fill"
    DESCRIPTION = _("Fill tags based on the file path")
    USAGE = "[--dry-run] <pattern> <file> [<files>]"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help="show changes, don't apply them")

    def _execute(self, options, args):
        if len(args) < 2:
            raise CommandError("Not enough arguments")

        pattern_text = args[0]
        self.log("Using pattern: %r" % pattern_text)
        paths = args[1:]

        pattern = TagsFromPattern(pattern_text)

        songs = []
        for path in paths:
            song = self.load_song(path)
            for header in pattern.headers:
                if not song.can_change(header):
                    raise CommandError(_("Can not set %r") % header)
            songs.append(song)

        if options.dry_run:
            self.__preview(pattern, songs)
        else:
            self.__apply(pattern, songs)

    def __apply(self, pattern, songs):
        for song in songs:
            match = pattern.match(song)
            self.log("%r: %r" % (song("~basename"), match))
            for header in pattern.headers:
                if header in match:
                    value = match[header]
                    song[header] = value

        self.save_songs(songs)

    def __preview(self, pattern, songs):
        rows = []
        for song in songs:
            match = pattern.match(song)
            row = [fsn2text(song("~basename"))]
            for header in pattern.headers:
                row.append(match.get(header, u""))
            rows.append(row)

        headers = [_("File")] + pattern.headers
        nicks = ["file"] + pattern.headers
        print_table(rows, headers, nicks, nicks)


# @Command.register
class FillTracknumberCommand(Command):
    NAME = "fill-tracknumber"
    DESCRIPTION = _("Fill tracknumbers for all files")
    USAGE = "[--dry-run] [--start] [--total] <file> [<files>]"

    def _add_options(self, p):
        p.add_option("--dry-run", action="store_true",
                     help="show changes, don't apply them")
        p.add_option("--start", action="store_true",
                     help="tracknumber to start with")
        p.add_option("--total", action="store_true",
                     help="total number of tracks")

    def _execute(self, options, args):
        if len(args) < 1:
            raise CommandError("Not enough arguments")


@Command.register
class PrintCommand(Command):
    NAME = "print"
    DESCRIPTION = _("Print tags based on the given pattern")
    USAGE = "[-p <pattern>] <file> [<files>]"

    def _add_options(self, p):
        p.add_option("-p", "--pattern", action="store", type="string",
                     help="use a custom pattern")

    def _execute(self, options, args):
        if len(args) < 1:
            raise CommandError("Not enough arguments")

        pattern = options.pattern
        if pattern is None:
            pattern = "<artist~album~tracknumber~title>"

        self.log("Using pattern: %r" % pattern)

        try:
            pattern = Pattern(pattern)
        except PatternError as e:
            raise CommandError(f"Invalid pattern: {pattern!r}") from e

        paths = args
        error = False
        for path in paths:
            try:
                util.print_(pattern % self.load_song(path))
            except CommandError:
                error = True

        if error:
            raise CommandError("One or more files failed to load.")


@Command.register
class HelpCommand(Command):
    NAME = "help"
    DESCRIPTION = _("Display help information")
    USAGE = "[<command>]"

    def _execute(self, options, args):
        if len(args) > 1:
            raise CommandError("Too many arguments")

        for cmd in Command.COMMANDS:
            if cmd.NAME == args[0]:
                cmd(self._main_cmd).print_help()
                break
        else:
            raise CommandError("Unknown command")
