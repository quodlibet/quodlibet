# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet.qltk.paned import RPaned, RVPaned, RHPaned, ConfigRVPaned, \
        MultiRVPaned, MultiRHPaned, ConfigMultiRVPaned, ConfigMultiRHPaned, \
        XHPaned, XVPaned, MultiXHPaned, MultiXVPaned
from quodlibet import config

from . import TestCase
from .helper import visible, relatively_close_test


class TRPaned(object):
    Kind = None

    def test_ctr(self):
        self.Kind().destroy()

    def test_pre_alloc(self):
        p = self.Kind()
        p.set_relative(0.25)
        self.failUnlessEqual(p.get_relative(), 0.25)
        self.assertRaises(ValueError, p.set_relative, 2.0)
        self.assertRaises(ValueError, p.set_relative, -2.0)

    def test_visible_no_setup(self):
        p = self.Kind()
        with visible(p):
            pass

    def test_visible_pre_setup_children(self):
        p = self.Kind()
        p.pack1(Gtk.Button())
        p.pack2(Gtk.Button())
        p.set_relative(0.75)
        self.failUnlessAlmostEqual(p.get_relative(), 0.75)
        with visible(p, width=200, height=200) as p:
            self.failUnlessAlmostEqual(p.get_relative(), 0.75, 2)

    def test_visible_pre_setup_empty(self):
        p = self.Kind()
        p.set_relative(0.75)
        self.failUnlessEqual(p.get_relative(), 0.75)
        with visible(p) as p:
            self.failUnlessAlmostEqual(p.get_relative(), 0.75, 2)

    def test_min_size_child(self):
        p = self.Kind()
        p.set_size_request(200, 200)
        p.pack1(Gtk.Label(), True, False)
        b2 = Gtk.Button()
        b2.set_size_request(50, 50)
        p.pack2(b2, True, False)
        p.set_relative(0.5)
        with visible(p) as p:
            self.assertEqual(p.get_position(), 100)


class RHPaned(TestCase, TRPaned):
    Kind = RHPaned


class RVPaned(TestCase, TRPaned):
    Kind = RVPaned


class TXPaned(object):
    Kind = None

    def test_ctr(self):
        self.Kind().destroy()

    def test_handle_collapse(self):
        p = self.Kind()

        exp1 = Gtk.Expander()
        d1 = 100 if p.ORIENTATION == Gtk.Orientation.HORIZONTAL else -1
        d2 = -1 if p.ORIENTATION == Gtk.Orientation.HORIZONTAL else 100
        exp1.set_size_request(d1, d2)

        exp2 = Gtk.Expander()
        d1 = 100 if p.ORIENTATION == Gtk.Orientation.HORIZONTAL else -1
        d2 = -1 if p.ORIENTATION == Gtk.Orientation.HORIZONTAL else 100
        exp2.set_size_request(d1, d2)

        p.add1(exp1)
        p.add2(exp2)

        with visible(p, 300, 200):
            title_size = exp1.style_get_property('expander-size') +\
                         exp1.style_get_property('expander-spacing')

            exp1.set_expanded(False)
            p.update(exp1)

            handle_position = p.get_position()
            self.failUnlessAlmostEqual(handle_position, title_size + 5)


class XHPaned(TestCase, TXPaned):
    Kind = XHPaned


class XVPaned(TestCase, TXPaned):
    Kind = XVPaned


class TConfigRPaned(TestCase):

    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_basic(self):
        self.failUnless(config.get("memory", "foobar", None) is None)

        p = ConfigRVPaned("memory", "foobar", 0.75)
        p.pack1(Gtk.Button())
        p.pack2(Gtk.Button())

        with visible(p, width=200, height=200) as p:
            self.failUnlessAlmostEqual(p.get_relative(), 0.75, 2)
            p.props.position = 20
            self.failUnlessAlmostEqual(p.get_relative(), 0.10, 2)

        config_value = config.getfloat("memory", "foobar")
        self.failUnlessAlmostEqual(config_value, 0.10, 2)


class TMultiPaned(object):
    Kind = None

    def test_set_widgets(self):
        """Test if widgets are properly set and in the correct order."""
        p = self.Kind()

        # 0 widgets
        p.set_widgets([])
        paned = p.get_paned()
        self.assertIsNotNone(paned)
        self.assertIsNone(paned.get_child1())
        self.assertIsNone(paned.get_child2())

        # 1 widget
        sw = Gtk.ScrolledWindow()
        p.set_widgets([sw])
        paned = p.get_paned()
        children = [paned.get_child1(), paned.get_child2()]
        self.assertIn(sw, children)

        # 2 widgets
        sws = [Gtk.ScrolledWindow() for _ in range(2)]
        p.set_widgets(sws)
        paned = p.get_paned()
        self.assertIs(sws[0], paned.get_child1())
        self.assertIs(sws[1], paned.get_child2())

        # 3 widgets
        sws = [Gtk.ScrolledWindow() for _ in range(3)]
        p.set_widgets(sws)

        root_paned = p.get_paned()
        self.assertIs(sws[0], root_paned.get_child1())

        sub_paned = root_paned.get_child2()
        self.assertIs(sws[1], sub_paned.get_child1())
        self.assertIs(sws[2], sub_paned.get_child2())

    def test_make_pane_sizes_equal(self):
        p = self.Kind()
        sws = [Gtk.ScrolledWindow() for _ in range(4)]
        p.set_widgets(sws)

        size = 500
        with visible(p.get_paned(), size, size):
            p.make_pane_sizes_equal()

            paneds = p.get_paneds()

            if isinstance(p.PANED(), RPaned):
                self.failUnlessAlmostEqual(
                    paneds[0].get_relative(), 1.0 / 4.0, 2)
                self.failUnlessAlmostEqual(
                    paneds[1].get_relative(), 1.0 / 3.0, 2)
                self.failUnlessAlmostEqual(
                    paneds[2].get_relative(), 1.0 / 2.0, 2)
            else:
                res, msg = relatively_close_test(
                               paneds[0].get_position(), size / 4, 0.02)
                self.failUnless(res, msg)
                res, msg = relatively_close_test(
                               paneds[1].get_position(), size / 4, 0.02)
                self.failUnless(res, msg)
                res, msg = relatively_close_test(
                               paneds[2].get_position(), size / 4, 0.02)
                self.failUnless(res, msg)

    def test_change_orientation(self):
        p = self.Kind()
        p.set_widgets([Gtk.ScrolledWindow()])

        opposite = Gtk.Orientation.HORIZONTAL
        horizontal_opposite = True
        if p.get_paned().props.orientation is Gtk.Orientation.HORIZONTAL:
            opposite = Gtk.Orientation.VERTICAL
            horizontal_opposite = False

        p.change_orientation(horizontal=horizontal_opposite)
        for paned in p.get_paneds():
            self.assertIs(paned.props.orientation, opposite)

    def test_destroy(self):
        self.Kind().destroy()


class TMultiRHPaned(TestCase, TMultiPaned):
    Kind = MultiRHPaned


class TMultiRVPaned(TestCase, TMultiPaned):
    Kind = MultiRVPaned


class TMultiXHPaned(TestCase, TMultiPaned):
    Kind = MultiXHPaned


class TMultiXVPaned(TestCase, TMultiPaned):
    Kind = MultiXVPaned

    def test_sizing(self):

        def _widgets(count):
            orientation = self.Kind().PANED().ORIENTATION
            d1 = 100 if orientation == Gtk.Orientation.HORIZONTAL else -1
            d2 = -1 if orientation == Gtk.Orientation.HORIZONTAL else 100
            ws = [Gtk.Expander() for _ in range(count)]
            for w in ws:
                w.set_expanded(False)
                w.set_size_request(d1, d2)
            return ws

        def _repack(w):
            # expand single pane only, implicitly its parents too
            while w.get_parent():
                p = w.get_parent()
                if isinstance(p, Gtk.Paned):
                    if w == p.get_child1():
                        p.remove(w)
                        p.pack1(w, True, False)
                    else:
                        p.remove(w)
                        p.pack2(w, True, False)
                w = p

        title_size = Gtk.Expander().style_get_property('expander-size') +\
                     Gtk.Expander().style_get_property('expander-spacing')
        handle_size = self.Kind().PANED().style_get_property('handle-size')

        # 2 widgets, bottom expandable
        p = self.Kind()
        exps = _widgets(2)
        p.set_widgets(exps, [(False, False)])
        exp = exps[1]
        exp.set_expanded(True)
        _repack(exp)

        with visible(p.get_paned(), 400, 400):
            for w in [w for w in exps if w is not exp]:
                w.get_parent().update(w)

            self.failUnlessEqual(
                exp.get_allocation().height,
                p.get_paned().get_allocation().height -
                (title_size + 5 + handle_size))

        # 3 widgets, top expandable
        p = self.Kind()
        exps = _widgets(3)
        p.set_widgets(exps, [(False, False)])
        exp = exps[0]
        exp.set_expanded(True)
        _repack(exp)
        with visible(p.get_paned(), 400, 400):

            exp.get_parent().update(exp)
            self.failUnlessEqual(
                exp.get_allocation().height,
                p.get_paned().get_allocation().height - 2 *
                (100 + handle_size))

            for w in [w for w in exps if w is not exp]:
                w.get_parent().update(w)

            res, msg = relatively_close_test(
                           exp.get_allocation().height,
                           p.get_paned().get_allocation().height - 2 *
                           (title_size + 5 + handle_size))
            self.failUnless(res, msg)

        # 4 widgets, 2nd expandable
        p = self.Kind()
        exps = _widgets(4)
        p.set_widgets(exps, [(False, False)])
        exp = exps[1]
        exp.set_expanded(True)
        _repack(exp)
        with visible(p.get_paned(), 400, 400):

            exp.get_parent().update(exp)
            self.failUnlessEqual(
                exp.get_allocation().height,
                p.get_paned().get_allocation().height - 3 *
                (100 + handle_size))

            for w in [w for w in exps if w is not exp]:
                w.get_parent().update(w)

            res, msg = relatively_close_test(
                           exp.get_allocation().height,
                           p.get_paned().get_allocation().height - 3 *
                           (title_size + 5 + handle_size))
            self.failUnless(res, msg)


class TConfigMultiRPaned(object):

    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_basic(self):
        self.assertTrue(config.get("memory", "pane_widths", None) is None)

        p = self.Kind("memory", "pane_widths")
        sws = [Gtk.ScrolledWindow() for _ in range(3)]
        p.set_widgets(sws)

        paneds = p.get_paneds()
        paneds[0].set_relative(0.4)
        paneds[1].set_relative(0.6)
        p.save_widths()

        widths = config.getstringlist("memory", "pane_widths")
        self.assertAlmostEqual(float(widths[0]), 0.4)
        self.assertAlmostEqual(float(widths[1]), 0.6)

        config.remove_option("memory", "pane_widths")


class TConfigMultiRHPaned(TestCase, TConfigMultiRPaned):
    Kind = ConfigMultiRHPaned


class TConfigMultiRVPaned(TestCase, TConfigMultiRPaned):
    Kind = ConfigMultiRVPaned
