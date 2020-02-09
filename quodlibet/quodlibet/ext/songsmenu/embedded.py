# Copyright 2013 Christoph Reiter
#     2013,2016,2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet import app
from quodlibet import util
from quodlibet.plugins.songshelpers import any_song, has_writable_image
from quodlibet.qltk.x import MenuItem
from quodlibet.qltk import Icons
from quodlibet.qltk.wlw import WritingWindow
from quodlibet.qltk._editutils import WriteFailedError
from quodlibet.formats import EmbeddedImage, AudioFileError
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class EditEmbedded(SongsMenuPlugin):
    PLUGIN_ID = "embedded_edit"
    PLUGIN_NAME = _("Edit Embedded Images")
    PLUGIN_DESC = _("Removes or replaces embedded images.")
    PLUGIN_ICON = Icons.INSERT_IMAGE

    plugin_handles = any_song(has_writable_image)
    """if any song supports editing, we are active"""

    def __init__(self, songs, *args, **kwargs):
        super(EditEmbedded, self).__init__(songs, *args, **kwargs)
        self.__menu = Gtk.Menu()
        self._init_submenu_items(self.__menu, songs)
        self.set_submenu(self.__menu)

    def __remove_images(self, menu_item, songs):
        win = WritingWindow(self.plugin_window, len(songs))
        win.show()

        for song in songs:
            if song.has_images and song.can_change_images:
                try:
                    song.clear_images()
                except AudioFileError:
                    util.print_exc()
                    WriteFailedError(win, song).run()

            if win.step():
                break

        win.destroy()
        self.plugin_finish()

    def __set_image(self, menu_item, songs):
        win = WritingWindow(self.plugin_window, len(songs))
        win.show()

        for song in songs:
            if song.can_change_images:
                fileobj = app.cover_manager.get_cover(song)
                if fileobj:
                    path = fileobj.name
                    image = EmbeddedImage.from_path(path)
                    if image:
                        try:
                            song.set_image(image)
                        except AudioFileError:
                            util.print_exc()
                            WriteFailedError(win, song).run()

            if win.step():
                break

        win.destroy()
        self.plugin_finish()

    def _init_submenu_items(self, menu, songs):
        remove_item = MenuItem(_("_Remove all Images"), "edit-delete")
        remove_item.connect('activate', self.__remove_images, songs)
        menu.append(remove_item)

        set_item = MenuItem(_("_Embed Current Image"), "edit-paste")
        set_item.connect('activate', self.__set_image, songs)
        menu.append(set_item)

        menu.show_all()
        return menu

    def plugin_songs(self, songs):
        return True
