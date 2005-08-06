import gtk
from qltk import ErrorMessage
__all__ = ['Export', 'Import']

class Export(object):

    PLUGIN_NAME = "ExportMeta"
    PLUGIN_DESC = "Export Metadata"
    PLUGIN_ICON = 'gtk-save'

    def plugin_album(self, songs):

        songs.sort(lambda a, b: cmp(a('~#track'), b('~#track')) or cmp(a('~basename'), b('~basename')) or cmp(a, b))

        chooser = gtk.FileChooserDialog(title="Export %s Metadata to ..." % songs[0]('album'), action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        resp = chooser.run()
        fn = chooser.get_filename()
        chooser.destroy()
        if resp != gtk.RESPONSE_ACCEPT: return

        out = open(fn, 'wU')

        for song in songs:
            print>>out, str(song('~basename'))
            keys = song.keys()
            keys.sort()
            for key in keys:
                if key.startswith('~'): continue
                for val in song.list(key):
                    print>>out, '%s=%s' % (key, val.encode('utf-8'))
            print>>out

class Import(object):

    PLUGIN_NAME = "ImportMeta"
    PLUGIN_DESC = "Import Metadata"
    PLUGIN_ICON = 'gtk-open'

    def plugin_album(self, songs):

        songs.sort(lambda a, b: cmp(a('~#track'), b('~#track')) or cmp(a('~basename'), b('~basename')) or cmp(a, b))

        chooser = gtk.FileChooserDialog(title="Import %s Metadata from ..." % songs[0]('album'), action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))

        append = gtk.CheckButton("Append Metadata")
        append.set_active(True)
        append.show()
        chooser.set_extra_widget(append)

        resp = chooser.run()
        append = append.get_active()
        fn = chooser.get_filename()
        chooser.destroy()
        if resp != gtk.RESPONSE_ACCEPT: return

        metadata = []
        index = 0
        for line in open(fn, 'rU'):
            if index == len(metadata):
                metadata.append({})
            elif line == '\n':
                index = len(metadata)
            else:
                key, value = line[:-1].split('=', 1)
                value = value.decode('utf-8')
                try: metadata[index][key].append(value)
                except KeyError: metadata[index][key] = [value]

        if len(songs) != len(metadata):
            ErrorMessage(None, "Songs mismatch", "There are %(select)d songs selected, but %(meta)d songs in the file. Aborting." % dict(select=len(songs), meta=len(metadata))).run()
            return

        for song, meta in zip(songs, metadata):
            for key, values in meta.iteritems():
                if append: values = song.list(key) + values
                song[key] = '\n'.join(values)
