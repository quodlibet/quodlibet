# QLScrobbler: an Audioscrobbler client plugin for Quod Libet.
# version 0.1
# (C) 2005 by Joshua Kwan <joshk@triplehelix.org>
# Licensed under GPLv2. See Quod Libet's COPYING for more information.

import httplib, md5, urllib, time, threading
import player, config
import gobject, gtk
from qltk import Message

class QLScrobbler(object):
	# session invariants
	PLUGIN_NAME = "QLScrobbler"
	PLUGIN_DESC = "AudioScrobbler client for Quod Libet"
	PLUGIN_VERSION = "1.0"
	CLIENT = "tst"
	PROTOCOL_VERSION = "1.1"

	# things that could change
	
	username = ""
	password = ""
	pwhash = ""
	timeout_id = -1

	challenge = ""
	submit_url = ""
	
	# state management
	waiting = False
	challenge_sent = False
	broken = False
	need_config = False
	need_update = False
	already_submitted = False
	locked = False

	# we need to store this because not all events get the song
	song_artist = ""
	song_title = ""
	song_album = ""
	song_length = 0

	queue = []

	def plugin_on_song_ended(self, song, stopped):
		if self.timeout_id > 0:
			gobject.source_remove(self.timeout_id)
			self.timeout_id = -1
	
	def plugin_on_song_started(self, song):
		self.already_submitted = False
		if self.timeout_id > 0:
			gobject.source_remove(self.timeout_id)
		
		self.timeout_id = -1

		if song is None: return
		# Protocol stipulation:
		#	* don't submit if artist and title are not available
		if not 'title' in song or not 'artist' in song:	return
		
		self.song_artist = song.comma("artist").encode("utf-8")
		self.song_title = song.comma("title").encode("utf-8")
		try: # Not required
			self.song_album = song.comma("album").encode("utf-8")
		except: self.song_album = ""
		self.song_length = int(song['~#length'])
		
		if player.playlist.paused == False:
			self.prepare()

	def plugin_on_paused(self):
		if self.timeout_id > 0:
			gobject.source_remove(self.timeout_id)
			# special value that will tell on_unpaused to check song length
			self.timeout_id = -2

	def plugin_on_unpaused(self):
		if self.already_submitted == False: self.prepare()
		
	def plugin_on_seek(self, song, msec):
		if self.timeout_id > 0:
			gobject.source_remove(self.timeout_id)
			self.timeout_id = -1
			
		if msec == 0: #I think this is okay!
			self.prepare()
		else:
			self.already_submitted = True # cancel
		
	def prepare(self):
		# Protocol stipulations:
		#	* don't submit when length < 00:30 or length > 30:00
		#	* submit 240 seconds in or at 50%, whichever comes first
		delay = 0
	
		if self.song_length > 30 * 60 or self.song_length < 30: return
		elif self.song_length / 2 < 240: delay = int(self.song_length / 2)
		else: delay = 240

		if self.timeout_id == -2: # change delta based on current progress
			# assumption is that self.already_submitted == 0, therefore
			# delay - progress > 0
			progress = int(player.playlist.info.time[0] / 1000)
			delay -= progress

		self.timeout_id = gobject.timeout_add(delay * 1000, self.submit_song)
	
	def read_config(self):
		username = ""
		password = ""
		try:
			username = config.get("plugins", "scrobbler_username")
			password = config.get("plugins", "scrobbler_password")
		except:
			if self.need_config == False:
				self.quick_info("Please visit the Preferences window to set QLScrobbler up. Until then, songs will not be submitted.")
				self.need_config = True
				return
		
		self.username = username
		
		hasher = md5.new()
		hasher.update(password);
		self.password = hasher.hexdigest()
		self.need_config = False
	
	def quick_error(self, str):
		gtk.threads_enter()
		Message(gtk.MESSAGE_ERROR, None, "QLScrobbler", str).run()
		gtk.threads_leave()
	
	def quick_info(self, str):
		gtk.threads_enter()
		Message(gtk.MESSAGE_INFO, None, "QLScrobbler", str).run()
		gtk.threads_leave()
	
	def clear_waiting(self):
		self.waiting = False
		
	def send_handshake(self):
		# construct url
		url = "/?hs=true&p=1.1&c=%s&v=%s&u=%s" % ( self.CLIENT, self.PLUGIN_VERSION, self.username )
		
		try:
			conn = httplib.HTTPConnection("post.audioscrobbler.com")
			conn.request("GET", url)
			resp = conn.getresponse()
			conn.close()
		except:
			return # challenge_sent is NOT set to 1
			
		if resp.status == 200:
			# check response
			lines = resp.read().rstrip().split("\n")
			status = lines.pop(0)

			print "Handshake status: %s" % status
			
			if status == "UPTODATE":
				# Scan for submit URL and challenge.
				self.challenge = lines.pop(0)

				print "Challenge: %s" % self.challenge

				# determine password
				hasher = md5.new()
				hasher.update(self.password)
				hasher.update(self.challenge)
				self.pwhash = hasher.hexdigest()

				self.submit_url = lines.pop(0)
			
				self.challenge_sent = True
			elif status.startswith("FAILED"):
				# Try again later. Check the INTERVAL...
				print "Server says to try later."
			elif status == "BADUSER":
				self.quick_error("Authentication failed: invalid username %s or bad password." % self.username)
				
				self.broken = True
			elif status.startswith("UPDATE"):
				self.quick_info("A new plugin is available at %s! Please download it,\nor this message will be displayed every session." % status.split(" ")[1])
				self.need_update = True
				lines.pop(0)

			# Honor INTERVAL
			interval = int(lines.pop(0).split(" ")[1])

			if interval > 0:
				self.waiting = True
				gobject.timeout_add(interval * 1000, self.clear_waiting)

	def submit_song(self):
		bg = threading.Thread(None, self.submit_song_helper)
		bg.start()

	def submit_song_helper(self):
		if self.already_submitted == True or self.broken == True: return

		stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
	
		store = {
			"artist": self.song_artist,
			"title": self.song_title,
			"length": str(self.song_length),
			"album": self.song_album,
			"mbid": "", # XXX
			"stamp": stamp
		}

		self.queue.insert(0, store)
		
		if self.locked == True:
			# another instance running, let it deal with this
			return

		self.locked = True

		if self.waiting == True:
			print "Waiting for INTERVAL to elapse before submitting."
		while self.waiting == True: time.sleep(1)

		# Read config, handshake, and send challenge if not already done
		if self.challenge_sent == False:
			self.read_config()
			if self.broken == False and self.need_config == False:
				self.send_handshake()
		
		data = {
			'u': self.username,
			's': self.pwhash
		}
		
		# INTERVAL may have been set during handshake.
		if self.waiting == True:
			print "Waiting for INTERVAL to elapse before submitting."
		while self.waiting == True: time.sleep(1)
			
		if self.challenge_sent == False:
			print "Deferring submission; no challenge has been sent yet."
			self.locked = False
			return
		
		print "Beginning submission"

		# Flush the cache
		for i in range(len(self.queue)):
			print "Sending song: %s - %s" % (self.queue[i]['artist'], self.queue[i]['title'])
			data["a[%d]" % i] = self.queue[i]['artist']
			data["t[%d]" % i] = self.queue[i]['title']
			data["l[%d]" % i] = str(self.queue[i]['length'])
			data["b[%d]" % i] = self.queue[i]['album']
			data["m[%d]" % i] = self.queue[i]['mbid']
			data["i[%d]" % i] = self.queue[i]['stamp']
		
		(host, file) = self.submit_url[7:].split("/") 

		conn = httplib.HTTPConnection(host)
		headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}

		resp = None
		
		try:
			data_str = urllib.urlencode(data)
			print "Sending request: %s" % data_str
			conn.request("POST", "/" + file, data_str, headers)
			resp = conn.getresponse()
			conn.close()
		except:
			# self-imposed INTERVAL
			self.waiting = True
			gobject.timeout_add(30000, self.clear_waiting)
			print "Failed to connect, will try later."
			self.locked = False
			return # preserve the queue, yadda yadda

		lines = resp.read().rstrip().split("\n")
		try: (status, interval) = lines
		except:
			print "Truncated server response, will try later..."
			self.locked = False
			return
		
		print "Submission status: %s" % status

		if status == "BADAUTH":
			self.quick_error("Your Audioscrobbler login data is incorrect, so you must re-enter it before any songs will be submitted.\n\nThis message will not be shown again.")
			self.broken = True
		elif status.startswith("FAILED"):
			# server error, no dialog, just try again
			print "Server says to try later."
		elif status == "OK":
			self.queue = []

		interval_secs = int(interval.split()[1])

		if interval_secs > 0:
			self.waiting = True
			gobject.timeout_add(interval_secs * 1000, self.clear_waiting)

		self.already_submitted = True
		self.locked = False

	def PluginPreferences(self, parent):
		def changed(entry):
			# having two functions is unnecessary..
			if entry.get_visibility() == False:
				config.set("plugins", "scrobbler_password", entry.get_text())
			else:
				config.set("plugins", "scrobbler_username", entry.get_text())

		def destroyed(*args):
			# if changed, let's say that things just got better and we should
			# try everything again
			newu = None
			newp = None
			try:
				newu = config.get("plugins", "scrobbler_username")
				newp = config.get("plugins", "scrobbler_password")
			except:
				return

			if self.username != newu or self.password != newp:
				self.broken = False

		table = gtk.Table(3, 2)
		table.attach(gtk.Label(_("Please enter your Audioscrobbler username and password.")), 0, 2, 0, 1)
		table.attach(gtk.Label(_("Username:")), 0, 1, 1, 2)
		table.attach(gtk.Label(_("Password:")), 0, 1, 2, 3)
		userent = gtk.Entry()
		pwent = gtk.Entry()
		pwent.set_visibility(False)
		pwent.set_invisible_char('*')
		
		try: userent.set_text(config.get("plugins", "scrobbler_username"))
		except: pass
		try: pwent.set_text(config.get("plugins", "scrobbler_password"))
		except: pass
		
		table.attach(userent, 1, 2, 1, 2)
		table.attach(pwent, 1, 2, 2, 3)
		pwent.connect('changed', changed)
		userent.connect('changed', changed)
		table.connect('destroy', destroyed)
		return table
