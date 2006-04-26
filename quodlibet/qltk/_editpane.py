# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject
import gtk

import config
import stock

from qltk.cbes import ComboBoxEntrySave
from qltk.ccb import ConfigCheckButton

class FilterCheckButton(ConfigCheckButton):
    __gsignals__ = {
        "preview": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }

    def __init__(self):
        super(FilterCheckButton, self).__init__(
            self._label, self._section, self._key)
        try: self.set_active(config.getboolean(self._section, self._key))
        except: pass
        self.connect_object('toggled', self.emit, 'preview')
    active = property(lambda s: s.get_active())

    def filter(self, original, filename): raise NotImplementedError
    def filter_list(self, origs, names): return map(self.filter, origs, names)

    def __cmp__(self, other):
        return (cmp(self._order, other._order) or
                cmp(type(self).__name__, type(other).__name__))

class EditPane(gtk.VBox):
    def __init__(self, cbes, cbes_defaults, plugins):
        super(EditPane, self).__init__(spacing=6)
        self.set_border_width(12)
        hbox = gtk.HBox(spacing=12)
        self.combo = ComboBoxEntrySave(cbes, cbes_defaults)
        hbox.pack_start(self.combo)
        self.preview = gtk.Button(stock=stock.PREVIEW)
        hbox.pack_start(self.preview, expand=False)
        self.pack_start(hbox, expand=False)
        self.combo.child.connect('changed', self._changed)

        model = gtk.ListStore(object, str, str)
        self.view = gtk.TreeView(model)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self.view)
        self.pack_start(sw)

        filters = [Kind() for Kind in self.FILTERS]
        filters.sort()
        vbox = gtk.VBox()
        map(vbox.pack_start, filters)
        self.pack_start(vbox, expand=False)

        hb = gtk.HBox()
        expander = gtk.Expander(label=_("_More options..."))
        expander.set_use_underline(True)
        adj = gtk.Alignment(yalign=1.0, xscale=1.0)
        adj.add(expander)
        hb.pack_start(adj)

        # Save button
        self.save = gtk.Button(stock=gtk.STOCK_SAVE)
        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.pack_start(self.save)
        hb.pack_start(bbox, expand=False)
        self.pack_start(hb, expand=False)

        for filt in filters:
            filt.connect_object('preview', gtk.Button.clicked, self.preview)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        vbox = gtk.VBox()

        self.filters = []

        instances = []
        for Kind in plugins:
            try: f = Kind()
            except:
                import traceback
                traceback.print_exc()
                continue
            else: instances.append(f)
        instances.sort()

        for f in instances:
            try: vbox.pack_start(f)
            except:
                import traceback
                traceback.print_exc()
                f.destroy()
            else:
                try: f.connect_object(
                    'preview', gtk.Button.clicked, self.preview)
                except:
                    try: f.connect_object(
                        'changed', self._changed, self.combo.child)
                    except:
                        import traceback
                        traceback.print_exc()
                    else: self.filters.append(f)
                else: self.filters.append(f)

        self.filters.extend(filters)
        self.filters.sort()

        sw.add_with_viewport(vbox)
        self.pack_start(sw, expand=False)

        expander.connect("notify::expanded", self.__notify_expanded, sw)
        expander.set_expanded(False)

        self.show_all()
        # Don't display the expander if there aren't any plugins.
        if len(self.filters) == len(self.FILTERS): expander.hide()
        sw.hide()

    def __notify_expanded(self, expander, event, vbox):
        vbox.set_property('visible', expander.get_property('expanded'))

    def _changed(self, entry):
        self.save.set_sensitive(False)
        self.preview.set_sensitive(bool(entry.get_text()))

