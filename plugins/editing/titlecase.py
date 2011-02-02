import gtk

from quodlibet import util
from quodlibet.plugins.editing import EditTagsPlugin

class TitleCase(EditTagsPlugin):
    PLUGIN_ID = "Title Case"
    PLUGIN_NAME = _("Title Case")
    PLUGIN_DESC = _("Title-case tag values in the tag editor.")
    PLUGIN_ICON = gtk.STOCK_SPELL_CHECK
    PLUGIN_VERSION = "1"

    def __init__(self, tag, value):
        super(TitleCase, self).__init__(_("Title-_case Value"))
        self.set_image(
            gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
        self.set_sensitive(util.title(value) != value)

    def activated(self, tag, value):
        return [(tag, util.title(value))]
