# -*- coding: utf-8 -*-
# Copyright 2010 Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""
This module will provide a unified notification area for informational
messages and active tasks. This will eventually handle interactions with
active tasks (e.g. pausing a copooled task), and provide shortcuts for
copooling or threading a task with a status notification. It will also provide
the UI for the planned global undo feature.

Of course, right now it does none of these things.
"""

# This module is still experimental and may change or be removed.

# TODO: Add pause and cancel buttons to tasks
# TODO: Make copooling things with notifications easier (optional)
# TODO: Make Ex Falso use this
# TODO: Port WaitLoadWindow to use this (and not block)
# TODO: Port Media browser to use this
# TODO: Port Download Manager to use this
# TODO: Add basic notification support
# TODO: Add notification history
# TODO: Add notification button/callback support (prereq for global undo)
# TODO: Optimize performance (deferred signals, etc)

import gtk
import pango
import traceback

class ParentProperty(object):
    """
    A property which provides a thin layer of protection against accidental
    reparenting: you must first 'unparent' an instance by setting this
    property to 'None' before you can set a new parent.
    """
    def __get__(self, inst, owner):
        return getattr(inst, '_parent', None)
    def __set__(self, inst, value):
        if getattr(inst, '_parent', None) is not None and value is not None:
            raise ValueError("Cannot set parent property without first "
                    "setting it to 'None'.")
        inst._parent = value

class Task(object):
    def __init__(self, source, desc, known_length=True, controller=None):
        self.source = source
        self.desc = desc
        if known_length:
            self.frac = 0.
        else:
            self.frac = None
        if controller:
            self.controller = controller
        else:
            self.controller = TaskController.default_instance
        self.controller.add_task(self)

    def update(self, frac):
        """
        Update a task's progress.
        """
        self.frac = frac
        self.controller.update()

    def pulse(self):
        """
        Indicate progress on a task of unknown length.
        """
        self.update(None)

    def finish(self):
        """
        Mark a task as finished, and remove it from the list of active tasks.
        """
        self.frac = 1.0
        self.controller.finish(self)

    def gen(self, gen):
        """
        Act as a generator pass-through, updating and finishing the task's
        progress automatically. If 'gen' has a __len__ property, it will be
        used to set the fraction accordingly.
        """
        if hasattr(gen, '__len__'):
            for i, x in enumerate(gen):
                self.update(float(i)/len(gen))
                yield x
        else:
            for x in gen:
                yield x
        self.finish()

    def list(self, l):
        """
        Evaluates the iterable argument before passing to 'gen'.
        """
        return self.gen(list(l))

    # Support context managers:
    # >>> with Task(...) as t:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False

class TaskController(object):
    """
    Controller logic for displaying tasks.
    """
    parent = ParentProperty()
    default_instance = None

    def __init__(self):
        self.active_tasks = []
        self._parent = None
        self.update()

    def add_task(self, task):
        self.active_tasks.append(task)
        self.update()

    def update(self):
        if len(self.active_tasks) == 0:
            self.source = ""
            self.desc = ""
            self.frac = 1.
        elif len(self.active_tasks) == 1:
            self.source = self.active_tasks[0].source
            self.desc = self.active_tasks[0].desc
            self.frac = self.active_tasks[0].frac
        else:
            self.source = _("Active tasks")
            self.desc = _("%d tasks running") % len(self.active_tasks)
            fracs = [t.frac for t in self.active_tasks if t.frac is not None]
            if fracs:
                self.frac = sum(fracs) / len(self.active_tasks)
            else:
                self.frac = None
        if self._parent is not None:
            self._parent.update()

    def finish(self, finished_task):
        self.active_tasks = filter(lambda t: t is not finished_task,
                                   self.active_tasks)
        self.update()

# Oh so deliciously hacky.
TaskController.default_instance = TaskController()

class TaskWidget(gtk.HBox):
    """
    Displays a task.
    """
    def __init__(self):
        super(TaskWidget, self).__init__()
        self.set_spacing(12)
        self.label = gtk.Label()
        self.label.set_alignment(1.0, 0.5)
        self.label.set_ellipsize(pango.ELLIPSIZE_END)
        self.pack_start(self.label)
        self.progress = gtk.ProgressBar()
        self.progress.set_size_request(200, -1)
        self.pack_start(self.progress, expand=False)
        self.pause = gtk.Button()


    # The lack of a mapping between a Task and a TaskWidget is intentional;
    # this allows Tasks to be tossed about without any concern for GLib
    # behaviors. Same goes for Notifications, when they get done.
    def update(self, task):
        formatted_label = "<b>%s</b>\n%s" % (task.source, task.desc)
        self.label.set_markup(formatted_label)
        if task.frac is not None:
            self.progress.set_fraction(task.frac)
        else:
            self.progress.pulse()

class StatusBar(gtk.HBox):

    default_instance = None

    def __init__(self, task_controller):
        super(StatusBar, self).__init__()
        self.set_spacing(12)
        self.task_controller = task_controller
        self.task_controller.parent = self

        self.default_label = gtk.Label()
        self.default_label.set_alignment(1.0, 0.5)
        self.default_label.set_text(_("No time information"))
        self.pack_start(self.default_label)
        self.task_widget = TaskWidget()
        self.pack_start(self.task_widget)
        # The history button will eventually hold the full list of running
        # tasks, as well as the list of previous notifications.
        #self.history_btn = gtk.Button(stock=gtk.STOCK_MISSING_IMAGE)
        #self.pack_start(self.history_btn, expand=False)

        self.show_all()
        self.set_no_show_all(True)
        self.__set_shown('default')

    def __set_shown(self, type):
        if type == 'default':   self.default_label.show()
        else:                   self.default_label.hide()
        if type == 'task':      self.task_widget.show()
        else:                   self.task_widget.hide()

    def set_default_text(self, text):
        self.default_label.set_text(text)

    def update(self):
        if self.task_controller.active_tasks:
            self.__set_shown('task')
            self.task_widget.update(self.task_controller)
        else:
            self.__set_shown('default')

