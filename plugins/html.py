#Copyright 2005 Eduardo Gonzalez
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import re
import gtk
import config

from cgi import escape

PLUGIN_NAME = "Save metadata to HTML"
PLUGIN_DESC = "Exports the selected songs' metadata as HTML"
PLUGIN_ICON = gtk.STOCK_CONVERT
PLUGIN_VERSION = "0.12"

html = '''<html>
<meta http-equiv="content-type" content="text/html; charset=UTF-8" />
<head><title>Quod Libet Playlist</title>
 <style type="text/css">
  table {table-collapse:collapse; border-spacing:0}
  td {border:2px groove black; padding:7px}
  th {border:2px groove black; padding:7px}
 </style>
</head>
<body>
  <h1><center>My <a href="http://www.sacredchao.net/quodlibet/">Quod Libet</a> playlist.</center></h1>
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
  
def plugin_songs(songs):
    if not songs: return
    global html
    html_ = html

    chooser = gtk.FileChooserDialog(title="Save Metadata to ...",
                                    action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                             gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
    resp = chooser.run()
    if resp != gtk.RESPONSE_ACCEPT: return

    fn = chooser.get_filename()
    chooser.destroy()
    
    cols = config.get("settings", "headers").split()

    cols_s = ""
    for col in cols:
        if col == "~current": continue
        cols_s += '<th>%s</th>' % (col)
    
    songs_s = ""
    for song in songs:
        s = '<tr>'
        for col in cols:
            if col == "~current": continue
            s += '\n<td>%s</td>' % escape(str(song.comma(col)))
        s += '</tr>'
        songs_s += s

    f = open(fn, 'wU')
    f.write(html_ % {'headers': cols_s, 'songs': songs_s})
    f.close()
