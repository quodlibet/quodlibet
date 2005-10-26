# Copyright 2004 Gustavo J. A. M. Carneiro
#           2005 Joe Wreschnig, Ton van den Heuvel
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import pango
import gtk
import gtk.gdk as gdk
import gobject
import re
import config
import util
from util import tag
import qltk

class Osd(object):
    PLUGIN_NAME = "On-Screen Display"
    PLUGIN_DESC = "Display song information on your screen when it changes."
    PLUGIN_VERSION = "0.14.1"

    BORDER = 4
    __sid = None
    __window = None
    __startDragPosition = None
    __width = 0

    def PluginPreferences(self, parent):
        w = gtk.Window()
        w.set_title("OSD Preferences")
        w.set_resizable(False)
        w.set_border_width(12)
        w.add(gtk.VBox(spacing=12))

        def Label(t): l = gtk.Label(t); l.set_alignment(0.0, 0.5); return l

        colors = config.get("plugins", "osd_colors").split()

        # Font and colour options.
        fc_box = gtk.VBox(spacing=6)

        text_a = gtk.ColorButton(gtk.gdk.color_parse(colors[0]))
        text_b = gtk.ColorButton(gtk.gdk.color_parse(colors[1]))
        border = gtk.ColorButton(gtk.gdk.color_parse(colors[2]))
        panel = gtk.ColorButton(gtk.gdk.color_parse(colors[3]))
        panel.set_use_alpha(True)

        buttons = [text_a, text_b, border, panel]
        for button in buttons:
            button.connect('color-set', self.__color_set, buttons)

        alpha = float(config.get('plugins', 'osd_transparency')) / 256.0
        panel.set_alpha(int(alpha * 65536))

        t = gtk.Table(2, 4)
        t.set_col_spacings(6)
        t.set_row_spacings(6)
        t.attach(Label("Text color #1:"), 0, 1, 0, 1)
        t.attach(Label("Text color #2:"), 0, 1, 1, 2)
        t.attach(Label("Panel color:"), 2, 3, 0, 1)
        t.attach(Label("Panel border color:"), 2, 3, 1, 2)
        t.attach(text_a, 1, 2, 0, 1, gtk.SHRINK)
        t.attach(text_b, 1, 2, 1, 2, gtk.SHRINK)
        t.attach(panel, 3, 4, 0, 1, gtk.SHRINK)
        t.attach(border, 3, 4, 1, 2, gtk.SHRINK)

        font = gtk.FontButton(config.get("plugins", "osd_font"))
        font.set_size_request(200, -1)
        font.connect('font-set', self.__font_set)

        fc_box.pack_start(t, expand=False)
        fc_box.pack_start(font, expand=False)

        # Positioning options.
        pos_box = gtk.HBox(spacing=6)

        cb_center_y = gtk.CheckButton('Center vertically')
        cb_center_y.set_active(config.getboolean("plugins", "osd_center_y"))
        cb_center_y.connect('toggled', self.__centering_toggled)
        cb_center_y.set_name("y")

        cb_center_x = gtk.CheckButton('Center horizontally')
        cb_center_x.set_active(config.getboolean("plugins", "osd_center_x"))
        cb_center_x.connect('toggled', self.__centering_toggled)
        cb_center_x.set_name("x")

        pos_box.pack_start(cb_center_x, expand=False)
        pos_box.pack_start(cb_center_y, expand=False)

        # Miscellaneous options.
        misc_box = gtk.HBox(spacing=6)

        timeout = gtk.SpinButton(
            gtk.Adjustment(float(config.get('plugins', 'osd_timeout')),
                           0, 60.0, 0.1, 1.0, 1.0),
            0.1, 1)
        timeout.set_numeric(True)
        timeout.connect('value-changed', self.__timeout_changed);

        misc_box.pack_start(Label("Display delay: "), expand=False)
        misc_box.pack_start(timeout, expand=False);
        misc_box.pack_start(Label("seconds"), expand=False)

        color_frame = qltk.Frame(_("Font & colors"), bold=True, child=fc_box);
        positioning_frame = qltk.Frame(_("Positioning"), bold=True, child=pos_box);
        misc_frame = qltk.Frame(_("Miscellaneous"), bold=True, child=misc_box);

        w.child.pack_start(color_frame)
        w.child.pack_start(positioning_frame)
        w.child.pack_start(misc_frame)
        w.child.show_all()

        w.set_transient_for(parent)
        w.connect('delete-event', self.__hide_preferences)
        w.connect('show', self.__show_panel)

        return w

    def __centering_toggled(self, toggle):
        opt = "osd_center_" + toggle.get_name()
        config.set('plugins', opt, str(toggle.get_active()))
        self.__show_panel()

    def __show_panel(self, widget=None):
        if self.__sid:
            gobject.source_remove(self.__sid)
            self.__sid = None

        self.__display(self.__get_preview_msg(), is_preview=True)

    def __hide_preferences(self, prefs, event):
        config.set("plugins", "osd_custom_position", "%d %d" % (
            tuple(self.__custom_position)))
        self.__hide_panel()
        prefs.hide()
        return True

    def __timeout_changed(self, spinbutton):
        config.set("plugins", "osd_timeout", spinbutton.get_value())

    def __font_set(self, font):
        config.set("plugins", "osd_font", font.get_font_name())
        self.__show_panel()

    def __get_preview_msg(self):
        color = config.get('plugins', 'osd_colors').split()[1]
        return ("<message id='quodlibet'>"
                "<span foreground='%s'>\xe2\x99\xaa</span> "
                "Drag to position "
                "<span foreground='%s'>\xe2\x99\xaa</span>"
                "</message>") % (color, color)

    def __color_set(self, color):
        colors = []
        for colorButton in [self.__textColorAButton, self.__textColorBButton, self.__panelBorderColorButton, self.__panelColorButton]:
            color = colorButton.get_color()
            colors.append("#%02x%02x%02x" % (color.red // 256, color.green // 256, color.blue // 256))

            # Write panel border transparency.
            if colorButton.get_use_alpha():
                config.set('plugins', 'osd_transparency', str(colorButton.get_alpha() // 256))

        config.set('plugins', 'osd_colors', ' '.join(colors))

        # Refresh OSD panel.
        self.__show_panel()

    def __dragging(self, widget, event):
        widget.move(int(event.x_root - self.__startDragPosition[0]), int(event.y_root - self.__startDragPosition[1]))

    def __start_dragging(self, widget, event):
        self.__startDragPosition = event.x, event.y
        self.__motionHandler = self.__window.connect('motion_notify_event', self.__dragging)

    def __end_dragging(self, widget, event):
        self.__window.disconnect(self.__motionHandler)
        self.__custom_position = self.__window.get_position()

        # Refresh OSD panel.
        self.__show_panel()

    def __init__(self):
        for key, value in {
            "custom_position": "-1 -1",
            "colors": "#ffbb00 #ff8800 #000000 #303030",
            "font": "Sans 22",
            "timeout": "7.5",
            "transparency": "75",
            "center_x": "1",
            "center_y": "0"}.items():
            try: config.get("plugins", "osd_" + key)
            except: config.set("plugins", "osd_" + key, value)

        color_str = config.get("plugins", "osd_colors") 
        for i in [len(config.get("plugins", "osd_colors").split()),4]:
            if len(config.get("plugins", "osd_colors").split()) < 4:
                color_str += " #000000"

        config.set("plugins", "osd_colors", color_str)

        self.__custom_position = map(
            int, config.get("plugins", "osd_custom_position").split())
        self.__window = gtk.Window(gtk.WINDOW_POPUP)
        self.__window.add_events(gtk.gdk.POINTER_MOTION_MASK)
        self.__window.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.__window.add_events(gtk.gdk.BUTTON_RELEASE_MASK)

    def plugin_on_song_started(self, song):
        if song is None: return

        cover = song.find_cover()

        color2 = config.get("plugins", "osd_colors").split()[1]

        # \xe2\x99\xaa is a music note.
        msg = "\xe2\x99\xaa "

        msg += "<span foreground='%s' style='italic'>%s</span>" %(
            color2, util.escape(song("~title~version")))
        msg += " <span size='small'>(%s)</span> " % song("~length")
        msg += "\xe2\x99\xaa\n"

        msg += "<span size='x-small'>"
        for key in ["artist", "album", "tracknumber"]:
            if key in song:
                msg += ("<span foreground='%s' size='xx-small' "
                        "style='italic'>%s:</span> %s   "%(
                    (color2, tag(key), util.escape(song.comma(key)))))
        msg = msg.strip() + "</span>"
        if isinstance(msg, unicode):
            msg = msg.encode("utf-8")
        msg = "<message id='quodlibet'>%s</message>" % msg
        self.__display(msg, cover)

    def plugin_on_song_ended(self, song, stopped):
        if self.__sid:
            gobject.source_remove(self.__sid)
            self.__sid = None

    def __display(self, msg, cover=None, is_preview=False):
        text = msg[msg.index(">")+1:msg.rindex("<")]

        if self.__window.get_property('visible'):
            if self.__window.child:
                child = self.__window.child
                self.__window.remove(self.__window.child)
                child.destroy()
            self.__window.hide()
            gobject.idle_add(self.__display, msg, cover, is_preview)
            return

        fgcolor = config.get('plugins', 'osd_colors').split()[0]
        panelBorderColor = config.get('plugins', 'osd_colors').split()[2]
        panelColor = config.get('plugins', 'osd_colors').split()[3]
        center_x = config.getboolean('plugins', 'osd_center_x')
        center_y = config.getboolean('plugins', 'osd_center_y')

        try:
            fontdesc = pango.FontDescription(config.get("plugins", "osd_font"))
        except: fontdesc = pango.FontDescription("Sans 22")

        darea = gtk.DrawingArea()
        win = self.__window
        win.add(darea)
        darea.show()

        # Generate shadow text from colored markup text.
        p = re.compile('#[0-9a-zA-Z]{6}')
        shadow_text = p.sub('#000000', text)

        layout = win.create_pango_layout('')
        layout.set_markup(shadow_text)
        layout.set_justify(False)
        layout.set_alignment(pango.ALIGN_CENTER)
        layout.set_font_description(fontdesc)

        monitor = gdk.Screen.get_monitor_geometry(gdk.screen_get_default(), 0)
        MAX_WIDTH = monitor.width - 8
        layout.set_width(pango.SCALE*MAX_WIDTH)
        layout.set_wrap(pango.WRAP_WORD)

        # Initialize width and height with the size of the pango layout.
        self.__width, height = layout.get_pixel_size()
        
        # Calculate final panel height by adding a border.
        height += self.BORDER * 4

        # Calculate the cover dimensions (if one is available)
        draw_cover = not cover is None and not is_preview
        if draw_cover:
            cover_dim = height - 2 * self.BORDER
        else:
            cover_dim = 0

        # Calculate text offsets.
        off_x = self.BORDER * 4 + cover_dim + self.__width / 2 - MAX_WIDTH / 2
        off_y = self.BORDER * 2

        # Calculate panel width.
        self.__width += self.BORDER * 6 + cover_dim

        darea.set_size_request(self.__width, height)
        darea.realize()

        # Draw the surrounding panel.
        pixmap = gtk.gdk.Pixmap(darea.window, self.__width, height)
        bg_gc = gdk.GC(pixmap)
        bg_gc.copy(darea.style.fg_gc[gtk.STATE_NORMAL])
        bg_gc.set_colormap(darea.window.get_colormap())

        win.width = self.__width
        win.height = height

        # Draw contents.
        panelBgColor = '#%02x%02x%02x' % (int(panelColor[1:3], 16), int(panelColor[3:5], 16),  int(panelColor[5:7], 16))

        bg_gc.set_foreground(darea.get_colormap().alloc_color(panelBgColor))
        pixmap.draw_rectangle(bg_gc, True, 1, 1, self.__width - 2, height - 2)

        #
        # Get root window contents at panel position.
        #
        if self.__custom_position[0] == -1:
            position = gdk.screen_height() - win.height - 48
            winX = monitor.x + monitor.width / 2 - win.width / 2
            winY = monitor.y + position
        else:
            if center_x:
                winX = monitor.x + monitor.width / 2 - win.width / 2
            else:
                winX = self.__custom_position[0]

            if center_y:
                winY = monitor.y + monitor.height / 2 - win.height / 2 
            else:
                winY = self.__custom_position[1]

        # Transparency is not enabled in preview mode.
        root_win = gdk.Screen.get_root_window(gdk.screen_get_default())
        root_pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 0, 8, self.__width, height)
        root_pb.get_from_drawable(root_win, root_win.get_colormap(), winX, winY, 0, 0, self.__width, height)

        # Composite panel pixbuf with root pixbuf
        compositedPixBuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 0, 8, self.__width, height)
        compositedPixBuf.get_from_drawable(pixmap, pixmap.get_colormap(), 0, 0, 0, 0, self.__width, height)
        alpha = int(config.get('plugins', 'osd_transparency'))
        compositedPixBuf.composite(root_pb, 0, 0, self.__width, height, 0, 0, 1, 1, gtk.gdk.INTERP_BILINEAR, alpha)
        pixmap.draw_pixbuf(darea.style.fg_gc[gtk.STATE_NORMAL], root_pb, 0, 0, 0, 0, -1, -1)

        # Draw panel border.
        bg_gc.set_foreground(darea.get_colormap().alloc_color(panelBorderColor))
        pixmap.draw_rectangle(bg_gc, False, 0, 0, self.__width - 1, height - 1)

        # Draw layout.
        fg_gc = gdk.GC(pixmap) 
        fg_gc.copy(darea.style.fg_gc[gtk.STATE_NORMAL])
        fg_gc.set_colormap(darea.window.get_colormap())
        fg_gc.set_foreground(darea.get_colormap().alloc_color("black"))

        # Draw shadow.
        pixmap.draw_layout(fg_gc, off_x + 1, off_y + 1, layout)

        # Draw actual text.
        fg_gc.set_foreground(darea.get_colormap().alloc_color(fgcolor))
        layout.set_markup(text)
        pixmap.draw_layout(fg_gc, off_x, off_y, layout)

        # Draw the cover image (if available).
        if not cover is None and not is_preview:
            try:
                cover = gtk.gdk.pixbuf_new_from_file_at_size(
                    cover.name, cover_dim, cover_dim)
            except: 
                cover = None
            else:
                left = self.BORDER + (cover_dim - cover.get_width())/2
                top = self.BORDER + (cover_dim - cover.get_height())/2
                pixmap.draw_pixbuf(darea.style.fg_gc[gtk.STATE_NORMAL], cover, 0, 0, left, top)
                # Draw a border around the cover image.
                bg_gc.set_foreground(darea.get_colormap().alloc_color("black"))
                pixmap.draw_rectangle( bg_gc, False, left - 1, top - 1, cover.get_width() + 1, cover.get_height() + 1)

        darea.window.set_back_pixmap(pixmap, False)

        win.move(winX, winY)
        win.show_all()
        self.__window = win

        if not is_preview:
            # An active OSD window is closed after a user-specified time.
            timeout = config.get('plugins', 'osd_timeout')
            if timeout > 0:
                self.__sid = gobject.timeout_add(int(float(timeout) * 1000), self.__hide_panel)
            # And it can be closed by clicking it.
            win.connect('button-press-event', self.__hide_panel)
        # A preview OSD can be dragged around.
        else: 
            win.connect('button-press-event', self.__start_dragging)
            win.connect('button-release-event', self.__end_dragging)

    def __hide_panel(self, window=None, event=None):
        if self.__window.child:
            c = self.__window.child
            self.__window.remove(c)
            c.destroy()
            self.__window.hide()
        if self.__sid:
            gobject.source_remove(self.__sid)
            self.__sid = None
