# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gtk

import const

QL_ICON = 'quodlibet'
EF_ICON = 'exfalso'

EDIT_TAGS = 'ql-edit-tags'
PLUGINS = 'ql-plugins'
PREVIEW = 'ql-preview'
REMOVE = 'ql-remove'
ENQUEUE = 'ql-enqueue'
PLAYLISTS = 'ql-add-to-playlist'
DEVICES = 'ql-copy-to-device'
RENAME = 'ql-rename'

IPOD = 'device-ipod'
STORAGE = 'device-generic'

EJECT = 'media-eject'

VOLUME_OFF = 'audio-volume-muted'
VOLUME_MIN = 'audio-volume-low'
VOLUME_MED = 'audio-volume-medium'
VOLUME_MAX = 'audio-volume-high'

NO_ALBUM = os.path.join(const.BASEDIR, 'missing-cover.svg')

_ICONS = [QL_ICON, EF_ICON, VOLUME_OFF, VOLUME_MIN, VOLUME_MED, VOLUME_MAX,
          IPOD, STORAGE, EJECT]

def init():
    factory = gtk.IconFactory()
    for fn in _ICONS:
        icon_filename = os.path.join(const.BASEDIR, fn + ".png")
        pb = gtk.gdk.pixbuf_new_from_file(icon_filename)
        factory.add(fn, gtk.IconSet(pb))

    gtk.stock_add([
        (EDIT_TAGS, _("Edit _Tags"), 0, 0, ""),
        (PLUGINS, _("_Plugins"), 0, 0, ""),
        (PREVIEW, _("_Preview"), 0, 0, ""),
        (ENQUEUE, _("Add to _Queue"), 0, 0, ""),
        (PLAYLISTS, _("_Add to Playlist"), 0, 0, ""),
        (DEVICES, _("_Copy to Device"), 0, 0, ""),
        (EJECT, _("_Eject"), 0, 0, ""),
        (RENAME, _("_Rename"), 0, 0, ""),
        ])

    lookup = gtk.icon_factory_lookup_default
    factory.add(EDIT_TAGS, lookup(gtk.STOCK_PROPERTIES))
    factory.add(PLUGINS, lookup(gtk.STOCK_EXECUTE))
    factory.add(PREVIEW, lookup(gtk.STOCK_CONVERT))
    factory.add(ENQUEUE, lookup(gtk.STOCK_ADD))
    factory.add(PLAYLISTS, lookup(gtk.STOCK_ADD))
    factory.add(DEVICES, lookup(gtk.STOCK_COPY))
    factory.add(RENAME, lookup(gtk.STOCK_EDIT))

    # Introduced in GTK 2.8
    try: gtk.STOCK_INFO
    except AttributeError:
        gtk.STOCK_INFO = 'gtk-info'
        if not gtk.stock_lookup(gtk.STOCK_INFO):
            factory.add(gtk.STOCK_INFO, lookup(gtk.STOCK_DIALOG_INFO))
            gtk.stock_add([(gtk.STOCK_INFO, _("_Information"), 0, 0, "")])

    factory.add(REMOVE, lookup(gtk.STOCK_REMOVE))
    # Translators: Only translate this if it conflicts with "Delete",
    # as is the case in e.g. Finnish. It should be disambiguated as
    # "Remove from Library" (as opposed to, from playlist, from disk, etc.)
    # Don't literally translate "ql-remove". It needs an access key, so
    # a sample translation would be "_Remove from Library".
    if _("ql-remove") == "ql-remove":
        gtk.stock_add([(REMOVE,) + gtk.stock_lookup(gtk.STOCK_REMOVE)[1:]])
    else:
        old = gtk.stock_lookup(gtk.STOCK_REMOVE)
        gtk.stock_add([(REMOVE, _("ql-remove"), 0, 0, "")])

    for key, name in [
        # Translators: Only translate this if GTK does so incorrectly or not
        # at all. Don't literally translate media/next/previous/play/pause.
        # This string needs an access key.
        (gtk.STOCK_MEDIA_NEXT, _('gtk-media-next')),
        # Translators: Only translate this if GTK does so incorrectly or not
        # at all. Don't literally translate media/next/previous/play/pause.
        # This string needs an access key.
        (gtk.STOCK_MEDIA_PREVIOUS, _('gtk-media-previous')),
        # Translators: Only translate this if GTK does so incorrectly or not
        # at all. Don't literally translate media/next/previous/play/pause.
        # This string needs an access key.
        (gtk.STOCK_MEDIA_PLAY, _('gtk-media-play')),
        # Translators: Only translate this if GTK does so incorrectly or not
        # at all. Don't literally translate media/next/previous/play/pause.
        # This string needs an access key.
        (gtk.STOCK_MEDIA_PAUSE, _('gtk-media-pause')),
        ]:
        if key != name: # translated, so re-register with a good name
            gtk.stock_add([(key, name) + gtk.stock_lookup(key)[2:]])

    factory.add_default()
