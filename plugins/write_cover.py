import os, util, config, shutil, gtk

try: config.get("plugins", __name__)
except:
    out = os.path.expanduser("~/.quodlibet/current.cover")
    config.set("plugins", __name__, out)

PLUGIN_NAME = "Picture Saver"
PLUGIN_DESC = "The cover image of the current song is saved to a file."

def plugin_on_song_started(song):
    outfile = config.get("plugins", __name__)
    if song is None:
        try: os.unlink(outfile)
        except EnvironmentError: pass
    else:
        cover = song.find_cover()
        if cover is None:
            try: os.unlink(outfile)
            except EnvironmentError: pass
        else:
            f = file(outfile, "wb")
            f.write(cover.read())
            f.close()

def Preferences():
    def changed(entry):
        fn = entry.get_text()
        try: shutil.move(config.get("plugins", __name__), fn)
        except: pass
        config.set("plugins", __name__, fn)

    hb = gtk.HBox(spacing=6)
    hb.set_border_width(6)
    hb.pack_start(gtk.Label(_("File:")), expand=False)
    e = gtk.Entry()
    e.set_text(config.get("plugins", __name__))
    e.connect('changed', changed)
    hb.pack_start(e)
    return hb
