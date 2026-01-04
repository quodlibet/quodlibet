# Copyright 2005 Joe Wreschnig, Michael Urman
#           2017 Fredrik Strupe
#           2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from gi.repository import Gtk

from quodlibet import config
from . import add_css


class Paned(Gtk.Paned):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ensure_wide_handle()

    def ensure_wide_handle(self):
        # GTK4: wide_handle and modern CSS selectors always available
        self.props.wide_handle = True
        add_css(
            self,
            """
            paned separator {
                border-width: 0;
                min-height: 5px;
                min-width: 5px;
                background-image: none;
            }
        """,
        )


class RPaned(Paned):
    """A Paned that supports relative (percentage) width/height setting."""

    ORIENTATION: Gtk.Orientation = None

    def __init__(self, *args, **kwargs):
        if self.ORIENTATION is not None:
            kwargs["orientation"] = self.ORIENTATION
        super().__init__(*args, **kwargs)
        # before first alloc: save value in relative and set on the first alloc
        # after the first alloc: use the normal properties
        self.__alloced = False
        self.__relative = None

    def _get_max(self):
        alloc = self.get_allocation()
        if self.get_orientation() == Gtk.Orientation.HORIZONTAL:
            return alloc.width
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
        ret = super().do_size_allocate(self, *args)
        if not self.__alloced and self.__relative is not None:
            self.__alloced = True
            self.set_relative(self.__relative)
            # call again so the children get alloced
            ret = super().do_size_allocate(self, *args)
        self.__alloced = True
        return ret


class RHPaned(RPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class RVPaned(RPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL


class ConfigRPaned(RPaned):
    def __init__(self, section, option, default, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_relative(config.getfloat(section, option, default))
        self.connect("notify::position", self.__changed, section, option)

    def __changed(self, widget, event, section, option):
        if self.get_property("position-set"):
            config.set(section, option, str(self.get_relative()))


class ConfigRHPaned(ConfigRPaned):
    ORIENTATION = Gtk.Orientation.HORIZONTAL


class ConfigRVPaned(ConfigRPaned):
    ORIENTATION = Gtk.Orientation.VERTICAL


class MultiRPaned:
    """A Paned that supports an unlimited number of panes."""

    # The Paned type (horizontal or vertical)
    PANED: type[RPaned] | None = None

    def __init__(self):
        self._root_paned = None

        if self.PANED is None:
            explanation = (
                "PANED is None. Do not directly"
                "instantiate MultiRPaned, use"
                "one of its subclasses."
            )
            raise AttributeError(explanation)

    def set_widgets(self, widgets):
        """Put a list of widgets in separate panes."""

        # root_paned will be the root of a nested paned structure.
        # if we have three panes - p1, p2 and p3 - root_paned will
        # eventually look like this: Paned(p1, Paned(p2, p3))
        self._root_paned = self.PANED()

        curr_paned = self._root_paned
        for widget in widgets:
            # the last widget completes the last paned
            if widget is widgets[-1]:
                # GTK4: pack2() → set_end_child()
                curr_paned.set_end_child(widget)
                curr_paned.set_resize_end_child(True)
                curr_paned.set_shrink_end_child(False)
                break
            # GTK4: pack1() → set_start_child()
            curr_paned.set_start_child(widget)
            curr_paned.set_resize_start_child(True)
            curr_paned.set_shrink_start_child(False)

            # the second last widget ends the nesting
            if widget is widgets[-2]:
                continue

            tmp_paned = self.PANED()
            # GTK4: pack2() → set_end_child()
            curr_paned.set_end_child(tmp_paned)
            curr_paned.set_resize_end_child(True)
            curr_paned.set_shrink_end_child(False)
            curr_paned = tmp_paned

    def get_paned(self):
        """Get the GTK Paned used for displaying."""

        return self._root_paned

    def make_pane_widths_equal(self):
        paneds = self._get_paneds()

        # the relative paned widths must be equal to the reciprocal (1/i) of
        # their respective indices (i) in reverse order (from right to left)
        # to make the pane widths equal. (i + 2) because +1 from changing
        # from zero- to one-indexed, and +1 for compensating that the last
        # paned contains two panes
        for i, paned in enumerate(reversed(paneds)):
            width = min(1.0 / (i + 2), 0.5)
            paned.set_relative(width)

    def change_orientation(self, horizontal):
        """Change the orientation of the paned."""

        hor = Gtk.Orientation.HORIZONTAL
        ver = Gtk.Orientation.VERTICAL

        for paned in self._get_paneds():
            paned.props.orientation = hor if horizontal else ver

    def destroy(self):
        if self._root_paned:
            # GTK4: self.destroy() removed - _root_paned cleaned up automatically
            pass

    def show_all(self):
        self._root_paned.show_all()

    def _get_paneds(self):
        """Get all internal paneds in a flat, ordered list."""

        paneds = [self._root_paned]

        # gather all the paneds in the nested structure
        curr_paned = self._root_paned
        while True:
            child = curr_paned.get_end_child()
            if type(child) is self.PANED:
                paneds.append(child)
                curr_paned = child
            else:
                break

        return paneds


class MultiRHPaned(MultiRPaned):
    PANED = RHPaned


class MultiRVPaned(MultiRPaned):
    PANED = RVPaned


class ConfigMultiRPaned(MultiRPaned):
    def __init__(self, section, option):
        super().__init__()
        self.section = section
        self.option = option

    def set_widgets(self, widgets):
        super().set_widgets(widgets)
        paneds = self._get_paneds()

        # Connect all paneds
        for paned in paneds:
            paned.connect("notify::position", self.__changed)

        self._restore_widths()

    def save_widths(self):
        """Save all current paned widths."""

        paneds = self._get_paneds()
        if len(paneds) == 1 and not paneds[0].get_start_child():
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
        paneds = self._get_paneds()

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


class ConfigMultiRHPaned(ConfigMultiRPaned):
    PANED = RHPaned


class ConfigMultiRVPaned(ConfigMultiRPaned):
    PANED = RVPaned
