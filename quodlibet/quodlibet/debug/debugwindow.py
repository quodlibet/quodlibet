import os
import sys
import time
import traceback

import gtk

from quodlibet import const
from quodlibet import util

class ExceptionDialog(gtk.Window):
    running = False
    old_hook = sys.excepthook

    @classmethod
    def excepthook(Kind, *args):
        seconds = int(time.time())
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
        Kind.old_hook(*args)

    @classmethod
    def __dump(self, Kind, value, trace, dump, minidump):
        import mutagen
        from quodlibet.util import logging
        dumpobj = file(dump, "w")
        minidumpobj = file(minidump, "w")
        header = "Quod Libet %s\nMutagen %s\nPython %s %s" %(
            const.VERSION, mutagen.version_string, sys.version,
            sys.platform)

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
        window = self.__create_window(Kind, value, traceback, dump, minidump)
        window.show_all()

    def __stack_row_activated(self, view, path, column):
        from quodlibet import util
        model = view.get_model()
        filename = model[path][0]
        line = model[path][2]
        util.spawn(["sensible-editor", "+%d" % line, filename])

    def __fill_list(self, view, model, value, trace):
        from quodlibet import util
        for frame in reversed(traceback.extract_tb(trace)):
            (filename, line, function, text) = frame
            model.append(row=[filename, function, line])
        view.connect('row-activated', self.__stack_row_activated)
        def cdf(column, cell, model, iter):
            cell.set_property("markup", "<b>%s</b> line %d\n\t%s" % (
                model[iter][1], model[iter][2],
                util.unexpand(util.escape(model[iter][0]))))
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
An exception has occured in Quod Libet. A dump file has been saved to <b>%s</b> that will help us debug the crash. Please email it to quodlibet.crash@gmail.com. This file may contain some identifying information about your system, such as a list of recent files played. If this is unacceptable, send <b>%s</b> instead with a description of what you were doing.

Quod Libet may now be unstable. Closing it and restarting is recommended. Your library will be saved.""")
                          % (util.unexpand(dump), util.unexpand(minidump)))
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
        close.connect('clicked', gtk.main_quit)

        return window

    def __destroy(self, window):
        type(self).running = False
        window.destroy()
