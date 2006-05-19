# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Encoding magic. Show off the submenu stuff.

import gtk
import util
import locale
from plugins.editing import EditTagsPlugin

ENCODINGS = """\
big5 cp1250 cp1251 cp1252 cp1253 cp1254 cp1255 cp1256 cp1257 cp1258
euc_jp euc_jis_2004 euc_jisx0213 euc_kr gb2312 gbk gb18030 iso2022_jp
iso2022_kr iso8859_2 iso8859_3 iso8859_4 iso8859_5 iso8859_6 iso8859_7
iso8859_8 iso8859_9 iso8859_10 iso8859_13 iso8859_14 iso8859_15 johab
koi8_r koi8_u ptcp154 shift_jis utf_16_be utf_16_le""".split()

if util.fscoding not in ENCODINGS + ["utf-8", "latin1"]:
    ENCODINGS.append(util.fscoding)
if locale.getpreferredencoding() not in ENCODINGS + ["utf-8", "latin1"]:
    ENCODINGS.append(util.fscoding)

class Iconv(EditTagsPlugin):
    PLUGIN_NAME = "Convert Encodings"
    PLUGIN_DESC = "Fix misinterpreted tag value encodings in the tag editor."
    PLUGIN_ICON = gtk.STOCK_CONVERT

    def __init__(self, tag, value):
        super(Iconv, self).__init__("_Convert Encoding...")
        self.set_image(
            gtk.image_new_from_stock(gtk.STOCK_CONVERT, gtk.ICON_SIZE_MENU))
        submenu = gtk.Menu()

        items = []

        # Ok, which encodings do work on this string?

        for enc in ENCODINGS:
            try:
                new = value.encode('latin1').decode(enc)
            except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
                   continue
            else:
                if new == value:
                    continue
                if not new in items:
                    items.append(new)
        
        if not items:
            self.set_sensitive(False)
        
        for i in items:
            item = gtk.MenuItem()
            item.value = i
            item_label = gtk.Label(i)
            item_label.set_alignment(0.0, 0.5)
            item.add(item_label)
            item.connect('activate', self.__convert)
            submenu.append(item)
        self.set_submenu(submenu)

    def __convert(self, item):
        self.__value = item.value
        self.activate()

    def activated(self, tag, value):
        try: return [(tag, self.__value)]
        except AttributeError: return [(tag, value)]
