# -*- coding: utf-8 -*-

# Copyright 2005-2013 By:
# Eduardo Gonzalez, Niklas Janlert, Christoph Reiter, Antonio Riva,
# Aymeric Mansoux, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# August 2013: Nick Boultbee
# - Tidy plugin and classes: PEP-8, comments, use  dict literals etc.
# - Convert to using PluginConfigMixin for consistency with newer plugins
# - Fix plugin ID for consistency
# - Add basic unit test (elsewhere)
#

# Sat, 01 Aug 2009 13:19:31 by Christoph Reiter <christoph.reiter@gmx.at>
# - Fix coverparadise by handling bad HTML better
# - Use AppEngine webapp proxy (by wm_eddie) for Amazon
# - Increase search limit to 7 (from 5)
# - Treeview hints and DND
# - Some cleanup and version bump -> 0.5.1

# Wed Mar 04 09:11:28 2009 by Christoph Reiter <christoph.reiter@gmx.at>
# - Nearly complete rewrite
# - search engines: darktown, coverparadise, amazon (no aws, because
#    there was no search limit which would cause endless searching for
#    common terms and loosing a dependency is always good) and discogs
# - new: open with GIMP, image zooming mode, absolutely no UI freezes,
#     enable/disable search engines
# - Bumped version number to 0.5

# Wed May 21 21:16:48 EDT 2008 by <wm.eddie@gmail.com>
# - Some cleanup
# - Added to SVN
# - Bumped version number to 0.41

# Tue 2008-05-13 19:40:12 (+0200) by <wxcover@users.sourceforge.net>
# - Added walmart, darktown and buy.com cover searching.
# - Few fixes
# - Updated version number (0.25 -> 0.4)

# Mon 2008-05-05 14:54:27 (-0400)
# - Updated for new Amazon API by Jeremy Cantrell <jmcantrell@gmail.com>

import os
import time
import threading
import gzip

import urllib
import urllib2
from HTMLParser import HTMLParser, HTMLParseError
from cStringIO import StringIO
from xml.dom import minidom

from gi.repository import Gtk, Pango, GLib, Gdk, GdkPixbuf
from quodlibet.plugins import PluginConfigMixin
from quodlibet.util import format_size, print_exc

from quodlibet import util, qltk, print_w, app
from quodlibet.qltk.views import AllTreeView
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.parse import Pattern
from quodlibet.util.path import fsencode, iscommand

USER_AGENT = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) " \
    "Gecko/20101210 Iceweasel/3.6.13 (like Firefox/3.6.13)"

PLUGIN_CONFIG_SECTION = 'cover'
CONFIG_ENG_PREFIX = 'engine_'


def get_encoding_from_socket(socket):
    content_type = socket.headers.get("Content-Type", "")
    p = map(str.strip, map(str.lower, content_type.split(";")))
    enc = [t.split("=")[-1].strip() for t in p if t.startswith("charset")]
    return (enc and enc[0]) or "utf-8"


def get_url(url, post={}, get={}):
    post_params = urllib.urlencode(post)
    get_params = urllib.urlencode(get)
    if get:
        get_params = '?' + get_params

    # add post, get data and headers
    url = '%s%s' % (url, get_params)
    if post_params:
        request = urllib2.Request(url, post_params)
    else:
        request = urllib2.Request(url)

    # for discogs
    request.add_header('Accept-Encoding', 'gzip')
    request.add_header('User-Agent', USER_AGENT)

    url_sock = urllib2.urlopen(request)
    enc = get_encoding_from_socket(url_sock)

    # unzip the response if needed
    data = url_sock.read()
    if url_sock.headers.get("content-encoding", "") == "gzip":
        data = gzip.GzipFile(fileobj=StringIO(data)).read()
    url_sock.close()

    return data, enc


def get_encoding(url):
    request = urllib2.Request(url)
    request.add_header('Accept-Encoding', 'gzip')
    request.add_header('User-Agent', USER_AGENT)
    url_sock = urllib2.urlopen(request)
    return get_encoding_from_socket(url_sock)


class BasicHTMLParser(HTMLParser, object):
    """Basic Parser, stores all tags in a 3-tuple with tagname, attrs and data
    between the start tags. Ignores nesting but gives a consistent structure.
    All in all an ugly hack."""

    encoding = "utf-8"

    def __init__(self):
        super(BasicHTMLParser, self).__init__()

        self.data = []
        self.__buffer = []
        # Make the crappy HTMLParser ignore more stuff
        self.CDATA_CONTENT_ELEMENTS = ()

    def parse_url(self, url, post={}, get={}):
        """Will read the data and parse it into the data variable.
        A tag will be ['tagname', {all attributes}, 'data until the next tag']
        Only start tags are handled / used."""

        self.data = []

        text, self.encoding = get_url(url, post, get)
        text = text.decode(self.encoding, 'replace')

        # Strip script tags/content. HTMLParser doesn't handle them well
        text = "".join([p.split("script>")[-1] for p in text.split("<script")])

        try:
            self.feed(text)
            self.close()
        except HTMLParseError:
            pass

    def handle_starttag(self, tag, attrs):
        if self.__buffer:
            self.__buffer.append('')
            self.data.append(self.__buffer)
            self.__buffer = []
        self.__buffer = [tag, dict(attrs)]

    def handle_data(self, data):
        if self.__buffer:
            self.__buffer.append(data)
            self.data.append(self.__buffer)
            self.__buffer = []
        else:
            self.data.append(['', {}, data])


class CoverParadiseParser(BasicHTMLParser):
    """A class for searching covers from coverparadise.to"""

    ROOT_URL = 'http://coverparadise.to'

    def start(self, query, limit=10):
        """Start the search and return a list of covers"""

        if isinstance(query, str):
            query = query.decode("utf-8")

        # Site only takes 3+ chars
        if len(query) < 3:
                return []

        query = query.encode(get_encoding(self.ROOT_URL))

        # Parse the first page
        self.__parse_search_list(query)

        # Get the max number of offsets and the step size
        max_offset = -1
        step_size = 0
        for i, (tag, attr, data) in enumerate(self.data):
            if "SimpleSearchPage" in attr.get("href", ""):
                offset = int(attr["href"].split(",")[1].strip("' "))
                if offset > max_offset:
                    step_size = step_size or (offset - max_offset)
                    max_offset = offset

        if max_offset == -1:
            # If there is no offset, this is a single result page
            covers = self.__extract_from_single()
        else:
            # otherwise parse it as a list for each page
            covers = self.__extract_from_list()
            for offset in range(step_size, max_offset + 1, step_size):
                if len(covers) >= limit:
                    break
                self.__parse_search_list(query, offset)
                covers.extend(self.__extract_from_list())

        del self.data
        return covers

    def __parse_search_list(self, query, offset=0):
        post = {
            "SearchString": query,
            "Page": offset,
            "Sektion": "2",
        }

        self.parse_url(self.ROOT_URL + '/?Module=SimpleSearch', post=post)

    def __extract_from_single(self):
        covers = []

        cover = None
        for i, (tag, attr, data) in enumerate(self.data):
            data = data.strip()

            if attr.get("class", "") == "ThumbDetails":
                cover = {"source": self.ROOT_URL}

            if cover:
                if attr.get("href"):
                    cover["cover"] = self.ROOT_URL + attr["href"]

                if attr.get("src") and "thumbnail" not in cover:
                    cover["thumbnail"] = attr["src"]
                    if "front" not in attr.get("alt").lower():
                        cover = None
                        continue

                if attr.get("title"):
                    cover["name"] = attr["title"]

                if tag == "br":
                    if data.endswith("px"):
                        cover["resolution"] = data.strip("@ ")
                    elif data.lower().endswith("b"):
                        cover["size"] = data.strip("@ ")

                if len(cover.keys()) >= 6:
                    covers.append(cover)
                    cover = None

        return covers

    def __extract_from_list(self):
        covers = []

        cover = None
        old_data = ""
        last_entry = ""
        for i, (tag, attr, data) in enumerate(self.data):
            data = data.strip()

            if "ViewEntry" in attr.get("href", "") and \
                    attr.get("href") != last_entry:
                cover = {"source": self.ROOT_URL}
                last_entry = attr.get("href")

            if cover:
                if attr.get("src") and "thumbnail" not in cover:
                    cover["thumbnail"] = attr["src"]

                    uid = attr["src"].rsplit("/")[-1].split(".")[0]
                    url = self.ROOT_URL + "/res/exe/GetElement.php?ID=" + uid
                    cover["cover"] = url

                if data and "name" not in cover:
                    cover["name"] = data

                if "dimension" in old_data.lower() and data:
                    cover["resolution"] = data

                if "filesize" in old_data.lower() and data:
                    cover["size"] = data

                if len(cover.keys()) >= 6:
                    covers.append(cover)
                    cover = None

            old_data = data

        return covers


class DiscogsParser(object):
    """A class for searching covers from discogs.com"""

    def __init__(self):
        self.api_key = 'e404383a2a'
        self.url = 'http://www.discogs.com'
        self.cover_list = []
        self.limit = 0
        self.limit_count = 0

    def __get_search_page(self, page, query):
        """Returns the XML DOM of a search result page. Starts with 1."""

        search_url = self.url + '/search'
        search_paras = {
            'type': 'releases',
            'q': query,
            'f': 'xml',
            'api_key': self.api_key,
            'page': page,
        }

        data, enc = get_url(search_url, get=search_paras)
        return minidom.parseString(data)

    def __parse_list(self, dom):
        """Returns a list with the album name and the uri.
        Since the naming of releases in the specific release pages
        seems complex.. use the one from the search result page."""

        list = []
        results = dom.getElementsByTagName('result')
        for result in results:
            uri_tag = result.getElementsByTagName('uri')[0]
            uri = uri_tag.firstChild.data
            name = result.getElementsByTagName('title')[0].firstChild.data
            list.append((uri, name))

        return list

    def __parse_release(self, url, name):
        """Parse the release page and add the cover to the list."""

        if len(self.cover_list) >= self.limit:
            return

        rel_paras = {
            'api_key': self.api_key,
            'f': 'xml',
        }

        data, enc = get_url(url, get=rel_paras)
        dom = minidom.parseString(data)
        imgs = dom.getElementsByTagName('image')
        cover = {}

        for img in imgs:
            if img.getAttribute('type') == 'primary':
                width = img.getAttribute('width')
                height = img.getAttribute('height')
                cover = {
                    'cover': img.getAttribute('uri'),
                    'resolution': '%s x %s px' % (width, height),
                    'thumbnail': img.getAttribute('uri150'),
                    'name': name,
                    'size': get_size_of_url(cover['cover']),
                    'source': self.url,
                }
                break

        if cover and len(self.cover_list) < self.limit:
            self.cover_list.append(cover)

    def start(self, query, limit=10):
        """Start the search and return the covers"""

        self.limit = limit
        self.limit_count = 0
        self.cover_list = []

        page = 1
        limit_stop = False

        while 1:
            dom = self.__get_search_page(page, query)

            result = dom.getElementsByTagName('searchresults')

            if not result:
                break

            # Number of all results
            all = int(result[0].getAttribute('numResults'))
            # Last result number on the page
            end = int(result[0].getAttribute('end'))

            urls = self.__parse_list(dom)

            thread_list = []
            for url, name in urls:
                self.limit_count += 1

                thr = threading.Thread(target=self.__parse_release,
                                       args=(url, name))
                thr.setDaemon(True)
                thr.start()
                thread_list.append(thr)

                # Don't search forever if there are many entries with no image
                # In the default case of limit=10 this will prevent searching
                # the second result page...
                if self.limit_count >= self.limit * 2:
                    limit_stop = True
                    break

            for thread in thread_list:
                thread.join()

            if end >= all or limit_stop:
                break

            page += 1
        return self.cover_list


class AmazonParser(object):
    """A class for searching covers from Amazon"""

    def __init__(self):
        self.page_count = 0
        self.covers = []
        self.limit = 0

    def __parse_page(self, page, query):
        """Gets all item tags and calls the item parsing function for each"""

        # Amazon now requires that all requests be signed.
        # I have built a webapp on AppEngine for this purpose. -- wm_eddie
        # url = 'http://webservices.amazon.com/onca/xml'
        url = 'http://qlwebservices.appspot.com/onca/xml'

        parameters = {
            'Service': 'AWSECommerceService',
            'AWSAccessKeyId': '0RKH4ZH1JCFZHMND91G2', # Now Ignored.
            'Operation': 'ItemSearch',
            'ResponseGroup': 'Images,Small',
            'SearchIndex': 'Music',
            'Keywords': query,
            'ItemPage': page,
            # This specifies where the money goes and needed since 1.11.2011
            # (What a good reason to break API..)
            # ...so use the gnome.org one
            'AssociateTag': 'gnomestore-20',
        }
        data, enc = get_url(url, get=parameters)
        dom = minidom.parseString(data)

        pages = dom.getElementsByTagName('TotalPages')
        if pages:
            self.page_count = int(pages[0].firstChild.data)

        items = dom.getElementsByTagName('Item')

        for item in items:
            self.__parse_item(item)
            if len(self.covers) >= self.limit:
                break

    def __parse_item(self, item):
        """Extract all information and add the covers to the list."""

        large = item.getElementsByTagName('LargeImage')
        small = item.getElementsByTagName('SmallImage')
        title = item.getElementsByTagName('Title')

        if large and small and title:
            cover = {}

            artist = item.getElementsByTagName('Artist')
            creator = item.getElementsByTagName('Creator')

            text = ''
            if artist:
                text = artist[0].firstChild.data
            elif creator:
                if len(creator) > 1:
                    text = ', '.join([i.firstChild.data for i in creator])
                else:
                    text = creator[0].firstChild.data

            title_text = title[0].firstChild.data

            if len(text) and len(title_text):
                text += ' - '

            cover['name'] = text + title_text

            url_tag = small[0].getElementsByTagName('URL')[0]
            cover['thumbnail'] = url_tag.firstChild.data

            url_tag = large[0].getElementsByTagName('URL')[0]
            cover['cover'] = url_tag.firstChild.data

            #Since we don't know the size, use the one from the HTML header.
            cover['size'] = get_size_of_url(cover['cover'])

            h_tag = large[0].getElementsByTagName('Height')[0]
            height = h_tag.firstChild.data

            w_tag = large[0].getElementsByTagName('Width')[0]
            width = w_tag.firstChild.data

            cover['resolution'] = '%s x %s px' % (width, height)

            cover['source'] = 'http://www.amazon.com'

            self.covers.append(cover)

    def start(self, query, limit=10):
        """Start the search and returns the covers"""

        self.page_count = 0
        self.covers = []
        self.limit = limit
        self.__parse_page(1, query)

        if len(self.covers) < limit:
            for page in xrange(2, self.page_count + 1):
                self.__parse_page(page, query)
                if len(self.covers) >= limit:
                    break

        return self.covers


class CoverArea(Gtk.VBox, PluginConfigMixin):
    """The image display and saving part."""

    CONFIG_SECTION = PLUGIN_CONFIG_SECTION

    def __init__(self, parent, song):
        super(CoverArea, self).__init__()
        self.song = song

        self.dirname = song("~dirname")
        self.main_win = parent

        self.data_cache = []
        self.current_data = None
        self.current_pixbuf = None

        self.image = Gtk.Image()
        self.button = Gtk.Button(stock=Gtk.STOCK_SAVE)
        self.button.set_sensitive(False)
        self.button.connect('clicked', self.__save)

        close_button = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        close_button.connect('clicked', lambda x: self.main_win.destroy())

        self.window_fit = self.ConfigCheckButton(_('Fit image to _window'),
                                                 'fit', True)
        self.window_fit.connect('toggled', self.__scale_pixbuf)

        self.name_combo = Gtk.ComboBoxText()

        self.cmd = qltk.entry.ValidatingEntry(iscommand)

        # Both labels
        label_open = Gtk.Label(label=_('_Program:'))
        label_open.set_use_underline(True)
        label_open.set_mnemonic_widget(self.cmd)
        label_open.set_justify(Gtk.Justification.LEFT)

        self.open_check = self.ConfigCheckButton(_('_Edit image after saving'),
                                                 'edit', False)
        label_name = Gtk.Label(label=_('File_name:'), use_underline=True)
        label_name.set_use_underline(True)
        label_name.set_mnemonic_widget(self.name_combo)
        label_name.set_justify(Gtk.Justification.LEFT)

        self.cmd.set_text(self.config_get('edit_cmd', 'gimp'))

        # Create the filename combo box
        fn_list = ['cover.jpg', 'folder.jpg', '.folder.jpg']

        # Issue 374 - add dynamic file names
        artist = song("artist")
        alartist = song("albumartist")
        album = song("album")
        labelid = song("labelid")
        if album:
            fn_list.append("<album>.jpg")
            if alartist:
                fn_list.append("<albumartist> - <album>.jpg")
            else:
                fn_list.append("<artist> - <album>.jpg")
        else:
            print_w("No album for \"%s\". Could be difficult finding art..." %
                    song("~filename"))
            title = song("title")
            if title and artist:
                fn_list.append("<artist> - <title>.jpg")
        if labelid:
            fn_list.append("<labelid>.jpg")

        set_fn = self.config_get('fn', fn_list[0])

        for i, fn in enumerate(fn_list):
                self.name_combo.append_text(fn)
                if fn == set_fn:
                    self.name_combo.set_active(i)

        if self.name_combo.get_active() < 0:
            self.name_combo.set_active(0)

        table = Gtk.Table(rows=2, columns=2, homogeneous=False)
        table.set_row_spacing(0, 5)
        table.set_row_spacing(1, 5)
        table.set_col_spacing(0, 5)
        table.set_col_spacing(1, 5)

        table.attach(label_open, 0, 1, 0, 1)
        table.attach(label_name, 0, 1, 1, 2)

        table.attach(self.cmd, 1, 2, 0, 1)
        table.attach(self.name_combo, 1, 2, 1, 2)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.add_with_viewport(self.image)
        self.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC,
                                 Gtk.PolicyType.AUTOMATIC)

        bbox = Gtk.HButtonBox()
        bbox.set_spacing(6)
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.pack_start(self.button, True, True, 0)
        bbox.pack_start(close_button, True, True, 0)

        bb_align = Gtk.Alignment.new(0, 1, 1, 0)
        bb_align.set_property('right-padding', 6)
        bb_align.add(bbox)

        main_hbox = Gtk.HBox()
        main_hbox.pack_start(table, False, True, 6)
        main_hbox.pack_start(bb_align, True, True, 0)

        top_hbox = Gtk.HBox()
        top_hbox.pack_start(self.open_check, True, True, 0)
        top_hbox.pack_start(self.window_fit, False, True, 0)

        main_vbox = Gtk.VBox()
        main_vbox.pack_start(top_hbox, True, True, 2)
        main_vbox.pack_start(main_hbox, True, True, 0)

        self.pack_start(self.scrolled, True, True, 0)
        self.pack_start(main_vbox, False, True, 5)

        # 5 MB image cache size
        self.max_cache_size = 1024 * 1024 * 5

        # For managing fast selection switches of covers..
        self.stop_loading = False
        self.loading = False
        self.current_job = 0

        self.connect('destroy', self.__save_config)

    def __save(self, *data):
        """Save the cover and spawn the program to edit it if selected"""

        filename = self.name_combo.get_active_text()
        # Allow support for filename patterns
        pattern = Pattern(filename)
        filename = fsencode(pattern.format(self.song))
        file_path = os.path.join(self.dirname, filename)

        msg = (_('The file <b>%s</b> already exists.\n\nOverwrite?')
                % util.escape(filename))
        if (os.path.exists(file_path)
                and not qltk.ConfirmAction(None, _('File exists'), msg).run()):
            return

        try:
            f = open(file_path, 'wb')
            f.write(self.current_data)
            f.close()
        except IOError:
            qltk.ErrorMessage(None, _('Saving failed'),
                _('Unable to save "%s".') % file_path).run()
        else:
            if self.open_check.get_active():
                try:
                    util.spawn([self.cmd.get_text(), file_path])
                except:
                    pass

            app.window.emit("artwork-changed", [self.song])

        self.main_win.destroy()

    def __save_config(self, widget):
        self.config_set('edit_cmd', self.cmd.get_text())
        self.config_set('fn', self.name_combo.get_active_text())

    def __update(self, loader, *data):
        """Update the picture while it's loading"""
        if self.stop_loading:
            return
        pixbuf = loader.get_pixbuf()
        GLib.idle_add(self.image.set_from_pixbuf, pixbuf)

    def __scale_pixbuf(self, *data):
        if not self.current_pixbuf:
            return
        pixbuf = self.current_pixbuf

        if self.window_fit.get_active():
            pb_width = pixbuf.get_width()
            pb_height = pixbuf.get_height()

            alloc = self.scrolled.get_allocation()
            width = alloc.width
            height = alloc.height

            if pb_width > width or pb_height > height:
                pb_ratio = float(pb_width) / pb_height
                win_ratio = float(width) / height

                if pb_ratio > win_ratio:
                    scale_w = width
                    scale_h = int(width / pb_ratio)
                else:
                    scale_w = int(height * pb_ratio)
                    scale_h = height

                # The size is wrong if the window is about to close
                if scale_w <= 0 or scale_h <= 0:
                    return

                thr = threading.Thread(
                    target=self.__scale_async,
                    args=(pixbuf, scale_w, scale_h))
                thr.setDaemon(True)
                thr.start()
            else:
                self.image.set_from_pixbuf(pixbuf)
        else:
            self.image.set_from_pixbuf(pixbuf)

    def __scale_async(self, pixbuf, w, h):
            pixbuf = pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
            GLib.idle_add(self.image.set_from_pixbuf, pixbuf)

    def __close(self, loader, *data):
        if self.stop_loading:
            return
        self.current_pixbuf = loader.get_pixbuf()
        GLib.idle_add(self.__scale_pixbuf)

    def set_cover(self, url):
        thr = threading.Thread(target=self.__set_async, args=(url,))
        thr.setDaemon(True)
        thr.start()

    def __set_async(self, url):
        """Manages various things:
        Fast switching of covers (aborting old HTTP requests),
        The image cache, etc."""

        self.current_job += 1
        job = self.current_job

        self.stop_loading = True
        while self.loading:
            time.sleep(0.05)
        self.stop_loading = False

        if job != self.current_job:
            return

        self.loading = True

        GLib.idle_add(self.button.set_sensitive, False)
        self.current_pixbuf = None

        pbloader = GdkPixbuf.PixbufLoader()
        pbloader.connect('closed', self.__close)

        # Look for cached images
        raw_data = None
        for entry in self.data_cache:
            if entry[0] == url:
                raw_data = entry[1]
                break

        if not raw_data:
            pbloader.connect('area-updated', self.__update)

            data_store = StringIO()

            try:
                request = urllib2.Request(url)
                request.add_header('User-Agent', USER_AGENT)
                url_sock = urllib2.urlopen(request)
            except urllib2.HTTPError:
                print_w(_("[albumart] HTTP Error: %s") % url)
            else:
                while not self.stop_loading:
                    tmp = url_sock.read(1024 * 10)
                    if not tmp:
                            break
                    pbloader.write(tmp)
                    data_store.write(tmp)

                url_sock.close()

                if not self.stop_loading:
                    raw_data = data_store.getvalue()

                    self.data_cache.insert(0, (url, raw_data))

                    while 1:
                        cache_sizes = [len(data[1]) for data in
                                       self.data_cache]
                        if sum(cache_sizes) > self.max_cache_size:
                            del self.data_cache[-1]
                        else:
                            break

            data_store.close()
        else:
            # Sleep for fast switching of cached images
            time.sleep(0.05)
            if not self.stop_loading:
                pbloader.write(raw_data)

        try:
            pbloader.close()
        except GLib.GError:
            pass

        self.current_data = raw_data

        if not self.stop_loading:
            GLib.idle_add(self.button.set_sensitive, True)

        self.loading = False


class AlbumArtWindow(qltk.Window, PluginConfigMixin):
    """The main window including the search list"""

    CONFIG_SECTION = PLUGIN_CONFIG_SECTION

    def __init__(self, songs):
        super(AlbumArtWindow, self).__init__()

        self.image_cache = []
        self.image_cache_size = 10
        self.search_lock = False

        self.set_title(_('Album Art Downloader'))
        self.set_icon_name(Gtk.STOCK_FIND)
        self.set_default_size(800, 550)

        image = CoverArea(self, songs[0])

        self.liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, object)
        self.treeview = treeview = AllTreeView(self.liststore)
        self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)

        targets = [("text/uri-list", 0, 0)]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        treeview.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK, targets, Gdk.DragAction.COPY)

        treeselection = self.treeview.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.SINGLE)
        treeselection.connect('changed', self.__select_callback, image)

        self.treeview.connect("drag-data-get",
            self.__drag_data_get, treeselection)

        rend_pix = Gtk.CellRendererPixbuf()
        img_col = Gtk.TreeViewColumn('Thumb')
        img_col.pack_start(rend_pix, False)
        img_col.add_attribute(rend_pix, 'pixbuf', 0)
        treeview.append_column(img_col)

        rend_pix.set_property('xpad', 2)
        rend_pix.set_property('ypad', 2)
        rend_pix.set_property('width', 56)
        rend_pix.set_property('height', 56)

        def escape_data(data):
            for rep in ('\n', '\t', '\r', '\v'):
                data = data.replace(rep, ' ')
            return util.escape(' '.join(data.split()))

        def cell_data(column, cell, model, iter, data):
            cover = model[iter][1]

            esc = escape_data

            txt = '<b><i>%s</i></b>' % esc(cover['name'])
            txt += _('\n<small>from <i>%s</i></small>') % esc(cover['source'])
            if 'resolution' in cover:
                txt += _('\nResolution: <i>%s</i>') % esc(cover['resolution'])
            if 'size' in cover:
                txt += _('\nSize: <i>%s</i>') % esc(cover['size'])

            cell.markup = txt
            cell.set_property('markup', cell.markup)

        rend = Gtk.CellRendererText()
        rend.set_property('ellipsize', Pango.EllipsizeMode.END)
        info_col = Gtk.TreeViewColumn('Info', rend)
        info_col.set_cell_data_func(rend, cell_data)

        treeview.append_column(info_col)

        sw_list = Gtk.ScrolledWindow()
        sw_list.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw_list.set_shadow_type(Gtk.ShadowType.IN)
        sw_list.add(treeview)

        self.search_field = Gtk.Entry()
        self.search_button = Gtk.Button(stock=Gtk.STOCK_FIND)
        self.search_button.connect('clicked', self.start_search)
        self.search_field.connect('activate', self.start_search)

        widget_space = 5

        search_hbox = Gtk.HBox(False, widget_space)
        search_hbox.pack_start(self.search_field, True, True, 0)
        search_hbox.pack_start(self.search_button, False, True, 0)

        self.progress = Gtk.ProgressBar()

        left_vbox = Gtk.VBox(False, widget_space)
        left_vbox.pack_start(search_hbox, False, True, 0)
        left_vbox.pack_start(sw_list, True, True, 0)

        hpaned = Gtk.HPaned()
        hpaned.set_border_width(widget_space)
        hpaned.pack1(left_vbox)
        hpaned.pack2(image)
        hpaned.set_position(275)

        self.add(hpaned)

        self.show_all()

        left_vbox.pack_start(self.progress, False, True, 0)

        if songs[0]('albumartist'):
            text = songs[0]('albumartist')
        else:
            text = songs[0]('artist')

        text += ' - ' + songs[0]('album')

        self.set_text(text)
        self.start_search()

    def __drag_data_get(self, view, ctx, sel, tid, etime, treeselection):
        model, iter = treeselection.get_selected()
        if not iter:
            return
        cover = model.get_value(iter, 1)
        sel.set_uris([cover['cover']])

    def start_search(self, *data):
        """Start the search using the text from the text entry"""

        text = self.search_field.get_text()
        if not text or self.search_lock:
            return

        self.search_lock = True
        self.search_button.set_sensitive(False)

        self.progress.set_fraction(0)
        self.progress.set_text(_('Searching...'))
        self.progress.show()

        self.liststore.clear()

        search = CoverSearch(self.__search_callback)

        for eng in engines:
            if self.config_get(CONFIG_ENG_PREFIX + eng['config_id'], True):
                search.add_engine(eng['class'], eng['replace'])

        search.start(text)

        # Focus the list
        self.treeview.grab_focus()

    def set_text(self, text):
        """set the text and move the cursor to the end"""

        self.search_field.set_text(text)
        self.search_field.emit('move-cursor', Gtk.MovementStep.BUFFER_ENDS,
            0, False)

    def __select_callback(self, selection, image):
        model, iter = selection.get_selected()
        if not iter:
            return
        cover = model.get_value(iter, 1)
        image.set_cover(cover['cover'])

    def __add_cover_to_list(self, cover):
        try:
            pbloader = GdkPixbuf.PixbufLoader()
            pbloader.write(get_url(cover['thumbnail'])[0])
            pbloader.close()

            size = 48

            pixbuf = pbloader.get_pixbuf().scale_simple(size, size,
                GdkPixbuf.InterpType.BILINEAR)

            thumb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8,
                                         size + 2, size + 2)
            thumb.fill(0x000000ff)
            pixbuf.copy_area(0, 0, size, size, thumb, 1, 1)
        except (GLib.GError, IOError):
            pass
        else:
            def append(data):
                self.liststore.append(data)
            GLib.idle_add(append, [thumb, cover])

    def __search_callback(self, covers, progress):
        for cover in covers:
            self.__add_cover_to_list(cover)

        if self.progress.get_fraction() < progress:
            self.progress.set_fraction(progress)

        if progress >= 1:
            self.progress.set_text(_('Done'))
            GLib.timeout_add(700, self.progress.hide)
            self.search_button.set_sensitive(True)
            self.search_lock = False


class CoverSearch(object):
    """Class for glueing the search engines together. No UI stuff."""

    def __init__(self, callback):
        self.engine_list = []
        self.callback = callback
        self.finished = 0
        self.overall_limit = 7

    def add_engine(self, engine, query_replace):
        """Adds a new search engine, query_replace is the string with which
        all special characters get replaced"""

        self.engine_list.append((engine, query_replace))

    def start(self, query):
        """Start search. The callback function will be called after each of
        the search engines has finished."""

        for engine, replace in self.engine_list:
            thr = threading.Thread(target=self.__search_thread,
                                   args=(engine, query, replace))
            thr.setDaemon(True)
            thr.start()

        #tell the other side that we are finished if there is nothing to do.
        if not len(self.engine_list):
            GLib.idle_add(self.callback, [], 1)

    def __search_thread(self, engine, query, replace):
        """Creates searching threads which call the callback function after
        they are finished"""

        clean_query = self.__cleanup_query(query, replace)
        result = []
        try:
            result = engine().start(clean_query, self.overall_limit)
        except Exception:
            print_w("[AlbumArt] %s: %r" % (engine.__name__, query))
            print_exc()

        self.finished += 1
        #progress is between 0..1
        progress = float(self.finished) / len(self.engine_list)
        GLib.idle_add(self.callback, result, progress)

    def __cleanup_query(self, query, replace):
        """split up at '-', remove some chars, only keep the longest words..
        more false positives but much better results"""

        query = query.lower()
        if query.startswith("the "):
            query = query[4:]

        split = query.split('-')
        replace_str = ('+', '&', ',', '.', '!', '´',
                       '\'', ':', ' and ', '(', ')')
        new_query = ''
        for part in split:
            for stri in replace_str:
                part = part.replace(stri, replace)

            p_split = part.split()
            p_split.sort(lambda x, y: len(y) - len(x))
            p_split = p_split[:max(len(p_split) / 4, max(4 - len(p_split), 2))]

            new_query += ' '.join(p_split) + ' '

        return new_query.rstrip()


#------------------------------------------------------------------------------
def get_size_of_url(url):
    request = urllib2.Request(url)
    request.add_header('Accept-Encoding', 'gzip')
    request.add_header('User-Agent', USER_AGENT)
    url_sock = urllib2.urlopen(request)
    size = url_sock.headers.get('content-length')
    url_sock.close()
    return format_size(int(size)) if size else ''

#------------------------------------------------------------------------------
engines = [
    {
        'class': CoverParadiseParser,
        'url': 'http://www.coverparadise.to/',
        'replace': '*',
        'config_id': 'coverparadise',
    },
    {
        'class': AmazonParser,
        'url': 'http://www.amazon.com/',
        'replace': ' ',
        'config_id': 'amazon',
    },
    # {
    #     'class': DiscogsParser,
    #     'url': 'http://www.discogs.com/',
    #     'replace': ' ',
    #     'config_id': 'discogs',
    # }
]
#------------------------------------------------------------------------------


class DownloadAlbumArt(SongsMenuPlugin, PluginConfigMixin):
    """Download and save album (cover) art from a variety of sources"""

    PLUGIN_ID = 'Download Album Art'
    PLUGIN_NAME = _('Download Album Art')
    PLUGIN_DESC = _('Download album covers from various websites')
    PLUGIN_ICON = Gtk.STOCK_FIND
    PLUGIN_VERSION = '0.5.2'
    CONFIG_SECTION = PLUGIN_CONFIG_SECTION

    @classmethod
    def PluginPreferences(cls, window):
        table = Gtk.Table(len(engines), 2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        frame = qltk.Frame(_("Sources"), child=table)

        for i, eng in enumerate(sorted(engines, key=lambda x: x["url"])):
            check = cls.ConfigCheckButton(
                eng['config_id'].title(),
                CONFIG_ENG_PREFIX + eng['config_id'],
                True)
            table.attach(check, 0, 1, i, i + 1)

            button = Gtk.Button(eng['url'])
            button.connect('clicked', lambda s: util.website(s.get_label()))
            table.attach(button, 1, 2, i, i + 1,
                         xoptions=Gtk.AttachOptions.FILL |
                         Gtk.AttachOptions.SHRINK)
        return frame

    def plugin_album(self, songs):
        return AlbumArtWindow(songs)
