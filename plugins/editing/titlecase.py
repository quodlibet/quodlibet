import gtk
import util

from plugins.editing import EditTagsPlugin

class TitleCase(EditTagsPlugin):
    def __init__(self, tag, value):
        super(TitleCase, self).__init__(_("Title-_case Value"))
        self.set_image(
            gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
        self.set_sensitive(util.title(value) != value)

    def activated(self, tag, value):
        return [(tag, util.title(value))]
