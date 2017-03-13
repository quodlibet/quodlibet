"""
raven.utils.json
~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""

from __future__ import absolute_import

import codecs
import datetime
import uuid
import json

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError


class BetterJSONEncoder(json.JSONEncoder):
    ENCODER_BY_TYPE = {
        uuid.UUID: lambda o: o.hex,
        datetime.datetime: lambda o: o.strftime('%Y-%m-%dT%H:%M:%SZ'),
        set: list,
        frozenset: list,
        bytes: lambda o: o.decode('utf-8', errors='replace')
    }

    def default(self, obj):
        try:
            encoder = self.ENCODER_BY_TYPE[type(obj)]
        except KeyError:
            try:
                return super(BetterJSONEncoder, self).default(obj)
            except TypeError:
                return repr(obj)
        return encoder(obj)


def better_decoder(data):
    return data


def dumps(value, **kwargs):
    try:
        return json.dumps(value, cls=BetterJSONEncoder, **kwargs)
    except Exception:
        kwargs['encoding'] = 'safe-utf-8'
        return json.dumps(value, cls=BetterJSONEncoder, **kwargs)


def loads(value, **kwargs):
    return json.loads(value, object_hook=better_decoder)


_utf8_encoder = codecs.getencoder('utf-8')


def safe_encode(input, errors='backslashreplace'):
    return _utf8_encoder(input, errors)


_utf8_decoder = codecs.getdecoder('utf-8')


def safe_decode(input, errors='replace'):
    return _utf8_decoder(input, errors)


class Codec(codecs.Codec):

    def encode(self, input, errors='backslashreplace'):
        return safe_encode(input, errors)

    def decode(self, input, errors='replace'):
        return safe_decode(input, errors)


class IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, input, final=False):
        return safe_encode(input, self.errors)[0]


class IncrementalDecoder(codecs.IncrementalDecoder):
    def decode(self, input, final=False):
        return safe_decode(input, self.errors)[0]


class StreamWriter(Codec, codecs.StreamWriter):
    pass


class StreamReader(Codec, codecs.StreamReader):
    pass


def getregentry(name):
    if name != 'safe-utf-8':
        return None
    return codecs.CodecInfo(
        name='safe-utf-8',
        encode=safe_encode,
        decode=safe_decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=StreamWriter,
    )


codecs.register(getregentry)
