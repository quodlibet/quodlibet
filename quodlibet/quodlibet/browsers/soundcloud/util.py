# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
from collections import defaultdict
from datetime import datetime
from gi.repository import Gtk

import operator

from quodlibet.util.dprint import print_w

from quodlibet.query._match import Inter, Tag, Union, Numcmp, NumexprTag, \
    NumexprNumber

from quodlibet import print_d
from quodlibet.util.path import normalize_path

DEFAULT_BITRATE = 128
EPOCH = datetime(1970, 1, 1)
SITE_URL = "http://soundcloud.com"
IMAGE_DIR = normalize_path(
    path.join(path.dirname(__file__), '../../images/branding/soundcloud'))


def _local_image(filename):
    """
    Get a local branding image from disk
    TODO: load these from the web (and cache)
    """
    return Gtk.Image.new_from_file(path.join(IMAGE_DIR, filename))


LOGO_IMAGE_BLACK = _local_image('soundcloud-logo-black-104x16.png')
LOGIN_IMAGES = [_local_image('btn-%s-l.png'
                             % ('disconnect' if online else 'connect'))
                for online in (False, True)]


class Wrapper(object):
    """Object-like wrapper for read-only dictionaries"""

    def __init__(self, data):
        self.data = data

    def __getattr__(self, name):
        if name in self.data:
            return self.data.get(name)
        raise AttributeError(name)

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        raise NotImplementedError

    def get(self, name, default=None):
        return self.data.get(name, default)

    def __str__(self):
        return "<Wrapped: %s>" % self.data


def json_callback(wrapped):
    """Decorator for `download_json` callbacks, handling common errors"""

    def _callback(self, message, json, data):
        if json is None:
            print_d('Invalid JSON ({message.status_code}): '
                    '{message.response_body.data} (request: {data})'
                    .format(**locals()))
            return
        if 'errors' in json:
            raise ValueError("Got HTTP %d (%s)" % (message.status_code,
                                                   json['errors']))
        if 'error' in json:
            raise ValueError("Got HTTP %d (%s)" % (message.status_code,
                                                   json['error']))
        return wrapped(self, json)

    return _callback


def clamp(val, low, high):
    intval = int(val or 0)
    return max(low, min(high, intval))


INVERSE_OPS = {operator.le: operator.gt,
               operator.gt: operator.le,
               operator.lt: operator.ge,
               operator.ge: operator.lt}


def extract(node):
    """Return a list of tuples of search terms
        that could be used to query the API
        and might return results useful for populating the songlist

        Note this is not a *translation* of the query in any sense,
        and that (currently) the browser filters ingested API results properly
        (given the tag mappings) so that the QL results are still valid
        based on
        the query given, even if some more could have been returned.
        ...so if in doubt, less restrictive is better here."""
    tuples = _extract_terms(node)
    terms = defaultdict(set)
    for (k, v) in tuples:
        terms[k].add(v)
    return terms

SUPPORTED = {'artist', 'title', 'genre', 'tags', 'album', 'comment'}


def _extract_terms(node):
    def terms_from_re(pattern):
        """Best efforts to de-regex"""
        pat = pattern.lstrip('^').rstrip('$')
        return {('q', p) for p in pat.split('|')}

    if isinstance(node, Tag) and set(node._names) & SUPPORTED:
        print_d("%r is a supported Tag" % (node,))
        return _extract_terms(node.res)
    elif isinstance(node, Inter) or isinstance(node, Union):
        # return reduce(lambda t, n: operator.ior(t, extract(n)),
        #               node.res, set())
        terms = set()
        for n in node.res:
            terms |= _extract_terms(n)
        return terms
    elif isinstance(node, Numcmp):
        def from_relative(op, l, r):
            tag = l._tag
            value = r._value
            if op == operator.eq:
                return {(tag, value)}
            elif op in (operator.le, operator.lt):
                return {(tag + "[to]", value)}
            elif op in (operator.ge, operator.gt):
                return {(tag + "[from]", value)}
            print_w("Unsupported operator: %s" % op)

        left = node._expr
        right = node._expr2
        if isinstance(left, NumexprTag) and isinstance(right, NumexprNumber):
            return from_relative(node._op, left, right)
        elif isinstance(right, NumexprTag) and isinstance(left, NumexprNumber):
            return from_relative(INVERSE_OPS[node._op], right, left)
        print_w("Unsupported numeric: %s" % node)
    elif hasattr(node, 'pattern'):
        return terms_from_re(node.pattern)
    print_d("Unhandled node of type '%s'" % (type(node).__name__))
    return set()
