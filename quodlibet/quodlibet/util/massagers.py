# -*- coding: utf-8 -*-
# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Iñigo Serna, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import locale
import re

class Massager(object):
    """Massage a tag value from various 'okay' formats to the
    'correct' format."""

    tags = []
    error = "Metaerror. This should be overridden in subclasses."
    options = []

    def validate(self, value):
        """Returns a validated value, or False if invalid"""
        raise NotImplementedError

    def is_valid(self, value):
        """Returns True if a field is valid, False if not"""
        return bool(self.validate(value))

class DateMassager(Massager):
    tags = ["date"]
    error = _("The date must be entered in 'YYYY', 'YYYY-MM-DD' or "
              "'YYYY-MM-DD HH:MM:SS' format.")
    __match = re.compile(r"^\d{4}([-.]\d{2}([-.]\d{2}([T ]\d{2}"
                          "([:.]\d{2}([:.]\d{2})?)?)?)?)?$").match
    def validate(self, value):
        value = value.strip().replace(".", "-").replace("/", "-")
        return self.__match(value) and value

class GainMassager(Massager):
    tags = ["replaygain_album_gain", "replaygain_track_gain"]
    error = _("Replay Gain gains must be entered in 'x.yy dB' format.")
    __match = re.compile(r"^[+-]\d+\.?\d+?\s+dB$").match

    def validate(self, value):
        if self.__match(value): return value
        else:
            try: f = float(value.split()[0])
            except (IndexError, TypeError, ValueError):
                try: f = locale.atof(value.split()[0])
                except (IndexError, TypeError, ValueError): return False
            else: return ("%+f" % f).rstrip("0") + " dB"

class PeakMassager(Massager):
    tags = ["replaygain_album_peak", "replaygain_track_peak"]
    error = _("Replay Gain peaks must be entered in 'x.yy' format.")
    def validate(self, value):
        value = value.strip()
        try: f = float(value)
        except (TypeError, ValueError):
            try: f = locale.atof(value)
            except (TypeError, ValueError): return False
        else: return (f >= 0) and (f < 2) and str(f)

class MBIDMassager(Massager):
    tags = ["musicbrainz_trackid", "musicbrainz_albumid",
            "musicbrainz_artistid", "musicbrainz_albumartistid",
            "musicbrainz_trmid", "musicip_puid"]
    error = _("MusicBrainz IDs must be in UUID format.")
    def validate(self, value):
        value = value.encode('ascii', 'replace')
        value = filter(str.isalnum, value.strip().lower())
        try: int(value, 16)
        except ValueError: return False
        else:
            if len(value) != 32: return False
            else: return "-".join([value[:8], value[8:12], value[12:16],
                                   value[16:20], value[20:]])

class MBAlbumStatus(Massager):
    tags = ["musicbrainz_albumstatus"]
    # Translators: Leave "official", "promotional", and "bootleg"
    # untranslated. They are the three possible literal values.
    error = _("MusicBrainz release status must be 'official', "
              "'promotional', or 'bootleg'.")
    options = ["official", "promotional", "bootleg"]
    def validate(self, value):
        return value in self.options and value

class LanguageMassager(Massager):
    tags = ["language"]
    error = _("Language must be an ISO 639-2 three-letter code")
    # Lovingly adapted from http://www.loc.gov/standards/iso639-2/
    ISO_639_2 =  ['aar', 'abk', 'ace', 'ach', 'ada', 'ady', 'afa', 'afh', 'afr',
    'ain', 'aka', 'akk', 'alb', 'sqi', 'ale', 'alg', 'alt', 'amh', 'ang', 'anp',
    'apa', 'ara', 'arc', 'arg', 'arm', 'hye', 'arn', 'arp', 'art', 'arw', 'asm',
    'ast', 'ath', 'aus', 'ava', 'ave', 'awa', 'aym', 'aze', 'bad', 'bai', 'bak',
    'bal', 'bam', 'ban', 'baq', 'eus', 'bas', 'bat', 'bej', 'bel', 'bem', 'ben',
    'ber', 'bho', 'bih', 'bik', 'bin', 'bis', 'bla', 'bnt', 'bos', 'bra', 'bre',
    'btk', 'bua', 'bug', 'bul', 'bur', 'mya', 'byn', 'cad', 'cai', 'car', 'cat',
    'cau', 'ceb', 'cel', 'cha', 'chb', 'che', 'chg', 'chi', 'zho', 'chk', 'chm',
    'chn', 'cho', 'chp', 'chr', 'chu', 'chv', 'chy', 'cmc', 'cop', 'cor', 'cos',
    'cpe', 'cpf', 'cpp', 'cre', 'crh', 'crp', 'csb', 'cus', 'cze', 'ces', 'dak',
    'dan', 'dar', 'day', 'del', 'den', 'dgr', 'din', 'div', 'doi', 'dra', 'dsb',
    'dua', 'dum', 'dut', 'nld', 'dyu', 'dzo', 'efi', 'egy', 'eka', 'elx', 'eng',
    'enm', 'epo', 'est', 'ewe', 'ewo', 'fan', 'fao', 'fat', 'fij', 'fil', 'fin',
    'fiu', 'fon', 'fre', 'fra', 'frm', 'fro', 'frr', 'frs', 'fry', 'ful', 'fur',
    'gaa', 'gay', 'gba', 'gem', 'geo', 'kat', 'ger', 'deu', 'gez', 'gil', 'gla',
    'gle', 'glg', 'glv', 'gmh', 'goh', 'gon', 'gor', 'got', 'grb', 'grc', 'gre',
    'ell', 'grn', 'gsw', 'guj', 'gwi', 'hai', 'hat', 'hau', 'haw', 'heb', 'her',
    'hil', 'him', 'hin', 'hit', 'hmn', 'hmo', 'hrv', 'hsb', 'hun', 'hup', 'iba',
    'ibo', 'ice', 'isl', 'ido', 'iii', 'ijo', 'iku', 'ile', 'ilo', 'ina', 'inc',
    'ind', 'ine', 'inh', 'ipk', 'ira', 'iro', 'ita', 'jav', 'jbo', 'jpn', 'jpr',
    'jrb', 'kaa', 'kab', 'kac', 'kal', 'kam', 'kan', 'kar', 'kas', 'kau', 'kaw',
    'kaz', 'kbd', 'kha', 'khi', 'khm', 'kho', 'kik', 'kin', 'kir', 'kmb', 'kok',
    'kom', 'kon', 'kor', 'kos', 'kpe', 'krc', 'krl', 'kro', 'kru', 'kua', 'kum',
    'kur', 'kut', 'lad', 'lah', 'lam', 'lao', 'lat', 'lav', 'lez', 'lim', 'lin',
    'lit', 'lol', 'loz', 'ltz', 'lua', 'lub', 'lug', 'lui', 'lun', 'luo', 'lus',
    'mac', 'mkd', 'mad', 'mag', 'mah', 'mai', 'mak', 'mal', 'man', 'mao', 'mri',
    'map', 'mar', 'mas', 'may', 'msa', 'mdf', 'mdr', 'men', 'mga', 'mic', 'min',
    'mis', 'mkh', 'mlg', 'mlt', 'mnc', 'mni', 'mno', 'moh', 'mon', 'mos', 'mul',
    'mun', 'mus', 'mwl', 'mwr', 'myn', 'myv', 'nah', 'nai', 'nap', 'nau', 'nav',
    'nbl', 'nde', 'ndo', 'nds', 'nep', 'new', 'nia', 'nic', 'niu', 'nno', 'nob',
    'nog', 'non', 'nor', 'nqo', 'nso', 'nub', 'nwc', 'nya', 'nym', 'nyn', 'nyo',
    'nzi', 'oci', 'oji', 'ori', 'orm', 'osa', 'oss', 'ota', 'oto', 'paa', 'pag',
    'pal', 'pam', 'pan', 'pap', 'pau', 'peo', 'per', 'fas', 'phi', 'phn', 'pli',
    'pol', 'pon', 'por', 'pra', 'pro', 'pus', 'que', 'raj', 'rap', 'rar', 'roa',
    'roh', 'rom', 'rum', 'ron', 'run', 'rup', 'rus', 'sad', 'sag', 'sah', 'sai',
    'sal', 'sam', 'san', 'sas', 'sat', 'scn', 'sco', 'sel', 'sem', 'sga', 'sgn',
    'shn', 'sid', 'sin', 'sio', 'sit', 'sla', 'slo', 'slk', 'slv', 'sma', 'sme',
    'smi', 'smj', 'smn', 'smo', 'sms', 'sna', 'snd', 'snk', 'sog', 'som', 'son',
    'sot', 'spa', 'srd', 'srn', 'srp', 'srr', 'ssa', 'ssw', 'suk', 'sun', 'sus',
    'sux', 'swa', 'swe', 'syc', 'syr', 'tah', 'tai', 'tam', 'tat', 'tel', 'tem',
    'ter', 'tet', 'tgk', 'tgl', 'tha', 'tib', 'bod', 'tig', 'tir', 'tiv', 'tkl',
    'tlh', 'tli', 'tmh', 'tog', 'ton', 'tpi', 'tsi', 'tsn', 'tso', 'tuk', 'tum',
    'tup', 'tur', 'tut', 'tvl', 'twi', 'tyv', 'udm', 'uga', 'uig', 'ukr', 'umb',
    'und', 'urd', 'uzb', 'vai', 'ven', 'vie', 'vol', 'vot', 'wak', 'wal', 'war',
    'was', 'wel', 'cym', 'wen', 'wln', 'wol', 'xal', 'xho', 'yao', 'yap', 'yid',
    'yor', 'ypk', 'zap', 'zbl', 'zen', 'zha', 'znd', 'zul', 'zun', 'zxx', 'zza']
    options = ISO_639_2

    tags = ["language"]
    def validate(self, value):
        # Issue 439: Actually, allow free-text through
        return value

    def is_valid(self, value):
        # Override, to allow empty string to be a valid language (freetext)
        return True

tags = {}
for f in globals().values():
    if isinstance(f, type) and issubclass(f, Massager):
        for t in f.tags:
            tags[t] = f()
del(f)
del(t)
