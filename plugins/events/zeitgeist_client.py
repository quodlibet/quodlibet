# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time

try:
    from zeitgeist.client import ZeitgeistClient
    from zeitgeist.datamodel import Event, Subject
    from zeitgeist.datamodel import Interpretation, Manifestation
except ImportError:
    from quodlibet.plugins import PluginImportException
    raise PluginImportException(
        _("Couldn't find 'zeitgeist' (Event logging service)."))

from quodlibet.plugins.events import EventPlugin

class Zeitgeist(EventPlugin):
    PLUGIN_ID = "zeitgeist"
    PLUGIN_NAME = _("Event Logging")
    PLUGIN_DESC = _("Send song events to the Zeitgeist event logging service")
    PLUGIN_ICON = 'gtk-network'
    PLUGIN_VERSION = "0.1"

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
