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

ENCODINGS = "Shift-JIS Big5 CP1251 EUC-KR EUC-JP".split()
if util.fscoding not in ENCODINGS + ["utf-8", "latin1"]:
    ENCODINGS.append(util.fscoding)

class Iconv(EditTagsPlugin):
    def __init__(self, tag, value):
        super(Iconv, self).__init__("_Convert From...")
        self.set_image(
            gtk.image_new_from_stock(gtk.STOCK_CONVERT, gtk.ICON_SIZE_MENU))
        submenu = gtk.Menu()
        for enc in ENCODINGS:
            item = gtk.MenuItem("dummy")
            try: new = value.encode('latin1').decode(enc, 'replace')
            except UnicodeEncodeError:
                new = _("[Invalid Encoding]")
                item.set_sensitive(False)
            else:
                if new == value: item.set_sensitive(False)
                else:
                    item.value = new
                    item.connect('activate', self.__convert)
            text = "<b>_%s</b>:\t%s" % (enc, util.escape(new))
            item.child.set_markup(text)
            item.child.set_use_underline(True)
            submenu.append(item)
        self.set_submenu(submenu)

    def __convert(self, item):
        self.__value = item.value
        self.activate()

    def activated(self, tag, value):
        try: return [(tag, self.__value)]
        except AttributeError: [(tag, value)]

                             
