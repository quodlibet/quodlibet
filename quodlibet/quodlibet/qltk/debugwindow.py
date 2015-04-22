# -*- coding: utf-8 -*-
import os
import sys
import time
import traceback
import platform

from gi.repository import Gtk

import quodlibet
from quodlibet import const
from quodlibet import util
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk import get_top_parent, Align
from quodlibet.util.path import unexpand, mkdir
from quodlibet.util import connect_obj
from quodlibet.util import logging

old_hook = sys.excepthook


class MinExceptionDialog(ErrorMessage):
    """A dialog which shows a title, description and an expandable
    error report.

    For example decode(traceback.format_exc()) for displaying details
    about an exception.
    """

    def __init__(self, parent, title, description, traceback):
        super(MinExceptionDialog, self).__init__(
            get_top_parent(parent),
            title, description)

        assert isinstance(title, unicode)
        assert isinstance(description, unicode)
        assert isinstance(traceback, unicode)

        exp = Gtk.Expander(label=_("Error Details"))
        lab = Gtk.Label(label=traceback)
        lab.set_alignment(0.0, 0.0)
        lab.set_selectable(True)
        win = Gtk.ScrolledWindow()
        win.add_with_viewport(Align(lab, border=6))
        win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        win.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        win.set_size_request(500, 150)
        win.show_all()
        exp.add(win)
        exp.set_resize_toplevel(True)

        area = self.get_message_area()
        exp.show()
        area.pack_start(exp, False, True, 0)


class ExceptionDialog(Gtk.Window):
    running = False
    instance = None

    DUMPDIR = os.path.join(quodlibet.get_user_dir(), "dumps")

    @classmethod
    def from_except(Kind, *args):
        mkdir(Kind.DUMPDIR)

        dump = os.path.join(
            Kind.DUMPDIR, time.strftime("Dump_%Y%m%d_%H%M%S.txt"))
        minidump = os.path.join(
            Kind.DUMPDIR, time.strftime("MiniDump_%Y%m%d_%H%M%S.txt"))

        full_args = list(args) + [dump, minidump]
        Kind.__dump(*full_args)
        # Don't get in a recursive exception handler loop.
        if not Kind.running:
            Kind.running = True
            Kind.instance = Kind(*full_args)
        return Kind.instance

    @classmethod
    def excepthook(Kind, *args):
        instance = Kind.from_except(*args)
        instance.show()
        old_hook(*args)

    @classmethod
    def __dump(self, Kind, value, trace, dump, minidump):
        import mutagen

        dumpobj = open(dump, "wb")
        minidumpobj = open(minidump, "wb")

        header = "Quod Libet %s\nMutagen %s\nPython %s %s\nPlatform %s" % (
            const.VERSION, mutagen.version_string, sys.version,
            sys.platform, platform.platform())

        minidump_data = ("=== SYSTEM INFORMATION:\n%s\n\n"
                         "=== STACK TRACE\n%s\n\n") % (
            header, "\n".join(traceback.format_exception(Kind, value, trace)))

        dumpobj.write(minidump_data)
        minidumpobj.write(minidump_data)
        minidumpobj.close()

        dumpobj.write("=== LOG:\n")
        for item in logging.get_content(limit=75):
            dumpobj.write(item.decode("utf-8") + "\n")

        dumpobj.close()

    def __init__(self, Kind, value, traceback, dump, minidump):
        # This is all implemented a bit different than the rest of Quod
        # Libet's windows since I want it to be as stupid as possible, to
        # minimize the chances of something going wrong with the thing
        # that handles things going wrong, i.e. it only uses GTK+ code,
        # no QLTK wrappers.

        Gtk.Window.__init__(self)
        self.set_default_size(400, 400)
        self.set_border_width(12)
        self.set_title(_("Error Occurred"))

        desc = _("An exception has occured in Quod Libet. A dump file has "
            "been saved to <b >%(dump-path)s</b> that will help us debug the "
            "crash. "
            "Please file a new issue at %(new-issue-url)s"
            "and attach this file or include its contents. This "
            "file may contain some identifying information about you or your "
            "system, such as a list of recent files played. If this is "
            "unacceptable, send <b>%(mini-dump-path)s</b> instead with a "
            "description of what "
            "you were doing.") % {
                "dump-path": unexpand(dump),
                "mini-dump-path": unexpand(minidump),
                "new-issue-url":
                    "https://github.com/quodlibet/quodlibet/issues/new",
            }

        suggestion = _("Quod Libet may now be unstable. Closing it and "
            "restarting is recommended. Your library will be saved.")

        label = Gtk.Label(label=desc + "\n\n" + suggestion)

        label.set_selectable(True)
        label.set_use_markup(True)
        label.set_line_wrap(True)
        box = Gtk.VBox(spacing=6)
        buttons = Gtk.HButtonBox()
        view = Gtk.TreeView()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)
        model = Gtk.ListStore(str, str, int)
        self.__fill_list(view, model, value, traceback)
        view.set_model(model)
        cancel = Gtk.Button(stock=Gtk.STOCK_CANCEL)
        close = Gtk.Button(stock=Gtk.STOCK_QUIT)
        buttons.pack_start(close, True, True, 0)
        buttons.pack_start(cancel, True, True, 0)
        box.pack_start(label, False, True, 0)
        box.pack_start(sw, True, True, 0)
        box.pack_start(buttons, False, True, 0)
        self.add(box)

        self.connect('destroy', self.__destroy)
        connect_obj(cancel, 'clicked', Gtk.Window.destroy, self)
        close.connect('clicked', lambda *x: Gtk.main_quit())

        self.get_child().show_all()

        def first_draw(*args):
            filename = unexpand(dump)
            offset = label.get_text().decode("utf-8").find(filename)
            label.select_region(offset, offset + len(filename))
            self.disconnect(self.__draw_id)

        self.__draw_id = self.connect("draw", first_draw)

    def __stack_row_activated(self, view, path, column):
        model = view.get_model()
        filename = model[path][0]
        line = model[path][2]
        util.spawn(["sensible-editor", "+%d" % line, filename])

    def __fill_list(self, view, model, value, trace):
        for frame in reversed(traceback.extract_tb(trace)):
            (filename, line, function, text) = frame
            model.append(row=[filename, function, line])
        view.connect('row-activated', self.__stack_row_activated)

        def cdf(column, cell, model, iter, data):
            cell.set_property("markup", "<b>%s</b> line %d\n\t%s" % (
                util.escape(model[iter][1]), model[iter][2],
                util.escape(unexpand(model[iter][0]))))
        render = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn(str(value).replace("_", "__"), render)
        col.set_cell_data_func(render, cdf)
        col.set_visible(True)
        col.set_expand(True)
        view.append_column(col)

    def __destroy(self, window):
        type(self).running = False
        type(self).instance = None
        window.destroy()
