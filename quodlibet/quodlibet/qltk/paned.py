# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#           2017 Fredrik Strupe, Pete Beardmore
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gdk

from quodlibet import config
from . import add_css, gtk_version
from quodlibet.util import print_d


class Paned(Gtk.Paned):

    def __init__(self, *args, **kwargs):
        super(Paned, self).__init__(*args, **kwargs)
        self.__handle_size = 5
        self.ensure_wide_handle()
        self.root = self

    def ensure_wide_handle(self):
        if gtk_version >= (3, 19):
            self.props.wide_handle = True
            add_css(self, """
                paned separator {
                    border-width: 0;
                    min-height: """ + str(self.__handle_size) + """px;
                    min-width: """ + str(self.__handle_size) + """px;
                    background-image: none;
                }
                paned {
                    padding: 0px;
                }
            """, True)
            return

        if hasattr(self.props, "wide_handle"):
            # gtk 3.16
            self.props.wide_handle = True
            add_css(self, """
                GtkPaned {
                    -GtkPaned-handle-size: """ + str(self.__handle_size) + """;
                    border-width: 0;
                    background: none;
                }
            """, True)
            return

        # gtk 3.14
        add_css(self, """
            GtkPaned {
                -GtkPaned-handle-size: """ + str(self.__handle_size) + """;
                background-image: none;
                margin: 0;
                border-width: 0;
            }
        """, True)

    @property
    def handle_size(self):
        return self.__handle_size

    def get_paneds(self):
        """Return a hierarchy of paneds in a flat, ordered list."""

        paneds = [self.root]
        # append any nested paneds in this structure
        curr_paned = self.root
        while True:
            child = curr_paned.get_child2()
            if isinstance(child, Paned):
                paneds.append(child)
                curr_paned = child
            else:
                break
        return paneds


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

        self.connect('button-press-event', self.__button_press)
        self.connect('button-release-event', self.__button_release)
        self.connect('enter-notify-event', self.__enter_notify)
        self.connect('check_resize', self.__check_resize)

        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        self.__disablenotify_id = None
        self.__disablenotify_id2 = None

        self.__mouse = False
        self.__toggling = False
        self.__resizing = False

        self.__active_paned = None
        self.__active_widget = None
        self.__pane_infos = None

        self.__allocated = 0

    def add1(self, *args):
        super(XPaned, self).add1(*args)
        XPaned.__expander_widget(self, self.get_child1())

    def add2(self, *args):
        super(XPaned, self).add2(*args)
        XPaned.__expander_widget(self, self.get_child2())

    def pack1(self, *args):
        super(XPaned, self).pack1(*args)
        XPaned.__expander_widget(self, self.get_child1())

    def pack2(self, *args):
        super(XPaned, self).pack2(*args)
        XPaned.__expander_widget(self, self.get_child2())

    def __expander_widget_allocated(self, widget, allocation):
        XPaned.__expander_widget(self, widget, True)

    @classmethod
    def __expander_widget(cls, xpaned, widget, allocated=False):
        """Test if a widget is an Expander instance and if so, ensure its
        title size is set"""

        if not isinstance(widget, Gtk.Expander):
            return

        if xpaned.__allocated >= 2:
            return

        # ensure we 'know' the expander's title size by forcing it in
        # the gentlist way possible..
        # dictate margins and padding, force expander arrow size but allow
        # its label natural sizing

        # this is necessary for testing, where we want to calculate the
        # position of where we expect the paned's handle to be positioned.
        # elsewhere, it is probably better/safer to utilise paneds
        # 'min|max-position' properties to set handle positions

        if not allocated:
            # call this function again when allocated
            widget.connect('size-allocate', xpaned.__expander_widget_allocated)

        # setup widget
        widget.set_property('margin', 0)

        __expander_size = 10
        __expander_spacing = 2
        __expander_padding = 2

        title_size = __expander_size + 2 * __expander_spacing

        __label_size = 0
        __label_padding = 0
        label = widget.get_label_widget()
        if label:
            req = label.get_requisition()
            if xpaned.ORIENTATION == Gtk.Orientation.VERTICAL:
                __label_size += req.height
            else:
                __label_size += req.width

            if title_size > __label_size:
                # pad label until bigger
                __label_padding = round((title_size - req.height) / 2.0)

            __label_padding += 2
            title_size = __label_size + 2 * __label_padding

        title_size += 2 * __expander_padding

        # version specific
        if gtk_version >= (3, 19):
            add_css(widget, """
                expander label, expander arrow {
                    min-height: """ + str(max(__expander_size,
                                              __label_size)) + """px;
                    min-width: """ + str(max(__expander_size,
                                             __label_size)) + """px;
                }
                expander arrow {
                    padding: """ + str(__expander_spacing) + """px;
                }""", True)
        else:
            add_css(widget, """
                GtkExpander, expander {
                    -GtkExpander-expander-size: """ +
                        str(__expander_size) + "; }", True)

        # common
        add_css(widget, """
            expander, GtkExpander {
                border-width: 0;
                background-image: none;
                margin: 0px;
                padding: """ + str(__expander_padding) + """px;
            }
            expander label,
            GtkExpander .label {
                border-width: 0;
                background-image: none;
                margin: 0px;
                padding: """ + str(__label_padding) + """px;
            }""", True)

        widget.title_size = title_size

        if allocated:
            xpaned.__allocated += 1

    def __enter_notify(self, *data):
        if self.root and \
           not self.root.__pane_infos:
            self.root.__active_paned = self

    def __button_press(self, *data):
        self.__mouse = True

    def __button_release(self, *data):
        self.__mouse = False
        self.__toggling = False
        self.__resizing = False

        if not self.root or \
           not self.root.__pane_infos:
            return

        for id, pi in self.root.__pane_infos.items():
            w = pi['widget']
            size = self.get_widget_size(w)
            alloc = w.get_size_request()
            size2 = alloc[1]
            if pi['locked'] and size != size2:
                print_d("[%s] locked, but size %d -> %d, resetting!" %
                        (id, size, size2))
                self.set_widget_size(w, size)

        self.root.__pane_infos = None

    def get_widget_id(self, widget):
        return widget.id if hasattr(widget, 'id') \
                         else "%s|%s" % (id(widget), type(widget))

    def get_widget_size(self, widget):
        size = -1
        id = self.get_widget_id(widget)
        if isinstance(widget, Gtk.Expander) and not widget.get_expanded():
            size = widget.title_size
        else:
            try:
                size = self.root.__pane_infos[id]['size']
            except:
                try:
                    size = widget.panelock.size
                except:
                    req = widget.get_allocation()
                    size = req.height if self.ORIENTATION == \
                                         Gtk.Orientation.VERTICAL \
                                      else req.width
        return size

    def set_widget_size(self, widget, size):
        if self.ORIENTATION == Gtk.Orientation.VERTICAL:
            widget.set_size_request(-1, size)
        else:
            widget.set_size_request(size, -1)

    def set_widget_resize(self, widget, resize):
        p = widget.get_parent()
        p.child_set_property(widget, 'resize', resize)

    def get_pane_info(self, widget):
        id = self.get_widget_id(widget)
        if hasattr(self.root, '_pane_infos') and \
           id in self.root.__pane_infos:
            return self.root.__pane_infos[id]
        return None

    def get_widgets(self):
        paneds = self.root.get_paneds()
        widgets = []
        for p in paneds:
            widgets.append(p.get_child1())
            w2 = p.get_child2()
            if not isinstance(w2, Paned):
                widgets.append(w2)
        return widgets

    def get_active_panes(self):
        """Get the (widgets in the) panes immediately above and below the
        active paned split."""

        # through use of the enter-notify-event, and given the nesting of
        # containers, '_active_paned' is always set to the most nested paned
        # and hence the 'panes of interest' (e.g. above / below the split,
        # are always child1 of the active paned, and child1 of the paned
        # nested in the active paned's child2(), unless active paned has no
        # nested paned in its child2 (e.g. the last / most nested paned), in
        # which case it is just the active paned's child1 and child2

        if not self.__active_paned:
            return
        w1 = self.__active_paned.get_child1()
        w2 = self.__active_paned.get_child2()
        if isinstance(w2, Paned):
            w2 = w2.get_child1()

        return (w1, w2)

    def dump_active_panes(self):
        (w1, w2) = self.get_active_panes()
        if not w1:
            return

        description = "active panes: [%s] / [%s]" % \
                          (w1.id if hasattr(w1, 'id') else w1,
                           w2.id if hasattr(w2, 'id') else w2)
        if description:
            print_d(description)

    def dump_pane_infos(self, operation):
        if not self.__pane_infos:
            return
        description = "pane_infos: %s" % operation
        for id, pi in self.__pane_infos.items():
            description += "\n[%s] size: %d, locked: %s" \
                           % (id, pi['size'], pi['locked'])
        if description:
            print_d(description)

    def set_pane_infos(self, target):
        """build reference dictionary of pane locks where target is either a
        widget (when toggling), of a paned (when resizing)"""

        pane_infos = []  # array of dictionaries

        # which panes (widgets!) need to be locked (i.e. size request set) ?
        widgets = self.get_widgets()
        for w in widgets:
            id = self.get_widget_id(w)
            size = self.get_widget_size(w)
            locked = False
            pi = {'id': id, 'widget': w, 'size': size, 'locked': locked}
            pane_infos.append(pi)

        # lock all
        for pi in pane_infos:
            w = pi['widget']
            pi['locked'] = True
            self.set_widget_size(w, pi['size'])
            self.set_widget_resize(w, False)

        def can_resize(pane_info):
            ret = True
            w = pane_info['widget']
            if isinstance(w, Gtk.Expander) and not w.get_expanded():
                ret = False
            return ret

        if self.__toggling:

            # unlock main and target to take the hit / absorb the toggled

            # main / unnamed
            for pi in pane_infos:
                w = pi['widget']
                if not hasattr(w, 'id'):
                    pi['locked'] = False
                    self.set_widget_resize(w, True)
                    self.set_widget_size(w, -1)
            idx = 0
            for pi in pane_infos:
                if pi['widget'] is target:
                    # target
                    pi['locked'] = False
                    self.set_widget_resize(target, True)
                    self.set_widget_size(target, -1)
                    break
                idx += 1

        elif self.__resizing:

            # using the given position of interest (poi), we can find the
            # nearest non-collapsed pane and then ensure that that is unlocked

            # so where are we?
            (w1, w2) = target
            self.root.dump_active_panes()
            idx_w1 = None
            l = 0
            for pi in pane_infos:
                w = pi['widget']
                if w is w1:
                    idx_w1 = l
                l += 1

            # unlock appropriate
            idx = idx_w1
            while idx > -1:
                pi = pane_infos[idx]
                if can_resize(pi):
                    # above
                    w = pi['widget']
                    pi['locked'] = False
                    self.set_widget_resize(w, True)
                    self.set_widget_size(w, -1)
                    break
                idx -= 1
            idx = idx_w1 + 1
            while idx < len(pane_infos):
                pi = pane_infos[idx]
                if can_resize(pane_infos[idx]):
                    # below
                    w = pi['widget']
                    pi['locked'] = False
                    self.set_widget_resize(w, True)
                    self.set_widget_size(w, -1)
                    break
                idx += 1

        # respect handle positions
        paneds = self.root.get_paneds()
        for p in paneds:
            p.props.position_set = True
        #w1.get_parent().props.position_set = True

        # update container
        self.root.__pane_infos = infos = {}
        for pi in pane_infos:
            infos[pi['id']] = pi

        # dump state
        self.root.dump_pane_infos("resizing" if self.__resizing
                                                       else "toggling")

    def update(self, widget):
        """Pass the widget whose pane needs updating."""

        if not isinstance(widget, Gtk.Expander):
            return

        # build once
        self.__toggling = True
        self.set_pane_infos(widget)

        expanded = widget.get_expanded()

        id = self.get_widget_id(widget)
        if expanded:
            # widget size changed. use stored if available
            size = self.get_widget_size(widget)
            self.set_widget_resize(widget, True)
            print_d("[%s] restoring size: %d" % (id, size))
            self.set_widget_size(widget, size)
        else:
            # ensure parent pane(s) are not using position-set
            parent = self
            while parent:
                if isinstance(parent, Gtk.Paned):
                    parent.props.position_set = False
                parent = parent.get_parent()

            title_size = widget.title_size
            if self.ORIENTATION == Gtk.Orientation.VERTICAL:
                widget.set_size_request(-1, title_size)
            else:
                widget.set_size_request(title_size, -1)

        p = widget
        while p is not self.root:
            p = p.get_parent()
            p.check_resize()

    def do_size_allocate(self, *args):

        if self.__mouse and not self.root.__pane_infos:
            # build once
            self.__resizing = True
            self.set_pane_infos(self.root.get_active_panes())

        # resize
        Gtk.HPaned.do_size_allocate(self, *args)

        return

    def __check_resize(self, data, *args):

        if self.__resizing:
            return

        def handle_cb(xpaned, param, widget):
            # note that use of 'min/max-position here is safer, but
            # we want to know if those don't match our expected values
            # calculated based on title and handle sizes
            widget = xpaned.get_child1()
            position = None
            if widget is xpaned.get_child1():
                if isinstance(widget, Gtk.Expander) and \
                   not widget.get_expanded():
                    position = widget.title_size
                else:
                    position = self.get_widget_size(widget)
            else:
                alloc = xpaned.get_allocation()
                size = None
                if isinstance(widget, Gtk.Expander) and \
                   not widget.get_expanded():
                    size = widget.title_size + xpaned.handle_size
                else:
                    size = self.get_widget_size(widget)
                position = (alloc.height if xpaned.ORIENTATION ==
                                            Gtk.Orientation.VERTICAL
                                         else alloc.width) - size
            xpaned.set_position(position)
            return True

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
            pack_shrink = packing[min(i, len(packing) - 1)][1]

            if widget is widgets[-1]:
                curr_paned.pack2(widget, pack_expand, pack_shrink)
                break
            curr_paned.pack1(widget, pack_expand, pack_shrink)

            # the second last widget ends the nesting
            if widget is widgets[-2]:
                continue

            tmp_paned = self.PANED()
            tmp_paned.root = self._root_paned

            curr_paned.pack2(tmp_paned, False, False)
            curr_paned = tmp_paned

    def get_paned(self):
        """Get the GTK Paned used for displaying."""

        return self._root_paned

    def get_paneds(self):
        """Get all internal paneds in a flat, ordered list."""

        return self._root_paned.get_paneds()

    def make_pane_sizes_equal(self):
        paneds = self.get_paneds()

        # paneds array packs root (biggest) first, to the most/last nested

        # the relative paned widths must be equal to the reciprocal (1/i) of
        # their respective indices (i) in reverse order (from right to left)
        # to make the pane widths equal. (i + 2) because +1 from changing
        # from zero- to one-indexed, and +1 for compensating that the last
        # paned contains two panes

        # the paned handle sits below the handle position (px) and
        # consideration of its size is needed, else the bottom pane in the
        # last nest will be wrong (too small by the size of the handle!)

        # inner nest -> outer outer nest iteration
        proportions = []
        for i, paned in enumerate(reversed(paneds)):
            proportions = [min(1.0 / (i + 2), 0.5)] + proportions

        # outer nest -> inner nest iteration
        for i, paned in enumerate(paneds):
            size = 0
            allocation = paned.get_allocation()
            if paned.ORIENTATION == Gtk.Orientation.HORIZONTAL:
                size = allocation.width
            else:
                size = allocation.height

            # adjustments
            size = size - ((len(paneds) - i) * paned.handle_size)
            # position
            position = round(size * proportions[i])
            paned.set_position(position)

            # important, else the next nested allocation will be wrong
            # simply iterating nests in reverse and hoping, is no good
            paned.check_resize()

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
            # don't store a collapsed height!
            self.size = alloc_size

#            print_d("[%s] size_allocate event. storing height: %d" %
#                    (self.id, self.size))
