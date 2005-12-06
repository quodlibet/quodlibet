import gtk

QL_ICON = 'quodlibet'
EF_ICON = 'exfalso'

EDIT_TAGS = 'ql-edit-tags'
PLUGINS = 'ql-plugins'
PREVIEW = 'ql-preview'
REMOVE = 'ql-remove'
ENQUEUE = 'ql-enqueue'

VOLUME_OFF = 'ql-volume-zero'
VOLUME_MIN = 'ql-volume-min'
VOLUME_MED = 'ql-volume-medium'
VOLUME_MAX = 'ql-volume-max'

_ICONS = [QL_ICON, EF_ICON, VOLUME_OFF, VOLUME_MIN, VOLUME_MED, VOLUME_MAX]

def init():
    factory = gtk.IconFactory()
    for fn in _ICONS:
        pb = gtk.gdk.pixbuf_new_from_file(fn+".png")
        factory.add(fn, gtk.IconSet(pb))
    factory.add_default()

    gtk.stock_add([
        (EDIT_TAGS, _("Edit _Tags"), 0, 0, ""),
        (PLUGINS, _("_Plugins"), 0, 0, ""),
        (PREVIEW, _("_Preview"), 0, 0, ""),
        (ENQUEUE, _("Add to _Queue"), 0, 0, "")
        ])

    icons = gtk.IconFactory()
    lookup = gtk.icon_factory_lookup_default
    icons.add(EDIT_TAGS, lookup(gtk.STOCK_PROPERTIES))
    icons.add(PLUGINS, lookup(gtk.STOCK_EXECUTE))
    icons.add(PREVIEW, lookup(gtk.STOCK_CONVERT))
    icons.add(ENQUEUE, lookup(gtk.STOCK_ADD))

    # Introduced in GTK 2.8
    try: gtk.STOCK_INFO
    except AttributeError:
        gtk.STOCK_INFO = 'gtk-info'
        if not gtk.stock_lookup(gtk.STOCK_INFO):
            icons.add(gtk.STOCK_INFO, lookup(gtk.STOCK_DIALOG_INFO))
            gtk.stock_add([(gtk.STOCK_INFO, _("_Information"), 0, 0, "")])

    # Translators: Only translate this if it conflicts with "Delete",
    # as is the case in e.g. Finnish. It should be disambiguated as
    # "Remove from Library" (as opposed to, from playlist, from disk, etc.)
    # Don't literally translate "ql-remove".
    icons.add(REMOVE, lookup(gtk.STOCK_REMOVE))
    if _("ql-remove") == "ql-remove":
        gtk.stock_add([(REMOVE,)+gtk.stock_lookup(gtk.STOCK_REMOVE)[1:]])
    else:
        old = gtk.stock_lookup(gtk.STOCK_REMOVE)
        gtk.stock_add([REMOVE, _("ql-remove"), 0, 0, ""])

    for key, name in [
        # Translators: Only translate this if GTK does so incorrectly.
        # or missing. Don't literally translate media/next/previous/play/pause.
        (gtk.STOCK_MEDIA_NEXT, _('gtk-media-next')),
        # Translators: Only translate this if GTK does so incorrectly.
        # or missing. Don't literally translate media/next/previous/play/pause.
        (gtk.STOCK_MEDIA_PREVIOUS, _('gtk-media-previous')),
        # Translators: Only translate this if GTK does so incorrectly.
        # or missing. Don't literally translate media/next/previous/play/pause.
        (gtk.STOCK_MEDIA_PLAY, _('gtk-media-play')),
        # Translators: Only translate this if GTK does so incorrectly.
        # or missing. Don't literally translate media/next/previous/play/pause.
        (gtk.STOCK_MEDIA_PAUSE, _('gtk-media-pause'))
        ]:
        if key != name: # translated, so re-register with a good name
            gtk.stock_add([(key, name,)+gtk.stock_lookup(key)[2:]])

    icons.add_default()
