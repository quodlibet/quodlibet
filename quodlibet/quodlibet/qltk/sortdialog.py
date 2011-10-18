# -*- coding: utf-8 -*-
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet.util import tag


class SortCriterionBox(gtk.ComboBox):
    """A ComboBox containing a list of tags for the user to choose from.
    The tag names are presented both translated and untranslated.

    The 'tag' attribute is the currently chosen tag."""

    __criterions = [
        (_("Track Headers"),
           """title genre ~title~version ~#track ~#playcount ~#skipcount
           ~#rating ~#length""".split()),
        (_("People Headers"),
           """artist ~people performer arranger author composer conductor
           lyricist originalartist""".split()),
        (_("Album Headers"),
           """album ~album~discsubtitle labelid ~#disc ~#discs ~#tracks
           albumartist""".split()),
        (_("Date Headers"),
           """date originaldate recordingdate ~#laststarted ~#lastplayed
           ~#added ~#mtime""".split()),
        (_("File Headers"),
           """~format ~#bitrate ~filename ~basename ~dirname ~uri""".split()),
        (_("Production Headers"),
           """copyright organization location isrc contact website""".split()),
    ]

    def __init__(self):
        super(SortCriterionBox, self).__init__(gtk.TreeStore(str, str))

        render = gtk.CellRendererText()
        self.pack_start(render, True)
        self.add_attribute(render, 'text', 1)

        model = self.get_model()
        for (group, items) in self.__criterions:
            group_row = model.append(None, row=[group, group])
            for t in items:
                model.append(group_row, row=[t, "%s (%s)" % (tag(t), t)])

        self.set_active(0)

    @property
    def tag(self):
        iter_ = self.get_active_iter()
        row = self.get_model()[iter_]
        if len(row.path) == 1:
            return
        return row[0]


class SortCriterionChooser(gtk.Table):
    def __init__(self):
        super(SortCriterionChooser, self).__init__()
        self.set_row_spacing(0, 6)
        self.set_col_spacing(0, 6)

        label = gtk.Label(_("Tag:"))

        self.combo = SortCriterionBox()
        optbox = gtk.HBox()
        self.optasc = gtk.RadioButton(label=_("Ascending"))
        self.optdesc = gtk.RadioButton(group=self.optasc,
                                       label=_("Descending"))
        optbox.add(self.optasc)
        optbox.add(self.optdesc)
        self.attach(label, 0, 1, 0, 1, xoptions=gtk.FILL)
        self.attach(self.combo, 1, 2, 0, 1)
        self.attach(optbox, 0, 2, 1, 2)

    @property
    def order(self):
        if self.optasc.get_active():
            return gtk.SORT_ASCENDING
        return gtk.SORT_DESCENDING

    @property
    def tag(self):
        return self.combo.tag


class SortDialog(gtk.Dialog):

    def sort_keys(self):
        """This returns a list of tuples (sorting key, order)."""
        return [(cc.tag, cc.order) for cc in self.choosers if cc.tag]

    def __add_criterion(self, *args):
        vbox = self.box

        hbox = gtk.HBox(spacing=6)
        vbox.pack_start(hbox, expand=False)

        cc = SortCriterionChooser()
        hbox.add(cc)

        del_btn = gtk.Button(stock=gtk.STOCK_REMOVE)
        del_btn.connect_object("clicked", self.__remove_criterion, cc, hbox)
        hbox.pack_start(del_btn, expand=False)

        hbox.show_all()

        self.choosers.append(cc)

    def __remove_criterion(self, cc, hbox):
        self.choosers.remove(cc)
        self.box.remove(hbox)

    def __init__(self, parent, critcount=1):
        super(SortDialog, self).__init__(title=_("Custom sort"))
        self.set_transient_for(parent)

        self.box = vbox = gtk.VBox(spacing=6)
        vbox.set_border_width(10)

        add_btn = gtk.Button(stock=gtk.STOCK_ADD)
        add_btn.connect("clicked", self.__add_criterion)
        vbox.pack_start(add_btn, expand=False)

        self.choosers = []
        for cc in xrange(critcount):
            self.__add_criterion()

        self.vbox.pack_start(vbox)

        self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.show_all()

    def run(self):
        resp = super(SortDialog, self).run()
        self.destroy()
        return resp
