# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gtk

from quodlibet import const
from quodlibet import util

from quodlibet.util import trash
from quodlibet.qltk import get_top_parent
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk.wlw import WaitLoadWindow
from quodlibet.qltk.x import Button

class DeleteDialog(gtk.Dialog):
    def __init__(self, parent, files, asktrash=True, askonly=False):
        super(DeleteDialog, self).__init__(
            _("Delete Files"), get_top_parent(parent))
        self.set_border_width(6)
        self.vbox.set_spacing(6)
        self.set_has_separator(False)
        self.action_area.set_border_width(0)
        self.set_resizable(False)

        self.__files = files

        if asktrash and trash.can_trash():
            b = Button(_("_Move to Trash"), gtk.STOCK_DELETE)
            self.add_action_widget(b, 0)

        self.__askonly = askonly

        self.add_button(gtk.STOCK_CANCEL, 1)
        self.add_button(gtk.STOCK_DELETE, 2)

        hbox = gtk.HBox()
        hbox.set_border_width(6)
        i = gtk.Image()
        i.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        i.set_padding(12, 0)
        i.set_alignment(0.5, 0.0)
        hbox.pack_start(i, expand=False)
        vbox = gtk.VBox(spacing=6)

        base = os.path.basename(files[0])
        if len(files) == 1: l = _("Permanently delete this file?")
        else: l = _("Permanently delete these files?")
        if len(files) == 1:
            exp = gtk.Expander("%s" % util.fsdecode(base))
        else:
            exp = gtk.Expander(ngettext("%(title)s and %(count)d more...",
                "%(title)s and %(count)d more...", len(files)-1) %
                {'title': util.fsdecode(base), 'count': len(files) - 1})

        lab = gtk.Label()
        lab.set_markup("<big><b>%s</b></big>" % l)
        lab.set_alignment(0.0, 0.5)
        vbox.pack_start(lab, expand=False)

        lab = gtk.Label("\n".join(
            map(util.fsdecode, map(util.unexpand, files))))
        lab.set_alignment(0.1, 0.0)
        exp.add(gtk.ScrolledWindow())
        exp.child.add_with_viewport(lab)
        exp.child.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        exp.child.child.set_shadow_type(gtk.SHADOW_NONE)
        vbox.pack_start(exp)
        hbox.pack_start(vbox)
        self.vbox.pack_start(hbox)
        self.vbox.show_all()

    def run(self):
        resp = super(DeleteDialog, self).run()
        if self.__askonly:
            self.destroy()
            return resp

        if resp == 1 or resp == gtk.RESPONSE_DELETE_EVENT: return []
        elif resp == 0: s = _("Moving %(current)d/%(total)d.")
        elif resp == 2: s = _("Deleting %(current)d/%(total)d.")
        else: return []
        files = self.__files
        w = WaitLoadWindow(self, len(files), s)
        removed = []

        if resp == 0:
            for filename in files:
                try:
                    trash.trash(filename)
                except trash.TrashError:
                    fn = util.escape(util.fsdecode(util.unexpand(filename)))
                    ErrorMessage(self, _("Unable to move to trash"),
                        (_("Moving <b>%s</b> to the trash failed.") %
                        fn)).run()
                    break
                removed.append(filename)
                w.step()
        else:
            for filename in files:
                try:
                    os.unlink(filename)
                except EnvironmentError, s:
                    try: s = unicode(s.strerror, const.ENCODING, 'replace')
                    except TypeError:
                        s = unicode(s.strerror[1], const.ENCODING, 'replace')
                    s = "\n\n" + s
                    fn = util.escape(util.fsdecode(util.unexpand(filename)))
                    ErrorMessage(
                        self, _("Unable to delete file"),
                        (_("Deleting <b>%s</b> failed.") % fn) + s).run()
                    break
                removed.append(filename)
                w.step()

        w.destroy()
        return removed
