# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Iñigo Serna, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import locale
import re

from quodlibet import _

from .iso639 import ISO_639_2


class ValidationError(Exception):
    pass


class Massager:
    """Massage a tag value from various 'okay' formats to the
    'correct' format."""

    tags: list[str] = []
    error = "Metaerror. This should be overridden in subclasses."
    options: list[str] = []

    _massagers: "dict[str, Massager]" = {}

    def validate(self, value):
        """Returns a validated value.

        Raises ValidationError if invalid.
        """

        raise NotImplementedError

    def is_valid(self, value):
        """Returns True if a field is valid, False if not"""

        try:
            self.validate(value)
        except ValidationError:
            return False
        return True

    @classmethod
    def _register(cls, other):
        """Register a new massager implementation"""

        assert issubclass(other, Massager)
        assert other.tags
        for tag in other.tags:
            cls._massagers[tag] = other
        return other

    @classmethod
    def get_massagers(cls):
        """Returns all massager subclasses"""

        return set(cls._massagers.values())

    @classmethod
    def for_tag(cls, tag):
        """Returns a massager instance for the tag or raises KeyError"""

        return cls._massagers[tag]()


def validate(tag, value):
    """Validate a value based on the tag.

    Raises ValidationError if invalid
    """

    try:
        return Massager.for_tag(tag).validate(value)
    except KeyError:
        return value


def is_valid(tag, value):
    """Returns True if the fields is valid"""

    try:
        return Massager.for_tag(tag).is_valid(value)
    except KeyError:
        return True


def error_message(tag, value):
    """Returns an error message for invalid tag values"""

    try:
        return Massager.for_tag(tag).error
    except KeyError:
        return ""


def get_options(tag):
    """Returns a list of suggested values for the tag. If the list is empty
    this either means that the tag is unknown or the set of valid values would
    be too large"""

    try:
        return list(Massager.for_tag(tag).options)
    except KeyError:
        return []


@Massager._register
class DateMassager(Massager):
    tags = ["date"]
    error = _(
        "The date must be entered in 'YYYY', 'YYYY-MM-DD' or "
        "'YYYY-MM-DD HH:MM:SS' format."
    )
    __match = re.compile(
        r"^\d{4}([-.]\d{2}([-.]\d{2}([T ]\d{2}" r"([:.]\d{2}([:.]\d{2})?)?)?)?)?$"
    ).match

    def validate(self, value):
        value = value.strip().replace(".", "-").replace("/", "-")
        if not self.__match(value):
            raise ValidationError
        return value


@Massager._register
class GainMassager(Massager):
    tags = ["replaygain_album_gain", "replaygain_track_gain"]
    error = _("Replay Gain gains must be entered in 'x.yy dB' format.")
    __match = re.compile(r"^[+-]\d+\.?\d+?\s+dB$").match

    def validate(self, value):
        if self.__match(value):
            return value
        else:
            try:
                f = float(value.split()[0])
            except (IndexError, TypeError, ValueError):
                try:
                    f = locale.atof(value.split()[0])
                except (IndexError, TypeError, ValueError) as e:
                    raise ValidationError from e
            else:
                return (f"{f:+f}").rstrip("0") + " dB"


@Massager._register
class PeakMassager(Massager):
    tags = ["replaygain_album_peak", "replaygain_track_peak"]
    error = _("Replay Gain peaks must be entered in 'x.yy' format.")

    def validate(self, value):
        value = value.strip()
        try:
            f = float(value)
        except (TypeError, ValueError):
            try:
                f = locale.atof(value)
            except (TypeError, ValueError) as e:
                raise ValidationError from e
        else:
            if f < 0 or f >= 2:
                raise ValidationError
            return str(f)


@Massager._register
class MBIDMassager(Massager):
    tags = [
        "musicbrainz_trackid",
        "musicbrainz_albumid",
        "musicbrainz_artistid",
        "musicbrainz_albumartistid",
        "musicbrainz_trmid",
        "musicip_puid",
    ]
    error = _("MusicBrainz IDs must be in UUID format.")

    def validate(self, value):
        value = value.encode("ascii", "replace").decode("ascii")
        value = "".join(filter(str.isalnum, value.strip().lower()))
        try:
            int(value, 16)
        except ValueError as e:
            raise ValidationError from e
        else:
            if len(value) != 32:
                raise ValidationError
            else:
                return "-".join(
                    [value[:8], value[8:12], value[12:16], value[16:20], value[20:]]
                )


@Massager._register
class MBAlbumStatus(Massager):
    tags = ["musicbrainz_albumstatus"]
    # Translators: Leave "official", "promotional", and "bootleg"
    # untranslated. They are the three possible literal values.
    error = _(
        "MusicBrainz release status must be 'official', " "'promotional', or 'bootleg'."
    )
    options = ["official", "promotional", "bootleg"]

    def validate(self, value):
        if value not in self.options:
            raise ValidationError
        return value


@Massager._register
class LanguageMassager(Massager):
    tags = ["language"]
    error = _("Language must be an ISO 639-2 three-letter code")

    options = ISO_639_2

    tags = ["language"]

    def validate(self, value):
        # Issue 439: Actually, allow free-text through
        return value

    def is_valid(self, value):
        # Override, to allow empty string to be a valid language (freetext)
        return True
