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
from plugins.editing import EditTagsPlugin

ENCODINGS = "Shift-JIS Big5 CP1251 EUC-KR EUC-JP UTF16BE UTF16LE ISO-2022-JP GB2312 EUC-CN EUC-TW".split()
if util.fscoding not in ENCODINGS + ["utf-8", "latin1"]:
    ENCODINGS.append(util.fscoding)

class Iconv(EditTagsPlugin):
    PLUGIN_NAME = "Convert Encodings"
    PLUGIN_DESC = "Fix misinterpreted tag value encodings in the tag editor."
    PLUGIN_ICON = gtk.STOCK_CONVERT

    def __init__(self, tag, value):
        super(Iconv, self).__init__("_Convert From...")
        self.set_image(
            gtk.image_new_from_stock(gtk.STOCK_CONVERT, gtk.ICON_SIZE_MENU))
        submenu = gtk.Menu()
        sizes = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        for enc in ENCODINGS:
            item = gtk.MenuItem("dummy")
            item.remove(item.child)
            try: new = value.encode('latin1').decode(enc, 'replace')
            except UnicodeEncodeError:
                new = _("[Invalid Encoding]")
                item.set_sensitive(False)
            else:
                if new == value: item.set_sensitive(False)
                else:
                    item.value = new
                    item.connect('activate', self.__convert)
            vb = gtk.HBox(spacing=3)
            encoding = gtk.Label()
            encoding.set_markup("<b>_%s:</b>" % enc)
            encoding.set_alignment(0.0, 0.5)
            sizes.add_widget(encoding)
            result = gtk.Label(new)
            result.set_alignment(0.0, 0.5)
            vb.pack_start(encoding, expand=False)
            vb.pack_start(result)
            item.add(vb)
            encoding.set_use_underline(True)
            submenu.append(item)
        self.set_submenu(submenu)

    def __convert(self, item):
        self.__value = item.value
        self.activate()

    def activated(self, tag, value):
        try: return [(tag, self.__value)]
        except AttributeError: return [(tag, value)]
