# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
import operator
from collections import defaultdict
from datetime import datetime

from quodlibet import print_d
from quodlibet.formats import AudioFile
from quodlibet.query import Query, QueryType
from quodlibet.query._match import Tag, Inter, Union, Numcmp, NumexprTag, \
    Numexpr, True_, error, False_

error

INVERSE_OPS = {operator.le: operator.gt,
               operator.gt: operator.le,
               operator.lt: operator.ge,
               operator.ge: operator.lt}

_DUMMY_AF = AudioFile()
_CLOCK = time.time


def convert_time(t):
    return datetime.strftime(datetime.fromtimestamp(int(t)),
                             '%Y-%m-%d %H:%S')

# Convert QL to Soundcloud tags with optional value mapper
_QL_TO_SC = {
    'genre': ('genres', None),
    'length': ('duration', lambda x: int((x or 0) * 1000)),
    'date': ('created_at', convert_time),
    'tags': ('tags', None),
    'bpm': ('bpm', None),
    'artist': ('q', None),
    'title': ('q', None),
    'comments': ('q', None),
    'soundcloud_user_id': ('user_id', None)
}
SUPPORTED = set(_QL_TO_SC.keys()) | {"rating"}


class SoundcloudQuery(Query):

    def __init__(self, string, star=None, clock=time.time):
        super().__init__(string, star)
        self._clock = clock
        try:
            self.terms = self._extract_terms(self._match)
        except self.error as e:
            print_d("Couldn't use query: %s" % e)
            self.type = QueryType.INVALID
            self.terms = {}

    def _extract_terms(self, node):
        """ Return a dict of sets keyed on API search term,
            with values for these that could be used to query the API
            and might return results useful for populating the songlist.

            Note this is not a *translation* of the query in any sense,
            and that (currently) the browser filters ingested API results
            so that the QL results are still valid based on
            the query given, even if some more could have been returned.

            ...so if in doubt, *less* restrictive is better here."""
        tuples = self._extract_terms_set(node)
        terms = defaultdict(set)
        for (k, v) in tuples:
            terms[k].add(v)
        return terms

    def _extract_terms_set(self, node, tag=None):
        def to_api(tag, raw_value):
            try:
                api_tag, converter = _QL_TO_SC[tag] if tag else ('q', None)
            except KeyError:
                if tag not in SUPPORTED:
                    raise self.error("Unsupported '%s' tag. Try: %s"
                                     % (tag, ", ". join(SUPPORTED)))
                return None, None
            else:
                value = str(converter(raw_value) if converter else raw_value)
                return api_tag, value

        def terms_from_re(pattern, t):
            """Best efforts to de-regex"""
            pat = pattern.lstrip('^').rstrip('$')
            api_tag, pat = to_api(t, pat)
            return {(api_tag, p) for p in pat.split('|')} if api_tag else set()

        if isinstance(node, Tag) and set(node._names) & SUPPORTED:
            if len(node._names) == 1:
                return self._extract_terms_set(node.res, tag=node._names[0])
            return self._extract_terms_set(node.res)
        elif isinstance(node, Inter) or isinstance(node, Union):
            # Treat identically as the text-based query will perform
            # relevance ranking itself, meaning that any term is still useful
            terms = set()
            for n in node.res:
                terms |= self._extract_terms_set(n)
            return terms
        elif isinstance(node, Numcmp):
            def from_relative(op, l, r):
                raw_value = r.evaluate(_DUMMY_AF, self._clock(), True)
                tag, value = to_api(l._tag, raw_value)
                if not value:
                    return set()
                if op == operator.eq:
                    return {(tag, value)}
                elif op in (operator.le, operator.lt):
                    return {(tag + "[to]", value)}
                elif op in (operator.ge, operator.gt):
                    return {(tag + "[from]", value)}
                raise self.error("Unsupported operator: %s" % op)

            left = node._expr
            right = node._expr2
            if isinstance(left, NumexprTag) and isinstance(right, Numexpr):
                return from_relative(node._op, left, right)
            elif isinstance(right, NumexprTag) and isinstance(left, Numexpr):
                # We can reduce the logic by flipping the expression
                return from_relative(INVERSE_OPS[node._op], right, left)
            raise self.error("Unsupported numeric: %s" % node)
        elif hasattr(node, 'pattern'):
            return terms_from_re(node.pattern, tag)
        elif isinstance(node, True_):
            return set()
        elif isinstance(node, False_):
            raise self.error("False can never be queried")
        raise self.error("Unhandled node: %r" % (node,))
