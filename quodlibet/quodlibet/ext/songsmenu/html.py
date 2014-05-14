# Copyright 2005 Eduardo Gonzalez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import config
from quodlibet.util import tag, escape
from quodlibet.plugins.songsmenu import SongsMenuPlugin

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


def to_html(songs):
    cols = config.get_columns()

    cols_s = ""
    for col in cols:
        cols_s += '<th>%s</th>' % tag(col)

    songs_s = ""
    for song in songs:
        s = '<tr>'
        for col in cols:
            col = {"~#rating": "~rating", "~#length": "~length"}.get(
                col, col)
            s += '\n<td>%s</td>' % (
                escape(unicode(song.comma(col))) or '&nbsp;')
        s += '</tr>'
        songs_s += s

    return HTML % {'headers': cols_s, 'songs': songs_s}


class ExportToHTML(SongsMenuPlugin):
    PLUGIN_ID = "Export to HTML"
    PLUGIN_NAME = _("Export to HTML")
    PLUGIN_DESC = _("Export the selected song list to HTML.")
    PLUGIN_ICON = Gtk.STOCK_CONVERT
    PLUGIN_VERSION = "0.17"

    def plugin_songs(self, songs):
        if not songs:
            return

        chooser = Gtk.FileChooserDialog(
            title="Export to HTML",
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                     Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        chooser.set_default_response(Gtk.ResponseType.ACCEPT)
        resp = chooser.run()
        if resp != Gtk.ResponseType.ACCEPT:
            chooser.destroy()
            return

        fn = chooser.get_filename()
        chooser.destroy()

        with open(fn, "wb") as f:
            f.write(to_html(songs).encode("utf-8"))
