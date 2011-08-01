# -*- coding: utf-8 -*-

# Copyright 2005-2010 By:
# Eduardo Gonzalez, Niklas Janlert, Christoph Reiter, Antonio Riva,
# Aymeric Mansoux
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

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
from HTMLParser import HTMLParser
from cStringIO import StringIO
from xml.dom import minidom

import gtk
import gobject
import pango

from quodlibet import util, qltk, config
from quodlibet.qltk.views import AllTreeView
from quodlibet.plugins.songsmenu import SongsMenuPlugin

#switch off, so that broken search engines wont crash the whole plugin
debug = False

USER_AGENT = "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) " \
    "Gecko/20101210 Iceweasel/3.6.13 (like Firefox/3.6.13)"

def get_encoding_from_socket(socket):
    content_type = socket.headers.get("Content-Type", "")
    p = map(str.strip, map(str.lower, content_type.split(";")))
    enc = [t.split("=")[-1].strip() for t in p if t.startswith("charset")]
    return (enc and enc[0]) or "utf-8"

def get_url(url, post={}, get={}):
    post_params = urllib.urlencode(post)
    get_params = urllib.urlencode(get)
    if get: get_params = '?' + get_params

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
        data = gzip.GzipFile(fileobj = StringIO(data)).read()
    url_sock.close()

    return data, enc

def get_encoding(url):
    request = urllib2.Request(url)
    request.add_header('Accept-Encoding', 'gzip')
    request.add_header('User-Agent', USER_AGENT)
    url_sock = urllib2.urlopen(request)
    return get_encoding_from_socket(url_sock)

class BasicHTMLParser(HTMLParser, object):
    """Basic Parser, stores all tags in a 3 tuple with tagname, attrs and data
    between the starttags. Ignores nesting but gives a consistent structure.
    All in all an ugly hack."""

    encoding = "utf-8"

    def __init__(self):
        super(BasicHTMLParser, self).__init__()

        self.data = []
        self.__buffer = []
        #to make the crappy HTMLParser ignore more stuff
        self.CDATA_CONTENT_ELEMENTS = ()

    def parse_url(self, url, post = {}, get = {}):
        """Will read the data and parse it into the data variable.
        A tag will be ['tagname', {all attributes}, 'data until the next tag']
        Only starttags are handled/used."""

        self.data = []

        text, self.encoding = get_url(url, post, get)
        text = text.decode(self.encoding, 'replace')

        #strip script tags/content. HTMLParser doesn't handle them well
        text = "".join([p.split("script>")[-1] for p in text.split("<script")])

        self.feed(text)
        self.close()

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

    def __init__(self):
        super(CoverParadiseParser, self).__init__()

        self.cover_count = 0
        self.page_step = 0
        self.query = ''
        self.root_url = 'http://coverparadise.to'

        self.covers = []

    def start(self, query, limit=10):
        """Start the search and return a list of covers"""

        self.cover_count = 0
        self.page_step = 0
        enc = get_encoding(self.root_url)
        self.query = query.decode("utf-8").encode(enc)
        self.covers = []

        #site only takes 3+ chars
        if len(query) < 3:
                return []

        #parse the first page
        self.__parse_search_list(0)

        #if there are pagenumbers: its a list
        if self.__parse_page_num():
            if limit > 0:
                self.limit = min(limit, self.cover_count)
            else:
                self.limit = self.cover_count

            self.__extract_from_list()

            #get the rest of the list
            for offset in xrange(self.page_step, self.limit, self.page_step):
                self.__parse_search_list(offset)
                self.__extract_from_list()
        #search went directly to the album page
        else:
            self.__extract_from_single()

        #delete the parsing data
        del self.data

        return self.covers

    def __extract_from_single(self):
        """The site will directly return the album page if there is only
        one search result"""

        cover = {}

        head_pos = 0
        for i, entry in enumerate(self.data):
            if entry[0] == 'div' and 'class' in entry[1] and \
                entry[1]['class'] == 'BoxHeadline':
                head_pos = i
                break

        cover['name'] = ''
        for i in xrange(head_pos + 1, len(self.data)):
            cover['name'] += self.data[i][2]
            if self.data[i + 1][0].strip():
                break

        cover['name'] = cover['name'].strip()

        if not cover['name']:
            return

        pic_pos = 0
        for i in xrange(head_pos, len(self.data)):
            if self.data[i][0] == 'img' and 'src' in self.data[i][1] and \
                self.data[i][1]['src'].find('/thumbs/') != -1:
                pic_pos = i
                break

        cover['thumbnail'] = self.data[pic_pos][1]['src']

        cover['cover'] = cover['thumbnail'].replace('/thumbs/', '/')

        sub_data = []
        for i in xrange(pic_pos + 1, len(self.data)):
            if self.data[i][0] == 'tr':
                break
            if not self.data[i][1] and self.data[i][2].strip():
                sub_data.append(self.data[i])

        cover['resolution'] = sub_data[-2][2].split(':')[1].strip()

        cover['size'] = sub_data[-3][2].split(':')[1].strip().replace(',', '.')

        cover['source'] = self.root_url

        self.covers.append(cover)

    def __parse_search_list(self, offset):
        """Will parse a specific page of a search"""

        search_url = self.root_url + '/?Module=SimpleSearch'
        #Sektion 2 is for audio, Page is a search result offset
        post_dic = {'SearchString' : self.query, 'Page': offset, 'Sektion' : 2}

        self.parse_url(search_url, post=post_dic)

    def __extract_from_list(self):
        """Extracts all the needed information from the already parsed
        search result page and adds the found cover to the list."""

        table_pos = []
        for i, entry in enumerate(self.data):
            if entry[0] == 'div' and 'class' in entry[1] and \
                entry[1]['class'] == 'ResultScroller':
                table_pos.append(i)

        table_pos = table_pos[-2:]

        if len(table_pos) != 2:
            return

        tr_pos = []
        for i in xrange(table_pos[0], table_pos[1]):
            if self.data[i][0] == 'tr' and not self.data[i][1]:
                tr_pos.append(i)

        for tr in xrange(0, len(tr_pos) - 1):
            cover = {}

            album = self.data[tr_pos[tr] : tr_pos[tr + 1]]

            name = []
            for i, entry in enumerate(album):
                if entry[0] == 'b':
                    for a in xrange(i, len(album)):
                        name.append(album[a][2])
                        if album[a + 1][0] == 'b':
                            break
                    break

            cover['name'] = ''.join(name).strip()

            sub_data = [i[2] for i in album if i[0] == '' and i[2].strip()]

            cover['size'] = sub_data[-1].strip().replace(',', '.')

            cover['resolution'] = sub_data[-2].strip()

            thumb_tag = [i[1] for i in album if i[0] == 'img'][0]
            cover['thumbnail'] = thumb_tag['src']

            id = cover['thumbnail'].split("/")[-1].split(".")[0]
            cover['cover'] = self.root_url + "/res/exe/GetElement.php?ID=" + id

            cover['source'] = self.root_url

            self.covers.append(cover)

            if(len(self.covers) >= self.limit):
                break

    def __parse_page_num(self):
        """Tries to find the number of found covers on an already parsed
        search result page and how many results are on one page
        (needed for result/page offset)"""

        pos = 0

        for i, entry in enumerate(self.data):
            if entry[0] == 'div' and 'class' in entry[1] and \
                entry[1]['class'] == 'BoxHeadline':
                pos = i
                break

        text = self.data[pos][2]
        nums = [int(i) for i in text.split() if i.isdigit()][-2:]

        if len(nums) == 2:
            self.page_step, self.cover_count = nums
            return True
        else:
            return False

class DiscogsParser(object):
    """A class for searching covers from discogs.com"""

    def __init__(self):
        self.api_key = 'e404383a2a'
        self.url = 'http://www.discogs.com'
        self.cover_list = []
        self.limit = 0
        self.limit_count = 0

    def __get_search_page(self, page, query):
        """Returns the XML dom of a search result page. Starts with 1."""

        search_url = self.url + '/search'
        search_paras = {}
        search_paras['type'] = 'releases'
        search_paras['q'] = query
        search_paras['f'] = 'xml'
        search_paras['api_key'] = self.api_key
        search_paras['page'] = page

        data, enc = get_url(search_url, get=search_paras)
        dom = minidom.parseString(data)

        return dom

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

        rel_paras = {}
        rel_paras['api_key'] = self.api_key
        rel_paras['f'] = 'xml'

        data, enc = get_url(url, get=rel_paras)

        dom = minidom.parseString(data)

        imgs = dom.getElementsByTagName('image')

        cover = {}

        for img in imgs:
            if img.getAttribute('type') == 'primary':
                cover['cover'] = img.getAttribute('uri')

                width = img.getAttribute('width')
                height = img.getAttribute('height')
                cover['resolution'] = '%s x %s px' % (width, height)

                cover['thumbnail'] = img.getAttribute('uri150')

                cover['name'] = name

                cover['size'] = get_size_of_url(cover['cover'])

                cover['source'] = self.url

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

            #all = number of all results, end = last result number on the page
            all = int(result[0].getAttribute('numResults'))
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

                #Don't search forever if there are many entries with no image
                #In the default case of limit=10 this will prevent searching
                #the second result page...
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
    """A class for searching covers from amazon"""

    def __init__(self):
        self.page_count = 0
        self.covers = []
        self.limit = 0

    def __parse_page(self, page, query):
        """Gets all item tags and calls the item parsing function for each"""

        #Amazon now requires that all requests be signed.
        #I have built a webapp on AppEngine for this purpose. -- wm_eddie
        #url = 'http://webservices.amazon.com/onca/xml'
        url = 'http://qlwebservices.appspot.com/onca/xml'

        parameters = {}
        parameters['Service'] = 'AWSECommerceService'
        parameters['AWSAccessKeyId'] = '0RKH4ZH1JCFZHMND91G2' # Now Ignored.
        parameters['Operation'] = 'ItemSearch'
        parameters['ResponseGroup'] = 'Images,Small'
        parameters['SearchIndex'] = 'Music'
        parameters['Keywords'] = query
        parameters['ItemPage'] = page

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
            for page in xrange(2 ,self.page_count + 1):
                self.__parse_page(page, query)
                if len(self.covers) >= limit:
                    break

        return self.covers

class DarktownParser(BasicHTMLParser):
    """A class for searching covers from darktown.to"""

    def __init__(self):
        super(DarktownParser, self).__init__()

        self.root_url = 'http://www.darktown.ws'
        self.page_count = 0
        self.limit = 0
        self.covers = []

        self.main_links = []

    def start(self, query, limit=10):
        """Start the search and returns the covers"""

        self.page_count = 0
        self.limit = limit
        #site only takes and returns latin-1

        enc = get_encoding(self.root_url)
        query = query.decode('utf-8').encode(enc)
        self.covers = []
        self.main_links = []

        #get first page
        self.__parse_page(1, query)

        #look if there are more
        self.__parse_page_count()

        #parse all the cover urls from page 1
        self.__parse_search_list()

        #do the same for the rest until the limit is reached
        for i in xrange(2, min(limit / 100, self.page_count) + 1):
            self.__parse_page(i, query)
            self.__parse_search_list()

        #go to each url and get all the infos
        self.__parse_all_covers()

        #delete all the parsed data
        del self.data

        return self.covers

    def __parse_all_covers(self):
        """Reads all URLs and adds the covers to the list"""

        for link in self.main_links:
            self.parse_url(self.root_url + link)

            cover = {}
            cover['source'] = self.root_url

            for tag in xrange(len(self.data)):
                if self.data[tag][0] == 'img' and 'thumbnail' not in cover:
                    cover['thumbnail'] = self.data[tag][1]['src']
                elif self.data[tag][0] == 'a' and 'cover' not in cover:
                    cover['cover'] = self.data[tag][1]['href']
                elif self.data[tag][0] == 'font' and 'size' in \
                    self.data[tag][1] and self.data[tag][1]['size'] == '4':
                    cover['name'] = (self.data[tag][2] + ' - ' + \
                        self.data[tag + 2][2]).strip()
                    cover['size'] = self.data[tag + 13][2].strip()

            self.covers.append(cover)

    def __parse_page(self, page, query):
        """Parses the search result page and saves the data to self.data"""

        params = {'action': 'search', 'what': query, \
            'category': 'audio', 'page': page}
        self.parse_url(self.root_url + '/search.php', get=params)

    def __parse_page_count(self):
        """Tries to figure out how many result pages we got."""

        for i in self.data:
            if 'href' in i[1]:
                if i[1]['href'].startswith('/search.php') \
                    and not i[2].isdigit():
                    start = i[1]['href'].rfind('=') + 1
                    self.page_count = int(i[1]['href'][start:])
                    break
                elif i[1]['href'].startswith('javascript:'):
                    break

    def __parse_search_list(self):
        """Extracts all album urls from the result page"""

        for tag in self.data:
            if tag[0] == 'a':
                split = tag[1]['href'].split('\'')
                if len(split) > 1 and split[1].endswith('&type=Front'):
                    self.main_links.append(split[1])

            if len(self.main_links) >= self.limit:
                break

class CoverArea(gtk.VBox):
    """The image display and saving part."""

    def __init__(self, parent, dirname):
        super(CoverArea, self).__init__()

        self.connect('destroy', self.__save_config)

        self.dirname = dirname
        self.main_win = parent

        self.data_cache = []
        self.current_data = None
        self.current_pixbuf = None

        self.image = gtk.Image()
        self.button = gtk.Button(stock=gtk.STOCK_SAVE)
        self.button.set_sensitive(False)
        self.button.connect('clicked', self.__save)

        self.window_fit = gtk.CheckButton(_('Fit image to _window'))
        self.window_fit.connect('toggled', self.__scale_pixbuf)

        self.name_combo = gtk.combo_box_new_text()

        self.cmd = qltk.entry.ValidatingEntry(util.iscommand)

        #both labels
        label_open = gtk.Label(_('_Program:'))
        label_open.set_use_underline(True)
        label_open.set_mnemonic_widget(self.cmd)
        label_open.set_justify(gtk.JUSTIFY_LEFT)

        self.open_check = gtk.CheckButton(_('_Edit image after saving'))
        label_name = gtk.Label(_('File_name:'))
        label_name.set_use_underline(True)
        label_name.set_mnemonic_widget(self.name_combo)
        label_name.set_justify(gtk.JUSTIFY_LEFT)

        # set all stuff from the config
        self.window_fit.set_active(cfg_get('fit', True))
        self.open_check.set_active(cfg_get('edit', False))
        self.cmd.set_text(cfg_get('edit_cmd', 'gimp'))

        #create the filename combo box
        fn_list = ['cover.jpg', 'folder.jpg', '.folder.jpg']

        set_fn = cfg_get('fn', fn_list[0])

        for i, fn in enumerate(fn_list):
                self.name_combo.append_text(fn)
                if fn == set_fn:
                    self.name_combo.set_active(i)

        if self.name_combo.get_active() < 0:
            self.name_combo.set_active(0)

        table = gtk.Table(rows=2, columns=2, homogeneous=False)
        table.set_row_spacing(0, 5)
        table.set_row_spacing(1, 5)
        table.set_col_spacing(0, 5)
        table.set_col_spacing(1, 5)

        table.attach(label_open, 0, 1, 0, 1)
        table.attach(label_name, 0, 1, 1, 2)

        table.attach(self.cmd, 1, 2, 0, 1)
        table.attach(self.name_combo, 1, 2, 1, 2)

        self.scrolled = gtk.ScrolledWindow()
        self.scrolled.add_with_viewport(self.image)
        self.scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        bbox = gtk.HButtonBox()
        bbox.pack_start(self.button)

        main_hbox = gtk.HBox()
        main_hbox.pack_start(table, False, padding=5)
        main_hbox.pack_start(bbox)

        top_hbox = gtk.HBox()
        top_hbox.pack_start(self.open_check)
        top_hbox.pack_start(self.window_fit, False)

        main_vbox = gtk.VBox()
        main_vbox.pack_start(top_hbox, padding=2)
        main_vbox.pack_start(main_hbox)

        self.pack_start(self.scrolled)
        self.pack_start(main_vbox, False, padding=5)

        # 5 MB image cache size
        self.max_cache_size = 1024 * 1024 * 5

        #for managing fast selection switches of covers..
        self.stop_loading = False
        self.loading = False
        self.current_job = 0

    def __save(self, *data):
        """save the cover, spawn the program to edit it if selected"""

        filename = self.name_combo.get_active_text()
        file_path = os.path.join(self.dirname, filename)

        if os.path.exists(file_path) and not qltk.ConfirmAction(None,
            _('File exists'), _('The file <b>%s</b> already exists.'
            '\n\nOverwrite?') % util.escape(filename)).run():
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

        self.main_win.destroy()

    def __save_config(self, widget):
        cfg_set('fit', self.window_fit.get_active())
        cfg_set('edit', self.open_check.get_active())
        cfg_set('edit_cmd', self.cmd.get_text())
        cfg_set('fn', self.name_combo.get_active_text())

    def __update(self, loader, *data):
        """update the picture while it is loading"""
        if self.stop_loading:
            return

        pixbuf = loader.get_pixbuf()
        gobject.idle_add(self.image.set_from_pixbuf, pixbuf)

    def __scale_pixbuf(self, *data):
        if not self.current_pixbuf:
            return

        pixbuf = self.current_pixbuf

        if self.window_fit.get_active():
            pb_width = pixbuf.get_width()
            pb_height = pixbuf.get_height()

            #substract 20 px because of the scrollbars
            width = self.scrolled.allocation.width - 20
            height = self.scrolled.allocation.height - 20

            if pb_width > width or pb_height > height:
                pb_ratio = float(pb_width) / pb_height
                win_ratio = float(width) / height

                if pb_ratio > win_ratio:
                    scale_w = width
                    scale_h = int(width / pb_ratio)
                else:
                    scale_w = int(height * pb_ratio)
                    scale_h = height

                #the size is wrong if the window is about to close
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
            pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_BILINEAR)
            gobject.idle_add(self.image.set_from_pixbuf, pixbuf)

    def __close(self, loader, *data):
        if self.stop_loading:
            return

        self.current_pixbuf = loader.get_pixbuf()
        gobject.idle_add(self.__scale_pixbuf)

    def set_cover(self, url):
        thr = threading.Thread(target=self.__set_async, args=(url,))
        thr.setDaemon(True)
        thr.start()

    def __set_async(self, url):
        """manages various stuff like fast switching of covers (aborting
        old HTTP requests), managing the image cache etc."""

        self.current_job += 1
        job = self.current_job

        self.stop_loading = True
        while self.loading:
            time.sleep(0.05)
        self.stop_loading = False

        if job != self.current_job:
            return

        self.loading = True

        gobject.idle_add(self.button.set_sensitive, False)
        self.current_pixbuf = None

        pbloader = gtk.gdk.PixbufLoader()
        pbloader.connect('closed', self.__close)

        #look for cached images
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
                        cache_sizes = [len(data[1]) for data in self.data_cache]
                        if sum(cache_sizes) > self.max_cache_size:
                            del self.data_cache[-1]
                        else:
                            break

            data_store.close()
        else:
            #sleep for fast switching of cached images
            time.sleep(0.05)
            if not self.stop_loading:
                pbloader.write(raw_data)

        try:
            pbloader.close()
        except gobject.GError:
            pass

        self.current_data = raw_data

        if not self.stop_loading:
            gobject.idle_add(self.button.set_sensitive, True)

        self.loading = False

class AlbumArtWindow(qltk.Window):
    """The main window including the search list"""

    def __init__(self, songs):
        super(AlbumArtWindow, self).__init__()

        self.image_cache = []
        self.image_cache_size = 10
        self.search_lock = False

        self.set_title(_('Album Art Downloader'))
        self.set_icon_name(gtk.STOCK_FIND)
        self.set_default_size(800, 550)

        image = CoverArea(self, songs[0]('~dirname'))

        self.liststore = gtk.ListStore(gtk.gdk.Pixbuf, object)
        self.treeview = treeview = AllTreeView(self.liststore)
        self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)

        targets = [("text/uri-list", 0, 0)]
        treeview.drag_source_set(
            gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)

        treeselection = self.treeview.get_selection()
        treeselection.set_mode(gtk.SELECTION_SINGLE)
        treeselection.connect('changed', self.__select_callback, image)

        self.treeview.connect("drag-data-get",
            self.__drag_data_get, treeselection)

        rend_pix = gtk.CellRendererPixbuf()
        img_col = gtk.TreeViewColumn('Thumb')
        img_col.pack_start(rend_pix, False)
        img_col.add_attribute(rend_pix, 'pixbuf', 0)
        treeview.append_column(img_col)

        rend_pix.set_property('xpad', 2)
        rend_pix.set_property('ypad', 2)
        rend_pix.set_property('width', 56)
        rend_pix.set_property('height', 56)

        def escape_data(data):
            for rep in ('\n','\t','\r', '\v'):
                data = data.replace(rep, ' ')

            return util.escape(' '.join(data.split()))

        def cell_data(column, cell, model, iter):
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

        rend = gtk.CellRendererText()
        rend.set_property('ellipsize', pango.ELLIPSIZE_END)
        info_col = gtk.TreeViewColumn('Info', rend)
        info_col.set_cell_data_func(rend, cell_data)

        treeview.append_column(info_col)

        sw_list = gtk.ScrolledWindow()
        sw_list.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw_list.set_shadow_type(gtk.SHADOW_IN)
        sw_list.add(treeview)

        self.search_field = gtk.Entry()
        self.search_button = gtk.Button(stock=gtk.STOCK_FIND)
        self.search_button.connect('clicked', self.start_search)
        self.search_field.connect('activate', self.start_search)

        widget_space = 5

        search_hbox = gtk.HBox(False, widget_space)
        search_hbox.pack_start(self.search_field)
        search_hbox.pack_start(self.search_button, False)

        self.progress = gtk.ProgressBar()

        left_vbox = gtk.VBox(False, widget_space)
        left_vbox.pack_start(search_hbox, False)
        left_vbox.pack_start(sw_list)

        hpaned = gtk.HPaned()
        hpaned.set_border_width(widget_space)
        hpaned.pack1(left_vbox)
        hpaned.pack2(image)
        hpaned.set_position(275)

        self.add(hpaned)

        self.show_all()

        left_vbox.pack_start(self.progress, False)

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

        global engines, config_eng_prefix

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
            if cfg_get(config_eng_prefix + eng['config_id'], True):
                search.add_engine(eng['class'], eng['replace'])

        search.start(text)

        #focus the list
        self.treeview.grab_focus()

    def set_text(self, text):
        """set the text and move the cursor to the end"""

        self.search_field.set_text(text)
        self.search_field.emit('move-cursor', gtk.MOVEMENT_BUFFER_ENDS,
            0, False)

    def __select_callback(self, selection, image):
        model, iter = selection.get_selected()
        if not iter:
            return
        cover = model.get_value(iter, 1)
        image.set_cover(cover['cover'])

    def __add_cover_to_list(self, cover):
        try:
            pbloader = gtk.gdk.PixbufLoader()
            pbloader.write(get_url(cover['thumbnail'])[0])
            pbloader.close()

            size = 48

            pixbuf = pbloader.get_pixbuf().scale_simple(size, size,
                gtk.gdk.INTERP_BILINEAR)

            thumb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
                size + 2, size + 2)
            thumb.fill(0x000000ff)
            pixbuf.copy_area(0, 0, size, size, thumb, 1, 1)
        except gobject.GError, IOError:
            pass
        else:
            def append(data):
                self.liststore.append(data)
            gobject.idle_add(append, [thumb, cover])

    def __search_callback(self, covers, progress):
        for cover in covers:
            self.__add_cover_to_list(cover)

        if self.progress.get_fraction() < progress:
            gobject.idle_add(self.progress.set_fraction, progress)

        if progress >= 1:
            gobject.idle_add(self.progress.set_text, _('Done'))

            time.sleep(0.7)

            gobject.idle_add(self.progress.hide)

            self.search_button.set_sensitive(True)
            self.search_lock = False

class CoverSearch(object):
    """Class for glueing the search eninges together. No UI stuff."""

    def __init__(self, callback):
        self.engine_list = []
        self.callback = callback
        self.finished = 0
        self.overall_limit = 7

    def add_engine(self, engine, query_replace):
        """Adds a new search engine, query_replace is the string with witch
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
            self.callback([], 1)

    def __search_thread(self, engine, query, replace):
        """Creates searching threads which call the callback function after
        they are finished"""

        global debug

        clean_query = self.__cleanup_query(query, replace)

        #Catch exceptions and print them in the warning console.
        #Some engines might break over time since the web interfaces
        #could change.

        if debug:
            eng_instance = engine()
            result = eng_instance.start(clean_query, self.overall_limit)
        else:
            try:
                eng_instance = engine()
                result = eng_instance.start(clean_query, self.overall_limit)
            except Exception, msg:
                text = _('[AlbumArt] %s failed: "%s", "%s"') \
                    % (engine.__name__, query, msg)
                print_w(text)
                result = []

        self.finished += 1
        #progress is between 0..1
        progress = float(self.finished) / len(self.engine_list)
        self.callback(result, progress)

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
def cfg_get(key, default):
    try:
        if type(default) == bool:
            value = config.getboolean('plugins', "cover_" + key)
        else:
            value = config.get('plugins', "cover_" + key)
        try:
            return type(default)(value)
        except ValueError:
            return default
    except (config.error, AttributeError):
        return default

config_eng_prefix = 'engine_'

#------------------------------------------------------------------------------
def cfg_set(key, value):
    if type(value) == bool:
        value = str(bool(value)).lower()
    config.set('plugins', "cover_" + key, value)

#------------------------------------------------------------------------------
def get_size_of_url(url):
    request = urllib2.Request(url)
    request.add_header('Accept-Encoding', 'gzip')
    request.add_header('User-Agent', USER_AGENT)
    url_sock = urllib2.urlopen(request)
    size =  url_sock.headers.get('content-length')
    url_sock.close()

    if size:
        size = int(size) / 1024.0
        if size < 1024:
            return '%.2f KB' % size
        else:
            return '%.2f MB' % size / 1024
    else:
        return ''

#------------------------------------------------------------------------------
engines = []

#-------
eng = {}
eng['class'] = DarktownParser
eng['url'] = 'http://www.darktown.ws/'
eng['replace'] = ' '
eng['config_id'] = 'darktown'

engines.append(eng)

#-------
eng = {}
eng['class'] = CoverParadiseParser
eng['url'] = 'http://www.coverparadise.to/'
eng['replace'] = '*'
eng['config_id'] = 'coverparadise'

engines.append(eng)

#-------
eng = {}
eng['class'] = AmazonParser
eng['url'] = 'http://www.amazon.com/'
eng['replace'] = ' '
eng['config_id'] = 'amazon'

engines.append(eng)

#-------
eng = {}
eng['class'] = DiscogsParser
eng['url'] = 'http://www.discogs.com/'
eng['replace'] = ' '
eng['config_id'] = 'discogs'

engines.append(eng)
#------------------------------------------------------------------------------

def change_config(checkb, id):
    global config_eng_prefix

    cfg_set(config_eng_prefix + id, checkb.get_active())

class DownloadAlbumArt(SongsMenuPlugin):
    PLUGIN_ID = 'Download Album art'
    PLUGIN_NAME = _('Download Album Art')
    PLUGIN_DESC = _('Download album covers from various websites')
    PLUGIN_ICON = gtk.STOCK_FIND
    PLUGIN_VERSION = '0.5.1'

    def PluginPreferences(klass, window):
        global engines, change_config, config_eng_prefix

        vbox = gtk.VBox(spacing=5)
        vbox.set_border_width(5)

        for eng in engines:
            check = gtk.CheckButton(eng['config_id'].title())
            vbox.pack_start(check)
            check.connect('toggled', change_config, eng['config_id'])

            checked = cfg_get(config_eng_prefix + eng['config_id'], True)

            check.set_active(checked)

            button = gtk.Button(eng['url'])
            button.connect('clicked', lambda s:util.website(s.get_label()))
            vbox.pack_start(button)

        return vbox

    PluginPreferences = classmethod(PluginPreferences)

    plugin_album = AlbumArtWindow
