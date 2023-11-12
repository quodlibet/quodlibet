# Copyright 2016 Ryan Dellenbaugh
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import random
import time

from quodlibet import _, print_d, print_w
from quodlibet.plugins.query import QueryPlugin, QueryPluginError, markup_for_syntax


class PythonQuery(QueryPlugin):
    PLUGIN_ID = "python_query"
    PLUGIN_NAME = _("Python Query")
    PLUGIN_DESC = _("🐍Use Python expressions in queries.")
    key = "python"
    query_syntax = _("@(python: expression)")
    query_description = _(
        "The variable <tt>s</tt> (or <tt>a</tt>) is the song / album being "
        "matched."
        "\n\n"
        "<tt>_ts</tt> is a (real number) timestamp at start of query."
        "\n\n"
        "Modules <tt>time</tt> and <tt>random</tt> are also available, and the "
        "class <tt>Random</tt> (==<tt>random.Random</tt>) too.")
    usage = markup_for_syntax(query_syntax) + "\n\n" + query_description

    def __init__(self):
        print_d("Initialising")
        self._globals = {"random": random, "Random": random.Random,
                         "time": time}
        self._reported = set()
        self._raw_body = None

    def search(self, data, body):
        try:
            self._globals["s"] = data
            # Albums can be queried too...
            self._globals["a"] = data
            # eval modifies the globals in place, it seems
            ret = eval(body, dict(self._globals))
            return ret
        except Exception as e:
            key = str(e)
            if key not in self._reported:
                self._reported.add(key)
                print_w(f"{type(e).__name__}({key}) in expression {self._raw_body!r}. "
                        f"Example failing data: {self._globals}")
            return False

    def parse_body(self, body):
        if body is None:
            raise QueryPluginError
        self._raw_body = body.strip()
        self._reported.clear()
        try:
            self._globals.update(_ts=time.time())
            return compile(body.strip(), "query", "eval")
        except SyntaxError as e:
            print_w("Couldn't compile query (%s)" % e)
            raise QueryPluginError from e
