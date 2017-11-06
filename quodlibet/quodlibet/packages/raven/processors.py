"""
raven.core.processors
~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
from __future__ import absolute_import

import re

from raven.utils.compat import string_types, text_type
from raven.utils import varmap


class Processor(object):
    def __init__(self, client):
        self.client = client

    def get_data(self, data, **kwargs):
        return

    def process(self, data, **kwargs):
        resp = self.get_data(data, **kwargs)
        if resp:
            data = resp

        if 'exception' in data:
            if 'values' in data['exception']:
                for value in data['exception'].get('values', []):
                    if 'stacktrace' in value:
                        self.filter_stacktrace(value['stacktrace'])

        if 'request' in data:
            self.filter_http(data['request'])

        if 'extra' in data:
            data['extra'] = self.filter_extra(data['extra'])

        return data

    def filter_stacktrace(self, data):
        pass

    def filter_http(self, data):
        pass

    def filter_extra(self, data):
        return data


class RemovePostDataProcessor(Processor):
    """Removes HTTP post data."""

    def filter_http(self, data, **kwargs):
        data.pop('data', None)


class RemoveStackLocalsProcessor(Processor):
    """Removes local context variables from stacktraces."""

    def filter_stacktrace(self, data, **kwargs):
        for frame in data.get('frames', []):
            frame.pop('vars', None)


class SanitizePasswordsProcessor(Processor):
    """
    Asterisk out things that look like passwords, credit card numbers,
    and API keys in frames, http, and basic extra data.
    """

    MASK = '*' * 8
    FIELDS = frozenset([
        'password',
        'secret',
        'passwd',
        'authorization',
        'api_key',
        'apikey',
        'sentry_dsn',
        'access_token',
    ])
    VALUES_RE = re.compile(r'^(?:\d[ -]*?){13,16}$')

    def sanitize(self, key, value):
        if value is None:
            return

        if isinstance(value, string_types) and self.VALUES_RE.match(value):
            return self.MASK

        if not key:  # key can be a NoneType
            return value

        # Just in case we have bytes here, we want to make them into text
        # properly without failing so we can perform our check.
        if isinstance(key, bytes):
            key = key.decode('utf-8', 'replace')
        else:
            key = text_type(key)

        key = key.lower()
        for field in self.FIELDS:
            if field in key:
                # store mask as a fixed length for security
                return self.MASK
        return value

    def filter_stacktrace(self, data):
        for frame in data.get('frames', []):
            if 'vars' not in frame:
                continue
            frame['vars'] = varmap(self.sanitize, frame['vars'])

    def filter_http(self, data):
        for n in ('data', 'cookies', 'headers', 'env', 'query_string'):
            if n not in data:
                continue

            if isinstance(data[n], string_types) and '=' in data[n]:
                # at this point we've assumed it's a standard HTTP query
                # or cookie
                if n == 'cookies':
                    delimiter = ';'
                else:
                    delimiter = '&'

                data[n] = self._sanitize_keyvals(data[n], delimiter)
            else:
                data[n] = varmap(self.sanitize, data[n])
                if n == 'headers' and 'Cookie' in data[n]:
                    data[n]['Cookie'] = self._sanitize_keyvals(
                        data[n]['Cookie'], ';'
                    )

    def filter_extra(self, data):
        return varmap(self.sanitize, data)

    def _sanitize_keyvals(self, keyvals, delimiter):
        sanitized_keyvals = []
        for keyval in keyvals.split(delimiter):
            keyval = keyval.split('=')
            if len(keyval) == 2:
                sanitized_keyvals.append((keyval[0], self.sanitize(*keyval)))
            else:
                sanitized_keyvals.append(keyval)

        return delimiter.join('='.join(keyval) for keyval in sanitized_keyvals)
