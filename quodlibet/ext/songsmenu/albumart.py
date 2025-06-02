# Copyright 2005 Eduardo Gonzalez <wm.eddie@gmail.com>, Niklas Janlert
#           2006 Joe Wreschnig
#           2008 Antonio Riva, Eduardo Gonzalez <wm.eddie@gmail.com>,
#                Anthony Bretaudeau <wxcover@users.sourceforge.net>,
#           2010 Aymeric Mansoux <aymeric@goto10.org>
#           2008-2013 Christoph Reiter
#           2011-2022 Nick Boultbee
#                2016 Mice Pápai
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import gzip
import json
import os
import re
import threading
import time
from io import BytesIO
from typing import Any
from urllib.parse import urlencode

from gi.repository import Gtk, Pango, GLib, Gdk, GdkPixbuf

from quodlibet import _
from quodlibet import util, qltk, app
from quodlibet.pattern import ArbitraryExtensionFileFromPattern
from quodlibet.pattern import Pattern
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.songshelpers import any_song, is_a_file
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons, ConfigRHPaned
from quodlibet.qltk.entry import ValidatingEntry
from quodlibet.qltk.image import scale, add_border_widget, get_surface_for_pixbuf
from quodlibet.qltk.msg import ConfirmFileReplace
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.window import PersistentWindowMixin
from quodlibet.qltk.x import Align, Button
from quodlibet.util import format_size, print_exc
from quodlibet.util.dprint import print_d, print_w
from quodlibet.util.path import iscommand
from quodlibet.util.urllib import urlopen, Request

USER_AGENT = (
    "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) "
    "Gecko/20101210 Iceweasel/3.6.13 (like Firefox/3.6.13)"
)

PLUGIN_CONFIG_SECTION = "cover"
CONFIG_ENG_PREFIX = "engine_"

SEARCH_PATTERN = Pattern(
    "<albumartist|<albumartist>|<artist>> - <album|<album>|<title>>"
)

REQUEST_LIMIT_MAX = 15


def get_encoding_from_socket(socket):
    content_type = socket.headers.get("Content-Type", "")
    p = [s.lower().strip() for s in content_type.split(";")]
    enc = [t.split("=")[-1].strip() for t in p if t.startswith("charset")]
    return (enc and enc[0]) or "utf-8"


def get_url(url, post=None, get=None):
    post_params = urlencode(post or {})
    get_params = urlencode(get or {})
    if get:
        get_params = "?" + get_params

    # add post, get data and headers
    url = f"{url}{get_params}"
    if post_params:
        request = Request(url, post_params)
    else:
        request = Request(url)

    # for discogs
    request.add_header("Accept-Encoding", "gzip")
    request.add_header("User-Agent", USER_AGENT)

    url_sock = urlopen(request)
    enc = get_encoding_from_socket(url_sock)

    # unzip the response if needed
    data = url_sock.read()
    if url_sock.headers.get("content-encoding", "") == "gzip":
        data = gzip.GzipFile(fileobj=BytesIO(data)).read()
    url_sock.close()
    content_type = url_sock.headers.get("Content-Type", "").split(";", 1)[0]
    domain = re.compile(r"\w+://([^/]+)/").search(url).groups(0)[0]
    print_d(f"Got {content_type} data from {domain}")
    return data if content_type.startswith("image") else data.decode(enc)


def get_encoding(url):
    request = Request(url)
    request.add_header("Accept-Encoding", "gzip")
    request.add_header("User-Agent", USER_AGENT)
    url_sock = urlopen(request)
    return get_encoding_from_socket(url_sock)


class CoverSearcher:
    def start(self, query, limit=5) -> list[dict[str, Any]]:
        """Start the search and return the covers"""
        raise NotImplementedError()


class DiscogsSearcher(CoverSearcher):
    """A class for searching covers from Amazon"""

    def __init__(self):
        self.page_count = 0
        self.covers = []
        self.limit = 0
        self.creds = {
            "key": "aWfZGjHQvkMcreUECGAp",
            "secret": "VlORkklpdvAwJMwxUjNNSgqicjuizJAl",
        }

    def __parse_page(self, page, query):
        """Gets all item tags and calls the item parsing function for each"""

        url = "https://api.discogs.com/database/search"

        parameters = {
            "type": "release",
            "q": query,
            "page": page,
            # Assume that not all results are useful
            "per_page": self.limit * 2,
        }

        parameters.update(self.creds)
        data = get_url(url, get=parameters)
        json_dict = json.loads(data)

        # TODO: rate limiting

        pages = json_dict.get("pagination", {}).get("pages", 0)
        if not pages:
            return
        self.page_count = int(pages)

        items = json_dict.get("results", {})
        print_d("Discogs: got %d search result(s)" % len(items))
        for item in items:
            self.__parse_item(item)
            if len(self.covers) >= self.limit:
                break

    def __parse_item(self, item):
        """Extract all information and add the covers to the list."""

        thumbnail = item.get("thumb", "")
        if thumbnail is None:
            print_d("Release doesn't have a cover")
            return

        res_url = item.get("resource_url", "")
        data = get_url(res_url, get=self.creds)
        json_dict = json.loads(data)

        images = json_dict.get("images", [])

        for _i, image in enumerate(images):
            type = image.get("type", "")
            if type != "primary":
                continue

            uri = image.get("uri", "")
            cover = {
                "source": "https://www.discogs.com",
                "name": item.get("title", ""),
                "thumbnail": image.get("uri150", thumbnail),
                "cover": uri,
                "size": get_size_of_url(uri),
            }

            width = image.get("width", 0)
            height = image.get("height", 0)
            cover["resolution"] = f"{width} x {height} px"

            self.covers.append(cover)
            if len(self.covers) >= self.limit:
                break

    def start(self, query, limit=3):
        self.page_count = 0
        self.covers = []
        self.limit = limit
        page = 1
        while len(self.covers) < limit:
            self.__parse_page(page, query)
            if page >= self.page_count:
                break
            page += 1

        return self.covers


class CoverArea(Gtk.Box, PluginConfigMixin):
    """The image display and saving part."""

    CONFIG_SECTION = PLUGIN_CONFIG_SECTION

    def __init__(self, parent, song):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.song = song

        self.dirname = song("~dirname")
        self.main_win = parent

        self.data_cache = []
        self.current_data = None
        self.current_pixbuf = None

        self.image = Gtk.Image()
        self.button = Button(_("_Save"), Icons.DOCUMENT_SAVE_AS)
        self.button.set_sensitive(False)
        self.button.connect("clicked", self.__save)

        close_button = Button(_("_Close"), Icons.WINDOW_CLOSE)
        close_button.connect("clicked", lambda x: self.main_win.destroy())

        self.window_fit = self.ConfigCheckButton(_("Fit image to _window"), "fit", True)
        self.window_fit.connect("toggled", self.__scale_pixbuf)

        self.name_combo = Gtk.ComboBoxText()
        self.name_combo.set_tooltip_text(
            _(
                "See '[plugins] cover_filenames' config entry "
                "for image filename strings"
            )
        )

        self.cmd = ValidatingEntry(iscommand)

        # Both labels
        label_open = Gtk.Label(label=_("_Program:"))
        label_open.set_use_underline(True)
        label_open.set_mnemonic_widget(self.cmd)
        label_open.set_justify(Gtk.Justification.LEFT)

        self.open_check = self.ConfigCheckButton(
            _("_Edit image after saving"), "edit", False
        )
        label_name = Gtk.Label(label=_("File_name:"), use_underline=True)
        label_name.set_use_underline(True)
        label_name.set_mnemonic_widget(self.name_combo)
        label_name.set_justify(Gtk.Justification.LEFT)

        self.cmd.set_text(self.config_get("edit_cmd", "gimp"))

        # populate the filename combo box
        fn_list = self.config_get_stringlist(
            "filenames", ["cover.jpg", "folder.jpg", ".folder.jpg"]
        )
        # Issue 374 - add dynamic file names
        fn_dynlist = []
        artist = song("artist")
        alartist = song("albumartist")
        album = song("album")
        labelid = song("labelid")
        if album:
            fn_dynlist.append("<album>.jpg")
            if alartist:
                fn_dynlist.append("<albumartist> - <album>.jpg")
            else:
                fn_dynlist.append("<artist> - <album>.jpg")
        else:
            print_w(
                f"No album for {song('~filename')}. Could be difficult finding art…"
            )
            title = song("title")
            if title and artist:
                fn_dynlist.append("<artist> - <title>.jpg")
        if labelid:
            fn_dynlist.append("<labelid>.jpg")
        # merge unique
        fn_list.extend(s for s in fn_dynlist if s not in fn_list)

        set_fn = self.config_get("filename", fn_list[0])

        for i, fn in enumerate(fn_list):
            self.name_combo.append_text(fn)
            if fn == set_fn:
                self.name_combo.set_active(i)

        if self.name_combo.get_active() < 0:
            self.name_combo.set_active(0)
        self.config_set("filename", self.name_combo.get_active_text())

        table = Gtk.Table(n_rows=2, n_columns=2, homogeneous=False)
        table.props.expand = False
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
        self.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        bbox = Gtk.HButtonBox()
        bbox.set_spacing(6)
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        bbox.prepend(self.button, True, True, 0)
        bbox.prepend(close_button, True, True, 0)

        bb_align = Align(valign=Gtk.Align.END, right=6)
        bb_align.add(bbox)

        main_hbox = Gtk.Box()
        main_hbox.prepend(table, False, True, 6)
        main_hbox.prepend(bb_align, True, True, 0)

        top_hbox = Gtk.Box()
        top_hbox.prepend(self.open_check, True, True, 0)
        top_hbox.prepend(self.window_fit, False, True, 0)

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, )
        main_vbox.prepend(top_hbox, True, True, 2)
        main_vbox.prepend(main_hbox, True, True, 0)

        self.prepend(self.scrolled, True, True, 0)
        self.prepend(main_vbox, False, True, 5)

        # 5 MB image cache size
        self.max_cache_size = 1024 * 1024 * 5

        # For managing fast selection switches of covers...
        self.stop_loading = False
        self.loading = False
        self.current_job = 0

        self.connect("destroy", self.__save_config)

    def __save(self, *data):
        """Save the cover and spawn the program to edit it if selected"""

        save_format = self.name_combo.get_active_text()
        # Allow use of patterns in creating cover filenames
        pattern = ArbitraryExtensionFileFromPattern(save_format)
        filename = pattern.format(self.song)
        print_d(f"Using {filename!r} as filename based on {save_format}")
        file_path = os.path.join(self.dirname, filename)

        if os.path.exists(file_path):
            resp = ConfirmFileReplace(self, file_path).run()
            if resp != ConfirmFileReplace.RESPONSE_REPLACE:
                return

        try:
            f = open(file_path, "wb")
            f.write(self.current_data)
            f.close()
        except OSError:
            qltk.ErrorMessage(
                None, _("Saving failed"), _('Unable to save "%s".') % file_path
            ).run()
        else:
            if self.open_check.get_active():
                try:
                    util.spawn([self.cmd.get_text(), file_path])
                except Exception:
                    pass

            app.cover_manager.cover_changed([self.song._song])

        self.main_win.destroy()

    def __save_config(self, widget):
        self.config_set("edit_cmd", self.cmd.get_text())
        self.config_set("filename", self.name_combo.get_active_text())

    def __update(self, loader, *data):
        """Update the picture while it's loading"""

        if self.stop_loading:
            return
        pixbuf = loader.get_pixbuf()

        def idle_set():
            if pixbuf is not None:
                surface = get_surface_for_pixbuf(self, pixbuf)
                self.image.set_from_surface(surface)

        GLib.idle_add(idle_set)

    def __scale_pixbuf(self, *data):
        if not self.current_pixbuf:
            return
        pixbuf = self.current_pixbuf

        if self.window_fit.get_active():
            alloc = self.scrolled.get_allocation()
            width = alloc.width
            height = alloc.height
            scale_factor = self.get_scale_factor()
            boundary = (width * scale_factor, height * scale_factor)
            pixbuf = scale(pixbuf, boundary, scale_up=False)

        if not pixbuf:
            return
        surface = get_surface_for_pixbuf(self, pixbuf)
        self.image.set_from_surface(surface)

    def __close(self, loader, *data):
        if self.stop_loading:
            return
        self.current_pixbuf = loader.get_pixbuf()
        GLib.idle_add(self.__scale_pixbuf)

    def set_cover(self, url):
        thr = threading.Thread(target=self.__set_async, args=(url,))
        thr.daemon = True
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
        pbloader.connect("closed", self.__close)

        # Look for cached images
        raw_data = None
        for entry in self.data_cache:
            if entry[0] == url:
                raw_data = entry[1]
                break

        if not raw_data:
            pbloader.connect("area-updated", self.__update)

            data_store = BytesIO()

            try:
                request = Request(url)
                request.add_header("User-Agent", USER_AGENT)
                url_sock = urlopen(request)
            except OSError:
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


class AlbumArtWindow(qltk.Window, PersistentWindowMixin, PluginConfigMixin):
    """The main window including the search list"""

    CONFIG_SECTION = PLUGIN_CONFIG_SECTION
    THUMB_SIZE = 128

    def __init__(self, songs):
        super().__init__()
        self.enable_window_tracking(f"plugin_{PLUGIN_CONFIG_SECTION}")

        self.image_cache = []
        self.image_cache_size = 10
        self.search_lock = False

        self.set_title(_("Album Art Downloader"))
        self.set_icon_name(Icons.EDIT_FIND)
        self.set_default_size(800, 550)

        image = CoverArea(self, songs[0])

        self.liststore = Gtk.ListStore(object, object)
        self.treeview = treeview = AllTreeView(model=self.liststore)
        self.treeview.set_headers_visible(False)
        self.treeview.set_rules_hint(True)

        targets = [("text/uri-list", 0, 0)]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        treeview.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK, targets, Gdk.DragAction.COPY
        )

        treeselection = self.treeview.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.SINGLE)
        treeselection.connect("changed", self.__select_callback, image)

        self.treeview.connect("drag-data-get", self.__drag_data_get, treeselection)

        rend_pix = Gtk.CellRendererPixbuf()
        img_col = Gtk.TreeViewColumn("Thumb")
        img_col.prepend(rend_pix, False)

        def cell_data_pb(column, cell, model, iter_, *args):
            surface = model[iter_][0]
            cell.set_property("surface", surface)

        img_col.set_cell_data_func(rend_pix, cell_data_pb, None)
        treeview.append_column(img_col)

        rend_pix.set_property("xpad", 2)
        rend_pix.set_property("ypad", 2)
        border_width = self.get_scale_factor() * 2
        rend_pix.set_property("width", self.THUMB_SIZE + 6 + border_width)
        rend_pix.set_property("height", self.THUMB_SIZE + 6 + border_width)

        def escape_data(data):
            for rep in ("\n", "\t", "\r", "\v"):
                data = data.replace(rep, " ")
            return util.escape(" ".join(data.split()))

        def cell_data(column, cell, model, iter, data):
            cover = model[iter][1]

            esc = escape_data

            txt = util.bold_italic(cover["name"], escaper=esc)
            txt += "\n<small>%s</small>" % (
                _("from %(source)s")
                % {"source": util.italic(cover["source"], escaper=esc)}
            )
            if "resolution" in cover:
                txt += "\n" + _("Resolution: %s") % util.italic(
                    cover["resolution"], escaper=esc
                )
            if "size" in cover:
                txt += "\n" + _("Size: %s") % util.italic(cover["size"], escaper=esc)

            cell.markup = txt
            cell.set_property("markup", cell.markup)

        rend = Gtk.CellRendererText()
        rend.set_property("ellipsize", Pango.EllipsizeMode.END)
        info_col = Gtk.TreeViewColumn("Info", rend)
        info_col.set_cell_data_func(rend, cell_data)

        treeview.append_column(info_col)

        sw_list = Gtk.ScrolledWindow()
        sw_list.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw_list.set_shadow_type(Gtk.ShadowType.IN)
        sw_list.add(treeview)

        search_labelraw = Gtk.Label("raw")
        search_labelraw.set_alignment(xalign=1.0, yalign=0.5)
        self.search_fieldraw = Gtk.Entry()
        self.search_fieldraw.connect("activate", self.start_search)
        self.search_fieldraw.connect("changed", self.__searchfieldchanged)
        search_labelclean = Gtk.Label("clean")
        search_labelclean.set_alignment(xalign=1.0, yalign=0.5)
        self.search_fieldclean = Gtk.Label()
        self.search_fieldclean.set_can_focus(False)
        self.search_fieldclean.set_alignment(xalign=0.0, yalign=0.5)

        self.search_radioraw = Gtk.CheckButton(group=None, label=None)
        self.search_radioraw.connect("toggled", self.__searchtypetoggled, "raw")
        self.search_radioclean = Gtk.CheckButton(group=self.search_radioraw, label=None)
        self.search_radioclean.connect("toggled", self.__searchtypetoggled, "clean")
        # note: set_active(False) appears to have no effect
        # self.search_radioraw.set_active(
        #    self.config_get_bool('searchraw', False))
        if self.config_get_bool("searchraw", False):
            self.search_radioraw.set_active(True)
        else:
            self.search_radioclean.set_active(True)

        search_labelresultsmax = Gtk.Label("limit")
        search_labelresultsmax.set_alignment(xalign=1.0, yalign=0.5)
        search_labelresultsmax.set_tooltip_text(_("Per engine 'at best' results limit"))
        search_adjresultsmax = Gtk.Adjustment(
            value=int(self.config_get("resultsmax", 3)),
            lower=1,
            upper=REQUEST_LIMIT_MAX,
            step_incr=1,
            page_incr=0,
            page_size=0,
        )
        self.search_spinresultsmax = Gtk.SpinButton(
            adjustment=search_adjresultsmax, climb_rate=0.2, digits=0
        )
        self.search_spinresultsmax.set_alignment(xalign=0.5)
        self.search_spinresultsmax.set_can_focus(False)

        self.search_button = Button(_("_Search"), Icons.EDIT_FIND)
        self.search_button.connect("clicked", self.start_search)
        search_button_box = Gtk.Alignment()
        search_button_box.set(1, 0, 0, 0)
        search_button_box.add(self.search_button)

        search_table = Gtk.Table(rows=3, columns=4, homogeneous=False)
        search_table.set_col_spacings(6)
        search_table.set_row_spacings(6)
        search_table.attach(
            search_labelraw, 0, 1, 0, 1, xoptions=Gtk.AttachOptions.FILL, xpadding=6
        )
        search_table.attach(self.search_radioraw, 1, 2, 0, 1, xoptions=0, xpadding=0)
        search_table.attach(self.search_fieldraw, 2, 4, 0, 1)
        search_table.attach(
            search_labelclean, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL, xpadding=6
        )
        search_table.attach(self.search_radioclean, 1, 2, 1, 2, xoptions=0, xpadding=0)
        search_table.attach(self.search_fieldclean, 2, 4, 1, 2, xpadding=4)
        search_table.attach(
            search_labelresultsmax,
            0,
            2,
            2,
            3,
            xoptions=Gtk.AttachOptions.FILL,
            xpadding=6,
        )
        search_table.attach(
            self.search_spinresultsmax,
            2,
            3,
            2,
            3,
            xoptions=Gtk.AttachOptions.FILL,
            xpadding=0,
        )
        search_table.attach(search_button_box, 3, 4, 2, 3)

        widget_space = 5

        self.progress = Gtk.ProgressBar()

        left_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=widget_space)
        left_vbox.prepend(search_table, False, True, 0)
        left_vbox.prepend(sw_list, True, True, 0)

        hpaned = ConfigRHPaned(
            section="plugins", option=f"{PLUGIN_CONFIG_SECTION}_pos", default=0.3
        )
        hpaned.set_border_width(widget_space)
        hpaned.pack1(left_vbox, shrink=False)
        hpaned.pack2(image, shrink=False)

        self.add(hpaned)

        self.show_all()

        left_vbox.prepend(self.progress, False, True, 0)

        self.connect("destroy", self.__save_config)

        song = songs[0]
        text = SEARCH_PATTERN.format(song)
        self.set_text(text)
        self.start_search()

    def __save_config(self, widget):
        self.config_set("searchraw", self.search_radioraw.get_active())
        self.config_set("resultsmax", self.search_spinresultsmax.get_value_as_int())

    def __drag_data_get(self, view, ctx, sel, tid, etime, treeselection):
        model, iter = treeselection.get_selected()
        if not iter:
            return
        cover = model.get_value(iter, 1)
        sel.set_uris([cover["cover"]])

    def __searchfieldchanged(self, *data):
        search = data[0].get_text()
        clean = cleanup_query(search, " ")
        self.search_fieldclean.set_text(util.italic(clean))
        self.search_fieldclean.set_use_markup(True)

    def __searchtypetoggled(self, *data):
        self.config_set("searchraw", self.search_radioraw.get_active())

    def start_search(self, *data):
        """Start the search using the text from the text entry"""

        text = self.search_fieldraw.get_text()
        if not text or self.search_lock:
            return

        self.search_lock = True
        self.search_button.set_sensitive(False)

        self.progress.set_fraction(0)
        self.progress.set_text(_("Searching…"))
        self.progress.show()

        self.liststore.clear()

        self.search = search = CoverSearch(self.__search_callback)

        for eng in ENGINES:
            if self.config_get_bool(CONFIG_ENG_PREFIX + eng["config_id"], True):
                search.add_engine(eng["class"], eng["replace"])

        raw = self.search_radioraw.get_active()
        limit = self.search_spinresultsmax.get_value_as_int()
        search.start(text, raw, limit)

        # Focus the list
        self.treeview.grab_focus()

        self.connect("destroy", self.__destroy)

    def __destroy(self, *args):
        self.search.stop()

    def set_text(self, text):
        """set the text and move the cursor to the end"""

        self.search_fieldraw.set_text(text)
        self.search_fieldraw.emit("move-cursor", Gtk.MovementStep.BUFFER_ENDS, 0, False)

    def __select_callback(self, selection, image):
        model, iter = selection.get_selected()
        if not iter:
            return
        cover = model.get_value(iter, 1)
        image.set_cover(cover["cover"])

    def __add_cover_to_list(self, cover):
        try:
            pbloader = GdkPixbuf.PixbufLoader()
            pbloader.write(get_url(cover["thumbnail"]))
            pbloader.close()

            scale_factor = self.get_scale_factor()
            size = self.THUMB_SIZE * scale_factor - scale_factor * 2
            pixbuf = pbloader.get_pixbuf().scale_simple(
                size, size, GdkPixbuf.InterpType.BILINEAR
            )
            pixbuf = add_border_widget(pixbuf, self)
            if not pixbuf:
                return
            surface = get_surface_for_pixbuf(self, pixbuf)
        except (OSError, GLib.GError):
            pass
        else:

            def append(data):
                self.liststore.append(data)

            GLib.idle_add(append, [surface, cover])

    def __search_callback(self, covers, progress):
        for cover in covers:
            self.__add_cover_to_list(cover)

        if self.progress.get_fraction() < progress:
            self.progress.set_fraction(progress)

        if progress >= 1:
            self.progress.set_text(_("Done"))
            GLib.timeout_add(700, self.progress.hide)
            self.search_button.set_sensitive(True)
            self.search_lock = False


class CoverSearch:
    """Class for glueing the search engines together. No UI stuff."""

    def __init__(self, callback):
        self.engine_list = []
        self._stop = False

        def wrap(*args, **kwargs):
            if not self._stop:
                return callback(*args, **kwargs)
            return None

        self.callback = wrap
        self.finished = 0

    def add_engine(self, engine, query_replace):
        """Adds a new search engine, query_replace is the string with which
        all special characters get replaced"""

        self.engine_list.append((engine, query_replace))

    def stop(self):
        """After stop the progress callback will no longer be called"""

        self._stop = True

    def start(self, query, raw, limit):
        """Start search. The callback function will be called after each of
        the search engines has finished."""

        for engine, replace in self.engine_list:
            thr = threading.Thread(
                target=self.__search_thread, args=(engine, query, replace, raw, limit)
            )
            thr.daemon = True
            thr.start()

        # tell the other side that we are finished if there is nothing to do.
        if not len(self.engine_list):
            GLib.idle_add(self.callback, [], 1)

    def __search_thread(self, engine, query, replace, raw, limit):
        """Creates searching threads which call the callback function after
        they are finished"""

        search = query if raw else cleanup_query(query, replace)

        print_d(f"[AlbumArt] running search {search!r} on engine {engine.__name__}")
        result = []
        try:
            result = engine().start(search, limit)
        except Exception as e:
            print_w(f"[AlbumArt] {engine.__name__}: {query!r} ({e})")
            print_exc()

        self.finished += 1
        # progress is between 0..1
        progress = float(self.finished) / len(self.engine_list)
        GLib.idle_add(self.callback, result, progress)


def cleanup_query(query, replace):
    """split up at '-', remove some chars, only keep the longest words...
    more false positives but much better results"""

    query = query.lower()
    if query.startswith("the "):
        query = query[4:]

    split = query.split("-")
    replace_str = ("+", "&", ",", ".", "!", "´", "'", ":", " and ", "(", ")")
    new_query = ""
    for part in split:
        for stri in replace_str:
            part = part.replace(stri, replace)

        p_split = part.split()
        p_split.sort(key=len, reverse=True)
        end = max(int(len(p_split) / 4), max(4 - len(p_split), 2))
        p_split = p_split[:end]

        new_query += " ".join(p_split) + " "

    return new_query.rstrip()


def get_size_of_url(url):
    request = Request(url)
    request.add_header("Accept-Encoding", "gzip")
    request.add_header("User-Agent", USER_AGENT)
    url_sock = urlopen(request)
    size = url_sock.headers.get("content-length")
    url_sock.close()
    return format_size(int(size)) if size else ""


ENGINES = [
    {
        "class": DiscogsSearcher,
        "url": "https://www.discogs.com/",
        "replace": " ",
        "config_id": "discogs",
    },
]


class DownloadAlbumArt(SongsMenuPlugin, PluginConfigMixin):
    """Download and save album (cover) art from a variety of sources"""

    PLUGIN_ID = "Download Album Art"
    PLUGIN_NAME = _("Download Album Art")
    PLUGIN_DESC = _("Downloads album covers from various websites.")
    PLUGIN_ICON = Icons.INSERT_IMAGE
    CONFIG_SECTION = PLUGIN_CONFIG_SECTION
    REQUIRES_ACTION = True

    plugin_handles = any_song(is_a_file)

    @classmethod
    def PluginPreferences(cls, window):
        table = Gtk.Table(n_rows=len(ENGINES), n_columns=2)
        table.props.expand = False
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        frame = qltk.Frame(_("Sources"), child=table)

        for i, eng in enumerate(sorted(ENGINES, key=lambda x: x["url"])):
            check = cls.ConfigCheckButton(
                eng["config_id"].title(), CONFIG_ENG_PREFIX + eng["config_id"], True
            )
            table.attach(check, 0, 1, i, i + 1)

            button = Gtk.Button(label=eng["url"])
            button.connect("clicked", lambda s: util.website(s.get_label()))
            table.attach(
                button,
                1,
                2,
                i,
                i + 1,
                xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK,
            )
        return frame

    def plugin_album(self, songs):
        return AlbumArtWindow(songs)
