# Copyright (C) 2018 Eoin O'Neill (eoinoneill1991@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk
from quodlibet import _, util
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons, ToggleButton
from quodlibet.plugins.gui import UserInterfacePlugin


class RatingBox(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, self)

        self.thumb_ups = 1
        self.thumb_downs = 1

        self.title = Gtk.Label("")
        self.title.set_line_wrap(True)
        self.title.set_lines(2)

        hbox = Gtk.Box()
        self.upvote = ToggleButton("👍")
        self.downvote = ToggleButton("👎")
        self.upvote.connect("toggled", self.__thumb_toggled)
        self.downvote.connect("toggled", self.__thumb_toggled)
        self.score_label = Gtk.Label("----")
        self.upvote.set_property("height-request", 50)
        self.downvote.set_property("height-request", 50)
        hbox.prepend(self.upvote, True, True, 5)
        hbox.prepend(self.downvote, True, True, 5)

        self.hbox = hbox
        self.prepend(self.title, False, False, 10)
        self.prepend(self.score_label, True, True, 5)
        self.prepend(self.hbox, False, False, 5)

    def set_current_title(self, title):
        self.title.set_text(title)

    def set_current_score(self, cth_up, cth_down):
        self.thumb_ups = cth_up
        self.thumb_downs = cth_down
        self.__set_pending_score_value(self.thumb_ups - self.thumb_downs)

    def poll_vote(self, reset=True):
        upward = 1 if self.upvote.get_active() else 0
        downward = 1 if self.downvote.get_active() else 0
        vote = (upward, downward)
        if reset:
            self.downvote.set_active(False)
            self.upvote.set_active(False)
        return vote

    def __set_pending_score_value(self, score):
        existing_score = self.thumb_ups - self.thumb_downs
        if score == existing_score:
            self.score_label.set_markup(util.bold(str(int(score))))
        elif score > existing_score:
            self.score_label.set_markup(
                '<b><span foreground="green">' + str(int(score)) + "</span></b>"
            )
        else:
            self.score_label.set_markup(
                '<b><span foreground="red">' + str(int(score)) + "</span></b>"
            )

    def __thumb_toggled(self, button):
        if button.get_active():
            if button == self.upvote:
                self.downvote.set_active(False)
            elif button == self.downvote:
                self.upvote.set_active(False)

        vote = self.poll_vote(False)
        self.__set_pending_score_value(
            self.thumb_ups + vote[0] - self.thumb_downs - vote[1]
        )


class ThumbRating(EventPlugin, UserInterfacePlugin):
    """Plugin for more hands off rating system using a
    thumb up / thumbdown system."""

    PLUGIN_ID = "Thumb Rating"
    PLUGIN_NAME = _("Thumb Rating")
    PLUGIN_DESC_MARKUP = _(
        "Adds a thumb-up / thumb-down scoring system "
        "which is converted to a rating value. Useful "
        "for keeping running vote totals and sorting by "
        "<b><tt>~#score</tt></b>."
    )
    PLUGIN_ICON = Icons.USER_BOOKMARKS

    # Threshold value where points should be recalculated
    score_point_threshold = 0.2

    def enabled(self):
        self.rating_box = RatingBox()

    def create_sidebar(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, )
        vbox.prepend(self.rating_box, False, False, 0)
        vbox.show_all()
        return vbox

    def disabled(self):
        self.rating_box.destroy()

    def plugin_on_song_ended(self, song, stopped):
        if song is not None:
            poll = self.rating_box.poll_vote()
            if poll[0] >= 1 or poll[1] >= 1:
                ups = int(song.get("~#wins") or 0)
                downs = int(song.get("~#losses") or 0)
                ups += poll[0]
                downs += poll[1]
                song["~#wins"] = ups
                song["~#losses"] = downs
                song["~#rating"] = ups / max((ups + downs), 2)
                # note: ^^^ Look into implementing w/ confidence intervals!
                song["~#score"] = ups - downs

    def plugin_on_song_started(self, song):
        if song is not None:
            ups = int(song("~#wins") or 0)
            downs = int(song("~#losses") or 0)

            # Handle case where there's no score but user has a defined rating.
            if (ups + downs == 0) and (song.get("~#rating")):
                percent = song["~#rating"]
                ups = int(percent * 10)
                downs = int((1.0 - percent) * 10.0)
                song["~#wins"] = ups
                song["~#losses"] = downs
            elif (
                song.get("~#rating")
                and abs((ups / max((ups + downs), 2)) - song["~#rating"])
                > self.score_point_threshold
            ):
                # Cases where rating and points are not in alignment.
                total = max(ups + downs, 10)
                percent = song["~#rating"]
                ups = int(percent * total)
                downs = int((1.0 - percent) * total)
                song["~#wins"] = ups
                song["~#losses"] = downs

            self.rating_box.set_current_score(ups, downs)
            self.rating_box.set_current_title(song("~artist~title"))
