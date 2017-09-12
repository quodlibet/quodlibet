# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#           2017 Fredrik Strupe, Pete Beardmore
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import config
from . import add_css, gtk_version


class Paned(Gtk.Paned):

    def __init__(self, *args, **kwargs):
        super(Paned, self).__init__(*args, **kwargs)
        self.ensure_wide_handle()
        self.root = self

    def ensure_wide_handle(self):
        if gtk_version >= (3, 19):
            self.props.wide_handle = True
            add_css(self, """
                paned separator {
                    border-width: 0;
                    min-height: 5px;
                    min-width: 5px;
                    background-image: none;
                }
            """)
            return

        if hasattr(self.props, "wide_handle"):
            # gtk 3.16
            self.props.wide_handle = True
            add_css(self, """
                GtkPaned {
                    border-width: 0;
                    background: none;
                }
            """)
            return

        # gtk 3.14
        add_css(self, """
            GtkPaned {
                -GtkPaned-handle-size: 6;
                background-image: none;
                margin: 0;
                border-width: 0;
            }
        """)


class RPaned(Paned):
    """A Paned that supports relative (percentage) width/height setting."""

    ORIENTATION = None

    def __init__(self, *args, **kwargs):
        if self.ORIENTATION is not None:
            kwargs["orientation"] = self.ORIENTATION
        super(RPaned, self).__init__(*args, **kwargs)
        # before first alloc: save value in relative and set on the first alloc
        # after the first alloc: use the normal properties
        self.__alloced = False
        self.__relative = None

    def _get_max(self):
        alloc = self.get_allocation()
        if self.get_orientation() == Gtk.Orientation.HORIZONTAL:
            return alloc.width
        else:
            return alloc.height

    def set_relative(self, v):
        """Set the relative position of the separator, [0..1]."""

        if v < 0 or v > 1:
            raise ValueError("v must be in [0..1]")

        if self.__alloced:
            max_pos = self._get_max()
            self.set_position(int(round(v * max_pos)))
        else:
            self.__relative = v

    def get_relative(self):
        """Return the relative position of the separator, [0..1]."""

        if self.__alloced:
            rel = float(self.get_position()) / self._get_max()
            if 0 <= rel <= 1:
                return rel

        if self.__relative is not None:
            return self.__relative

        # before first alloc and set_relative not called
        return 0.5

    def do_size_allocate(self, *args):
        ret = Gtk.HPaned.do_size_allocate(self, *args)
        if not self.__alloced and self.__relative is not None:
            self.__alloced = True
            self.set_relative(self.__relative)
            # call again so the children get alloced
            ret = Gtk.HPaned.do_size_allocate(self, *args)
        self.__alloced = True
        return ret


class RHPaned(RPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class RVPaned(RPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL


class XPaned(Paned):
    """A Paned with addition support for expander widget children."""

    ORIENTATION = None

    def __init__(self, *args, **kwargs):
        if self.ORIENTATION is not None:
            kwargs["orientation"] = self.ORIENTATION
        super(XPaned, self).__init__(*args, **kwargs)

        self.connect('button-release-event', self.__button_release)
        self.connect('check_resize', self.__check_resize)

        self.__disablenotify_id = None
        self.__disablenotify_id2 = None

        self.__panelocks = []
        self.__updating = False
        self.__resizing = False

    def __button_release(self, *data):
        for w in self.__panelocks:
            alloc = w.get_size_request()
            size = 0
            if self.ORIENTATION == Gtk.Orientation.VERTICAL:
                size = alloc[1]
                w.set_size_request(-1, size)
            else:
                size = alloc[0]
                w.set_size_request(size, -1)
#            print_d("%r | resetting locked size %d" % (w.id, size))
        del self.__panelocks
        self.__panelocks = []

    def panelocks(self, widget, has=True):
        widgets = []
        if isinstance(widget.get_child1(), XPaned):
            children = self.panelocks(widget.get_child1(), has)
            if children:
                widgets.extend(children)
        elif widget.get_child1() and \
                 hasattr(widget.get_child1(), "panelock") == has:
            widgets.append(widget.get_child1())
        if isinstance(widget.get_child2(), XPaned):
            children = self.panelocks(widget.get_child2(), has)
            if children:
                widgets.extend(children)
        elif widget.get_child2() and \
                 hasattr(widget.get_child2(), "panelock") == has:
            widgets.append(widget.get_child2())
        return widgets

    def update(self, widget):
        """Pass the widget whose pane needs updating."""

        self.__updating = True

        if not isinstance(widget, Gtk.Expander):
            return

        # lock other non-expander or expanded widgets
        widgets = self.panelocks(self.root)
        for w in widgets:
            if w is widget:
                # ignore as this is the widget we're targetting to update!
                continue
            if isinstance(w, Gtk.Expander) and not w.get_expanded():
                # ignore collapsed expanders
                continue

            # widget already changed. use stored if available
            size = w.panelock.size
#            print_d("%r | setting size request: %d" % (w.id, size))
            if self.ORIENTATION == Gtk.Orientation.VERTICAL:
                w.set_size_request(-1, size)
            else:
                w.set_size_request(size, -1)

        expanded = widget.get_expanded()

        # set up parent pane(s) position-set
        parent = self
        while parent:
            if isinstance(parent, Gtk.Paned):
                parent.props.position_set = expanded
            parent = parent.get_parent()

        if expanded:
            # widget size changed. use stored if available
            size = 0
            try:
                size = widget.panelock.size
            except:
                req = widget.get_requisition()
                size = req.height if \
                           self.ORIENTATION == Gtk.Orientation.VERTICAL\
                           else req.width
#            print_d("%r | restoring size: %d" % (widget.id, size))
            if self.ORIENTATION == Gtk.Orientation.VERTICAL:
                widget.set_size_request(-1, size)
            else:
                widget.set_size_request(size, -1)
        else:
            # ensure parent pane(s) are not using position-set
            parent = self
            while parent:
                if isinstance(parent, Gtk.Paned):
                    parent.props.position_set = False
                parent = parent.get_parent()

            title_size = widget.style_get_property('expander-size') +\
                         widget.style_get_property('expander-spacing')
            if widget.get_label_widget():
                alloc = widget.get_label_widget().get_allocation()
                if self.ORIENTATION == Gtk.Orientation.VERTICAL:
                    title_size = max(title_size, alloc.height)
                else:
                    title_size = max(title_size, alloc.width)
            if self.ORIENTATION == Gtk.Orientation.VERTICAL:
                widget.set_size_request(-1, title_size + 5)
            else:
                widget.set_size_request(title_size + 5, -1)

        p = widget
        while p is not self.root:
            p = p.get_parent()
            p.check_resize()

        self.__updating = False

    def do_size_allocate(self, *args):
        # clear size requests to allow shrinking
        Gtk.HPaned.do_size_allocate(self, *args)

        if self.__updating:
            return

        if not self.__panelocks:
            widgets = self.panelocks(self.root)
            for w in widgets:
                if isinstance(w, Gtk.Expander) and not w.get_expanded():
                    continue
#                print_d("%r | adding to panelocks, size: %d"
#                        % (w.id, w.panelock.size))
                self.__panelocks.append(w)
#                print_d("%r | setting parent pane(s) to respect "
#                        "handle position" % w.id)
                parent = self
                while parent:
                    if isinstance(parent, Gtk.Paned):
                        parent.props.position_set = True
                    parent = parent.get_parent()

#                print_d("%r | clearing size request" % w.id)
                w.set_size_request(-1, -1)

    def __check_resize(self, data, *args):

        if self.__resizing:
            return

        def handle_cb(pane, param, widget):
            if isinstance(widget, Gtk.Expander):
                title_size = widget.style_get_property('expander-size') +\
                             widget.style_get_property('expander-spacing')
                if widget.get_label_widget():
                    alloc = widget.get_label_widget().get_allocation()
                    if pane.ORIENTATION == Gtk.Orientation.VERTICAL:
                        title_size = max(title_size, alloc.height)
                    else:
                        title_size = max(title_size, alloc.width)

                if widget is pane.get_child1():
                    pane.set_position(title_size + 5)
                else:
                    alloc = pane.get_allocation()
                    if pane.ORIENTATION == Gtk.Orientation.VERTICAL:
                        pane.set_position(alloc.height - title_size - 5)
                    else:
                        pane.set_position(alloc.width - title_size - 5)
            return True

        # resize for collapsed children
        for w in self.get_children():
            if isinstance(w, Gtk.Expander) and not w.get_expanded():
                # refresh expandable
                self.__resizing = True
                expandables = self.panelocks(self.root, False)
                for w2 in expandables:
                    if w2.get_parent() is not self:
                        w2.get_parent().check_resize()
                self.__resizing = False
                break

        # handle position lock(s)
        widget = self.get_child1()
        if isinstance(widget, Gtk.Expander):
            if widget.get_expanded():
                # remove lock
                if self.__disablenotify_id:
                    if self.handler_is_connected(self.__disablenotify_id):
                        self.handler_disconnect(self.__disablenotify_id)
                    self.__disablenotify_id = None
            else:
                # add lock
                if self.__disablenotify_id:
                    if self.handler_is_connected(self.__disablenotify_id):
                        return
                self.__disablenotify_id = \
                    self.connect("notify", handle_cb, widget)

        widget = self.get_child2()
        if isinstance(widget, Gtk.Expander):
            if widget.get_expanded() or \
                (self.__disablenotify_id and
                 self.handler_is_connected(self.__disablenotify_id)):
                # remove lock
                if self.__disablenotify_id2:
                    if self.handler_is_connected(self.__disablenotify_id2):
                        self.handler_disconnect(self.__disablenotify_id2)
                    self.__disablenotify_id2 = None
            else:
                # add lock
                if self.__disablenotify_id2:
                    if self.handler_is_connected(self.__disablenotify_id2):
                        return
                self.__disablenotify_id2 = \
                    self.connect("notify", handle_cb, widget)


class XHPaned(XPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class XVPaned(XPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL


class ConfigRPaned(RPaned):
    def __init__(self, section, option, default, *args, **kwargs):
        super(ConfigRPaned, self).__init__(*args, **kwargs)
        self.set_relative(config.getfloat(section, option, default))
        self.connect('notify::position', self.__changed, section, option)

    def __changed(self, widget, event, section, option):
        if self.get_property('position-set'):
            config.set(section, option, str(self.get_relative()))


class ConfigRHPaned(ConfigRPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class ConfigRVPaned(ConfigRPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL


class MultiPaned(object):
    """A Paned that supports an unlimited number of panes."""

    # The Paned type (horizontal or vertical)
    PANED = None

    def __init__(self):
        self._root_paned = None

        if self.PANED is None:
            explanation = ("PANED is None. Do not directly"
                           "instantiate MultiPaned, use"
                           "one of its subclasses.")
            raise AttributeError(explanation)

    def set_widgets(self, widgets, packing=[(True, False)]):
        """Put a list of widgets in separate panes."""

        # root_paned will be the root of a nested paned structure.
        # if we have three panes - p1, p2 and p3 - root_paned will
        # eventually look like this: Paned(p1, Paned(p2, p3))
        self._root_paned = self.PANED()

        curr_paned = self._root_paned
        for i, widget in enumerate(widgets):
            # the last widget completes the last paned

            pack_expand = packing[min(i, len(packing) - 1)][0]
            pack_fill = packing[min(i, len(packing) - 1)][1]

            if widget is widgets[-1]:
                curr_paned.pack2(widget, pack_expand, pack_fill)
                break
            curr_paned.pack1(widget, pack_expand, pack_fill)

            # the second last widget ends the nesting
            if widget is widgets[-2]:
                continue

            tmp_paned = self.PANED()
            tmp_paned.root = self._root_paned

            curr_paned.pack2(tmp_paned, pack_expand, pack_fill)
            curr_paned = tmp_paned

    def get_paned(self):
        """Get the GTK Paned used for displaying."""

        return self._root_paned

    def make_pane_sizes_equal(self):
        paneds = self.get_paneds()

        # the relative paned widths must be equal to the reciprocal (1/i) of
        # their respective indices (i) in reverse order (from right to left)
        # to make the pane widths equal. (i + 2) because +1 from changing
        # from zero- to one-indexed, and +1 for compensating that the last
        # paned contains two panes
        for i, paned in enumerate(reversed(paneds)):
            proportion = min(1.0 / (i + 2), 0.5)
            if isinstance(paned, RPaned):
                # relative
                paned.set_relative(proportion)
            else:
                # absolute
                if paned.ORIENTATION == Gtk.Orientation.HORIZONTAL:
                    paned.set_position(
                        paned.get_allocation().width * proportion)
                else:
                    paned.set_position(
                        paned.get_allocation().height * proportion)

    def change_orientation(self, horizontal):
        """Change the orientation of the paned."""

        hor = Gtk.Orientation.HORIZONTAL
        ver = Gtk.Orientation.VERTICAL

        for paned in self.get_paneds():
            paned.props.orientation = hor if horizontal else ver

    def destroy(self):
        if self._root_paned:
            self._root_paned.destroy()

    def show_all(self):
        self._root_paned.show_all()

    def get_paneds(self):
        """Get all internal paneds in a flat, ordered list."""

        paneds = [self._root_paned]

        # gather all the paneds in the nested structure
        curr_paned = self._root_paned
        while True:
            child = curr_paned.get_child2()
            if type(child) is self.PANED:
                paneds.append(child)
                curr_paned = child
            else:
                break

        return paneds


class MultiRHPaned(MultiPaned):
    PANED = RHPaned


class MultiRVPaned(MultiPaned):
    PANED = RVPaned


class MultiXHPaned(MultiPaned):
    PANED = XHPaned


class MultiXVPaned(MultiPaned):
    PANED = XVPaned


class ConfigMultiPaned(MultiPaned):

    def __init__(self, section, option):
        super(ConfigMultiPaned, self).__init__()
        self.section = section
        self.option = option

    def set_widgets(self, widgets):
        super(ConfigMultiPaned, self).set_widgets(widgets)
        paneds = self.get_paneds()

        # Connect all paneds
        for paned in paneds:
            paned.connect('notify::position', self.__changed)

        self._restore_widths()

    def save_widths(self):
        """Save all current paned widths."""

        paneds = self.get_paneds()
        if len(paneds) == 1 and not paneds[0].get_child1():
            # If there's only one pane (i.e. the only paned has just one
            # child), do not save the paned width, as this will cause
            # a later added second pane to get the width of the previous
            # second pane
            widths = []
        else:
            widths = [str(p.get_relative()) for p in paneds]

        config.setstringlist(self.section, self.option, widths)

    def _restore_widths(self):
        """Restore pane widths from the config."""

        widths = config.getstringlist(self.section, self.option, [])
        paneds = self.get_paneds()

        if not widths:
            # If no widths are saved, save the current widths
            self.__changed()
        else:
            # Restore as many widths as we have saved
            # (and convert them from str to float)
            for i, width in enumerate(map(float, widths)):
                if i >= len(paneds):
                    break
                paneds[i].set_relative(width)
            self.__changed()

    def __changed(self, widget=None, event=None):
        """Callback function for individual paneds. Saves all current paned
        widths.

        Widget and event default to None, as they aren't really used. They
        are just required for GTK.
        """

        self.save_widths()


class ConfigMultiRHPaned(ConfigMultiPaned):
    PANED = RHPaned


class ConfigMultiRVPaned(ConfigMultiPaned):
    PANED = RVPaned


class PaneLock(object):
    """XPaned helper to allow easy identification of child widgets that want
    to lock their parent pane size
    """

    def __init__(self, id, orientation, default_size=0):
        self.id = id
        self.size = self.default_size = default_size
        self.orientation = orientation
        self.updating = False

    def size_allocate(self, allocation):

        alloc_size = allocation.height \
            if self.orientation == Gtk.Orientation.VERTICAL \
            else allocation.width

        if alloc_size > self.default_size:
            self.size = alloc_size

#            print_d("%s | size_allocate event. storing height: %d" %
#                    (self.id, self.size))
