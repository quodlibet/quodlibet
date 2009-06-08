# QLScrobbler: an Audioscrobbler client plugin for Quod Libet.
# version 0.8
# (C) 2005 by Joshua Kwan <joshk@triplehelix.org>,
#             Joe Wreschnig <piman@sacredchao.net>
# Licensed under GPLv2. See Quod Libet's COPYING for more information.

import random
import md5, urllib, urllib2, time, threading, os
import player, config, const, widgets, parse
import gobject, gtk
from qltk.msg import Message, WarningMessage
from qltk.entry import ValidatingEntry

def to(string): print string.encode("ascii", "replace")

from plugins.events import EventPlugin

# Set this to True to enable logging
verbose = False

def log(msg):
    if verbose:
        print "[qlscrobbler]", msg

class QLScrobbler(EventPlugin):
    # session invariants
    PLUGIN_ID = "QLScrobbler"
    PLUGIN_NAME = _("AudioScrobbler Submission")
    PLUGIN_DESC = "Audioscrobbler client for Quod Libet"
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.8.1"
    CLIENT = "qlb"
    PROTOCOL_VERSION = "1.1"
    try: DUMP = os.path.join(const.USERDIR, "scrobbler_cache")
    except AttributeError:
        DUMP = os.path.join(const.DIR, "scrobbler_cache")

    services = {
            'Last.fm':  'http://post.audioscrobbler.com/',
            'Libre.fm': 'http://turtle.libre.fm/'
            }

    # things that could change
    
    username = ""
    password = ""
    pwhash = ""
    exclude = ""
    
    timeout_id = -1
    submission_tid = -1

    challenge = ""
    base_url = ""
    submit_url = ""

    # state management
    waiting = False
    challenge_sent = False
    broken = False
    need_config = False
    need_update = False
    already_submitted = False
    locked = False
    flushing = False
    __enabled = False
    offline = False

    # we need to store this because not all events get the song
    song = None

    queue = []

    def __init__(self):
        # Read dumped queue and delete it
        try:
            dump = open(self.DUMP, 'r')
            self.read_dump(dump)
        except: pass

        # Read configuration
        self.read_config()
        
        # Set up exit hook to dump queue
        gtk.quit_add(0, self.dump_queue)

    def read_dump(self, dump):
        log("Loading dumped queue.")
    
        current = {}

        for line in dump.readlines():
            key = ""
            value = ""
            
            line = line.rstrip("\n")
            try: (key, value) = line.split(" = ", 1)
            except:
                if line == "-":
                    for key in ["album", "mbid"]:
                        if key not in current:
                            current[key] = ""
                    
                    for reqkey in ["artist", "title", "length", "stamp"]:
                        # discard if somehow invalid
                        if reqkey not in current:
                            current = {}

                    if current != {}:
                        self.queue.append(current)
                        current = {}
                continue
                
            if key == "length": current[key] = int(value)
            else: current[key] = value

        dump.close()

        os.remove(self.DUMP)

        # Try to flush it immediately
        if len(self.queue) > 0:
            self.flushing = True
            self.submit_song()
        else: log("Queue was empty!")

    def dump_queue(self):
        if len(self.queue) == 0: return 0
        
        log("Dumping offline queue, will submit next time.")

        dump = open(self.DUMP, 'w')
        
        for item in self.queue:
            for key in item:
                dump.write("%s = %s\n" % (key, item[key]))
            dump.write("-\n")

        dump.close()

        return 0
        
    def plugin_on_removed(self, songs):
        try:
            if self.song in songs:
                self.already_submitted = True
        except:
            # Older version compatibility.
            if self.song is songs:
                self.already_submitted = True

    def plugin_on_song_ended(self, song, stopped):
        if song is None: return

        if self.timeout_id > 0:
            gobject.source_remove(self.timeout_id)
            self.timeout_id = -1
    
    def plugin_on_song_started(self, song):
        if song is None: return
        
        self.already_submitted = False
        if self.timeout_id > 0:
            gobject.source_remove(self.timeout_id)
        
        self.timeout_id = -1

        # Protocol stipulation:
        #    * don't submit when length < 00:30
        #     NOTE: >30:00 stipulation has been REMOVED as of Protocol1.1
        #    * don't submit if artist and title are not available
        #if song["~#length"] < 30: return
        if 'title' not in song: return
        elif "artist" not in song:
            if ("composer" not in song) and ("performer" not in song): return
        
        # Check to see if this song is not something we'd like to submit
        #    e.g. "Hit Me Baby One More Time"
        if self.exclude != "" and parse.Query(self.exclude).search(song):
            log(to("Not submitting: %s - %s" % (song["artist"], song["title"])))
            return

        self.song = song
        if player.playlist.paused == False:
            self.prepare()

    def plugin_on_paused(self):
        if self.timeout_id > 0:
            gobject.source_remove(self.timeout_id)
            # special value that will tell on_unpaused to check song length
            self.timeout_id = -2

    def plugin_on_unpaused(self):
        if self.already_submitted == False and self.timeout_id == -1: self.prepare()
        
    def plugin_on_seek(self, song, msec):
        if self.timeout_id > 0:
            gobject.source_remove(self.timeout_id)
            self.timeout_id = -1
            
        if msec == 0: #I think this is okay!
            self.prepare()
        else:
            self.already_submitted = True # cancel
        
    def prepare(self):
        if self.song is None: return

        # Protocol stipulations:
        #    * submit 240 seconds in or at 50%, whichever comes first
        delay = int(min(self.song["~#length"] / 2, 240))

        if self.timeout_id == -2: # change delta based on current progress
            # assumption is that self.already_submitted == 0, therefore
            # delay - progress > 0
            progress = int(player.playlist.get_position() / 1000)
            delay -= progress

        self.timeout_id = gobject.timeout_add(delay * 1000, self.submit_song)
    
    def read_config(self):
        username = ""
        password = ""
        url = ""
        try:
            username = config.get("plugins", "scrobbler_username")
            password = config.get("plugins", "scrobbler_password")
            url = self._get_url(config.get("plugins", "scrobbler_service"))
        except:
            if (self.need_config == False and
                getattr(self, 'PMEnFlag', False)):
                self.quick_dialog("Please visit the Preferences window to set QLScrobbler up. Until then, songs will not be submitted.", gtk.MESSAGE_INFO)
                self.need_config = True
                return

        try: self.offline = (config.get("plugins", "scrobbler_offline") == "true")
        except: pass
        try: self.exclude = config.get("plugins", "scrobbler_exclude")
        except: pass
        
        self.username = username
        
        hasher = md5.new()
        hasher.update(password);
        self.password = hasher.hexdigest()
        self.base_url = url
        self.need_config = False

    def _get_url(self, service):
        if service in self.services:
            return self.services[service]
        else:
            try:
                return config.get("plugins", "scrobbler_url")
            except:
                return ""

    def __destroy_cb(self, dialog, response_id):
        dialog.destroy()
    
    def quick_dialog_helper(self, type, str):
        dialog = Message(gtk.MESSAGE_INFO, widgets.main, "QLScrobbler", str)
        dialog.connect('response', self.__destroy_cb)
        dialog.show()

    def quick_dialog(self, str, type):
        gobject.idle_add(self.quick_dialog_helper, type, str)
    
    def clear_waiting(self):
        self.waiting = False

    def send_handshake(self):
        # construct url
        url = "%s/?hs=true&p=%s&c=%s&v=%s&u=%s" % ( self.base_url,
                self.PROTOCOL_VERSION, self.CLIENT,
                self.PLUGIN_VERSION, self.username )
        
        log("Sending handshake to Audioscrobbler.")

        resp = None

        try:
            resp = urllib2.urlopen(url);
        except:
            log("Server not responding, handshake failed.")
            return # challenge_sent is NOT set to 1
            
        # check response
        lines = resp.read().rstrip().split("\n")
        status = lines.pop(0)

        log("Handshake status: %s" % status)
            
        if status == "UPTODATE" or status.startswith("UPDATE"):
            if status.startswith("UPDATE"):
                self.quick_dialog("A new plugin is available at %s! Please download it, or your Audioscrobbler stats may not be updated, and this message will be displayed every session." % status.split()[1], gtk.MESSAGE_INFO)
                self.need_update = True

            # Scan for submit URL and challenge.
            self.challenge = lines.pop(0)

            log("Challenge: %s" % self.challenge)

            # determine password
            hasher = md5.new()
            hasher.update(self.password)
            hasher.update(self.challenge)
            self.pwhash = hasher.hexdigest()

            self.submit_url = lines.pop(0)
            
            self.challenge_sent = True
        elif status == "BADUSER":
            self.quick_dialog("Authentication failed: invalid username %s or bad password." % self.username, gtk.MESSAGE_ERROR)
                
            self.broken = True

        # Honor INTERVAL if available
        try: interval = int(lines.pop(0).split()[1])
        except: interval = 0

        if interval > 1:
            self.waiting = True
            gobject.timeout_add(interval * 1000, self.clear_waiting)
            log("Server says to wait for %d seconds." % interval)
    
    def submit_song(self):
        bg = threading.Thread(None, self.submit_song_helper)
        bg.setDaemon(True)
        bg.start()

    def enabled(self):
        self.__enabled = True

    def disabled(self):
        self.__enabled = False

    def submit_song_helper(self):
        if self.__enabled:
            log("Plugin re-enabled - accepting new songs.")
            if self.submission_tid != -1:
                gobject.source_remove(self.submission_tid);
                self.submission_tid = -1
        else:
            log("Plugin disabled - not accepting any new songs.")
            if len(self.queue) > 0:
                self.submission_tid = gobject.timeout_add(120 * 1000, self.submit_song_helper)
                log("Attempts will continue to submit the last %d songs." % len(self.queue))

        if self.already_submitted == True or self.broken == True: return

        # Scope.
        store = {}
        
        if self.flushing == False:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    
            store = {
                "title": self.song.comma("title"),
                "length": str(self.song["~#length"]),
                "album": self.song.comma("album"),
                "mbid": "", # will be correctly set if available
                "stamp": stamp
            }

            if "artist" in self.song:
                store["artist"] = self.song.comma("artist")
            elif "composer" in self.song:
                store["artist"] = self.song.comma("composer")
            elif "performer" in self.song:
                performer = self.song.comma('performer')
                if performer[-1] == ")" and "(" in performer:
                    store["artist"] = performer[:performer.rindex("(")].strip()
                else:
                    store["artist"] = performer
            if "musicbrainz_trackid" in self.song:
                store["mbid"] = self.song["musicbrainz_trackid"]

            self.queue.append(store)
        else: self.flushing = False

        # Just note to stdout if either of these are true..
        # locked means another instance if s_s_h is dealing with sending.
        if self.offline or self.locked:
            log(to("Queuing: %s - %s" % (store["artist"], store["title"])))
            return

        self.locked = True

        while self.waiting == True: time.sleep(1)

        # Read config, handshake, and send challenge if not already done
        if self.challenge_sent == False:
            self.read_config()
            if self.broken == False and self.need_config == False:
                self.send_handshake()
        
        # INTERVAL may have been set during handshake.
        while self.waiting == True: time.sleep(1)
            
        if self.challenge_sent == False:
            self.locked = False
            return
        
        data = {
            'u': self.username,
            's': self.pwhash
        }
        
        # Flush the cache
        for i in range(min(len(self.queue), 10)):
            log(to("Sending song: %s - %s" % (self.queue[i]['artist'], self.queue[i]['title'])))
            data["a[%d]" % i] = self.queue[i]['artist'].encode('utf-8')
            data["t[%d]" % i] = self.queue[i]['title'].encode('utf-8')
            data["l[%d]" % i] = str(self.queue[i]['length'])
            data["b[%d]" % i] = self.queue[i]['album'].encode('utf-8')
            data["m[%d]" % i] = self.queue[i]['mbid']
            data["i[%d]" % i] = self.queue[i]['stamp']
        

        resp = None
        
        try:
            data_str = urllib.urlencode(data)
            resp = urllib2.urlopen(self.submit_url, data_str)
        except:
            log("Audioscrobbler server not responding, will try later.")
            self.locked = False
            return # preserve the queue, yadda yadda

        resp_save = resp.read()
        lines = resp_save.rstrip().split("\n")
        
        try: (status, interval) = lines
        except:
            try: status = lines[0]
            except:
                log("Truncated server response, will try later...")
                self.locked = False
                return
            interval = None
        
        log("Submission status: %s" % status)

        if status == "BADAUTH":
            log("Attempting to re-authenticate.")
            self.challenge_sent = False
            self.send_handshake()
            if self.challenge_sent == False:
                self.quick_dialog("Your Audioscrobbler login data is incorrect, so you must re-enter it before any songs will be submitted.\n\nThis message will not be shown again.", gtk.MESSAGE_ERROR)
                self.broken = True
        elif status == "OK":
            self.queue = self.queue[10:]
        elif status.startswith("FAILED"):
            if status.startswith("FAILED Plugin bug"):
                log("Plugin bug!? Ridiculous! Dumping queue contents.")
                for item in self.queue:
                    for key in item:
                        log(to("%s = %s" % (key, item[key])))
            # possibly handle other specific cases here for debugging later
        else:
            log("Unknown response from server: %s" % status)
            log("Dumping full response:")
            log(resp_save)

        if interval != None: interval_secs = int(interval.split()[1])
        else: interval_secs = 0

        if interval_secs > 1:
            self.waiting = True
            gobject.timeout_add(interval_secs * 1000, self.clear_waiting)
            log("Server says to wait for %d seconds." % interval_secs)

        if not self.__enabled and len(self.queue) == 0 and self.submission_tid != -1:
            log("All songs submitted, disabling retries.")
            gobject.source_remove(self.submission_tid)
            self.submission_tid = -1

        self.already_submitted = True
        self.locked = False

    def PluginPreferences(self, parent):
        def toggled(widget):
            if widget.get_active():
                config.set("plugins", "scrobbler_offline", "true")
                self.offline = True
            else:
                config.set("plugins", "scrobbler_offline", "false")
                self.offline = False

        def changed(entry, key):
            # having a function for each entry is unnecessary..
            if entry.get_property('sensitive'):
                config.set("plugins", "scrobbler_" + key, entry.get_text())

        def combo_changed(widget, urlent):
            service = widget.get_active_text()
            config.set("plugins", "scrobbler_service", service)
            urlent.set_sensitive( (service not in self.services) )
            urlent.set_text(self._get_url(service))

        def destroyed(*args):
            # if changed, let's say that things just got better and we should
            # try everything again
            newu = None
            newp = None
            news = None
            newsu = None
            try:
                newu = config.get("plugins", "scrobbler_username")
                newp = config.get("plugins", "scrobbler_password")
                news = config.get("plugins", "scrobbler_service")
                newsu = config.get("plugins", "scrobbler_url")
            except:
                return

            try: self.exclude = config.get("plugins", "scrobbler_exclude")
            except: pass

            if (self.username != newu or self.password != newp or self.service != news
                    or (news == "Other..." and self.target != newsu)):
                self.broken = False

        table = gtk.Table(6, 3)
        table.set_col_spacings(3)
        table.set_border_width(6)
        ls = gtk.Label(_("Service:"))
        lsu = gtk.Label(_("URL:"))
        lu = gtk.Label(_("Username:"))
        lp = gtk.Label(_("Password:"))
        lv = gtk.Label(_("Exclude filter:"))
        for l in [ls, lsu, lu, lp, lv]:
            l.set_line_wrap(True)
            l.set_alignment(0.0, 0.5)
        table.attach(ls,  0, 1, 0, 1, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(lsu, 0, 1, 1, 2, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(lu,  0, 1, 2, 3, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(lp,  0, 1, 3, 4, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(lv,  0, 1, 4, 5, xoptions=gtk.FILL | gtk.SHRINK)

        serv = gtk.combo_box_new_text()
        off = gtk.CheckButton(_("Offline mode (don't submit anything)"))
        urlent = gtk.Entry()
        userent = gtk.Entry()
        pwent = gtk.Entry()
        pwent.set_visibility(False)
        pwent.set_invisible_char('*')
        ve = ValidatingEntry(parse.Query.is_valid_color)
        ve.set_tooltip_text(_("Songs matching this filter will not be submitted."))

        table.attach(serv,      2, 3, 0, 1, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(urlent,    2, 3, 1, 2, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(userent,   2, 3, 2, 3, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(pwent,     2, 3, 3, 4, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(ve,        2, 3, 4, 5, xoptions=gtk.FILL | gtk.SHRINK)
        table.attach(off,       0, 3, 5, 6, xoptions=gtk.FILL | gtk.SHRINK)

        try: cur_service = config.get("plugins", "scrobbler_service")
        except: cur_service = sorted(self.services.keys())[0]
        for i, s in enumerate(sorted(self.services.keys()) + ["Other..."]):
            serv.append_text(s)
            if cur_service == s:
                serv.set_active(i)
        if serv.get_active() == -1:
            serv.set_active(0)
        urlent.set_sensitive( (cur_service not in self.services) )
        urlent.set_text(self._get_url(cur_service))
        try: userent.set_text(config.get("plugins", "scrobbler_username"))
        except: pass
        try: pwent.set_text(config.get("plugins", "scrobbler_password"))
        except: pass
        try:
            if config.get("plugins", "scrobbler_offline") == "true":
                off.set_active(True)
        except: pass
        try: ve.set_text(config.get("plugins", "scrobbler_exclude"))
        except: pass

        serv.connect('changed', combo_changed, urlent)
        urlent.connect('changed', changed, 'url')
        pwent.connect('changed', changed, 'password')
        userent.connect('changed', changed, 'username')
        ve.connect('changed', changed, 'exclude')
        table.connect('destroy', destroyed)
        off.connect('toggled', toggled)

        return table
