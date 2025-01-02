# Copyright 2019 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import unicodedata

_remove_punctuation_trans = dict.fromkeys(
    i for i in range(sys.maxunicode) if unicodedata.category(chr(i)).startswith("P")
)


def remove_punctuation(s: str) -> str:
    """Removes all known Unicode punctuation from the given string"""
    return s.translate(_remove_punctuation_trans)


def remove_diacritics(s: str) -> str:
    """Canonicalises and removes all diacritics from the given string"""
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c)
    )
