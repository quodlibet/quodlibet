# Copyright 2021 Joschua Gandert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from dataclasses import dataclass

from gi.repository import Gtk, Pango
from typing import Generic, TypeVar
from collections.abc import Callable

from quodlibet.qltk.models import ObjectStore

from quodlibet.qltk.views import HintedTreeView

from quodlibet.qltk import Icons

from quodlibet import _, app

from quodlibet.qltk.window import PersistentWindowMixin, Dialog


MATCH_DESC = _(
    "Check if the columns on the left side approximately match the ones on "
    "the right side. If they don't, you can change the order here (use _ "
    "for rows that shouldn't be matched):"
)

T = TypeVar("T")


@dataclass
class ColumnSpec(Generic[T]):
    """Simple data class for specifying the behavior and content of a column"""

    title: str
    cell_text_getter: Callable[[T], str]
    is_resizable: bool = True


# We're using a Dialog, since a ConfirmationPrompt looks really ugly at such a width
class MatchListsDialog(Dialog, PersistentWindowMixin, Generic[T]):
    """
    A prompt whose run method returns the chosen order, or an empty list if the user
    pressed cancel.
    """

    def __init__(
        self,
        a_items: list[T],
        b_items: list[T],
        b_order: list[int | None],
        columns: list[ColumnSpec[T]],
        title: str,
        ok_button_text: str,
        ok_button_icon: str = Icons.DOCUMENT_SAVE,
        description: str = MATCH_DESC,
        parent=app.window,
        id_for_window_tracking: str | None = None,
    ):
        super().__init__(
            title=title, transient_for=parent, modal=True, destroy_with_parent=True
        )

        # A lot of information to display, so make resizable and maximize
        self.set_resizable(True)
        self.set_default_size(750, 500)
        self.maximize()

        if id_for_window_tracking is not None:
            self.enable_window_tracking(id_for_window_tracking)

        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.get_content_area().pack_start(vb, True, True, 0)
        vb.set_spacing(24)
        self.set_border_width(5)

        desc_lbl = Gtk.Label(f"\n{description}\n", wrap=True)
        vb.pack_start(desc_lbl, False, False, 0)

        self.add_button(_("_Cancel"), Gtk.ResponseType.REJECT)
        self.add_icon_button(ok_button_text, ok_button_icon, Gtk.ResponseType.OK)

        order_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        lbl = Gtk.Label(_("Right side order:"))
        order_box.pack_start(lbl, False, True, 0)

        self.order_entry = Gtk.Entry()
        order_box.pack_start(self.order_entry, True, True, 0)

        vb.pack_start(order_box, False, True, 1)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        vb.pack_start(sw, True, True, 1)

        tree = MatchListsTreeView(a_items, b_items, columns)
        self._tree = tree
        sw.add(tree)
        tree.b_order = b_order

        default_order_text = ", ".join(
            ("_" if i is None else str(i + 1)) for i in b_order
        )
        self.order_entry.set_text(default_order_text)
        legal_characters = set(default_order_text)
        legal_characters.add("_")

        def changed_order_entry(widget):
            text = widget.get_text()

            # remove illegal characters
            new_text = "".join(c for c in text if c in legal_characters)
            widget.set_text(new_text)

            num_tracks = len(b_items)
            reordered = one_indexed_csv_to_unique_indices(new_text, num_tracks)
            if reordered:
                tree.b_order = reordered

        self.order_entry.connect("changed", changed_order_entry)

    def run(self, destroy=True) -> list[int | None]:
        self.show_all()
        resp = super().run()
        if destroy:
            self.destroy()
        return self.order if resp == Gtk.ResponseType.OK else []

    @property
    def order(self):
        return self._tree.b_order


def one_indexed_csv_to_unique_indices(
    text,
    target_length,
    char_for_none_matching="_",
    require_target_length_elements=False,
):
    """
    :return: List of indices from the comma separated list of one-indexed numbers.
             List will be empty if any index is repeated or out of bounds.

    By default '_' can be used to specify that a position has no match, which
    will be represented in the returned list with None.
    """

    # remove trailing commas, then split
    nums = text.strip(", ").split(",")
    if require_target_length_elements and len(nums) != target_length:
        return []

    reordered = []
    for n in nums:
        n = n.strip()

        if n == char_for_none_matching:
            i = None
        else:
            try:
                i = int(n) - 1
            except ValueError:
                return []

            # i is not in range and/or not unique
            if i < 0 or i >= target_length or i in reordered:
                return []

        reordered.append(i)

    return reordered


class MatchListsTreeView(HintedTreeView, Generic[T]):
    _b_order: list[int | None]

    def __init__(
        self, a_items: list[T], b_items: list[T], columns: list[ColumnSpec[T]]
    ):
        self.model = ObjectStore()
        self.model.append_many(a_items)
        self._b_items = b_items

        super().__init__(self.model)
        self.set_headers_clickable(False)
        self.set_rules_hint(True)
        self.set_reorderable(False)
        self.get_selection().set_mode(Gtk.SelectionMode.NONE)

        def show_id(col, cell, model, itr, data):
            idx = model.get_path(itr)[0]
            imp_idx = self._b_order[idx]
            num = "_" if imp_idx is None else imp_idx + 1
            cell.set_property("markup", f'<span weight="bold">{num}</span>')

        def df_for_a_items(a_attr_getter):
            def data_func(col, cell, model, itr, data):
                a_item = model[itr][0]
                text = ""
                if a_item is not None:
                    text = a_attr_getter(a_item)
                cell.set_property("text", text)

            return data_func

        def df_for_b_items(b_attr_getter):
            def data_func(col, cell, model, itr, data):
                self._set_text(model, itr, cell, b_attr_getter)

            return data_func

        for c in columns:
            self._add_col(c.title, df_for_a_items(c.cell_text_getter), c.is_resizable)

        self._add_col("#", show_id, False)

        for c in columns:
            self._add_col(c.title, df_for_b_items(c.cell_text_getter), c.is_resizable)

        self._b_order = []  # Initialize the backing field of b_order
        self.b_order = list(range(len(b_items)))  # Update it and rows

        self.update_b_items(b_items)

    def _add_col(self, title, func, resize):
        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)
        col = Gtk.TreeViewColumn(title, render)
        col.set_cell_data_func(render, func)
        col.set_resizable(resize)
        col.set_expand(resize)
        self.append_column(col)

    def _set_text(self, model, itr, cell, get_attr):
        idx = model.get_path(itr)[0]
        text = ""
        if idx < len(self._b_order):
            it_idx = self._b_order[idx]
            if it_idx is not None:
                text = get_attr(self._b_items[it_idx])
        cell.set_property("text", text)

    def update_b_items(self, b_items: list[T]):
        """
        Updates the TreeView, handling results with a different number of b_items than
        there are a_items.
        """
        self._b_items = b_items

        for _i in range(len(self.model), len(b_items)):
            self.model.append((None,))

        for _i in range(len(self.model), len(b_items), -1):
            if self.model[-1][0] is not None:
                break
            itr = self.model.get_iter_from_string(str(len(self.model) - 1))
            self.model.remove(itr)

        self._rows_changed()
        self.columns_autosize()

    def _rows_changed(self):
        for row in self.model:
            self.model.row_changed(row.path, row.iter)

    @property
    def b_order(self) -> list[int | None]:
        return list(self._b_order)

    @b_order.setter
    def b_order(self, order: list[int | None]):
        """
        Supports a partial order list. For example, if there are 5 elements in the
        b_items list, you could supply [4, 1, 2]. This will result in an ascending order
        for the last 2 rows, so [0, 3].
        """
        if order == self._b_order:
            return

        b_len = len(self._b_items)
        if len(order) < b_len:
            # add missing indices
            for i in range(b_len):
                if i not in order:
                    order.append(i)

        while len(order) < len(self.model):
            order.append(None)

        self._b_order = order
        self._rows_changed()
