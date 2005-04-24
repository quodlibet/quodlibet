import time
import gobject, gtk
import player

class Lullaby(object):
    PLUGIN_NAME = "Lullaby"
    PLUGIN_DESC = "Slowly fade out your music."

    def __init__(self):
        self.__starttime = -1
        self.__enabled = False

    def plugin_on_song_started(self, song):
        if self.__enabled:
            time_ = time.localtime()[3] * 60 + time.localtime()[4]
            if self.__starttime > 0 and self.__starttime < time_:
                self.__enabled = False
                gobject.timeout_add(100, self.__fadeout, player.device.volume)

    def __fadeout(self, volume):
        player.device.volume = max(player.device.volume - 0.002, 0)
        if player.device.volume == 0:
            player.playlist.paused = True
            player.device.volume = volume
        else: return True

    def __clicked(self, cb, hb):
        self.__enabled = cb.get_active()
        hb.set_sensitive(self.__enabled)

    def __set_time(self, entry):
        t = entry.get_text()
        try: hour, minute = map(int, t.split(":"))
        except: self.__starttime = -1
        else: self.__starttime = hour * 60 + minute

    def PluginPreferences(self, parent):
        hb = gtk.HBox(spacing=12)
        hb.set_border_width(6)
        cb = gtk.CheckButton("Fade out at:")
        e = gtk.Entry()
        if self.__starttime == -1: e.set_text("Enter a time in HH:MM format.")
        else: e.set_text("%d:%02d" % (
            self.__starttime / 60, self.__starttime % 60))
        e.connect('changed', self.__set_time)
        cb = gtk.CheckButton("Set alarm")
        cb.set_active(self.__enabled)
        cb.connect('clicked', self.__clicked, e)
        hb.pack_start(cb, expand=False)
        hb.pack_start(e, expand=True)
        hb.show_all()
        return hb
