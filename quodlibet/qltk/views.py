# Copyright 2005 Joe Wreschnig, Michael Urman
#           2012, 2013 Christoph Reiter
#                 2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import contextlib
import os

from gi.repository import Gtk, Gdk, GObject, Graphene, Pango, GLib
import cairo

from quodlibet import print_e
from quodlibet import config
from quodlibet.qltk import (
    is_accel,
    is_accel_pressed,
    is_wayland,
    menu_popup,
    get_primary_accel_mod,
)

from .util import GSignals


class TreeViewHints(Gtk.Window):
    """Handle 'hints' for treeviews. This includes expansions of truncated
    columns, and in the future, tooltips."""

    class _MinLabel(Gtk.Label):
        def do_get_preferred_width(*args):
            return (0, Gtk.Label.do_get_preferred_width(*args)[0])

    # Note: hover tooltips on truncated TreeView cells are not yet wired up
    # for GTK4. The original GTK3 motion handler relied on bin_window and
    # convert_bin_window_to_widget_coords, both removed. A future pass should
    # attach a Gtk.EventControllerMotion and compute positions in widget
    # coordinates.

    def __init__(self):
        try:
            # gtk+ 3.20
            TreeViewHints.set_css_name("tooltip")
        except AttributeError:
            pass

        super().__init__()
        self.__clabel = Gtk.Label()
        self.__clabel.set_valign(0.5)
        self.__clabel.set_ellipsize(Pango.EllipsizeMode.NONE)

        self.__label = label = self._MinLabel()
        label.set_valign(0.5)
        label.set_ellipsize(Pango.EllipsizeMode.NONE)
        self.set_child(label)

        context = self.get_style_context()
        context.add_class("tooltip")
        context.add_class("ql-tooltip")

        self.set_can_focus(False)
        # Hint window must not intercept pointer events; events should reach
        # the view underneath.
        self.set_can_target(False)
        self.set_resizable(False)
        self.set_name("gtk-tooltip")

        self.__handlers = {}
        self.__current_path = self.__current_col = None
        self.__current_renderer = None
        self.__view = None
        self.__hide_id = None

    def connect_view(self, view):
        # don't depend on padding set by theme, we need the text coordinates
        # to match in all cases
        self._style_provider = style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            .ql-tooltip * {
                border-width: 0px;
                padding: 0px;
            }
            .ql-tooltip {
                padding: 0px;
            }
        """)

        # somehow this doesn't apply if we set it on the window, only
        # if set for the screen. gets reverted again in disconnect_view()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Hide the hint on view-level events. Motion/showing the hint itself
        # is currently disabled — see the TODO on the class.
        self.__handlers[view] = [
            view.connect("unmap", self.__undisplay),
        ]
        scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.BOTH_AXES
        )
        scroll_controller.connect("scroll", self.__undisplay)
        view.add_controller(scroll_controller)
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.__undisplay)
        view.add_controller(key_controller)

    def disconnect_view(self, view):
        try:
            for handler in self.__handlers[view]:
                view.disconnect(handler)
            del self.__handlers[view]
        except KeyError:
            pass
        # Hide if the active treeview is going away
        if view is self.__view:
            self.__undisplay()
        self.set_transient_for(None)

        if self.__hide_id:
            GLib.source_remove(self.__hide_id)
            self.__hide_id = None
            self.set_visible(False)

        Gtk.StyleContext.remove_provider_for_display(
            Gdk.Display.get_default(), self._style_provider
        )

    def __undisplay(self, *args, **kwargs):
        if not self.__view:
            return

        if self.__current_renderer and self.__edit_id:
            self.__current_renderer.disconnect(self.__edit_id)
        self.__current_renderer = self.__edit_id = None
        self.__current_path = self.__current_col = None
        self.__view = None

        self.__hide_id = None
        self.set_visible(False)


class DragScroll:
    """A treeview mixin for smooth drag and scroll (needs BaseView).

    Call scroll_motion in the 'drag-motion' handler and
    scroll_disable in the 'drag-leave' handler.

    """

    __scroll_delay = None
    __scroll_periodic = None
    __scroll_args = (0, 0, 0, 0)
    __scroll_length = 0
    __scroll_last = None

    def __enable_scroll(self):
        """Start scrolling if it hasn't already"""
        if self.__scroll_periodic is not None or self.__scroll_delay is not None:
            return

        def periodic_scroll():
            """Get the tree coords for 0,0 and scroll from there"""
            wx, wy, dist, ref = self.__scroll_args
            x, y = self.convert_widget_to_tree_coords(0, 0)
            x, y = self.convert_bin_window_to_widget_coords(x, y)

            # We reached an end, stop
            if self.__scroll_last == y:
                self.scroll_disable()
                return
            self.__scroll_last = y

            # If we went full speed for a while.. speed up
            # .. every number is made up here
            if self.__scroll_length >= 50 * ref:
                dist *= self.__scroll_length / (ref * 10)
            if self.__scroll_length < 2000 * ref:
                self.__scroll_length += abs(dist)

            try:
                self.scroll_to_point(-1, y + dist)
            except OverflowError:
                pass
            self.set_drag_dest(wx, wy)
            # we have to re-add the timeout.. otherwise they could add up
            # because scroll can last longer than 50ms
            GLib.source_remove(self.__scroll_periodic)
            self.__scroll_periodic = None
            enable_periodic_scroll()

        def enable_periodic_scroll():
            self.__scroll_periodic = GLib.timeout_add(50, periodic_scroll)
            self.__scroll_delay = None

        self.__scroll_delay = GLib.timeout_add(350, enable_periodic_scroll)

    def scroll_disable(self):
        """Disable all scrolling"""
        if self.__scroll_periodic is not None:
            GLib.source_remove(self.__scroll_periodic)
            self.__scroll_periodic = None
        if self.__scroll_delay is not None:
            GLib.source_remove(self.__scroll_delay)
            self.__scroll_delay = None
        self.__scroll_length = 0
        self.__scroll_last = None

    def scroll_motion(self, x, y):
        """Call with current widget coords during a dnd action to update
        scrolling speed"""

        visible_rect = self.get_visible_rect()
        if visible_rect is None:
            self.scroll_disable()
            return

        # I guess the bin to visible_rect difference is the header height
        # but this could be wrong
        start = self.convert_bin_window_to_widget_coords(0, 0)[1]
        end = visible_rect.height + start

        # Get the font height as size reference
        reference = max(self.create_pango_layout("").get_pixel_size()[1], 1)

        # If the drag is in the scroll area, adjust the speed
        scroll_offset = int(reference * 3)
        in_upper_scroll = start < y < start + scroll_offset
        in_lower_scroll = y > end - scroll_offset

        # thanks TI200
        def accel(x):
            try:
                return int(1.1 ** (x * 12 / reference)) - (x / reference)
            except ValueError:
                return 0

        if in_lower_scroll:
            diff = accel(y - end + scroll_offset)
        elif in_upper_scroll:
            diff = -accel(start + scroll_offset - y)
        else:
            self.scroll_disable()
            return

        # The area where we can go to full speed
        full_offset = int(reference * 0.8)
        in_upper_full = start < y < start + full_offset
        in_lower_full = y > end - full_offset
        if not in_upper_full and not in_lower_full:
            self.__scroll_length = 0

        # For the periodic scroll function
        self.__scroll_args = (x, y, diff, reference)

        # The area to trigger a scroll is a bit smaller
        trigger_offset = int(reference * 2.5)
        in_upper_trigger = start < y < start + trigger_offset
        in_lower_trigger = y > end - trigger_offset

        if in_upper_trigger or in_lower_trigger:
            self.__enable_scroll()


class BaseView(Gtk.TreeView):
    __gsignals__: GSignals = {
        # like the tree selection changed signal but doesn't emit twice in case
        # a row is activated
        "selection-changed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self, *args, **kwargs):
        # GTK4: TreeView requires model= as keyword argument
        if args and "model" not in kwargs:
            kwargs["model"] = args[0]
            args = args[1:]
        super().__init__(**kwargs)
        event_controller = Gtk.EventControllerKey()
        event_controller.connect("key-pressed", self.__key_pressed)
        self.add_controller(event_controller)

        self._setup_selection_signal()

    def _setup_selection_signal(self):
        # Forwards selection changed events except in case row-activated
        # just happened and the selection changed event is a result of the
        # button release after the row-activated event.
        # This makes the selection change only once in case of double clicking
        # a row.

        self._sel_ignore_next = False
        self._sel_should_ignore = False

        def on_selection_changed(selection):
            if not self._sel_should_ignore:
                self.emit("selection-changed", selection)
            self._sel_should_ignore = False

        self._sel_change_handler = self.get_selection().connect(
            "changed", on_selection_changed
        )

        def on_row_activated(*args):
            self._sel_ignore_next = True

        self.connect_after("row-activated", on_row_activated)

        def on_button_release_event(gesture, n_press, x, y):
            if self._sel_ignore_next:
                self._sel_should_ignore = True
            self._sel_ignore_next = False

        controller = Gtk.GestureClick()
        controller.connect("released", on_button_release_event)
        self.add_controller(controller)

    def destroy(self):
        if hasattr(self, "_sel_change_handler"):
            try:
                self.get_selection().disconnect(self._sel_change_handler)
            except Exception:
                pass

    def do_key_press_event(self, event):
        if is_accel(event, "space", "KP_Space"):
            return False
        return Gtk.TreeView.do_key_press_event(self, event)

    def __key_pressed(self, controller, keyval, keycode, state):
        # GTK4: EventControllerKey.key-pressed has different signature
        # Create event-like object for compatibility
        class KeyEvent:
            def __init__(self, keyval, keycode, state):
                self.type = Gdk.EventType.KEY_PRESS
                self.keyval = keyval
                self.keycode = keycode
                self.state = state

            def get_state(self):
                return self.state

        event = KeyEvent(keyval, keycode, state)

        def get_first_selected():
            selection = self.get_selection()
            model, paths = selection.get_selected_rows()
            return paths and paths[0] or None

        if is_accel(event, "Right") or is_accel(event, "<Primary>Right"):
            first = get_first_selected()
            if first:
                self.expand_row(first, False)
        elif is_accel(event, "Left") or is_accel(event, "<Primary>Left"):
            first = get_first_selected()
            if first:
                if self.row_expanded(first):
                    self.collapse_row(first)
                else:
                    # if we can't collapse, move the selection to the parent,
                    # so that a second attempt collapses the parent
                    model = self.get_model()
                    parent = model.iter_parent(model.get_iter(first))
                    if parent:
                        self.set_cursor(model.get_path(parent))

    def remove_paths(self, paths):
        """Remove rows and restore the selection if it got removed"""

        model = self.get_model()
        self.remove_iters([model.get_iter(p) for p in paths])

    def remove_iters(self, iters):
        """Remove rows and restore the selection if it got removed"""

        self.__remove_iters(iters)

    def remove_selection(self):
        """Remove all currently selected rows and select the position
        of the first removed one."""

        selection = self.get_selection()
        mode = selection.get_mode()
        if mode in (Gtk.SelectionMode.SINGLE, Gtk.SelectionMode.BROWSE):
            model, iter_ = selection.get_selected()
            if iter_:
                self.__remove_iters([iter_], force_restore=True)
        elif mode == Gtk.SelectionMode.MULTIPLE:
            model, paths = selection.get_selected_rows()
            iters = list(map(model.get_iter, paths or []))
            self.__remove_iters(iters, force_restore=True)

    def select_by_func(self, func, scroll=True, one=False):
        """Calls func with every Gtk.TreeModelRow in the model and selects
        it if func returns True. In case func never returned True,
        the selection will not be changed.

        Returns True if the selection was changed."""

        model = self.get_model()
        if not model:
            return False

        selection = self.get_selection()
        first = True
        for row in model:
            if func(row):
                if not first:
                    selection.select_path(row.path)
                    continue
                self.set_cursor(row.path)
                if scroll:
                    self.scroll_to_cell(row.path, use_align=True, row_align=0.5)
                first = False
                if one:
                    break
        return not first

    def iter_select_by_func(self, func, scroll=True):
        """Selects the next row after the current selection for which func
        returns True, removing the selection of all other rows.

        func gets passed Gtk.TreeModelRow and should return True if
        the row should be selected.

        If scroll=True then scroll to the selected row if the selection
        changes.

        Returns True if the selection was changed.
        """

        model = self.get_model()
        if not model:
            return False

        if not model.get_iter_first():
            # empty model
            return False

        selection = self.get_selection()
        model, paths = selection.get_selected_rows()

        # get the last iter we shouldn't be looking at
        if not paths:
            last_iter = model[-1].iter
        else:
            last_iter = model.get_iter(paths[-1])

        # get the first iter we should be looking at
        start_iter = model.iter_next(last_iter)
        if start_iter is None:
            start_iter = model.get_iter_first()

        row_iter = Gtk.TreeModelRowIter(model, start_iter)

        for row in row_iter:
            if not func(row):
                continue
            self.set_cursor(row.path)
            if scroll:
                self.scroll_to_cell(row.path, use_align=True, row_align=0.5)
            return True

        last_path = model.get_path(last_iter)
        for row in model:
            if row.path.compare(last_path) == 0:
                return False
            if not func(row):
                continue
            self.set_cursor(row.path)
            if scroll:
                self.scroll_to_cell(row.path, use_align=True, row_align=0.5)
            return True

        return False

    def set_drag_dest(self, x, y, into_only=False):
        """Sets a drag destination for widget coords

        into_only will only highlight rows or the whole widget and no
        lines between rows.
        """

        dest_row = self.get_dest_row_at_pos(x, y)
        if dest_row is None:
            rows = len(self.get_model())
            if not rows:
                self.add_css_class("drop-target")
            else:
                self.remove_css_class("drop-target")
                self.set_drag_dest_row(
                    Gtk.TreePath(rows - 1), Gtk.TreeViewDropPosition.AFTER
                )
        else:
            self.remove_css_class("drop-target")
            path, pos = dest_row
            if into_only:
                if pos == Gtk.TreeViewDropPosition.BEFORE:
                    pos = Gtk.TreeViewDropPosition.INTO_OR_BEFORE
                elif pos == Gtk.TreeViewDropPosition.AFTER:
                    pos = Gtk.TreeViewDropPosition.INTO_OR_AFTER
            self.set_drag_dest_row(path, pos)

    def __remove_iters(self, iters, force_restore=False):
        if not iters:
            return

        selection = self.get_selection()
        model = self.get_model()

        if force_restore:
            for iter_ in iters:
                model.remove(iter_)
        else:
            old_count = selection.count_selected_rows()
            for iter_ in iters:
                model.remove(iter_)
            # only restore a selection if all selected rows are gone afterwards
            if not old_count or selection.count_selected_rows():
                return

        # model.remove makes the removed iter point to the next row if possible
        # so check if the last iter is a valid one and select it or
        # simply select the last row
        if model.iter_is_valid(iters[-1]):
            selection.select_iter(iters[-1])
        elif len(model):
            selection.select_path(model[-1].path)

    @contextlib.contextmanager
    def without_model(self):
        """Context manager which removes the model from the view
        and adds it back afterwards.

        Tries to preserve all state that gets reset on a model change.
        """

        old_model = self.get_model()
        search_column = self.get_search_column()
        sorts = [column.get_sort_indicator() for column in self.get_columns()]
        self.set_model(None)

        yield old_model

        self.set_model(old_model)
        self.set_search_column(search_column)
        for column, value in zip(self.get_columns(), sorts, strict=False):
            column.set_sort_indicator(value)


class DragIconTreeView(BaseView):
    """TreeView that sets the selected rows as drag icons

    - Drag icons include 3 rows/2 plus a "and more" count
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        controller = Gtk.DragSource()
        controller.connect("drag-begin", self.__begin)
        self.add_controller(controller)

    def __begin(self, drag_source, drag):
        model, paths = self.get_selection().get_selected_rows()
        paintable = self.create_multi_row_drag_icon(paths, max_rows=3)
        if paintable is not None:
            hot_x, hot_y = self.__drag_hotspot(drag_source, paths, paintable)
            Gtk.DragIcon.set_from_paintable(drag, paintable, hot_x, hot_y)

    def __drag_hotspot(self, drag_source, paths, paintable):
        """Compute the drag-icon hotspot as the cursor's offset within
        the first selected row's cell area, clamped to the paintable."""
        sequence = drag_source.get_current_sequence()
        ok, x, y = drag_source.get_point(sequence)
        if not ok or not paths:
            return 0, 0
        cell_area = self.get_cell_area(paths[0], None)
        max_x = max(0, paintable.get_intrinsic_width() - 1)
        max_y = max(0, paintable.get_intrinsic_height() - 1)
        hot_x = min(max(0, int(x - cell_area.x)), max_x)
        hot_y = min(max(0, int(y - cell_area.y)), max_y)
        return hot_x, hot_y

    def create_multi_row_drag_icon(self, paths, max_rows):
        """Composite up to max_rows row paintables stacked vertically into
        a single Gdk.Paintable, or None if paths is empty."""

        if not paths:
            return None

        paintables = [self.create_row_drag_icon(p) for p in paths[:max_rows]]
        paintables = [p for p in paintables if p is not None]
        if not paintables:
            return None
        if len(paintables) == 1:
            return paintables[0]

        width = max(p.get_intrinsic_width() for p in paintables)
        height = sum(p.get_intrinsic_height() for p in paintables)

        snapshot = Gtk.Snapshot()
        y = 0
        for paintable in paintables:
            ph = paintable.get_intrinsic_height()
            snapshot.save()
            snapshot.translate(Graphene.Point().init(0, y))
            paintable.snapshot(snapshot, paintable.get_intrinsic_width(), ph)
            snapshot.restore()
            y += ph

        return snapshot.to_paintable(Graphene.Size().init(width, height))


class MultiDragTreeView(BaseView):
    """TreeView with multirow drag support.

    Button press events which would result in a row getting unselected
    get delayed until the next button release event.

    This makes it possible to drag one or more selected rows without
    changing the selection.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        controller = Gtk.GestureClick()
        controller.connect("pressed", self.__button_press)
        controller.connect("released", self.__button_release)
        self.add_controller(controller)
        self.__pending_action = None

    def __button_press(self, gesture, n_press, x, y):
        # GTK4: GestureClick.pressed signal has different signature
        button = gesture.get_current_button()
        if button == Gdk.BUTTON_PRIMARY:
            return self.__block_selection(gesture, x, y)
        return None

    def __block_selection(self, gesture, x, y):
        x, y = map(int, [x, y])
        try:
            path, col, cellx, celly = self.get_path_at_pos(x, y)
        except TypeError:
            return True
        selection = self.get_selection()
        is_selected = selection.path_is_selected(path)
        # GTK4: get modifier state from gesture
        event = gesture.get_last_event(gesture.get_current_sequence())
        state = event.get_modifier_state() if event else 0
        mod_active = state & (get_primary_accel_mod() | Gdk.ModifierType.SHIFT_MASK)

        if is_selected:
            self.__pending_action = (path, col, mod_active)
            selection.set_select_function(lambda *args: False, None)
        else:
            self.__pending_action = None
            selection.set_select_function(lambda *args: True, None)
        return None

    def __button_release(self, gesture, n_press, x, y):
        # GTK4: GestureClick.released signal has different signature
        if self.__pending_action:
            path, col, single_unselect = self.__pending_action
            selection = self.get_selection()
            selection.set_select_function(lambda *args: True, None)
            if single_unselect:
                selection.unselect_path(path)
            else:
                self.set_cursor(path, col, 0)
            self.__pending_action = None


class RCMTreeView(BaseView):
    """Emits popup-menu when a row is right-clicked on, or when the menu /
    Shift+F10 key is pressed."""

    __gsignals__: GSignals = {
        "popup-menu": (GObject.SignalFlags.RUN_LAST, bool, ()),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        click_ctrl = Gtk.GestureClick()
        click_ctrl.set_button(Gdk.BUTTON_SECONDARY)
        click_ctrl.connect("pressed", self.__button_press)
        self.add_controller(click_ctrl)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self.__key_pressed)
        self.add_controller(key_ctrl)

    def __button_press(self, _gesture, _n_press, x, y):
        return self.__check_popup(x, y)

    def __key_pressed(self, _controller, keyval, _keycode, state):
        if is_accel_pressed(keyval, state, "Menu", "<Shift>F10"):
            return self.emit("popup-menu")
        return False

    def __check_popup(self, x, y):
        x, y = map(int, [x, y])
        try:
            path, col, cellx, celly = self.get_path_at_pos(x, y)
        except TypeError:
            return True
        self.grab_focus()
        selection = self.get_selection()
        if not selection.path_is_selected(path):
            self.set_cursor(path, col, 0)
        else:
            col.focus_cell(col.get_cells()[0])
        self.__position_at_mouse = True
        self.emit("popup-menu")
        return True

    def ensure_popup_selection(self):
        try:
            self.__position_at_mouse  # noqa
        except AttributeError:
            path, col = self.get_cursor()
            if path is None:
                return False
            self.scroll_to_cell(path, col)
            # ensure current cursor path is selected, just like right-click
            selection = self.get_selection()
            if not selection.path_is_selected(path):
                selection.unselect_all()
                selection.select_path(path)
            return True

    def popup_menu(self, menu, button, time):
        try:
            del self.__position_at_mouse
        except AttributeError:
            # suppress menu if the cursor isn't on a real path
            if not self.ensure_popup_selection():
                return False
            pos_func = self.__popup_position
        else:
            pos_func = None

        # GTK4: PopoverMenu uses set_parent() instead of attach_to_widget()
        if isinstance(menu, Gtk.PopoverMenu):
            current_parent = menu.get_parent()
            if current_parent != self:
                if current_parent is not None:
                    menu.unparent()
                menu.set_parent(self)
            # GTK4: PopoverMenus position automatically, ignore pos_func
            menu_popup(menu, None, None, None, None, button, time)
        else:
            # GTK3 fallback
            attached_widget = menu.get_attach_widget()
            if attached_widget != self:
                if attached_widget is not None:
                    menu.detach()
                menu.attach_to_widget(self, None)
            menu_popup(menu, None, None, pos_func, None, button, time)
        return True

    def __popup_position(self, menu, *args):
        path, col = self.get_cursor()

        # get a rectangle describing the cell render area (assume 3 px pad)
        rect = self.get_cell_area(path, col)
        padding = 3
        rect.x += padding
        rect.width = max(rect.width - padding * 2, 0)
        rect.y += padding
        rect.height = max(rect.height - padding * 2, 0)

        x, y = self.get_window().get_origin()[1:]
        x, y = self.convert_bin_window_to_widget_coords(x + rect.x, y + rect.y)

        ma = menu.get_allocation()
        menu_y = rect.height + y
        if self.get_direction() == Gtk.TextDirection.LTR:
            menu_x = x
        else:
            menu_x = x - ma.width + rect.width

        # on X11/win32 we can use the screen size
        if not is_wayland():
            # fit menu to screen, aligned per text direction
            screen = self.get_screen()
            screen_width = screen.get_width()
            screen_height = screen.get_height()

            # show above row if no space below and enough above
            if menu_y + ma.height > screen_height and y - ma.height > 0:
                menu_y = y - ma.height

            # make sure it's not outside of the screen
            if self.get_direction() == Gtk.TextDirection.LTR:
                menu_x = max(0, min(menu_x, screen_width - ma.width))
            else:
                menu_x = min(max(0, menu_x), screen_width)

        return (menu_x, menu_y, True)  # x, y, move_within_screen


class HintedTreeView(BaseView):
    """A TreeView that pops up a tooltip when you hover over a cell that
    contains ellipsized text."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.supports_hints():
            try:
                tvh = HintedTreeView.hints
            except AttributeError:
                tvh = HintedTreeView.hints = TreeViewHints()
            tvh.connect_view(self)

    def destroy(self):
        if self.supports_hints() and hasattr(type(self), "hints"):
            type(self).hints.disconnect_view(self)
        super().destroy()

    def set_tooltip_text(self, *args, **kwargs):
        print_e(
            "Setting a tooltip on the view breaks tv hints. Set it"
            " on the parent scrolled window instead"
        )
        return super().set_tooltip_text(*args, **kwargs)

    def supports_hints(self):
        """If the treeview hints support is enabled. Can be used to
        display scroll bars instead for example.
        """

        if "QUODLIBET_NO_HINTS" in os.environ:
            return False

        return not config.state("disable_hints")


class _TreeViewColumnLabel(Gtk.Label):
    """A label which fades  into the background at the end; for use
    only in TreeViewColumns.

    The hackery with using the parent's allocation is needed because
    the label always gets the allocation it has requested, ignoring
    the actual width of the column header.
    """

    def do_draw(self, ctx):
        alloc = self.get_allocation()
        # in case there are no parents use the same alloc which should
        # result in no custom drawing.
        p1 = self.get_parent() or self
        p2 = p1.get_parent() or p1
        p3 = p2.get_parent() or p2
        p2_alloc = p2.get_allocation()
        p3_alloc = p3.get_allocation()

        # remove the space needed by the arrow and add the space
        # added by the padding so we only start drawing when we clip
        # the text directly
        available_width = (
            p2_alloc.width - abs(p2_alloc.x - alloc.x) + (p2_alloc.x - p3_alloc.x)
        )

        if alloc.width <= available_width:
            return Gtk.Label.do_draw(self, ctx)

        req_height = self.get_requisition().height
        w, h = alloc.width, alloc.height
        aw = available_width

        # possible when adding new columns.... create_similar will fail
        # in this case below, so just skip.
        if min(w, h) < 0:
            return Gtk.Label.do_draw(self, ctx)

        surface = ctx.get_target()

        # draw label to image surface
        label_surface = surface.create_similar(cairo.CONTENT_COLOR_ALPHA, w, h)
        label_ctx = cairo.Context(label_surface)
        res = Gtk.Label.do_draw(self, label_ctx)

        # create a gradient.
        # make the gradient width depend roughly on the font size
        gradient_width = min(req_height * 0.8, aw)

        if self.get_direction() == Gtk.TextDirection.RTL:
            start = w - aw
            end = start + gradient_width
        else:
            end = aw - gradient_width
            start = end + gradient_width

        pat = cairo.LinearGradient(start, 0, end, 0)
        pat.add_color_stop_rgba(0, 0, 0, 0, 0)
        pat.add_color_stop_rgba(gradient_width, 1, 1, 1, 1)

        # gradient surface
        grad_surface = surface.create_similar(cairo.CONTENT_COLOR_ALPHA, w, h)
        imgctx = cairo.Context(grad_surface)
        imgctx.set_source(pat)
        imgctx.paint()

        # draw label using the gradient as the alpha channel mask
        ctx.save()
        ctx.set_source_surface(label_surface)
        ctx.mask_surface(grad_surface)
        ctx.restore()

        return res


class TreeViewColumn(Gtk.TreeViewColumn):
    __gsignals__: GSignals = {
        # Signal of: tree-view-changed(old_tree_view, new_tree_view)
        # Triggers when the columns gets added/removed from a tree view.
        # The passed values are either a TreeView or None
        "tree-view-changed": (GObject.SignalFlags.RUN_LAST, None, (object, object)),
    }

    def __init__(self, **kwargs):
        title = kwargs.pop("title", "")
        # skip overrides which don't allow to set properties
        GObject.Object.__init__(self, **kwargs)

        label = _TreeViewColumnLabel(label=title)
        label.show()
        self.set_widget(label)

        # the button gets created once the widget gets realized
        self._button = None
        self._tooltip_text = None
        label.__realize = label.connect("realize", self.__realized)

    def __realized(self, widget):
        widget.disconnect(widget.__realize)
        self._button = widget.get_ancestor(Gtk.Button)
        self.set_tooltip_text(self._tooltip_text)

        self._last_parent = None

        def on_notify_parent(button, _pspec):
            new_parent = button.get_parent()
            assert new_parent is None or isinstance(new_parent, Gtk.TreeView)
            old_parent = self._last_parent
            self._last_parent = new_parent
            self.emit("tree-view-changed", old_parent, new_parent)

        # parent already set, emit manually
        on_notify_parent(self._button, None)
        self._button.connect("notify::parent", on_notify_parent)

    def set_tooltip_text(self, text):
        if self._button:
            self._button.props.tooltip_text = text
        else:
            self._tooltip_text = text

    def set_use_markup(self, value):
        widget = self.get_widget()
        if isinstance(widget, Gtk.Label):
            widget.set_use_markup(value)


class TreeViewColumnButton(TreeViewColumn):
    """A TreeViewColumn that forwards its header events:
    button-press-event and popup-menu"""

    __gsignals__: GSignals = {
        "button-press-event": (GObject.SignalFlags.RUN_LAST, bool, (object,)),
        "popup-menu": (GObject.SignalFlags.RUN_LAST, bool, ()),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        label = self.get_widget()
        label.__realize = label.connect("realize", self.__connect_menu_event)

    def __connect_menu_event(self, widget):
        widget.disconnect(widget.__realize)
        del widget.__realize
        button = widget.get_ancestor(Gtk.Button)
        if button:
            click_ctrl = Gtk.GestureClick()
            click_ctrl.set_button(0)
            click_ctrl.connect("pressed", self.__on_button_pressed)
            button.add_controller(click_ctrl)

            key_ctrl = Gtk.EventControllerKey()
            key_ctrl.connect("key-pressed", self.__on_key_pressed)
            button.add_controller(key_ctrl)

    def __on_button_pressed(self, gesture, n_press, x, y):
        event = gesture.get_last_event(None)
        return self.emit("button-press-event", event)

    def __on_key_pressed(self, _controller, keyval, _keycode, state):
        if is_accel_pressed(keyval, state, "Menu", "<Shift>F10"):
            return self.emit("popup-menu")
        return False


class RCMHintedTreeView(HintedTreeView, RCMTreeView, DragIconTreeView):
    """A TreeView that has hints and a context menu."""


class AllTreeView(HintedTreeView, RCMTreeView, DragIconTreeView, MultiDragTreeView):
    """A TreeView that has hints, a context menu, and multi-selection
    dragging support."""
