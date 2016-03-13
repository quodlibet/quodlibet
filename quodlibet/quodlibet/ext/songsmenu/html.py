# -*- coding: utf-8 -*-
# Copyright 2005 Eduardo Gonzalez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet.qltk import Icons
from quodlibet.util import tag, escape
from quodlibet.qltk.songlist import get_columns
from quodlibet.plugins.songsmenu import SongsMenuPlugin

HTML = '''<html>
<head><title>Quod Libet Playlist</title>
 <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
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
    cols = get_columns()

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
    PLUGIN_DESC = _("Exports the selected song list to HTML.")
    REQUIRES_ACTION = True
    PLUGIN_ICON = Icons.TEXT_HTML

    def plugin_songs(self, songs):
        if not songs:
            return

        chooser = Gtk.FileChooserDialog(
            title="Export to HTML",
            action=Gtk.FileChooserAction.SAVE)
        chooser.add_button(_("_Cancel"), Gtk.ResponseType.REJECT)
        chooser.add_button(_("_OK"), Gtk.ResponseType.ACCEPT)
        chooser.set_default_response(Gtk.ResponseType.ACCEPT)
        resp = chooser.run()
        if resp != Gtk.ResponseType.ACCEPT:
            chooser.destroy()
            return

        fn = chooser.get_filename()
        chooser.destroy()

        with open(fn, "wb") as f:
            f.write(to_html(songs).encode("utf-8"))
