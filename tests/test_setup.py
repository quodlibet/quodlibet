# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import shutil
from pathlib import Path
from tempfile import mkdtemp

from _pytest.fixtures import fixture

import quodlibet
from gdist import create_po, GDistribution, create_pot, update_po, po_stats
from quodlibet.util import get_module_dir

SRC_FILE = Path(get_module_dir(quodlibet)).parent / "quodlibet.py"


@fixture
def dist(temp_po_dir) -> GDistribution:
    dist = GDistribution()
    dist.po_directory = str(temp_po_dir)
    return dist


@fixture
def temp_po_dir() -> Path:
    out_path = Path(mkdtemp())
    po_path = out_path / "po"
    po_path.mkdir()
    with open(po_path / "POTFILES.in", "w") as f:
        f.write(f"{SRC_FILE.name}\n")
    shutil.copy(SRC_FILE, out_path / SRC_FILE.name)
    return po_path


def test_create_po_command(dist):
    cmd = create_po(dist)
    cmd.lang = "fr_FR"
    cmd.run()


def test_create_pot_command(dist):
    cmd = create_pot(dist)
    cmd.run()


def test_update_po_command(dist, temp_po_dir):
    (temp_po_dir / "en_GB.po").touch()
    cmd = update_po(dist)
    cmd.lang = "en_GB"
    cmd.run()


def test_po_stats_command(dist, temp_po_dir):
    cmd = po_stats(dist)
    cmd.lang = "en_GB"
    cmd.run()
