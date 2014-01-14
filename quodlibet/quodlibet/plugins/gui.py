from quodlibet import config
from gi.repository import Gtk


class MenuItemPlugin(Gtk.ImageMenuItem):
    """
    A base plugin that appears in a menu, typically


    During plugin callbacks, `self.plugin_window` will be
    available. This is the `Gtk.Window` that the plugin was invoked from.
    It provides access to two important widgets, `self.plugin_window.browser`
    and `self.plugin_window.songlist`.
    """

    # An upper limit on how many instances of the plugin should be launched
    # at once without warning. Heavyweight plugins should override this value
    # to prevent users killing their performance by opening on many songs.
    MAX_INVOCATIONS = config.getint("plugins", "default_max_invocations", 30)

    def __init__(self, window):
        super(Gtk.ImageMenuItem, self).__init__(self.PLUGIN_NAME)
        self.plugin_window = window
        self.__set_icon()
        self.__initialized = True

    def __set_icon(self):
        """Sets the GTK icon for this plugin item"""
        icon = getattr(self, "PLUGIN_ICON", Gtk.STOCK_EXECUTE)

        image = (Gtk.Image.new_from_stock(icon, Gtk.IconSize.MENU)
                 if Gtk.stock_lookup(icon)
                 else Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
        self.set_always_show_image(True)
        self.set_image(image)

    @property
    def initialized(self):
        # If the GObject __init__ method is bypassed, it can cause segfaults.
        # This explicitly prevents a bad plugin from taking down the app.
        return self.__initialized
