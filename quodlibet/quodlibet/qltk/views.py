# Copyright 2005 Joe Wreschnig, Michael Urman
#           2012, 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk, GObject, Pango, GLib
import cairo

from quodlibet import config
from quodlibet.qltk import get_top_parent, is_accel, is_wayland


class TreeViewHints(Gtk.Window):
    """Handle 'hints' for treeviews. This includes expansions of truncated
    columns, and in the future, tooltips."""

    # input_shape_combine_region does not work under Windows, we have
    # to pass all events to the treeview. In case it does work, this handlers
    # will never be called.
    __gsignals__ = dict.fromkeys(
        ['button-press-event', 'button-release-event',
         'motion-notify-event', 'scroll-event'],
        'override')

    def __init__(self):
        super(TreeViewHints, self).__init__(Gtk.WindowType.POPUP)
        self.__label = label = Gtk.Label()
        label.set_alignment(0, 0.5)
        label.show()
        label.set_ellipsize(Pango.EllipsizeMode.NONE)
        self.add(label)

        self.add_events(
            Gdk.EventMask.BUTTON_MOTION_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.KEY_PRESS_MASK |
            Gdk.EventMask.KEY_RELEASE_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.SCROLL_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK)

        context = self.get_style_context()
        context.add_class("tooltip")

        self.set_accept_focus(False)
        self.set_resizable(False)
        self.set_name("gtk-tooltip")
        self.set_border_width(1)
        self.connect('leave-notify-event', self.__undisplay)

        self.__handlers = {}
        self.__current_path = self.__current_col = None
        self.__current_renderer = None
        self.__view = None

    def connect_view(self, view):
        self.__handlers[view] = [
            view.connect('motion-notify-event', self.__motion),
            view.connect('scroll-event', self.__undisplay),
            view.connect('key-press-event', self.__undisplay),
            view.connect('unmap', self.__undisplay),
            view.connect('destroy', self.disconnect_view),
            view.connect('leave-notify-event', self.__leave_undisplay),
        ]

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

    def __motion(self, view, event):
        label = self.__label

        # trigger over row area, not column headers
        if event.window is not view.get_bin_window():
            self.__undisplay()
            return False

        # hide if any modifier is active
        if event.get_state() & Gtk.accelerator_get_default_mod_mask():
            self.__undisplay()
            return False

        # get the cell at the mouse position
        x, y = map(int, [event.x, event.y])
        try:
            path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError:
            # no hints where no rows exist
            self.__undisplay()
            return False

        area = view.get_cell_area(path, col)
        # make sure we are on the same level
        if x < area.x:
            self.__undisplay()
            return False

        # hide for partial hidden rows at the bottom
        if y > view.get_visible_rect().height:
            self.__undisplay()
            return False

        # get the renderer at the mouse position and get the xpos/width
        renderers = col.get_cells()
        pos = sorted(zip(map(col.cell_get_position, renderers), renderers))
        pos = filter(lambda ((x, w), r): x < cellx, pos)
        if not pos:
            self.__undisplay()
            return False
        (render_offset, render_width), renderer = pos[-1]

        if self.__current_renderer == renderer and self.__current_path == path:
            return False
        else:
            self.__undisplay()

        # only ellipsized text renderers
        if not isinstance(renderer, Gtk.CellRendererText):
            return False
        if renderer.get_property('ellipsize') == Pango.EllipsizeMode.NONE:
            return False

        # don't display if the renderer is in editing mode
        if renderer.props.editing:
            return False

        # set the cell renderer attributes for the active cell
        model = view.get_model()
        col.cell_set_cell_data(model, model.get_iter(path), False, False)

        # the markup attribute is write only, so the markup text needs
        # to be saved on the python side, so we can copy it to the label
        markup = getattr(renderer, "markup", None)
        if markup is None:
            label.set_text(renderer.get_property('text'))
        else:
            # markup can also be column index
            if isinstance(markup, int):
                markup = model[path][markup]
            label.set_markup(markup)

        # Use the renderer padding as label padding so the text offset matches
        render_xpad = renderer.get_property("xpad")
        label.set_ellipsize(Pango.EllipsizeMode.NONE)
        label.set_padding(render_xpad, 0)
        # size_request makes sure the layout size got updated
        label.size_request()
        label_width = label.get_layout().get_pixel_size()[0]
        label_width += label.get_layout_offsets()[0] or 0
        # layout offset includes the left padding, so add one more
        label_width += render_xpad

        # CellRenderer width is too large if it's the last one in a column.
        # Use cell_area width as a maximum and limit render_width.
        max_width = view.get_cell_area(path, col).width
        if render_width + render_offset > max_width:
            render_width = max_width - render_offset

        # don't display if it doesn't need expansion
        if label_width < render_width:
            return False

        dummy, ox, oy = view.get_window().get_origin()

        # save for adjusting passthrough events
        self.__dx, self.__dy = area.x + render_offset, area.y

        # final window coordinates/size
        x = ox + self.__dx
        y = oy + self.__dy
        x, y = view.convert_bin_window_to_widget_coords(x, y)

        w = label_width
        h = area.height

        if not is_wayland():
            # clip on the right if it's bigger than the screen
            screen_border = 5  # leave some space
            space_right = Gdk.Screen.width() - x - w - screen_border

            if space_right < 0:
                w += space_right
                label.set_ellipsize(Pango.EllipsizeMode.END)
            else:
                label.set_ellipsize(Pango.EllipsizeMode.NONE)

        # Don't show if the resulting tooltip would be smaller
        # than the visible area (if not all is on the display)
        if w < render_width:
            return False

        self.__view = view
        self.__current_renderer = renderer
        self.__edit_id = renderer.connect('editing-started', self.__undisplay)
        self.__current_path = path
        self.__current_col = col

        self.set_transient_for(get_top_parent(view))
        self.set_size_request(w, h)
        self.resize(w, h)
        self.move(x, y)

        self.show()
        return False

    def __leave_undisplay(self, view, event):
        # We don't get motion-notify events in all cases, so
        # quickly escaping the view can leave stray tooltips.
        # leave-notify is triggered when we leave the view but also when we
        # show the tooltip, so this has to check if the cursor is not on
        # it to not get in an endless hide/show loop.

        if not self.__view:
            return False

        device = event.get_device()
        # see docs: get_window_at_position
        if device and device.get_device_type() != Gdk.DeviceType.SLAVE:
            win = device.get_window_at_position()[0]
            if win and win != self.get_window():
                self.__undisplay()
        return False

    def __undisplay(self, *args):
        if not self.__view:
            return

        if self.__current_renderer and self.__edit_id:
            self.__current_renderer.disconnect(self.__edit_id)
        self.__current_renderer = self.__edit_id = None
        self.__current_path = self.__current_col = None
        self.__view = None
        self.hide()

    def __event(self, event):
        if not self.__view:
            return True

        # hack: present the main window on key press
        if event.type == Gdk.EventType.BUTTON_PRESS:
            # hack: present is overridden to present all windows.
            # bypass to only select one
            if not is_wayland():  # present duplicates windows in weston
                Gtk.Window.present(get_top_parent(self.__view))

        type_ = event.type
        real_event = None
        if type_ == Gdk.EventType.BUTTON_PRESS:
            real_event = event.button
        elif type_ == Gdk.EventType.BUTTON_RELEASE:
            real_event = event.button
        elif type_ == Gdk.EventType.MOTION_NOTIFY:
            real_event = event.motion

        if real_event:
            real_event.x += self.__dx
            real_event.y += self.__dy

        # modifying event.window is a necessary evil, made okay because
        # nobody else should tie to any TreeViewHints events ever.
        event.any.window = self.__view.get_bin_window()

        event.put()

        return True

    def do_button_press_event(self, event):
        return self.__event(event)

    def do_button_release_event(self, event):
        return self.__event(event)

    def do_motion_notify_event(self, event):
        return self.__event(event)

    def do_scroll_event(self, event):
        return self.__event(event)


class DragScroll(object):
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
        if self.__scroll_periodic is not None or \
                self.__scroll_delay is not None:
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

            self.scroll_to_point(-1, y + dist)
            self.set_drag_dest(wx, wy)
            # we have to re-add the timeout.. otherwise they could add up
            # because scroll can last longer than 50ms
            GLib.source_remove(self.__scroll_periodic)
            enable_periodic_scroll()

        def enable_periodic_scroll():
            self.__scroll_periodic = GLib.timeout_add(50, periodic_scroll)

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
        reference = self.create_pango_layout("").get_pixel_size()[1]

        # If the drag is in the scroll area, adjust the speed
        scroll_offset = int(reference * 3)
        in_upper_scroll = (start < y < start + scroll_offset)
        in_lower_scroll = (y > end - scroll_offset)

        # thanks TI200
        accel = lambda x: int(1.1 ** (x * 12 / reference)) - (x / reference)
        if in_lower_scroll:
            diff = accel(y - end + scroll_offset)
        elif in_upper_scroll:
            diff = - accel(start + scroll_offset - y)
        else:
            self.scroll_disable()
            return

        # The area where we can go to full speed
        full_offset = int(reference * 0.8)
        in_upper_full = (start < y < start + full_offset)
        in_lower_full = (y > end - full_offset)
        if not in_upper_full and not in_lower_full:
            self.__scroll_length = 0

        # For the periodic scroll function
        self.__scroll_args = (x, y, diff, reference)

        # The area to trigger a scroll is a bit smaller
        trigger_offset = int(reference * 2.5)
        in_upper_trigger = (start < y < start + trigger_offset)
        in_lower_trigger = (y > end - trigger_offset)

        if in_upper_trigger or in_lower_trigger:
            self.__enable_scroll()


class BaseView(Gtk.TreeView):

    def __init__(self, *args, **kwargs):
        super(BaseView, self).__init__(*args, **kwargs)
        self.connect("key-press-event", self.__key_pressed)

    def __key_pressed(self, view, event):
        def get_first_selected():
            selection = self.get_selection()
            model, paths = selection.get_selected_rows()
            return paths and paths[0] or None

        if is_accel(event, "Right") or is_accel(event, "<ctrl>Right"):
            first = get_first_selected()
            if first:
                self.expand_row(first, False)
        elif is_accel(event, "Left") or is_accel(event, "<ctrl>Left"):
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

        self.remove_iters(map(self.get_model().get_iter, paths))

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
            iters = map(model.get_iter, paths or [])
            self.__remove_iters(iters, force_restore=True)

    def select_by_func(self, func, scroll=True, one=False):
        """Calls func with every Gtk.TreeModelRow in the model and selects
        it if func returns True. In case func never returned True,
        the selection will not be changed.

        Returns True if the selection was changed."""

        selection = self.get_selection()
        first = True
        for row in self.get_model():
            if func(row):
                if not first:
                    selection.select_path(row.path)
                    continue
                self.set_cursor(row.path)
                if scroll:
                    self.scroll_to_cell(row.path, use_align=True,
                                        row_align=0.5)
                first = False
                if one:
                    break
        return not first

    def set_drag_dest(self, x, y, into_only=False):
        """Sets a drag destination for widget coords

        into_only will only highlight rows or the whole widget and no
        lines between rows.
        """

        dest_row = self.get_dest_row_at_pos(x, y)
        if dest_row is None:
            rows = len(self.get_model())
            if not rows:
                (self.get_parent() or self).drag_highlight()
            else:
                self.set_drag_dest_row(Gtk.TreePath(rows - 1),
                                       Gtk.TreeViewDropPosition.AFTER)
        else:
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


class DragIconTreeView(BaseView):
    """TreeView that sets the selected rows as drag icons

    - Drag icons include 3 rows/2 plus a "and more" count
    """

    def __init__(self, *args, **kwargs):
        super(DragIconTreeView, self).__init__(*args, **kwargs)
        self.connect('drag-begin', self.__begin)

    def __begin(self, view, drag_ctx):
        model, paths = self.get_selection().get_selected_rows()
        if not paths:
            return

        MAX = 3

        icons = map(self.create_row_drag_icon, paths[:MAX])
        if len(icons) == 1:
            Gtk.drag_set_icon_surface(drag_ctx, icons[0])
            return

        width = max([s.get_width() for s in icons])
        height = sum([s.get_height() for s in icons])

        layout = None
        if len(paths) > MAX:
            more = _("and %d more...") % (len(paths) - MAX)
            more = "<i>%s</i>" % more
            layout = self.create_pango_layout("")
            layout.set_markup(more)
            layout.set_alignment(Pango.Alignment.CENTER)
            layout.set_width(Pango.SCALE * (width - 2))
            lw, lh = layout.get_pixel_size()
            height += lh
            height += 6  # padding

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        # render background
        style_ctx = self.get_style_context()
        Gtk.render_background(style_ctx, ctx, 0, 0, width, height)

        # render rows
        count_y = 0
        for icon in icons:
            ctx.save()
            icon_width = icon.get_width()
            icon_height = icon.get_height()
            ctx.set_source_surface(icon, 2, count_y + 2)
            ctx.rectangle(2, count_y + 2, icon_width - 4, icon_height - 4)
            ctx.clip()
            ctx.paint()
            ctx.restore()
            count_y += icon_height

        if layout:
            Gtk.render_layout(style_ctx, ctx, 1, count_y, layout)

        # render border
        Gtk.render_line(style_ctx, ctx, 0, 0, 0, height - 1)
        Gtk.render_line(style_ctx, ctx, 0, height - 1, width - 1, height - 1)
        Gtk.render_line(style_ctx, ctx, width - 1, height - 1, width - 1, 0)
        Gtk.render_line(style_ctx, ctx, width - 1, 0, 0, 0)

        Gtk.drag_set_icon_surface(drag_ctx, surface)


class MultiDragTreeView(BaseView):
    """TreeView with multirow drag support:

    - Selections don't change until button-release-event...
    - Unless they're a Shift/Ctrl modification, then they happen immediately
    - Drag icons include 3 rows/2 plus a "and more" count
    """

    def __init__(self, *args, **kwargs):
        super(MultiDragTreeView, self).__init__(*args, **kwargs)
        self.connect('button-press-event', self.__button_press)
        self.connect('button-release-event', self.__button_release)
        self.__pending_event = None

    def __button_press(self, view, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            return self.__block_selection(event)

    def __block_selection(self, event):
        x, y = map(int, [event.x, event.y])
        try:
            path, col, cellx, celly = self.get_path_at_pos(x, y)
        except TypeError:
            return True
        self.grab_focus()
        selection = self.get_selection()
        is_selected = selection.path_is_selected(path)
        mod_active = event.get_state() & (
            Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)

        if is_selected and not mod_active:
            self.__pending_event = [x, y]
            selection.set_select_function(lambda *args: False, None)
        elif event.type == Gdk.EventType.BUTTON_PRESS:
            self.__pending_event = None
            selection.set_select_function(lambda *args: True, None)

    def __button_release(self, view, event):
        if self.__pending_event:
            selection = self.get_selection()
            selection.set_select_function(lambda *args: True, None)
            oldevent = self.__pending_event
            self.__pending_event = None

            x, y = map(int, [event.x, event.y])
            if oldevent != [x, y]:
                return True

            try:
                path, col, cellx, celly = self.get_path_at_pos(x, y)
            except TypeError:
                return True
            self.set_cursor(path, col, 0)


class RCMTreeView(BaseView):
    """Emits popup-menu when a row is right-clicked on."""

    def __init__(self, *args):
        super(RCMTreeView, self).__init__(*args)
        self.connect('button-press-event', self.__button_press)

    def __button_press(self, view, event):
        if event.button == Gdk.BUTTON_SECONDARY:
            return self.__check_popup(event)

    def __check_popup(self, event):
        x, y = map(int, [event.x, event.y])
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
        self.emit('popup-menu')
        return True

    def ensure_popup_selection(self):
        try:
            self.__position_at_mouse
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

        menu.popup(None, None, pos_func, None, button, time)
        return True

    def __popup_position(self, menu, *args):
        path, col = self.get_cursor()
        if col is None:
            col = self.get_column(0)

        # get a rectangle describing the cell render area (assume 3 px pad)
        rect = self.get_cell_area(path, col)
        rect.x += 3
        rect.width -= 6
        rect.y += 3
        rect.height -= 6
        dummy, dx, dy = self.get_window().get_origin()
        dy += self.get_bin_window().get_position()[1]

        # fit menu to screen, aligned per text direction
        screen_width = Gdk.Screen.width()
        screen_height = Gdk.Screen.height()
        menu.realize()
        ma = menu.get_allocation()
        menu_y = rect.y + rect.height + dy
        if menu_y + ma.height > screen_height and rect.y + dy - ma.height > 0:
            menu_y = rect.y + dy - ma.height
        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.LTR:
            menu_x = min(rect.x + dx, screen_width - ma.width)
        else:
            menu_x = max(0, rect.x + dx - ma.width + rect.width)

        return (menu_x, menu_y, True)  # x, y, move_within_screen


class HintedTreeView(BaseView):
    """A TreeView that pops up a tooltip when you hover over a cell that
    contains ellipsized text."""

    def __init__(self, *args):
        super(HintedTreeView, self).__init__(*args)
        if not config.state('disable_hints'):
            try:
                tvh = HintedTreeView.hints
            except AttributeError:
                tvh = HintedTreeView.hints = TreeViewHints()
            tvh.connect_view(self)


class TreeViewColumn(Gtk.TreeViewColumn):
    def __init__(self, title="", *args, **kwargs):
        super(TreeViewColumn, self).__init__(None, *args, **kwargs)
        label = Gtk.Label(label=title)
        label.set_padding(1, 1)
        label.show()
        self.set_widget(label)

    def set_use_markup(self, value):
        widget = self.get_widget()
        if isinstance(widget, Gtk.Label):
            widget.set_use_markup(value)


class TreeViewColumnButton(TreeViewColumn):
    """A TreeViewColumn that forwards its header events:
        button-press-event and popup-menu"""

    __gsignals__ = {
        'button-press-event': (GObject.SignalFlags.RUN_LAST, bool, (object,)),
        'popup-menu': (GObject.SignalFlags.RUN_LAST, bool, ()),
    }

    def __init__(self, title="", *args, **kw):
        super(TreeViewColumnButton, self).__init__(title, *args, **kw)
        label = self.get_widget()
        label.__realize = label.connect('realize', self.__connect_menu_event)

    def __connect_menu_event(self, widget):
        widget.disconnect(widget.__realize)
        del widget.__realize
        button = widget.get_ancestor(Gtk.Button)
        if button:
            button.connect('button-press-event', self.button_press_event)
            button.connect('popup-menu', self.popup_menu)

    def button_press_event(self, widget, event):
        return self.emit('button-press-event', event)

    def popup_menu(self, widget):
        return self.emit('popup-menu')


class RCMHintedTreeView(HintedTreeView, RCMTreeView, DragIconTreeView):
    """A TreeView that has hints and a context menu."""
    pass


class AllTreeView(HintedTreeView, RCMTreeView, DragIconTreeView,
                  MultiDragTreeView):
    """A TreeView that has hints, a context menu, and multi-selection
    dragging support."""
    pass
