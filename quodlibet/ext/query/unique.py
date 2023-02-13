# Copyright 2023 LoveIsGrief
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from typing import Any, Optional

from quodlibet import _, print_d, print_w
from quodlibet.formats import AudioFile
from quodlibet.plugins.query import QueryPlugin, QueryPluginError


class UniqueQuery(QueryPlugin):
    PLUGIN_ID = "unique_query"
    PLUGIN_NAME = _("Unique Query")
    PLUGIN_DESC = _("Filter search results by unique tags.")
    key = 'unique'
    query_syntax = _("@(unique: tag)")
    query_description = "<tt>tag</tt> can be album, artist, title or any other tag. " \
        "Use multiple <tt>@(unique: tag)</tt> to filter by multiple tags."

    usage = f"{query_syntax}\n\n{query_description}"

    def __init__(self):
        self.unique_tag_values = set()
        """The unique tag values that have been seen in the songs being filtered"""
        self._reported = set()
        """Unique errors to counter error log spam"""

    def search(self, song: AudioFile, body: Optional[Any]) -> bool:
        return_value = False
        try:
            field_value = song[body]
            return_value = field_value not in self.unique_tag_values
            self.unique_tag_values.add(field_value)
            print_d(f"unique filtering value '{field_value}': {return_value}")
        except KeyError:
            pass
        except Exception as e:
            err_str = str(e)
            if err_str not in self._reported:
                self._reported.add(err_str)
                print_w(f"{type(e).__name__} while filtering unique values for "
                        f"'{body}': {err_str}")
        return return_value

    def parse_body(self, body: str) -> str:
        self.unique_tag_values.clear()
        if body is None:
            raise QueryPluginError
        unique_tag = body.strip()
        print_d(f"unique filtering tag: {unique_tag}")
        self._reported.clear()
        return unique_tag
