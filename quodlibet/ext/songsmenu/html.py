# Copyright 2005 Eduardo Gonzalez
#           2020 Roneel Valambhia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.qltk import Icons
from quodlibet.util import tag, escape
from quodlibet.qltk.songlist import get_columns
from quodlibet.qltk.chooser import choose_target_file
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
  <h1>My <a href="https://quodlibet.readthedocs.io/">Quod Libet</a>
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
                escape(str(song.comma(col))) or '&nbsp;')
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

        target = choose_target_file(
            self.plugin_window, _("Export to HTML"), _("_Save"))
        if target is not None:
            with open(target, "wb") as f:
                f.write(to_html(songs).encode("utf-8"))
