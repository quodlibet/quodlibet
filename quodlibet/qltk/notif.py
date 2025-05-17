# Copyright 2010 Steven Robertson
#      2020-2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
This module will provide a unified notification area for informational
messages and active tasks. This will eventually handle interactions with
active tasks (e.g. pausing a copooled task), and provide shortcuts for
copooling or threading a task with a status notification. It will also provide
the UI for the planned global undo feature.

Of course, right now it does none of these things.
"""

# This module is still experimental and may change or be removed.

# TODO: Make copooling things with notifications easier (optional)
# TODO: Make Ex Falso use this
# TODO: Port WaitLoadWindow to use this (and not block)
# TODO: Port Media browser to use this
# TODO: Port Download Manager to use this
# TODO: Add basic notification support
# TODO: Add notification history
# TODO: Add notification button/callback support (prereq for global undo)
# TODO: Optimize performance (deferred signals, etc)

from gi.repository import Gtk, GLib, Pango

from quodlibet import _, util
from quodlibet.util import copool
from quodlibet.qltk.x import SmallImageToggleButton, SmallImageButton, Align
from quodlibet.qltk import Icons, add_css


class ParentProperty:
    """
    A property which provides a thin layer of protection against accidental
    reparenting: you must first 'unparent' an instance by setting this
    property to 'None' before you can set a new parent.
    """

    def __get__(self, inst, owner):
        return getattr(inst, "_parent", None)

    def __set__(self, inst, value):
        if getattr(inst, "_parent", None) is not None and value is not None:
            raise ValueError(
                "Cannot set parent property without first setting it to 'None'."
            )
        inst._parent = value


class Task:
    def __init__(
        self, source, desc, known_length=True, controller=None, pause=None, stop=None
    ):
        self.source = source
        self.desc = desc
        if known_length:
            self.frac = 0.0
        else:
            self.frac = None
        if controller:
            self.controller = controller
        else:
            self.controller = TaskController.default_instance
        self._pause = pause
        self._stop = stop
        self.pausable = bool(pause)
        self.stoppable = bool(stop)
        self._paused = False
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

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, value):
        if self.pausable:
            self._pause(value)
            self._paused = value

    def stop(self):
        if self._stop:
            self._stop()
        self.finish()

    def gen(self, gen):
        """
        Act as a generator pass-through, updating and finishing the task's
        progress automatically. If 'gen' has a __len__ property, it will be
        used to set the fraction accordingly.
        """
        try:
            if hasattr(gen, "__len__"):
                for i, x in enumerate(gen):
                    self.update(float(i) / len(gen))
                    yield x
            else:
                for x in gen:
                    yield x
        finally:
            self.finish()

    def list(self, l):
        """
        Evaluates the iterable argument before passing to 'gen'.
        """
        return self.gen(list(l))

    def copool(self, funcid, pause=True, stop=True):
        """
        Convenience function: set the Task's 'pause' and 'stop' callbacks to
        act upon the copool with the given funcid.
        """
        if pause:

            def pause_func(state):
                if state != self._paused:
                    if state:
                        copool.pause(funcid)
                    else:
                        copool.resume(funcid)

            self._pause = pause_func
            self.pausable = True
        if stop:
            self._stop = lambda: copool.remove(funcid)
            self.stoppable = True

    # Support context managers:
    # >>> with Task(...) as t:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False


class TaskController:
    """
    Controller logic for displaying and managing a list of Tasks. Also
    implements the full Task interface to act as a pass-through or summary of
    all tasks in flight on this controller.
    """

    parent = ParentProperty()
    default_instance: "TaskController"

    def __init__(self):
        self.active_tasks = []
        self._parent = None
        self.update()

    def add_task(self, task):
        self.active_tasks.append(task)
        self.update()

    @property
    def source(self):
        if len(self.active_tasks) == 1:
            return self.active_tasks[0].source
        return _("Active tasks")

    @property
    def desc(self):
        if len(self.active_tasks) == 1:
            return self.active_tasks[0].desc
        return _("%d tasks running") % len(self.active_tasks)

    @property
    def frac(self):
        fracs = [t.frac for t in self.active_tasks if t.frac is not None]
        if fracs:
            return sum(fracs) / len(self.active_tasks)
        return None

    @property
    def paused(self):
        pausable = [t for t in self.active_tasks if t.pausable]
        if not pausable:
            return False
        return not [t for t in pausable if not t.paused]

    @paused.setter
    def paused(self, val):
        for t in self.active_tasks:
            if t.pausable:
                t.paused = val

    def stop(self):
        [t.stop() for t in self.active_tasks if t.stoppable]

    @property
    def pausable(self):
        return [t for t in self.active_tasks if t.pausable]

    @property
    def stoppable(self):
        return [t for t in self.active_tasks if t.stoppable]

    def update(self):
        if self._parent is not None:
            self._parent.update()

    def finish(self, finished_task):
        self.active_tasks = [t for t in self.active_tasks if t is not finished_task]
        self.update()


# Oh so deliciously hacky.
TaskController.default_instance = TaskController()


class TaskWidget(Gtk.HBox):
    """
    Displays a task.
    """

    def __init__(self, task):
        super().__init__(spacing=3)
        self.task = task
        self.label = Gtk.Label()
        self.label.set_alignment(1.0, 0.5)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.pack_start(self.label, True, False, 3)
        self.progress = Gtk.ProgressBar()
        self.progress.set_size_request(200, 12)
        add_css(self.progress, "progress, trough { min-height: 12px }")
        vb = Gtk.VBox(valign=Gtk.Align.CENTER)
        vb.pack_start(self.progress, True, True, 0)
        self.pack_start(vb, True, True, 3)
        self.pause = SmallImageToggleButton()
        self.pause.add(
            Gtk.Image.new_from_icon_name(Icons.MEDIA_PLAYBACK_PAUSE, Gtk.IconSize.MENU)
        )
        self.pause.connect("toggled", self.__pause_toggled)
        self.pack_start(self.pause, False, True, 3)
        self.stop = SmallImageButton()
        self.stop.add(
            Gtk.Image.new_from_icon_name(Icons.MEDIA_PLAYBACK_STOP, Gtk.IconSize.MENU)
        )
        self.stop.connect("clicked", self.__stop_clicked)
        self.pack_start(self.stop, False, True, 0)

    def __pause_toggled(self, btn):
        if self.task.pausable:
            self.task.paused = btn.props.active

    def __stop_clicked(self, btn):
        if self.task.stoppable:
            self.task.stop()

    def update(self):
        formatted_label = f"{util.bold(self.task.source)} – {self.task.desc}"
        self.label.set_markup(formatted_label)
        if self.task.frac is not None:
            self.progress.set_fraction(self.task.frac)
        else:
            self.progress.pulse()
        if self.pause.props.sensitive != self.task.pausable:
            self.pause.props.sensitive = self.task.pausable
        show_as_active = self.task.pausable and self.task.paused
        if self.pause.props.active != show_as_active:
            self.pause.props.active = show_as_active
        if self.stop.props.sensitive != self.task.stoppable:
            self.stop.props.sensitive = self.task.stoppable


class StatusBar(Gtk.HBox):
    def __init__(self, task_controller):
        super().__init__()
        self.__dirty = False
        self.set_spacing(12)
        self.task_controller = task_controller
        self.task_controller.parent = self

        self.default_label = Gtk.Label(selectable=True)
        self.default_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.pack_start(Align(self.default_label, halign=Gtk.Align.END), True, True, 0)
        self.task_widget = TaskWidget(task_controller)
        self.pack_start(self.task_widget, False, False, 0)

        self.show_all()
        self.set_no_show_all(True)
        self.__set_shown("default")
        self.connect("destroy", self.__destroy)

    def __destroy(self, *args):
        self.task_controller.parent = None

    def __set_shown(self, type):
        if type == "default":
            self.default_label.show()
        else:
            self.default_label.hide()
        if type == "task":
            self.task_widget.show()
        else:
            self.task_widget.hide()

    def set_default_text(self, text):
        self.default_label.set_text(text)

    def __update(self):
        self.__dirty = False
        if self.task_controller.active_tasks:
            self.__set_shown("task")
            self.task_widget.update()
        else:
            self.__set_shown("default")

    def update(self):
        if not self.__dirty:
            self.__dirty = True
            GLib.idle_add(self.__update)
