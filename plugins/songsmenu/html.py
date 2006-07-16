# Copyright 2005 Eduardo Gonzalez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import re
import gtk
import config

from util import tag, escape
from plugins.songsmenu import SongsMenuPlugin

HTML = '''<?xml version="1.0" encoding="UTF-8"?>
<html>
<head><title>Quod Libet Playlist</title>
 <style type="text/css">
  table {table-collapse:collapse; border-spacing:0; width: 100%%}
  td {border: 0; padding:7px}
  th {border: 0; padding:7px; text-align: left}
 </style>
</head>
<body>
  <h1>My <a href="http://www.sacredchao.net/quodlibet/">Quod Libet</a>
  Playlist</h1>
  <br />
  <table id="songTable">
    <thead>
      <tr>
        %(headers)s
      </tr>
    </thead>
    <tbody id="songData">%(songs)s</tbody>
  </table>
</body>
</html>
'''

class ExportToHTML(SongsMenuPlugin):
    PLUGIN_ID = "Export to HTML"
    PLUGIN_NAME = _("Export to HTML")
    PLUGIN_DESC = _("Export the selected song list to HTML.")
    PLUGIN_ICON = gtk.STOCK_CONVERT
    PLUGIN_VERSION = "0.17"

    def plugin_songs(self, songs):
        if not songs: return

        chooser = gtk.FileChooserDialog(
            title="Export to HTML",
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                     gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        chooser.set_default_response(gtk.RESPONSE_ACCEPT)
        resp = chooser.run()
        if resp != gtk.RESPONSE_ACCEPT:
            chooser.destroy()
            return

        fn = chooser.get_filename()
        chooser.destroy()

        cols = config.get("settings", "headers").split()

        cols_s = ""
        for col in cols:
            cols_s += '<th>%s</th>' % tag(col)

        songs_s = ""
        for song in songs:
            s = '<tr>'
            for col in cols:
                col = {"~#rating":"~rating", "~#length":"~length"}.get(
                    col, col)
                s += '\n<td>%s</td>' % (
                    escape(unicode(song.comma(col))) or '&nbsp;')
            s += '</tr>'
            songs_s += s

        f = open(fn, 'wU')
        f.write((HTML % {'headers': cols_s, 'songs': songs_s}).encode('utf-8'))
        f.close()
