#! /usr/bin/env python
#
#    Copyright (C) 2005  Michael Urman
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of version 2 of the GNU General Public License as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import gtk, gobject, os, sys
__all__ = []

class Subprocess(gobject.GObject):

    SIG_INT = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (int,))
    SIG_INTSTR = (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (int, str))

    __gsignals__ = {
        'output-line': SIG_INTSTR,
        'output-chunk': SIG_INTSTR,
        'output-eof': SIG_INT,
    }

    __gproperties__ = {
        'newlines': (str, 'line splitters',
                'these characters also case a line to be reported',
                '\n', gobject.PARAM_READWRITE),

        'process': (object, 'process', 'process name and arguments',
                gobject.PARAM_READABLE),

        'cmdname': (str, 'cmdname', 'command when name is overriden',
                '', gobject.PARAM_READABLE),

        'stdin' : (int, 'stdin', "child's stdin file descriptor",
                -1, 0x7fffffff, -1, gobject.PARAM_READABLE),

        'stdout' : (int, 'stdout', "child's stdout file descriptor",
                -1, 0x7fffffff, -1, gobject.PARAM_READABLE),

        'stderr' : (int, 'stderr', "child's stderr file descriptor",
                -1, 0x7fffffff, -1, gobject.PARAM_READABLE),
    }

    def __init__(self, process=[], cmd='', newlines='\n', stdin=None):
        gobject.GObject.__init__(self)
        self.newlines = newlines
        self.process = process
        self.cmdname = cmd or process[0]
        self.__buf = {}
        if stdin is not None:
            raise NotImplementedError, "Overriding stdin is not implemented"

    def start(self):
        from popen2 import Popen3
        self.__child = Popen3(self.process, capturestderr=True)

        self.__out_id = gobject.io_add_watch(self.stdout,
                gobject.IO_IN|gobject.IO_ERR|gobject.IO_HUP|gobject.IO_NVAL,
                self.__on_output)
        self.__err_id = gobject.io_add_watch(self.stderr,
                gobject.IO_IN|gobject.IO_ERR|gobject.IO_HUP|gobject.IO_NVAL,
                self.__on_output)

    stdin = property(lambda s: s.__child.tochild.fileno(),
            doc='child stdin fd')
    stdout = property(lambda s: s.__child.fromchild.fileno(),
            doc='child stdout fd')
    stderr = property(lambda s: s.__child.childerr.fileno(),
            doc='child stderr fd')
    pid = property(lambda s: s.__child.pid, doc='child pid')

    def poll(self):
        """Return the exit status of the child process, or -1 if unfinished."""
        return self.__child.poll()

    def wait(self):
        """Wait for and return the exit status of the child process."""
        return self.__child.wait()

    def do_get_property(self, property):
        if property.name in self.__gproperties__:
            return getattr(self, property.name)
        else:
            raise AttributeError, 'unknown property %s' % property.name

    def do_set_property(self, property, value):
        if property.name in self.__gproperties__:
            return setattr(self, property.name, value)
        else:
            raise AttributeError, 'unknown property %s' % property.name

    def output_chunk(self, fd, chunk):
        gobject.idle_add(self.emit, 'output-chunk', fd, chunk)
    def output_line(self, fd, line):
        gobject.idle_add(self.emit, 'output-line', fd, line)
    def output_eof(self, fd):
        gobject.idle_add(self.emit, 'output-eof', fd)

    def __on_output(self, fd, cond):
        if cond & gobject.IO_IN == gobject.IO_IN:
            read = os.read(fd, 1024)
            if read != '':
               self.output_chunk(fd, read)
            output = self.__buf.setdefault(fd, '') + read

            lines = [output]
            for splitter in self.newlines:
                lines = sum([line.split(splitter) for line in lines], [])
            self.__buf[fd] = lines.pop()

            for line in lines:
                self.output_line(fd, line)
            if read == '':
                self.output_line(fd, self.__buf.pop(fd))
                self.output_eof(fd)
                return False
            return True

        elif cond & (gobject.IO_ERR|gobject.IO_HUP|gobject.IO_NVAL):
            self.output_eof(fd)
            return False
