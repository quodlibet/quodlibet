# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Functions for adjusting regular expressions so that ASCII characters in
them match similar looking unicode characters.

re_add_variants(u"Mum") =>
    u"[MḾṀṂ][uùúûüũūŭůűųưǔǖǘǚǜȕȗṳṵṷṹṻụủứừửữự][mḿṁṃ]"

This is similar to Asymmetric Search:
    http://unicode.org/reports/tr10/#Asymmetric_Search

The goal is to make searching easy using a english keyboard without any
knowledge of other languages.
"""

from .parser import compile


compile
