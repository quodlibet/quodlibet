# -*- coding: utf-8 -*-
# Copyright 2016 Mice Pápai
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import shelve
import time
from datetime import date
from threading import Thread

from gi.repository import Gtk, GLib

import quodlibet
from quodlibet import _
from quodlibet import config, util, qltk
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk import Icons
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.compat import urlencode
from quodlibet.util.urllib import urlopen
from quodlibet.qltk.notif import Task
from quodlibet.util import copool
from quodlibet.util.i18n import numeric_phrase

try:
    import json
except ImportError:
    import simplejson as json

API_KEY = "f536cdadb4c2aec75ae15e2b719cb3a1"


def log(msg):
    util.print_d('[lastfmsync] %s' % msg)


def apicall(method, **kwargs):
    """Performs Last.fm API call."""
    real_args = {
            'api_key': API_KEY,
            'format': 'json',
            'method': method,
            }
    real_args.update(kwargs)
    url = ''.join(["https://ws.audioscrobbler.com/2.0/?",
                   urlencode(real_args)])
    log(url)
    uobj = urlopen(url)
    resp = json.load(uobj)
    if 'error' in resp:
        errmsg = 'Last.fm API error: %s' % resp.get('message', '')
        log(errmsg)
        raise EnvironmentError(resp['error'], errmsg)
    return resp


class LastFMSync2(SongsMenuPlugin):
    PLUGIN_ID = "Last.fm Sync 2"
    PLUGIN_NAME = _("Last.fm Sync 2")
    PLUGIN_DESC = _("Updates your library's statistics from your "
                    "Last.fm profile.")
    PLUGIN_ICON = Icons.EMBLEM_SHARED

    CACHE_PATH = os.path.join(quodlibet.get_user_dir(), "lastfmsync2.db")


    def plugin_songs(self, songs):

        user = "micemusculus" #config_get('username', '')

        def update_chart_list(self):
            resp = apicall('user.getweeklychartlist',
                           user=self.username)
            charts = resp['weeklychartlist']['chart']
            desc = numeric_phrase("%d chart", "%d charts", len(charts))
            with Task(_("Updating chart list"), desc) as task:
                task.copool(self.update_chart_list)
                for i, chart in enumerate(charts):
                    time.sleep(1)
                    # Charts keys are 2-tuple
                    # (from_timestamp, to_timestamp)
                    # values are whether we still need to fetch
                    # the chart
                    fro, to = map(lambda s: int(chart[s]),
                                  ('from', 'to'))

                    # If the chart is older than the register date of
                    # the user, don't download it. (So the download
                    # doesn't start with ~2005 every time.)
                    if to < self.registered:
                        continue

                    self.charts.setdefault((fro, to), True)
                    task.update((float(i) + 1) / len(charts))
                    yield
                self.lastupdated = time.time()

