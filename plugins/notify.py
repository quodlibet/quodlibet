from parse import XMLFromPattern
import dbus

print "[notify] loading"

class Notify(object):
    PLUGIN_NAME = "Notify"
    PLUGIN_DESC = "Display a notification when the song changes."
    PLUGIN_VERSION = "0.2"

    def __init__(self):
        print "[notify] connecting to D-Bus session bus"
        bus = dbus.SessionBus()
        obj = bus.get_object(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications")
        self.ni = dbus.Interface(obj, "org.freedesktop.Notifications")
        self.last_id = None

    # david's default settings - this needs to be configurable
    class conf(object):
        timeout = 4000
        show_icon = False
        single_notification = False
        string = r'''<album|\<b\><album>\</b\><discnumber| - Disc <discnumber>><part| - \<b\><part>\</b\>><tracknumber| - <tracknumber>>
>\<span weight='bold' size='large'\><title>\</span\> - <~length><version|
\<small\>\<i\><version>\</i\>\</small\>><~people|
by <~people>>'''

    # for rapid debugging
    def plugin_single_song(self, song): self.plugin_on_song_started(song)

    def plugin_on_song_started(self, song):
        if not song:
            return

        s = XMLFromPattern(self.conf.string) % song

        icon = ""
        if self.conf.show_icon:
            # This should perhaps scale the icon somehow
            iconf = song.find_cover()
            if iconf:
                icon = iconf.name

        if self.conf.single_notification and self.last_id is not None:
            last_id = self.last_id
        else:
            last_id = 0

        self.last_id = self.ni.Notify("Quod Libet", last_id, icon,
                                      "Now playing", s,
                                      "", {}, self.conf.timeout)
