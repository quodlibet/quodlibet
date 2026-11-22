# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import quodlibet.config
from quodlibet import app
from quodlibet.formats import AudioFile
from quodlibet.qltk import find_widgets
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.tracknumbers import TrackNumbers
from quodlibet.qltk.views import HintedTreeView
from tests import TestCase, init_fake_app, destroy_fake_app


class TTrackNumbers(TestCase):
    def setUp(self):
        init_fake_app()
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()
        destroy_fake_app()

    def test_reordering_rows_renumbers_them(self):
        songs = [AudioFile({"~filename": f"/dev/{n}", "tracknumber": n}) for n in "123"]
        props = SongProperties(app.library, songs, app.window)
        page = TrackNumbers(props, app.library)
        props.emit("changed", songs)
        (view,) = find_widgets(page, HintedTreeView)
        model = view.get_model()
        assert not page.save.get_sensitive()

        # what a TreeView drag reorder does to the model
        model.insert(0, [model[2][0]])
        model.remove(model.get_iter(3))

        assert [(e.song, e.tracknumber) for e in model.values()] == [
            (songs[2], "1/3"),
            (songs[0], "2/3"),
            (songs[1], "3/3"),
        ]
        assert page.save.get_sensitive()
