# -*- coding: utf-8 -*-
# Copyright 2010 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

# Free Media Player Specifications 1.1 by Jeff Mitchell
# http://freedesktop.org/wiki/Specifications/free-media-player-specs


FMPS_NOTHING = u"FMPS_NOTHING"

LIST_SEPERATOR = u";;"
ENTRY_SEPERATOR = u"::"

def _split_left(val, sep):
    """Split a string by a delimiter which can be escaped by \\"""
    result = []
    temp = u""
    escaped = False
    index = 0
    left = True
    for c in val:
        left = False
        temp += c
        if c == sep[index] and not escaped:
            index += 1
        else:
            index = 0
            if c == u"\\":
                escaped ^= True
            else:
                escaped = False
        if index >= len(sep):
            left = True
            index = 0
            result.append(temp[:-len(sep)])
            temp = u""
    if temp or left:
        result.append(temp)
    return result

def _split(val, sep):
    """Split and filter invalid segments.
    Entries seperated by ::: for example need to be set invalid
    because they could be split in two ways.
    """
    invalid = []
    inval = []
    valid = []
    vals = _split_left(val, sep)
    c = False
    # Look if a segment starts with :/;
    # and mark it and the next one as invalid (except the last one)
    for i, v in enumerate(vals[-1::-1]):
        new_c = v.startswith(sep[0])
        excp = i == len(vals)-1
        if c or (new_c and not excp):
            inval.insert(0, v)
        else:
            if inval:
                invalid.insert(0, sep.join(inval))
                inval = []
            valid.insert(0, v)
        c = new_c
    if inval:
        invalid.insert(0, sep.join(inval))
    return invalid, valid

def _unescape(val):
    return val.replace(
        ur"\;", u";").replace(ur"\:", u":").replace(ur"\\", u"\\")
def _escape(val):
    return val.replace(
        u"\\", ur"\\").replace(u";", ur"\;").replace(u":", ur"\:")

def _escape_inval(val):
    if val.startswith(";"):
        return u"\\" + val
    return val

class FmpsValue(object):
    _data = None
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._data))

    def native(self):
        return self._data

    def __unicode__(self):
        return unicode(self._data)

    def __str__(self):
        return str(self._data)

class FmpsFloat(FmpsValue):
    def __init__(self, data):
        if not isinstance(data, basestring):
            self._validate(data)
            self._data = unicode(round(float(data), 6))
        else:
            data = unicode(data)
            self._validate(data)
            self._data = data

    def _validate(self, data):
        return float(data)

    def native(self):
        return float(self._data)

class FmpsPositiveFloat(FmpsFloat):
    def _validate(self, data):
        num = super(FmpsPositiveFloat, self)._validate(data)
        if num < 0  or (not isinstance(data, basestring)
            and num > 4294967294.999999):
            raise ValueError("Value not in range.")
        return num

class FmpsRatingFloat(FmpsFloat):
    def _validate(self, data):
        num = super(FmpsRatingFloat, self)._validate(data)
        if not 0 <= num <= 1:
            raise ValueError("Value not in range.")
        return num

class FmpsPositiveIntegerFloat(FmpsPositiveFloat):
    def _validate(self, data):
        num = super(FmpsPositiveIntegerFloat, self)._validate(data)
        if int(num) != num:
            raise ValueError("Value not an integer.")
        return num

    def native(self):
        return int(super(FmpsPositiveIntegerFloat, self).native())

class FmpsText(FmpsValue):
    def __init__(self, data):
        self._data = unicode(data)

class FmpsInvalidValue(FmpsText): pass

class FmpsDict(object):
    _kind = None

    def __init__(self, data=None):
        self.__dict = {}
        self.__invalid = []
        if data:
            self.__load(data)

    def __load(self, data):
        if not isinstance(data, (list, tuple)):
            data = [data]
        data = map(unicode, data)
        vals = []
        for seg in data:
            i, v = _split(seg, LIST_SEPERATOR)
            vals.extend(v)
            self.__invalid.extend(map(_escape_inval, i))
        for val in vals:
            inval, fields = _split(val, ENTRY_SEPERATOR)
            if len(fields) != 2 or inval:
                self.__invalid.append(_escape_inval(val))
                continue
            key, value = map(_unescape, fields)
            try:
                value = self._kind(value)
            except ValueError:
                value = FmpsInvalidValue(value)

            if key in self.__dict:
                self.__dict[key].append(value)
            else:
                self.__dict[key] = [value]

    def iterkeys(self):
        return self.__dict.iterkeys()
    keys = lambda self: list(self.iterkeys())

    def iteritems(self):
        for key, values in self.__dict.iteritems():
            for value in values:
                if not isinstance(value, FmpsInvalidValue):
                    yield(key, value.native())
    items = lambda s: list(s.iteritems())

    def get_all(self, key):
        if key in self.__dict:
            return [f.native() for f in self.__dict[key]
                if not isinstance(f, FmpsInvalidValue)]
        return []

    def remove_all(self, key):
        if key in self.__dict:
            del self.__dict[key]

    def set_all(self, key, value):
        key = unicode(key)
        if not isinstance(value, (list, tuple)):
            value = [value]
        value = map(self._kind, value)
        self.remove_all(key)
        if key in self.__dict:
            self.__dict[key].extend(value)
        else:
            self.__dict[key] = value

    def append(self, key, value):
        self.extend(key, [value])

    def extend(self, key, values):
        key = unicode(key)
        values = map(self._kind, values)
        if key in self.__dict:
            self.__dict[key].extend(values)
        else:
            self.__dict[key] = values

    def to_data(self):
        fields = []
        for key, values in self.__dict.iteritems():
            values = map(_escape, map(unicode, values))
            key = _escape(key)
            for val in values:
                fields.append(ENTRY_SEPERATOR.join([key, val]))
        return LIST_SEPERATOR.join(fields + filter(None, self.__invalid))

    def __repr__(self):
        return "%s(%s, invalid=%s)" % (
            self.__class__.__name__, repr(self.__dict), repr(self.__invalid))

class FmpsNamespaceDict(object):
    _kind = None

    def __init__(self, data=None):
        self.__dict = {}
        self.__invalid = []
        if data:
            self.__load(data)

    def __load(self, data):
        if not isinstance(data, (list, tuple)):
            data = [data]
        data = map(unicode, data)
        vals = []
        for seg in data:
            i, v = _split(seg, LIST_SEPERATOR)
            vals.extend(v)
            self.__invalid.extend(map(_escape_inval, i))
        for val in vals:
            inval, fields = _split(val, ENTRY_SEPERATOR)
            if len(fields) != 3 or inval:
                self.__invalid.append(_escape_inval(val))
                continue
            namespace, key, value = fields
            if not namespace or not key:
                self.__invalid.append(val)
                continue
            namespace, key, value = map(_unescape, (namespace, key, value))
            try:
                value = self._kind(value)
            except ValueError:
                value = FmpsInvalidValue(value)

            if namespace in self.__dict:
                if key in self.__dict[namespace]:
                    self.__dict[namespace][key].append(value)
                else:
                    self.__dict[namespace][key] = [value]
            else:
                self.__dict[namespace] = {key: [value]}

    def get_all(self, namespace, key=None):
        """Will return a list of values if key is given, else a dict"""
        if namespace in self.__dict:
            if key is not None:
                if key in self.__dict[namespace]:
                    return [f.native() for f in self.__dict[namespace][key]
                        if not isinstance(f, FmpsInvalidValue)]
                else:
                    return []
            else:
                new_dict = {}
                for key, values in self.__dict[namespace].iteritems():
                    new_dict[key] = [f.native() for f in values
                        if not isinstance(f, FmpsInvalidValue)]
                return new_dict
        else:
            if key is not None:
                return []
            return {}

    def remove_all(self, namespace, key=None):
        if namespace in self.__dict:
            if key is not None:
                if key in self.__dict[namespace]:
                    del self.__dict[namespace][key]
                    if not self.__dict[namespace]:
                        del self.__dict[namespace]
            else:
                del self.__dict[namespace]

    def set_all(self, namespace, key, value):
        """value can be a list or a singe value, or a dict
        in case key is None"""
        if not namespace or (key is not None and not key):
            raise ValueError("No empty namespace/key allowed.")
        if key is None and not isinstance(value, dict):
            raise ValueError("You have to pass a dict in case key is None.")
        if key is not None and isinstance(value, dict):
            raise ValueError("You can only pass a dict in case key is None.")

        namespace = unicode(namespace)
        key = key is not None and unicode(key)

        if isinstance(value, dict):
            value = dict(value)
            for key in value.iterkeys():
                if not isinstance(value[key], (list, tuple)):
                    value[key] = [value[key]]
                value[key] = map(self._kind, value[key])
            self.__dict[namespace] = dict(value)
            return

        if not isinstance(value, (list, tuple)):
            value = [value]
        value = map(self._kind, value)

        if namespace in self.__dict:
            if key in self.__dict[namespace]:
                self.__dict[namespace][key] = value
        else:
            self.__dict[namespace] = {key: value}

    def append(self, namespace, key, value):
        self.extend(namespace, key, [value])

    def extend(self, namespace, key, values):
        if not namespace or not key:
            raise ValueError("No empty namespace/key allowed.")

        namespace = unicode(namespace)
        key = unicode(key)

        values = map(self._kind, values)
        if namespace in self.__dict:
            if key in self.__dict[namespace]:
                self.__dict[namespace][key].extend(values)
            else:
                self.__dict[namespace][key] = values
        else:
            self.__dict[namespace] = {key: values}

    def iterkeys(self):
        return self.__dict.iterkeys()
    keys = lambda self: list(self.iterkeys())

    def iteritems(self):
        for namespace, sub in self.__dict.iteritems():
            for key, values in sub.iteritems():
                for val in values:
                    yield (namespace, key, val.native())
    items = lambda self: list(self.iteritems())

    def to_data(self):
        fields = []
        for namespace, sub in self.__dict.iteritems():
            namespace = _escape(namespace)
            for key, values in sub.iteritems():
                key = _escape(key)
                values = map(_escape, map(unicode, values))
                for val in values:
                    fields.append(ENTRY_SEPERATOR.join([namespace, key, val]))
        return LIST_SEPERATOR.join(fields + filter(None, self.__invalid))

    def __repr__(self):
        return "%s(%s, invalid=%s)" % (
            self.__class__.__name__, repr(self.__dict), repr(self.__invalid))

class FmpsNoEmptyKeyDict(FmpsDict):
    def set_all(self, key, values):
        if not key:
            raise ValueError("No empty key allowed.")
        super(FmpsNoEmptyKeyDict, self).set_all(key, values)

    def extend(self, key, values):
        if not key:
            raise ValueError("No empty key allowed.")
        super(FmpsNoEmptyKeyDict, self).extend(key, values)

#All simple Formats
class Rating(FmpsRatingFloat): pass
class Playcount(FmpsPositiveIntegerFloat): pass
class Lyrics(FmpsText): pass

#All Dicts
class RatingUser(FmpsNoEmptyKeyDict):
    _kind = FmpsRatingFloat
class PlaycountUser(FmpsNoEmptyKeyDict):
    _kind = FmpsPositiveIntegerFloat
class Performers(FmpsDict):
    _kind = FmpsText
class LyricsSources(FmpsDict):
    _kind = FmpsText

#All NamespaceDicts
class RatingCritic(FmpsNamespaceDict):
    _kind=FmpsRatingFloat
class RatingAlgorithm(FmpsNamespaceDict):
    _kind=FmpsRatingFloat
class PlaycountAlgorithm(FmpsNamespaceDict):
    _kind=FmpsPositiveFloat

# AlbumsCompilations needs checks for unique
# Application(case sensitive)+Type(case insensitive)+Identifier(case sensitive)
# and should check if the keys are album/compilation only...
# but I don't care atm so that's left to the user.
class AlbumsCompilations(FmpsNamespaceDict):
    _kind = FmpsText
