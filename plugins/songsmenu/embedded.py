# Copyright 2013 Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet.qltk.x import MenuItem
from quodlibet.qltk.wlw import WritingWindow
from quodlibet.formats._image import EmbeddedImage
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class EditEmbedded(SongsMenuPlugin):
    PLUGIN_ID = "embedded_edit"
    PLUGIN_NAME = _("Edit Embedded Images")
    PLUGIN_DESC = _("Remove or replace embedded images")
    PLUGIN_ICON = Gtk.STOCK_EDIT

    def __init__(self, songs, *args, **kwargs):
        super(EditEmbedded, self).__init__(songs, *args, **kwargs)
        self.__menu = Gtk.Menu()
        self.__menu.connect('map', self.__map, songs)
        self.__menu.connect('unmap', self.__unmap)
        self.set_submenu(self.__menu)

    def __remove_images(self, menu_item, songs):
        win = WritingWindow(self.plugin_window, len(songs))
        win.show()

        for song in songs:
            if song.has_images and song.can_change_images:
                song.clear_images()

            if win.step():
                break

        win.destroy()
        self.plugin_finish()

    def __set_image(self, menu_item, songs):
        win = WritingWindow(self.plugin_window, len(songs))
        win.show()

        for song in songs:
            if song.can_change_images:
                fileobj = song.find_cover()
                if fileobj:
                    path = fileobj.name
                    image = EmbeddedImage.from_path(path)
                    if image:
                        song.set_image(image)

            if win.step():
                break

        win.destroy()
        self.plugin_finish()

    def __map(self, menu, songs):
        remove_item = MenuItem(_("_Remove image(s)"), "edit-delete")
        remove_item.connect('activate', self.__remove_images, songs)
        menu.append(remove_item)

        set_item = MenuItem(_("_Embed current image(s)"), "edit-paste")
        set_item.connect('activate', self.__set_image, songs)
        menu.append(set_item)

        menu.show_all()

    def __unmap(self, menu):
        for child in self.__menu.get_children():
            self.__menu.remove(child)

    def plugin_songs(self, songs):
        return True

    def plugin_handles(self, songs):
        # if any song supports editing, we are active
        for song in songs:
            if song.can_change_images:
                return True
        return False
