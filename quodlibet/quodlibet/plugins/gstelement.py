# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

class GStreamerPlugin(object):
    """GStreamer Plugins define an element that gets inserted into the
    GStreamer pipeline before the audio sink and after the playbin.

    The method setup_element should return a new element instance or None:
        self.setup_element()

    One optional method can be implemented:
        self.update_element(element)

    update_element should apply all settings and will be called after
    queue_update or on pipeline creation etc.

    All plugin elements will be sorted by their priority attribute
    (higher priority elements come first)
    To notify setting changes, call queue_update.
    """

    _handler = None

    priority = 0

    @classmethod
    def setup_element(cls):
        """Return a new element instance or None"""
        return None

    @classmethod
    def update_element(cls, element):
        """Apply settings to the instance"""
        pass

    @classmethod
    def queue_update(cls):
        """Call if you want to update settings"""
        cls._handler._queue_update(cls)
