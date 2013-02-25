import os
import sys
import time
import traceback
import platform

import gtk

from quodlibet import app
from quodlibet import const
from quodlibet import util

old_hook = sys.excepthook

class ExceptionDialog(gtk.Window):
    running = False

    @classmethod
    def excepthook(Kind, *args):
        dump = os.path.join(
            const.USERDIR, time.strftime("Dump_%Y%m%d_%H%M%S.txt"))
        minidump = os.path.join(
            const.USERDIR, time.strftime("MiniDump_%Y%m%d_%H%M%S.txt"))
        full_args = list(args) + [dump, minidump]
        Kind.__dump(*full_args)
        # Don't get in a recursive exception handler loop.
        if not Kind.running:
            Kind.running = True
            Kind(*full_args)
        old_hook(*args)

    @classmethod
    def __dump(self, Kind, value, trace, dump, minidump):
        import mutagen
        from quodlibet.util import logging
        dumpobj = file(dump, "w")
        minidumpobj = file(minidump, "w")
        header = "Quod Libet %s\nMutagen %s\nPython %s %s\nPlatform %s" %(
            const.VERSION, mutagen.version_string, sys.version,
            sys.platform, platform.platform())

        minidump_data = ("=== SYSTEM INFORMATION:\n%s\n\n"
                         "=== STACK TRACE\n%s\n\n") % (
            header, "\n".join(traceback.format_exception(Kind, value, trace)))

        print >>dumpobj, minidump_data
        print >>minidumpobj, minidump_data

        minidumpobj.close()

        for logname in logging.names():
            print >>dumpobj, "=== LOG: %r\n%s\n\n" %(
                logname, "\n".join(logging.contents(logname)[-50:]))

        dumpobj.close()

    def __init__(self, Kind, value, traceback, dump, minidump):
        self.__create_window(Kind, value, traceback, dump, minidump)

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
        def cdf(column, cell, model, iter):
            cell.set_property("markup", "<b>%s</b> line %d\n\t%s" % (
                util.escape(model[iter][1]), model[iter][2],
                util.escape(util.unexpand(model[iter][0]))))
        render = gtk.CellRendererText()
        col = gtk.TreeViewColumn(str(value).replace("_", "__"), render)
        col.set_cell_data_func(render, cdf)
        col.set_visible(True)
        col.set_expand(True)
        view.append_column(col)

    # This is all implemented a bit different than the rest of Quod
    # Libet's windows since I want it to be as stupid as possible, to
    # minimize the chances of something going wrong with the thing
    # that handles things going wrong, i.e. it only uses GTK+ code,
    # no QLTK wrappers.
    def __create_window(self, Kind, value, traceback, dump, minidump):
        window = gtk.Window()
        window.set_default_size(400, 400)
        window.set_border_width(12)
        window.set_title(_("Error Occurred"))

        label = gtk.Label(_("""\
An exception has occured in Quod Libet. A dump file has been saved to <b>%s</b> that will help us debug the crash. Please file a new issue at http://code.google.com/p/quodlibet/issues/list and attach this file or include its contents. This file may contain some identifying information about you or your system, such as a list of recent files played. If this is unacceptable, send <b>%s</b> instead with a description of what you were doing.

Quod Libet may now be unstable. Closing it and restarting is recommended. Your library will be saved.""")
                          % (util.unexpand(dump), util.unexpand(minidump)))
        label.set_selectable(True)
        label.set_use_markup(True)
        label.set_line_wrap(True)
        box = gtk.VBox(spacing=6)
        buttons = gtk.HButtonBox()
        view = gtk.TreeView()
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        model = gtk.ListStore(str, str, int)
        self.__fill_list(view, model, value, traceback)
        view.set_model(model)
        cancel = gtk.Button(stock=gtk.STOCK_CANCEL)
        close = gtk.Button(stock=gtk.STOCK_QUIT)
        buttons.pack_start(close)
        buttons.pack_start(cancel)
        box.pack_start(label, expand=False)
        box.pack_start(sw)
        box.pack_start(buttons, expand=False)
        window.add(box)

        window.connect('destroy', self.__destroy)
        cancel.connect_object('clicked', gtk.Window.destroy, window)
        close.connect('clicked', lambda *x: app.quit())

        window.show_all()
        filename = util.unexpand(dump)
        offset = label.get_text().decode("utf-8").find(filename)
        label.select_region(offset, offset + len(filename))
        return window

    def __destroy(self, window):
        type(self).running = False
        window.destroy()
