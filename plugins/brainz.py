# (C) 2005 Joshua Kwan <joshk@triplehelix.org>
# redistributable under the terms of the GNU GPL, version 2 or later

import musicbrainz, os, gtk
from musicbrainz.queries import *
from qltk import GetStringDialog, ErrorMessage, ConfirmAction, Message
from util import tag, escape

__all__ = ["QLBrainz"]

class AlbumCandidate(object):
	various = False
	tracklist = []
	trmlist = []
	id = ""

	def __init__(self):
		self.various = False
		self.tracklist = []
		self.trmlist = []
		self.id = ""

# Shamelessly stolen from cddb.py
class AskAction(ConfirmAction):
    """A message dialog that asks a yes/no question."""
    def __init__(self, *args, **kwargs):
        kwargs["buttons"] = gtk.BUTTONS_YES_NO
        Message.__init__(self, gtk.MESSAGE_QUESTION, *args, **kwargs)

class AlbumChooser(gtk.Dialog):
	active_candidate = None
	candidates = {}
	first = True

	def __title_match(self, a, b):
		c = filter(lambda x: x.isalnum(), a.lower())
		d = filter(lambda x: x.isalnum(), b.lower())

		return (c == d or c.startswith(d) or c.endswith(d) or d.startswith(c) or d.endswith(c))
	
	def __cursor_changed(self, view):
		selection = view.get_selection()
		selection.set_mode(gtk.SELECTION_SINGLE)
		model, iter = view.get_selection().get_selected()

		# This MAY be the parent node or not.
		while model.iter_parent(iter) != None: iter = model.iter_parent(iter)

		selection.unselect_all()
		view.collapse_all()
		view.expand_row(model.get_path(iter), False)
		selection.set_mode(gtk.SELECTION_MULTIPLE)
		selection.select_iter(iter)
		for i in range(0, model.iter_n_children(iter)):
			view.get_selection().select_iter(model.iter_nth_child(iter, i))
		self.active_candidate = model[iter][2]
		
		return

	def run(self):
		self.show_all()
		resp = gtk.Dialog.run(self)
		if resp == gtk.RESPONSE_OK:
			value = self.active_candidate
		else: value = None
		self.destroy()
		return value

	def __init__(self, brainz, album, candidates):
		gtk.Dialog.__init__(self, "Album selection")

		self.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK,
			gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)

		self.candidates = candidates
		
		label = gtk.Label(_("Multiple albums found, please select one. (Bold entries denote a track title match with the tags this album already has.)"))
		label.set_line_wrap(True)

		# Initialize the TreeStore and seed it with data from candidates
		treestore = gtk.TreeStore(str, str, str)
		
		for candidate in candidates.values():
			iter = treestore.append(None,
				["<i>%s</i>" % escape(candidate.tracklist[0]['album']),
				"", candidate.id])
			i = 1
			for track in candidate.tracklist:
				if 'title' in album[i - 1] and self.__title_match(album[i - 1]['title'], track['title']):
					treestore.append(iter,
						[escape(track['artist']), "%d. <b>%s</b>" %
						  (i, escape(track['title'])), ""])
				else:
					treestore.append(iter,
						[escape(track['artist']), "%d. %s" %
						  (i, escape(track['title'])), ""])
				i = i + 1
		
		view = gtk.TreeView(treestore)
		
		i = 0

		def pango_format(column, cell, model, iter, arg):
			cell.set_property('markup', model[iter][arg])

		for column in ["Album / Artist", "Title"]:
			renderer = gtk.CellRendererText()
			tvcolumn = gtk.TreeViewColumn(column, renderer, text=i)
			if column is "Title":
				tvcolumn.set_cell_data_func(renderer, pango_format, 1)
			else:
				tvcolumn.set_cell_data_func(renderer, pango_format, 0)
			
			tvcolumn.set_clickable(False)
			tvcolumn.set_resizable(True)
			view.append_column(tvcolumn)
			i = i + 1
		
		self.set_size_request(400, 300)
		
		swin = gtk.ScrolledWindow()
		swin.add(view)

		swin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)

		self.vbox.pack_start(label, expand=False, fill=True)
		self.vbox.pack_start(swin)

		view.connect('cursor-changed', self.__cursor_changed)

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

	""" A function that assumes you just 'select'ed an album. Returns an
	    AlbumCandidate with cached track list and list of TRMs for each
		track. """
	def __cache_this_album(self, tracks):
		tracklist = []
			
		this_numtracks = self.mb.GetResultInt(MBE_AlbumGetNumTracks)
		this_title = self.mb.GetResultData(MBE_AlbumGetAlbumName)
		this_artistid = self.mb.GetIDFromURL(self.mb.GetResultData(MBE_AlbumGetAlbumArtistId))

#		print "Album has %d tracks" % this_numtracks
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
				track_data['tracknumber'] = u"%d/%d" % (j, tracks)

				new_candidate.tracklist.append(track_data)

#				self.mb.Select1(MBS_SelectTrack, j - 1)

#				for k in range(0, self.mb.GetResultInt(MBE_GetNumTrmids, j)):
#					self.mb.Select(MBS_SelectTrmid, k)

#				self.mb.Select(MBS_Back)

#			print "Album: %s" % new_candidate.tracklist[0]['album']
#			k = 1
#			for track in new_candidate.tracklist:
#				print "%d. %s - %s (%s)" % (k, track['artist'], track['title'],
#					track['musicbrainz_trackid'])
#				k = k + 1

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

	def do_tag(self, album, candidate):
		i = 0

		album_artist = ""

		if candidate.various: album_artist = "Various Artists"
		else: album_artist = candidate.tracklist[0]['artist']

		message = [
			"<b>%s:</b> %s" % (tag("artist"), escape(album_artist)),
			"<b>%s:</b> %s" % (tag("album"), escape(candidate.tracklist[0]['album'])),
			"\n<u>%s</u>" % _("Track List")
		]
			
		for i in range(0, len(album)):
			if candidate.various:
				message.append("<b>%d.</b> %s - %s" % (i + 1,
					escape(candidate.tracklist[i]['artist']),
					escape(candidate.tracklist[i]['title'])))
			else:
				message.append("<b>%d.</b> %s" % (i + 1,
					escape(candidate.tracklist[i]['title'])))

		if AskAction(None, _("Save the following information?"),
			"\n".join(message)).run():
			for i in range(0, len(album)):
				for key in ['artist', 'title', 'album', 'musicbrainz_trackid', 'tracknumber']:
					if key not in album[i] or album[i][key] != candidate.tracklist[i][key]:
						album[i][key] = candidate.tracklist[i][key]

	def __get_album_trm(self, album):
		trm_this_album = []
		for track in album:
			i, o = None, None
			try: i, o = os.popen2(['trm', track('~filename')])
			except: raise TRMError #lame

			try: trm_this_album.append(o.readlines()[0].rstrip())
			except: raise TRMError

		return trm_this_album

	def __choose_album(self, album, candidates):
		ret = AlbumChooser(self, album, candidates).run()
		if ret is None: return
		else: self.do_tag(album, candidates[ret])

	def plugin_album(self, album, override=None):
		# If there is already an album name. When plugin_album is called,
		# all of the 'album' entries are guaranteed to be the same.
		mb_album = None
		
		# Test for user error.
		if 'tracknumber' in album[0] and int(album[0]('tracknumber').split("/")[0]) != 1:
			ErrorMessage(None, "",
			_("Please select the entire album (starting from track 1!)")).run()
		elif override is not None or 'album' in album[0]:
			album_name = ""
			if override is not None: album_name = override
			else: album_name = album[0]('album')
			
			candidates = self.__lookup_by_album_name(album_name, len(album))

			if len(candidates) > 1:
				self.__choose_album(album, candidates)

			elif len(candidates) == 0:
				name = GetStringDialog(
					None, _("Couldn't locate album by name"),
					_("Couldn't find an album with the name \"%s\". To retry "
					  "with another possible album name, enter it here.") %
					  album_name, [], gtk.STOCK_OK).run()
				# recursion. well...
				if name: self.plugin_album(album, name)
					
			else:
				self.do_tag(album, candidates[candidates.keys()[0]])
		elif 'album' not in album[0]: # and override is None
			name = GetStringDialog(
				None, _("Not enough information to locate album"),
				_("Please enter an album name to match this one to."), [],
				gtk.STOCK_OK).run()
			if name: self.plugin_album(album, name)
