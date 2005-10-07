QL_ICON = 'quodlibet'
EF_ICON = 'exfalso'

VOLUME_OFF = 'ql-volume-zero'
VOLUME_MIN = 'ql-volume-min'
VOLUME_MED = 'ql-volume-medium'
VOLUME_MAX = 'ql-volume-max'

_ICONS = [QL_ICON, EF_ICON, VOLUME_OFF, VOLUME_MIN, VOLUME_MED, VOLUME_MAX]

def init():
    import gtk
    factory = gtk.IconFactory()
    for fn in _ICONS:
        pb = gtk.gdk.pixbuf_new_from_file(fn+".png")
        factory.add(fn, gtk.IconSet(pb))
    factory.add_default()
