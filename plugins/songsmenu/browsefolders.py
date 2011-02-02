import gtk

from quodlibet import util, config
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.entry import ValidatingEntry
from quodlibet.qltk.msg import ErrorMessage

class BrowseFolders(SongsMenuPlugin):
    PLUGIN_ID = 'Browse Folders'
    PLUGIN_NAME = _('Browse Folders')
    PLUGIN_DESC = "View the songs' folders in a file manager"
    PLUGIN_ICON = gtk.STOCK_OPEN
    PLUGIN_VERSION = '2'

    try: config.get("plugins", __name__)
    except: config.set("plugins", __name__, "thunar")

    def PluginPreferences(klass, window):
        vb = gtk.HBox(spacing=3)
        label = gtk.Label(_("_Program:"))
        entry = ValidatingEntry(util.iscommand)
        program = config.get("plugins", __name__)
        entry.set_text(program)
        entry.connect(
            'changed', lambda e: config.set('plugins', __name__, e.get_text()))
        label.set_mnemonic_widget(entry)
        label.set_use_underline(True)
        vb.pack_start(label, expand=False)
        vb.pack_start(entry)
        vb.show_all()
        return vb
    PluginPreferences = classmethod(PluginPreferences)

    def plugin_songs(self, songs):
        program = config.get("plugins", __name__)
        if not program:
            ErrorMessage(self.plugin_window,
                              _("Unable to open folders"),
                              _("No program is set to open folders. Configure "
                                "this plugin in the Plugins dialog.")).run()
            return
        program_args = program.split()
        program_name = program_args[0]
        dirs = dict.fromkeys([song('~dirname') for song in songs]).keys()
        try: util.spawn(program_args + dirs)
        except Exception, err:
            ErrorMessage(
                self.plugin_window,
                _("Unable to start %s" % util.escape(program_name)),
                util.escape(str(err))).run()
