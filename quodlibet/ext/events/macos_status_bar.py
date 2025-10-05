# Copyright 2025 Umiko
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys, traceback
from pathlib import Path
from quodlibet import app
from quodlibet.plugins.events import EventPlugin

class MacOSStatusBarPlugin(EventPlugin):
    PLUGIN_ID   = "macos_status_bar"
    PLUGIN_NAME = "MacOS Status Bar"
    PLUGIN_DESC = "Status bar application with player controls, song/album/artist information, album cover, and real-playback_t playback monitoring (MacOS Only)."

    def __init__(self):
        super().__init__()
        self._cocoa = None

    def enabled(self):
        """
        Enable the plugin with the plugin interface
        """
        if sys.platform != "darwin":
            return False
        
        # Wait to import anything until we confirm we're running on a "Darwin" machine
        try:
            import objc
            from AppKit import (NSCalibratedRGBColorSpace, NSImage, NSStatusBar, NSImageOnly, NSStatusBar, NSImage, NSApp, NSVariableStatusItemLength, NSMenu, NSMenuItem, NSView, NSImageView, NSColor, NSTextField, NSButton)
            from Foundation import NSObject, NSTimer, NSRunLoop, NSRunLoopCommonModes
            from Quartz.CoreGraphics import CGColorCreateGenericRGB
        except Exception:
            traceback.print_exc()
            return False

        @staticmethod
        def _set_status_bar_icon(button, image: NSImage):
            """
            Set an image as the status bar icon. This is set to the album cover by default
            """
            thickness = NSStatusBar.systemStatusBar().thickness()
            side = max(1.0, thickness - 1.0 * 2)

            image.setSize_((side, side))
            button.setTitle_("")
            button.setImage_(image)

            try:
                button.setImagePosition_(NSImageOnly)
            except Exception:
                button.setImagePosition_(2)

        @staticmethod
        def _ns_color_to_cg_color(nscolor):
            """
            Convert NSColor → CGColor (This is just to shush a few ObjCPointerWarnings)
            """
            cg = nscolor.colorUsingColorSpaceName_(NSCalibratedRGBColorSpace)

            if cg is None:
                cg = nscolor

            r = cg.redComponent()
            g = cg.greenComponent()
            b = cg.blueComponent()
            a = cg.alphaComponent()

            return CGColorCreateGenericRGB(r, g, b, a)
        
        @staticmethod
        def _mmss(current=None, duration=None):
            """
            Handle the millisecond -> MM:SS conversion for real-playback_t playback playback_t
            """
            if current:
                minutes, seconds = divmod(current // 1000, 60)
                return f"{minutes:02d}:{seconds:02d}"
            
            if duration:
                minutes, seconds = divmod(max(0, int(duration or 0)), 60)
                return f"{minutes:02d}:{seconds:02d}"
            
        @staticmethod
        def _cover_img_from_folder():
            """
            Attempt to locate a cover image to use across the plugin
            """
            try:
                s = app.player.song

                if not s:
                    return None
                
                # Attempt to locate the same directory where the audio file currently resides
                fn = (s("~filename") or s("file") or s("location") or "").replace("file://","")

                if not fn:
                    return None

                folder = Path(fn).parent

                if not folder.exists():
                    return None
                
                # Search for a cover photo, defaults to the same directory as the audio file
                # NOTE: This isn't required for the plugin, however, it makes it look a lot nicer as the status bar icon is actually the album cover (or just an image)
                for name in ("cover.jpg", "cover.png", "folder.jpg", "folder.png", f"{folder.name}.jpg", f"{folder.name}.png"):
                    cover_img = folder / name

                    if cover_img.exists():
                        return cover_img

                for cover_img in folder.iterdir():
                    if cover_img.suffix.lower() in {".jpg",".jpeg",".png",".webp"} and cover_img.is_file():
                        return cover_img

            except Exception:
                pass

            return None
        
        class StatusBarView(NSView):
            """
            The main class for handling drawing and events
            """
            PLUGIN_WIDTH = 320.0
            PLUGIN_HEIGHT = 150.0
            PADDING = 10.0

            def isFlipped(self):
                """
                Use a flipped coordinate system
                """
                return True

            def initWithFrame_(self, frame):
                """
                Initialize the frame and configure various aspects of the plugin using the rectangle specifications
                """
                self = objc.super(StatusBarView, self).initWithFrame_(frame)

                if self is None:
                    return None

                self.setAutoresizesSubviews_(False)

                # Configure the image's "container"
                self.img_container = NSImageView.alloc().initWithFrame_(((0, 0), (self.PLUGIN_WIDTH, self.PLUGIN_HEIGHT)))
                self.img_container.setImageScaling_(3)
                self.img_container.setWantsLayer_(True)
                self.img_container.layer().setMasksToBounds_(True)

                try:
                    self.img_container.layer().setContentsGravity_("resizeAspectFill")
                except Exception:
                    pass

                self.addSubview_(self.img_container)

                # Overlays a slight dark tint on the cover image section
                self.overlay = NSView.alloc().initWithFrame_(self.img_container.frame())
                self.overlay.setWantsLayer_(True)
                self.overlay.layer().setBackgroundColor_(_ns_color_to_cg_color(NSColor.blackColor().colorWithAlphaComponent_(0.10)))
                self.addSubview_(self.overlay)

                y = self.PLUGIN_HEIGHT + 10.0

                # Here we handle the placement for certain text fields such as song name and album name
                self.title = NSTextField.alloc().initWithFrame_(((self.PADDING, y), (self.PLUGIN_WIDTH - 20 * self.PADDING, 20.0)))
                self.subtitle = NSTextField.alloc().initWithFrame_(((self.PADDING, y + 22.0), (self.PLUGIN_WIDTH - 2 * self.PADDING, 18.0)))

                # Set the size and color for the previously added text fields
                for text_type, size, color in ((self.title, 14.0, NSColor.labelColor()), (self.subtitle, 12.0, NSColor.secondaryLabelColor())):
                    text_type.setBezeled_(False)
                    text_type.setDrawsBackground_(False)
                    text_type.setEditable_(False)
                    text_type.setSelectable_(False)
                    text_type.setFont_(text_type.font().fontWithSize_(size))
                    text_type.setTextColor_(color)

                self.addSubview_(self.title)
                self.addSubview_(self.subtitle)

                # Here we configure the player controls (buttons) and playback playback_t
                # This includes placement, text color, and icon specification
                y += 55.0

                self.btn_prev = self._make_icon_button("backward.fill", "prev", self.PLUGIN_WIDTH / 2 - 80)
                self.btn_play = self._make_icon_button("play.fill", "playpause", self.PLUGIN_WIDTH / 2 - 14)
                self.btn_next = self._make_icon_button("forward.fill", "next", self.PLUGIN_WIDTH / 2 + 50)
                self.addSubview_(self.btn_prev); self.addSubview_(self.btn_play); self.addSubview_(self.btn_next)

                self.playback_t = NSTextField.alloc().initWithFrame_(((self.PLUGIN_WIDTH - 85, y - 50.0), (80, 16)))
                self.playback_t.setBezeled_(False)
                self.playback_t.setDrawsBackground_(False)
                self.playback_t.setEditable_(False)
                self.playback_t.setSelectable_(False)
                self.playback_t.setAlignment_(2)
                self.playback_t.setFont_(self.playback_t.font().fontWithSize_(11.0))
                self.playback_t.setTextColor_(NSColor.tertiaryLabelColor())
                self.addSubview_(self.playback_t)

                self.setFrame_(((0.0, 0.0), (self.PLUGIN_WIDTH, y + 40.0)))
                return self

            @objc.python_method
            def _symbol(self, name: str):
                """
                Here we try to use builtin symbols/images provided by MacOS (mainly "play.fill" and "pause.fill" for dynamic play/pause within the plugin)
                """
                try:
                    img_symbol = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)

                    if img_symbol:
                        try:
                            img_symbol.setTemplate_(True)
                        except Exception:
                            pass

                        return img_symbol
                except Exception:
                    pass

                return None

            @objc.python_method
            def _image_only(self, btn):
                """
                A simple function for mainly just cleaning up the appearence of the symbol buttons after assigning them
                """
                try:
                    btn.setTitle_("")
                    btn.setImagePosition_(NSImageOnly)
                except Exception:
                    btn.setImagePosition_(2)

                btn.setBordered_(False)

                try:
                    btn.setBezelStyle_(0)
                except Exception:
                    pass

                try:
                    btn.setContentTintColor_(NSColor.labelColor())
                except Exception:
                    pass

            @objc.python_method
            def _make_icon_button(self, sf_symbol: str, action: str, x: float):
                """
                Create the play/pause, next, and previous buttons at the bottom of the status bar widget using SF symbol syntax
                """
                b = NSButton.alloc().initWithFrame_(((x,  self.PLUGIN_HEIGHT + 60), (28.0, 28.0)))
                img = self._symbol(sf_symbol)

                if img:
                    b.setImage_(img)
                else:
                    # A fallback for certain symbols
                    # This can break the appearence of the player controls, but not the functionality
                    b.setTitle_({"prev":"«","playpause":"▶/⏸","next":"»"}.get(action, "•"))

                self._image_only(b)
                b.setTarget_(self)
                b.setAction_(action + ":")
                b.setWantsLayer_(True)
                b.layer().setCornerRadius_(14.0)
                b.layer().setBackgroundColor_(_ns_color_to_cg_color(NSColor.whiteColor().colorWithAlphaComponent_(0.18)))
                return b
            
            # Time for the Objective-C selectors
            def prev_(self, sender):
                app.player.previous()

            def playpause_(self, sender):
                app.player.playpause()

            def next_(self, sender):
                app.player.next()

            def update_content(self):
                """
                The primary content pipeline for the plugin
                """
                try:
                    s = app.player.song

                    # If unable to locate an artist's name, return "N/A"
                    artist = (s.comma("~people") if s else "") or (s("artist") if s else "") or "N/A"

                    # If unable to locate an title, return plugin name
                    title = (s("title") if s else "") or "MacOS Status Bar"

                    # If unable to locate an album, return "N/A"
                    album = (s("album") if s else "") or "N/A"
                    self.title.setStringValue_(title)

                    # The artist and album divider
                    self.subtitle.setStringValue_(" • ".join(p for p in (artist, album) if p))

                    # We want to make sure to get updates on the current position of the track's playback
                    current = int(app.player.get_position() or 0)

                    # The full duration of the song
                    duration = int(float(s("~#length") or 0)) if s else 0

                    # Here we display the data in widget. Thanks to `_mmss`, we can display it in a more comfortable format
                    self.playback_t.setStringValue_(f"{_mmss(current=current)} / {_mmss(duration=duration)}")

                    # Collect and display the cover image (checks the same directory as the audio file)
                    cov = _cover_img_from_folder()

                    # If no cover image is found, we just default to the application icon image
                    img = NSImage.alloc().initWithContentsOfFile_(str(cov)) if cov else NSApp.applicationIconImage()
                    self.img_container.setImage_(img)
                    self.overlay.setFrame_(self.img_container.frame())

                    # Here is where we handle the dynamic play/pause during playback
                    if app.player.paused:
                        icon = self._symbol("play.fill")
                    else:
                        icon = self._symbol("pause.fill")

                    # Set the image/symbol accordingly
                    if icon:
                        self.btn_play.setImage_(icon)
                        self._image_only(self.btn_play)

                except Exception:
                    traceback.print_exc()

        class StatusBarController(NSObject):
            """
            The controller is just a simple class for handling some miscellaneous operations and making sure everything is tied together. The only real notable functions are `tick_` and `NSRunLoop.currentRunLoop()`
            """
            def init(self):
                self = objc.super(StatusBarController, self).init()

                if self is None:
                    return None

                self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
                self.button = self.status_item.button()
                self.button.setTitle_("MacOS Status Bar")

                self.menu = NSMenu.alloc().init()
                self.menu.setAutoenablesItems_(False)
                app_icon = NSApp.applicationIconImage()

                if app_icon:
                    _set_status_bar_icon(self.button, app_icon)

                self.status_bar_view = StatusBarView.alloc().initWithFrame_(((0.0, 0.0), (StatusBarView.PLUGIN_WIDTH, StatusBarView.PLUGIN_HEIGHT + 28.0)))
                self.status_bar_view.update_content()
                self.header_item = NSMenuItem.alloc().init()
                self.header_item.setView_(self.status_bar_view)
                self.menu.addItem_(self.header_item)
                self.menu.addItem_(NSMenuItem.separatorItem())
                self.status_item.setMenu_(self.menu)

                try:
                    self.button.setTarget_(None)
                    self.button.setAction_(None)
                except Exception:
                    pass

                self.tick_(None)
                self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(1.0, self, "tick:", None, True)

                # This is what allows us to share the playback data in real-time via the plugin's UI
                # NSRunLoop:Timer basically comes down to this:
                # Per Apple: "A timer that fires after a certain time interval has elapsed, sending a specified message to a target object"
                NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

                return self
    
            def prevAction_(self, _):
                try:
                    app.player.previous()
                except Exception:
                    traceback.print_exc()

            def playPauseAction_(self, _):
                try:
                    app.player.playpause()
                except Exception:
                    traceback.print_exc()

            def nextAction_(self, _):
                try:
                    app.player.next()
                except Exception:
                    traceback.print_exc()

            def tick_(self, _):
                """
                Every "tick_", we run the `update_content()` method, alongside updating the image/cover
                """
                try:
                    if self.status_bar_view:
                        self.status_bar_view.update_content()

                    img = self.status_bar_view.img_container.image() if self.status_bar_view else None

                    if img:
                        _set_status_bar_icon(self.button, img)
                    else:
                        # This fallback happens if there's no image present
                        fallback = NSApp.applicationIconImage()

                        if fallback:
                            _set_status_bar_icon(self.button, fallback)

                except Exception:
                    traceback.print_exc()

            # Everything beyond this point handles disabling the plugin and making sure it gracefully disables

            def teardown(self):
                try:
                    if getattr(self, "timer", None):
                        self.timer.invalidate()
                        self.timer = None
                except Exception:
                    pass

        # Instantiate controller
        try:
            self._cocoa = StatusBarController.alloc().init()
        except Exception:
            traceback.print_exc()
            return False

        return True
    
    def disabled(self):
        try:
            if self._cocoa:
                self._cocoa.teardown()
        except Exception:
            pass

        self._cocoa = None
