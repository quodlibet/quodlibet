# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

import time

try:
    import __builtin__
    # zeitgeist overrides our gettext functions
    old_builtin = __builtin__.__dict__.copy()
    from zeitgeist.client import ZeitgeistClient
    from zeitgeist.datamodel import Event, Subject
    from zeitgeist.datamodel import Interpretation, Manifestation
    __builtin__.__dict__.update(old_builtin)
except ImportError as e:
    from quodlibet import plugins
    raise (plugins.MissingModulePluginException("zeitgeist") if
           hasattr(plugins, "MissingModulePluginException") else e)

from quodlibet import _
from quodlibet.qltk import Icons
from quodlibet.plugins.events import EventPlugin
from quodlibet.util import print_d


class Zeitgeist(EventPlugin):
    PLUGIN_ID = "zeitgeist"
    PLUGIN_NAME = _("Event Logging")
    PLUGIN_DESC = _("Sends song events to the Zeitgeist event logging "
                    "service.")
    PLUGIN_ICON = Icons.NETWORK_WORKGROUP

    def enabled(self):
        self.client = ZeitgeistClient()
        self.__stopped_by_user = False

    def disabled(self):
        del self.client
        del self.__stopped_by_user

    def plugin_on_song_started(self, song):
        if self.__stopped_by_user:
            manifestation = Manifestation.USER_ACTIVITY
        else:
            manifestation = Manifestation.SCHEDULED_ACTIVITY

        self.__send_event(song, Interpretation.ACCESS_EVENT, manifestation)

    def plugin_on_song_ended(self, song, stopped):
        self.__stopped_by_user = stopped

        if stopped:
            manifestation = Manifestation.USER_ACTIVITY
        else:
            manifestation = Manifestation.SCHEDULED_ACTIVITY

        self.__send_event(song, Interpretation.LEAVE_EVENT, manifestation)

    def __send_event(self, song, interpretation, manifestation):
        if not song:
            return

        print_d("event: interpretation=%s, manifestation=%s" %
                (interpretation.__name__, manifestation.__name__))

        subject = Subject.new_for_values(
            uri=song("~uri"),
            interpretation=Interpretation.AUDIO,
            manifestation=Manifestation.FILE_DATA_OBJECT,
        )

        event = Event.new_for_values(
            timestamp=int(time.time() * 1000),
            interpretation=interpretation,
            manifestation=manifestation,
            actor="application://quodlibet.desktop",
            subjects=[subject]
        )

        self.client.insert_event(event)
