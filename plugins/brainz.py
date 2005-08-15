# (C) 2005 Joshua Kwan <joshk@triplehelix.org>
# redistributable under the terms of the GNU GPL, version 2 or later

import musicbrainz, os, gtk
from musicbrainz.queries import *
from qltk import *

class AlbumCandidate(object):
	various = False
	tracklist = []
	id = ""

# Shamelessly stolen from cddb.py
class AskAction(ConfirmAction):
    """A message dialog that asks a yes/no question."""
    def __init__(self, *args, **kwargs):
        kwargs["buttons"] = gtk.BUTTONS_YES_NO
        Message.__init__(self, gtk.MESSAGE_QUESTION, *args, **kwargs)

class QLBrainz(object):
	PLUGIN_NAME = 'MusicBrainz lookup'
	PLUGIN_ICON = 'gtk-cdrom'
	PLUGIN_DESC = 'Retag an album based on a MusicBrainz search.'
	PLUGIN_VERSION = '0.1'

	VARIOUS_ARTISTS_ARTISTID = '89ad4ac3-39f7-470e-963a-56509c546377'

	mb = None
	
	def __init__(self):
		# Prepare the MusicBrainz client class
		self.mb = musicbrainz.mb()
		self.mb.SetDepth(4)

	# A function that assumes you just 'select'ed an album. Returns
	def __cache_this_album(self, tracks):
		tracklist = []

		# local mb has state data, this should work.
			
		this_numtracks = self.mb.GetResultInt(MBE_AlbumGetNumTracks)
		this_title = self.mb.GetResultData(MBE_AlbumGetAlbumName)
		this_artistid = self.mb.GetResultData(MBE_AlbumGetAlbumArtistId)

		print "Album has %d tracks" % this_numtracks
		if this_numtracks == tracks:
			new_candidate = AlbumCandidate()
			
			new_candidate.id = self.mb.GetIDFromURL(self.mb.GetResultData(MBE_AlbumGetAlbumId))
		
			if this_artistid == self.VARIOUS_ARTISTS_ARTISTID:
				new_candidate.various = True
				
			# Now cache EVERYTHING for all tracks
			# If this tracklist is used, its dict will be merged into the
			# target song's dict, so use the proper keys.
			for j in range(1, tracks + 1):
				track_data = {}
					
				track_data['musicbrainz_trackid'] = self.mb.GetIDFromURL(self.mb.GetResultData1(MBE_AlbumGetTrackId, j))

				# VA album is possible, just obliquely cover all cases
				track_data['artist'] = self.mb.GetResultData1(MBE_AlbumGetArtistName, j)
				track_data['title'] = self.mb.GetResultData1(MBE_AlbumGetTrackName, j)
				track_data['album'] = this_title
				track_data['tracknumber'] = str(j)

				new_candidate.tracklist.append(track_data)
					
			print "Album: %s" % new_candidate.tracklist[0]['album']
			k = 1
			for track in new_candidate.tracklist:
				print "%d. %s - %s (%s)" % (k, track['artist'], track['title'],
					track['musicbrainz_trackid'])
				k = k + 1

			return new_candidate
		return None

	def __lookup_by_album_name(self, album, tracks):
		candidates = {}
		
		self.mb.QueryWithArgs(MBQ_FindAlbumByName, [album])

		n_albums = self.mb.GetResultInt(MBE_GetNumAlbums)

		print "Found %d albums" % n_albums

		for i in range(1, n_albums + 1):
			self.mb.Select(MBS_Rewind)
			self.mb.Select1(MBS_SelectAlbum, i)

			candidate = self.__cache_this_album(tracks)

			if candidate != None:
				candidates[candidate.id] = candidate

		return candidates

	def __do_tag(self, album, candidate):
		i = 0

		message = [
			"<b>Artist:</b> %s" % candidate.tracklist[0]['artist'],
			"<b>Album:</b> %s" % candidate.tracklist[0]['album'],
			"\n<u>%s</u>" % _("Track List")
		]
			
		for i in range(0, len(album)):
			if candidate.various:
				message.append("<b>%d.</b> %s - %s" % (i + 1,
					candidate.tracklist[i]['artist'],
					candidate.tracklist[i]['title']))
			else:
				message.append("<b>%d.</b> %s" % (i + 1,
					candidate.tracklist[i]['title']))

		if AskAction(None, _("Save the following information?"),
			"\n".join(message)).run():
			for i in range(0, len(album)):
				for key in ['artist', 'title', 'album', 'musicbrainz_trackid', 'tracknumber']:
					if key not in album[i] or album[i][key] != candidate.tracklist[i][key]:
						album[i][key] = candidate.tracklist[i][key]

	def __do_tag_by_album_id(self, album, albumid):
		self.mb.QueryWithArgs(MBQ_GetAlbumById, [albumid])
		
		n_albums = self.mb.GetResultInt(MBE_GetNumAlbums)
		print "Found %d albums" % n_albums

		if n_albums == 1: # there better only be one album per ID
			self.mb.Select1(MBS_SelectAlbum, 1)
			
			candidate = self.__cache_this_album(len(album))

			self.__do_tag(album, candidate)
				
	def __get_album_trm(self, album):
		trm_this_album = []
		for track in album:
			i, o = None, None
			try: i, o = os.popen2(['trm', track('~filename')])
			except: raise TRMError #lame

			try: trm_this_album.append(o.readlines()[0].rstrip())
			except: raise TRMError

		return trm_this_album

	def __try_match_by_trm(self, album, candidates=[]):
		ErrorMessage(None, "", _("TRM matching feature not done yet, sorry.")).run()

#	def __get_album_id_from_track_id(self, track):
#		self.mb.QueryWithArgs(MBQ_GetTrackById, [track])

		
	def plugin_album(self, album, override=None):
		# If there is already an album name. When plugin_album is called,
		# all of the 'album' entries are guaranteed to be the same.
		mb_album = None
		
		# Test for user error.
		if 'tracknumber' in album[0] and int(album[0]('tracknumber').split("/")[0]) != 1:
			ErrorMessage(None, "",
			_("Please select the entire album (starting from track 1!)")).run()
#		elif 'musicbrainz_trackid' in album[0]: # Fetch album information
#			albumid = self.__get_album_id_from_track_id(album[0]('musicbrainz_trackid'))
#			self.__do_tag_by_album_id(album, albumid)
		elif override is not None or 'album' in album[0]:
			album_name = ""
			if override is not None: album_name = override
			else: album_name = album[0]('album')
			
			candidates = self.__lookup_by_album_name(album_name, len(album))

			# differentiate by TRM
			if len(candidates) > 1:
				self.__try_match_by_trm(album, candidates)

			elif len(candidates) == 0:
				name = GetStringDialog(
					None, _("Couldn't locate album by name"),
					_("Couldn't find an album with the name \"%s\". To retry "
					  "with another possible album name, enter it here. If "
					  "left blank, each track will be fingerprinted and an "
					  "attempt to match the album using the audio fingerprints "
					  "will occur.") % album_name, [], gtk.STOCK_OK).run()
				# recursion. well...
				if name: self.plugin_album(album, name)
				else: self.__try_match_by_trm(album)
					
			else:
				self.__do_tag(album, candidates[candidates.keys()[0]])
		elif 'album' not in album[0]: # and override is None
			name = GetStringDialog(
				None, _("Not enough information to locate album"),
				_("Please enter an album name to match this one to, or just "
				  "hit OK to attempt to match these tracks to an album based "
				  "on an audio fingerprint."), [],
				gtk.STOCK_OK).run()
			if name: self.plugin_album(album, name)
			else: self.__try_match_by_trm(album)
