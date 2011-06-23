import gtk

from quodlibet import config, util
from quodlibet.plugins.editing import EditTagsPlugin
from quodlibet.qltk.ccb import ConfigCheckButton

class TitleCase(EditTagsPlugin):
    PLUGIN_ID = "Title Case"
    PLUGIN_NAME = _("Title Case")
    PLUGIN_DESC = _("Title-case tag values in the tag editor.")
    PLUGIN_ICON = gtk.STOCK_SPELL_CHECK
    PLUGIN_VERSION = "1.1"
    CFG_PREFIX = "titlecase_"

    # Issue 753: Allow all caps (as before).
    # Set to False means you get Run Dmc, Ac/Dc, Cd 1/2 etc
    allow_all_caps = True;

    def process_tag(self, str):
        if self.allow_all_caps:
            return util.title(str)
        else: return util.title(str.lower())

    @classmethod
    def cfg_get(cls, key, default=''):
        try:
            return config.getboolean('plugins', cls.CFG_PREFIX + key)
        except config.error:
            return default

    def __init__(self, tag, value):
        self.allow_all_caps = self.cfg_get('allow_all_caps', True)
        super(TitleCase, self).__init__(_("Title-_case Value"))
        self.set_image(
            gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
        self.set_sensitive(self.process_tag(value) != value)

    @classmethod
    def PluginPreferences(cls, window):
        vb = gtk.VBox()
        vb.set_spacing(8)

        config_toggles = [
            ('allow_all_caps', _("Allow _ALL-CAPS in tags"), True)
        ]
        for key, label, default in config_toggles:
            ccb = ConfigCheckButton(label, 'plugins', cls.CFG_PREFIX + key)
            ccb.set_active(cls.cfg_get(key, default))
            vb.pack_start(ccb)

        return vb

    def activated(self, tag, value):
        return [(tag, self.process_tag(value))]
