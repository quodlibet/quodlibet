from parse import XMLFromPattern
import dbus
import gtk.gdk
import const
import os.path

from plugins.events import EventPlugin

# print "[notify] loading"

class Notify(EventPlugin):
    PLUGIN_ID = "Notify"
    PLUGIN_NAME = _("Notify")
    PLUGIN_DESC = "Display a notification when the song changes."
    PLUGIN_VERSION = "0.5"

    def __init__(self):
        # print "[notify] connecting to D-Bus session bus"
        bus = dbus.SessionBus()
        obj = bus.get_object(
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications")
        self.ni = dbus.Interface(obj, "org.freedesktop.Notifications")
        self.last_id = None

    # david's default settings - this needs to be configurable
    class conf(object):
        timeout = 4000
        show_icon = True
        single_notification = True
        string = r'''<album|\<b\><album>\</b\><discnumber| - Disc <discnumber>><part| - \<b\><part>\</b\>><tracknumber| - <tracknumber>>
>\<b\><title>\</b\> - <~length><version|
\<i\><version>\</i\>><~people|
by <~people>>'''

    # for rapid debugging
    def plugin_single_song(self, song): self.plugin_on_song_started(song)

    def plugin_on_song_started(self, song):
        if not song:
            return

        s = XMLFromPattern(self.conf.string) % song

        icon = ""
        if self.conf.show_icon:
            iconf = song.find_cover()
            if iconf is not None:
                try:
                    iconf = gtk.gdk.pixbuf_new_from_file_at_size(
                        iconf.name, 46, 46)
                except:
                        print "[notify] failed to create small cover image"
                else:
                    # add a black outline, using the same style from AlbumList
                    w, h = iconf.get_width(), iconf.get_height()
                    newcover = gtk.gdk.Pixbuf(
                        gtk.gdk.COLORSPACE_RGB, True, 8, w + 2, h + 2)
                    newcover.fill(0x000000ff)
                    iconf.copy_area(0, 0, w, h, newcover, 1, 1)
                    try:
                        # FIXME: This should be using a TemporaryFile anyway.
                        try: coverart = os.path.join(const.USERDIR, "cover.png")
                        except AttributeError:
                            os.path.join(const.DIR, "cover.png")
                        newcover.save(coverart, "png", {})
                        icon = coverart
                    except:
                        print "[notify] failed to save small cover image"

        if self.conf.single_notification and self.last_id is not None:
            last_id = self.last_id
        else:
            last_id = 0

        self.last_id = self.ni.Notify("Quod Libet", last_id, icon,
                                      "Now playing", s,
                                      "", {}, self.conf.timeout)
