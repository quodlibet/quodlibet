# QLScrobbler: an Audioscrobbler client plugin for Quod Libet.
# version 0.10.1
# (C) 2005-2010 by Joshua Kwan <joshk@triplehelix.org>,
#                  Joe Wreschnig <piman@sacredchao.net>,
#                  Franz Pletyz <fpletz@franz-pletz.org>,
#                  Nicholas J. Michalek <djphazer@gmail.com>,
#                  Steven Robertson <steven@strobe.cc>
# Licensed under GPLv2. See Quod Libet's COPYING for more information.

import urllib
import urllib2
import time
import threading
import os
import cPickle as pickle

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

import gobject, gtk

from quodlibet import player, config, const, widgets, parse, util, qltk
from quodlibet.qltk.msg import Message
from quodlibet.qltk.entry import ValidatingEntry, UndoEntry
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.plugins.events import EventPlugin

SERVICES = {
            'Last.fm':  'http://post.audioscrobbler.com/',
            'Libre.fm': 'http://turtle.libre.fm/'
           }

DEFAULT_SERVICE = 'Last.fm'
DEFAULT_TITLEPAT = '<title><version| (<version>)>'
DEFAULT_ARTISTPAT = '<artist|<artist>|<composer|<composer>|<performer>>>'

def log(msg):
    print_d("[qlscrobbler] %s" % msg)

def config_get(key, default=''):
    """Returns value for 'key' from config. If key is missing *or empty*,
    return default."""
    try:
        return (config.get("plugins", "scrobbler_%s" % key) or default)
    except config.error:
        return default

def config_get_url():
    # This logic is used often enough to be split out
    service = config_get('service', DEFAULT_SERVICE)
    if service in SERVICES:
        return SERVICES[service]
    else:
        return config_get('url')

class QLSubmitQueue:
    """Manages the submit queue for scrobbles. Works independently of the
    QLScrobbler plugin being enabled; other plugins may use submit() to queue
    songs for scrobbling."""

    CLIENT = "qlb"
    PROTOCOL_VERSION = "1.2"
    DUMP = os.path.join(const.USERDIR, "scrobbler_cache")

    # These objects are shared across instances, to allow other plugins to
    # queue scrobbles in future versions of QL
    queue = []
    changed_event = threading.Event()

    def nowplaying(self, song):
        """Send a Now Playing notification."""
        formatted = self._format_song(song)
        if not formatted or self.nowplaying_song == formatted:
            return
        self.nowplaying_song = formatted
        self.nowplaying_sent = False
        self.changed()

    def submit(self, song, timestamp=0):
        """Submit a song. If 'timestamp' is 0, the current time will
        be used."""
        formatted = self._format_song(song)
        if formatted is None: return
        if timestamp > 0:
            formatted['i'] = str(timestamp)
        elif timestamp == 0:
            formatted['i'] = str(int(time.time()))
        else:
            # Forging timestamps for submission from PMPs may be implemented
            # for QL 2.5
            return
        self.queue.append(formatted)
        self.changed()

    def _format_song(self, song):
        """Returns a dict with the keys formatted as required by spec."""
        store = {
            "l": str(song.get("~#length", 0)),
            "n": str(song("~#track")),
            "b": song.comma("album"),
            "m": song("musicbrainz_trackid"),
            "t": self.titlepat.format(song),
            "a": self.artpat.format(song),
        }

        # Spec requires title and artist at minimum
        if not (store.get("a") and store.get("t")):
            return None
        return store

    def __init__(self):
        self.nowplaying_song = None
        self.nowplaying_sent = False
        self.sessionid = None

        self.broken = False

        self.username, self.password, self.base_url = ('', '', '')

        # These need to be set early for _format_song to work
        self.titlepat = parse.Pattern(config_get('titlepat', DEFAULT_TITLEPAT))
        self.artpat = parse.Pattern(config_get('artistpat', DEFAULT_ARTISTPAT))

        try:
            disk_queue_file = open(self.DUMP, 'r')
            disk_queue = pickle.load(disk_queue_file)
            disk_queue_file.close()
            os.unlink(self.DUMP)
            self.queue += disk_queue
        except:
            pass

    @classmethod
    def dump_queue(klass):
        if klass.queue:
            try:
                disk_queue_file = open(klass.DUMP, 'w')
                pickle.dump(klass.queue, disk_queue_file)
                disk_queue_file.close()
            except IOError:
                pass
        return 0

    def _check_config(self):
        user = config_get('username')
        passw = md5(config_get('password')).hexdigest()
        url = config_get_url()
        if not user or not passw or not url:
            if self.queue and not self.broken:
                self.quick_dialog("Please visit the Plugins window to set "
                              "QLScrobbler up. Until then, songs will not be "
                              "submitted.", gtk.MESSAGE_INFO)
                self.broken = True
        elif (self.username, self.password, self.base_url)!=(user, passw, url):
            self.username, self.password, self.base_url = (user, passw, url)
            self.broken = False
            self.handshake_sent = False
        self.offline = (config_get('offline') == "true")
        self.titlepat = parse.Pattern(config_get('titlepat', DEFAULT_TITLEPAT))
        self.artpat = parse.Pattern(config_get('artistpat', DEFAULT_ARTISTPAT))

    def changed(self):
        """Signal that settings or queue contents were changed."""
        self._check_config()
        if not self.broken and not self.offline and (self.queue or
                (self.nowplaying_song and not self.nowplaying_sent)):
            self.changed_event.set()
            return
        self.changed_event.clear()

    def run(self):
        """Submit songs from the queue. Call from a daemon thread."""
        # The spec calls for exponential backoff of failed handshakes, with a
        # minimum of 1m and maximum of 120m delay between attempts.
        self.handshake_sent = False
        self.handshake_event = threading.Event()
        self.handshake_event.set()
        self.handshake_delay = 1

        self.failures = 0

        while True:
            self.changed_event.wait()
            if not self.handshake_sent:
                self.handshake_event.wait()
                if self.send_handshake():
                    self.failures = 0
                    self.handshake_delay = 1
                    self.handshake_sent = True
                else:
                    self.handshake_event.clear()
                    self.handshake_delay = min(self.handshake_delay*2, 120)
                    gobject.timeout_add(self.handshake_delay*60*1000,
                                        self.handshake_event.set)
                    continue
            self.changed_event.wait()
            if self.queue:
                if self.send_submission():
                    self.failures = 0
                else:
                    self.failures += 1
                    if self.failures >= 3:
                        self.handshake_sent = False
            elif self.nowplaying_song and not self.nowplaying_sent:
                self.send_nowplaying()
                self.nowplaying_sent = True
            else:
                # Nothing left to do; wait until something changes
                self.changed_event.clear()

    def send_handshake(self, show_dialog=False):
        # construct url
        stamp = int(time.time())
        auth = md5(self.password + str(stamp)).hexdigest()
        url = "%s/?hs=true&p=%s&c=%s&v=%s&u=%s&a=%s&t=%d" % (
                    self.base_url, self.PROTOCOL_VERSION, self.CLIENT,
                    QLScrobbler.PLUGIN_VERSION, self.username, auth, stamp)
        log("Sending handshake to service.")

        try:
            resp = urllib2.urlopen(url)
        except IOError:
            if show_dialog:
                self.quick_dialog(
                    "Could not contact service '%s'." %
                    util.escape(self.base_url), gtk.MESSAGE_ERROR)
            else:
                log("Could not contact service. Queueing submissions.")
            return False
        except ValueError:
            self.quick_dialog("Authentication failed: invalid URL.",
                gtk.MESSAGE_ERROR)
            self.broken = True
            return False

        # check response
        lines = resp.read().rstrip().split("\n")
        status = lines.pop(0)
        log("Handshake status: %s" % status)

        if status == "OK":
            self.session_id, self.nowplaying_url, self.submit_url = lines
            self.handshake_sent = True
            log("Session ID: %s, NP URL: %s, Submit URL: %s" % (
                self.session_id, self.nowplaying_url, self.submit_url))
            return True
        elif status == "BADAUTH":
            self.quick_dialog("Authentication failed: Invalid username '%s' "
                            "or bad password." % util.escape(self.username),
                            gtk.MESSAGE_ERROR)
            self.broken = True
        elif status == "BANNED":
            self.quick_dialog("Client is banned. Contact the author.",
                              gtk.MESSAGE_ERROR)
            self.broken = True
        elif status == "BADTIME":
            self.quick_dialog("Wrong system time. Submissions may fail until "
                              "it is corrected.", gtk.MESSAGE_ERROR)
        else:  # "FAILED"
            self.quick_dialog(status, gtk.MESSAGE_ERROR)
        self.changed()
        return False

    def _check_submit(self, url, data):
        data_str = urllib.urlencode(data)
        try:
            resp = urllib2.urlopen(url, data_str)
        except IOError:
            log("Audioscrobbler server not responding, will try later.")
            return False

        resp_save = resp.read()
        status = resp_save.rstrip().split("\n")[0]
        log("Submission status: %s" % status)

        if status == "OK":
            return True
        elif status == "BADSESSION":
            self.handshake_sent = False
            return False
        else:
            return False

    def send_submission(self):
        data = {'s': self.session_id}
        to_submit = self.queue[:min(len(self.queue), 50)]
        for idx, song in enumerate(to_submit):
            for key, val in song.items():
                data['%s[%d]' % (key, idx)] = val.encode('utf-8')
            data['o[%d]' % idx] = 'P'
            data['r[%d]' % idx] = ''

        log('Submitting song(s): %s' %
            ('\n\t'.join(['%s - %s' % (s['a'], s['t']) for s in to_submit])))

        if self._check_submit(self.submit_url, data):
            del self.queue[:len(to_submit)]
            return True
        else:
            return False

    def send_nowplaying(self):
        data = {'s': self.session_id}
        for key, val in self.nowplaying_song.items():
            data[key] = val.encode('utf-8')
        log('Now playing song: %s - %s' %
                (self.nowplaying_song['a'], self.nowplaying_song['t']))

        return self._check_submit(self.nowplaying_url, data)

    def quick_dialog_helper(self, dialog_type, msg):
        dialog = Message(dialog_type, widgets.main, "QLScrobbler", msg)
        dialog.connect('response', lambda dia, resp: dia.destroy())
        dialog.show()

    def quick_dialog(self, msg, dialog_type):
        gobject.idle_add(self.quick_dialog_helper, dialog_type, msg)

class QLScrobbler(EventPlugin):
    PLUGIN_ID = "QLScrobbler"
    PLUGIN_NAME = _("AudioScrobbler Submission")
    PLUGIN_DESC = _("Audioscrobbler client for Last.fm, Libre.fm and other "
        "Audioscrobbler services.")
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.10.1"

    def __init__(self):
        self.__enabled = False
        self.queue = QLSubmitQueue()
        queue_thread = threading.Thread(None, self.queue.run)
        queue_thread.setDaemon(True)
        queue_thread.start()

        self.start_time = 0
        self.unpaused_time = 0
        self.elapsed = 0
        self.nowplaying = None

        self.exclude = config_get('exclude')

        # Set up exit hook to dump queue
        gtk.quit_add(0, self.queue.dump_queue)

    def plugin_on_song_ended(self, song, stopped):
        if song is None or not self.__enabled:
            return
        if self.unpaused_time > 0:
            self.elapsed += time.time() - self.unpaused_time
        # Spec: * don't submit when song length < 00:30
        #       * submit at end of playback (not in the middle, as with v1.1)
        #       * submit if played for >= .5*length or >= 240s
        # we check 'elapsed' rather than 'length' to work around wrong ~#length
        if self.elapsed < 30:
            return
        if self.elapsed < 240 and self.elapsed <= .5 * song.get("~#length", 0):
            return
        if self.exclude != "" and parse.Query(self.exclude).search(song):
            log("Not submitting: %s - %s" % (song.get("artist"),
                                             song.get("title")))
            return
        self.queue.submit(song, self.start_time)

    def plugin_on_song_started(self, song):
        if song is None:
            return
        self.start_time = int(time.time())
        if player.playlist.paused:
            self.unpaused_time = 0
        else:
            self.unpaused_time = time.time()
        self.elapsed = 0
        if self.__enabled and not player.playlist.paused:
            self.queue.nowplaying(song)
        else:
            self.nowplaying = song

    def plugin_on_paused(self):
        if self.unpaused_time > 0:
            self.elapsed += time.time() - self.unpaused_time
        self.unpaused_time = 0

    def plugin_on_unpaused(self):
        self.unpaused_time = time.time()
        if self.__enabled and self.nowplaying:
            self.queue.nowplaying(self.nowplaying)
            self.nowplaying = None

    def enabled(self):
        self.__enabled = True
        log("Plugin enabled - accepting new songs.")

    def disabled(self):
        self.__enabled = False
        log("Plugin disabled - not accepting any new songs.")

    def PluginPreferences(self, parent):
        def changed(entry, key):
            if entry.get_property('sensitive'):
                config.set("plugins", "scrobbler_" + key, entry.get_text())

        def combo_changed(widget, urlent):
            service = widget.get_active_text()
            config.set("plugins", "scrobbler_service", service)
            urlent.set_sensitive( (service not in SERVICES) )
            urlent.set_text(config_get_url())

        def check_login(*args):
            queue = QLSubmitQueue()
            queue.changed()
            status = queue.send_handshake(show_dialog=True)
            if status:
                queue.quick_dialog("Authentication successful.",
                    gtk.MESSAGE_INFO)

        box = gtk.VBox(spacing=12)

        # first frame
        table = gtk.Table(5, 2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        labels = []
        label_names = [_("_Service:"), _("_URL:"), _("User_name:"),
            _("_Password:")]
        for idx, label in enumerate(map(gtk.Label, label_names)):
            label.set_alignment(0.0, 0.5)
            label.set_use_underline(True)
            table.attach(label, 0, 1, idx, idx+1,
                         xoptions=gtk.FILL | gtk.SHRINK)
            labels.append(label)

        row = 0
        service_combo = gtk.combo_box_new_text()
        table.attach(service_combo, 1, 2, row, row + 1)
        cur_service = config_get('service')
        for idx, serv in enumerate(sorted(SERVICES.keys()) + ["Other..."]):
            service_combo.append_text(serv)
            if cur_service == serv:
                service_combo.set_active(idx)
        if service_combo.get_active() == -1:
            service_combo.set_active(0)
        labels[row].set_mnemonic_widget(service_combo)
        row += 1

        # url
        entry = UndoEntry()
        entry.set_text(config_get('url'))
        entry.connect('changed', changed, 'url')
        service_combo.connect('changed', combo_changed, entry)
        service_combo.emit('changed')
        table.attach(entry, 1, 2, row, row + 1)
        labels[row].set_mnemonic_widget(entry)
        row += 1

        # username
        entry = UndoEntry()
        entry.set_text(config_get('username'))
        entry.connect('changed', changed, 'username')
        table.attach(entry, 1, 2, row, row + 1)
        labels[row].set_mnemonic_widget(entry)
        row += 1

        # password
        entry = UndoEntry()
        entry.set_text(config_get('password'))
        entry.set_visibility(False)
        entry.connect('changed', changed, 'password')
        table.attach(entry, 1, 2, row, row + 1)
        labels[row].set_mnemonic_widget(entry)
        row += 1

        # verify data
        button = qltk.Button(_("_Verify account data"), gtk.STOCK_INFO)
        button.connect('clicked', check_login)
        table.attach(button, 0, 2, 4, 5)

        box.pack_start(qltk.Frame(_("Account"), child=table))

        # second frame
        table = gtk.Table(4, 2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        label_names = [_("_Artist pattern:"), _("_Title pattern:"),
            _("Exclude _filter:")]

        labels = []
        for idx, label in enumerate(map(gtk.Label, label_names)):
            label.set_alignment(0.0, 0.5)
            label.set_use_underline(True)
            table.attach(label, 0, 1, idx, idx+1,
                         xoptions=gtk.FILL | gtk.SHRINK)
            labels.append(label)

        row = 0
        # artist pattern
        entry = UndoEntry()
        entry.set_text(config_get('artistpat'))
        entry.connect('changed', changed, 'artistpat')
        table.attach(entry, 1, 2, row, row + 1)
        entry.set_tooltip_text(_("The pattern used to format "
            "the artist name for submission. Leave blank for default."))
        labels[row].set_mnemonic_widget(entry)
        row += 1

        # title pattern
        entry = UndoEntry()
        entry.set_text(config_get('titlepat'))
        entry.connect('changed', changed, 'titlepat')
        table.attach(entry, 1, 2, row, row + 1)
        entry.set_tooltip_text(_("The pattern used to format "
            "the title for submission. Leave blank for default."))
        labels[row].set_mnemonic_widget(entry)
        row += 1

        # exclude filter
        entry = ValidatingEntry(parse.Query.is_valid_color)
        entry.set_text(config_get('exclude'))
        entry.set_tooltip_text(
                _("Songs matching this filter will not be submitted."))
        entry.connect('changed', changed, 'exclude')
        table.attach(entry, 1, 2, row, row + 1)
        labels[row].set_mnemonic_widget(entry)
        row += 1

        # offline mode
        offline = ConfigCheckButton(_("_Offline mode (don't submit anything)"),
                                'plugins', 'scrobbler_offline')
        offline.set_active(config_get('offline') == "true")
        table.attach(offline, 0, 2, row, row + 1)

        box.pack_start(qltk.Frame(_("Submission"), child=table))

        return box
