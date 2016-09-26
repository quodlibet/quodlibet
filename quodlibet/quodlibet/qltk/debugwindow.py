# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import time
import platform

import mutagen
from gi.repository import Gtk
from senf import fsn2text

import quodlibet
from quodlibet import _
from quodlibet import util
from quodlibet import qltk
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk import Icons
from quodlibet.qltk import get_top_parent, Align
from quodlibet.util.path import unexpand, mkdir
from quodlibet.util import connect_obj
from quodlibet.util import logging, gdecode
from quodlibet.util.dprint import format_exception, extract_tb
from quodlibet.compat import text_type


class MinExceptionDialog(ErrorMessage):
    """A dialog which shows a title, description and an expandable
    error report.

    For example format_exc() for displaying details
    about an exception.
    """

    def __init__(self, parent, title, description, traceback):
        super(MinExceptionDialog, self).__init__(
            get_top_parent(parent),
            title, description)

        assert isinstance(title, text_type)
        assert isinstance(description, text_type)
        assert isinstance(traceback, text_type)

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


def excepthook(type_, value, traceback):
    """Custom exception hook which displays a ExceptionDialog window"""

    instance = ExceptionDialog.from_except(type_, value, traceback)
    if instance:
        instance.show()
        instance.dump_to_disk(type_, value, traceback)
    return sys.__excepthook__(type_, value, traceback)


def format_dump_header(type_, value, traceback):
    """Returns system information and the traceback as`text_type`"""

    lines = [
        u"=== SYSTEM INFORMATION:"
        u"",
        u"Quod Libet %s" % quodlibet.get_build_description(),
        u"Mutagen %s" % mutagen.version_string,
        u"Python %s %s" % (sys.version, sys.platform),
        u"Platform %s" % platform.platform(),
        u"=== STACK TRACE",
        u"",
    ]

    lines.extend(format_exception(type_, value, traceback))
    lines.append(u"")
    return os.linesep.join(lines)


def format_dump_log(limit=75):
    """Returns recent log entries as `text_type`"""

    dump = [u"=== LOG:"]
    dump.extend(logging.get_content(limit=limit))
    return os.linesep.join(dump)


class ExceptionDialog(Gtk.Window):
    """The windows which is shown if an unhandled exception occurred"""

    _running = False
    _instance = None

    DUMPDIR = os.path.join(quodlibet.get_user_dir(), "dumps")

    @classmethod
    def from_except(cls, type_, value, traceback):
        """Returns an instance or None."""

        # Don't get in a recursive exception handler loop.
        if not cls._running:
            cls._running = True
            cls._instance = cls(type_, value, traceback)
            return cls._instance

    @property
    def dump_path(self):
        return os.path.join(
            self.DUMPDIR,
            time.strftime("Dump_%Y%m%d_%H%M%S.txt", self._time))

    @property
    def minidump_path(self):
        return os.path.join(
            self.DUMPDIR,
            time.strftime("MiniDump_%Y%m%d_%H%M%S.txt", self._time))

    def dump_to_disk(self, type_, value, traceback):
        """Writes the dump files to DUMDIR"""

        mkdir(self.DUMPDIR)

        header = format_dump_header(type_, value, traceback).encode("utf-8")
        log = format_dump_log().encode("utf-8")

        print(self.dump_path)
        with open(self.dump_path, "wb") as dump:
            with open(self.minidump_path, "wb") as minidump:
                minidump.write(header)
                dump.write(header)
            dump.write(log)

    def __init__(self, type_, value, traceback):
        # This is all implemented a bit different than the rest of Quod
        # Libet's windows since I want it to be as stupid as possible, to
        # minimize the chances of something going wrong with the thing
        # that handles things going wrong, i.e. it only uses GTK+ code,
        # no QLTK wrappers.

        self._time = time.localtime()

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
                "dump-path": unexpand(self.dump_path),
                "mini-dump-path": unexpand(self.minidump_path),
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
        model = Gtk.ListStore(object, object, object)
        self.__fill_list(view, model, value, traceback)
        view.set_model(model)
        cancel = qltk.Button(_("_Cancel"))
        close = qltk.Button(_("_Quit"), Icons.APPLICATION_EXIT)
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
            filename = unexpand(self.dump_path)
            offset = gdecode(label.get_text()).find(filename)
            label.select_region(offset, offset + len(filename))
            self.disconnect(self.__draw_id)

        self.__draw_id = self.connect("draw", first_draw)

    def __stack_row_activated(self, view, path, column):
        model = view.get_model()
        filename = model[path][0]
        line = model[path][2]
        util.spawn(["sensible-editor", "+%d" % line, filename])

    def __fill_list(self, view, model, value, trace):
        for frame in reversed(extract_tb(trace)):
            (filename, line, function, text) = frame
            model.append(row=[filename, function, line])
        view.connect('row-activated', self.__stack_row_activated)

        def cdf(column, cell, model, iter, data):
            row = model[iter]
            filename = fsn2text(unexpand(row[0]))
            function = row[1]
            line = row[2]
            cell.set_property(
                "markup", "<b>%s</b> line %d\n\t%s" % (
                    util.escape(function), line, util.escape(filename)))

        render = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn(text_type(value).replace("_", "__"), render)
        col.set_cell_data_func(render, cdf)
        col.set_visible(True)
        col.set_expand(True)
        view.append_column(col)

    def __destroy(self, window):
        type(self)._running = False
        type(self).instance = None
        window.destroy()
