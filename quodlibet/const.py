# -*- coding: utf-8 -*-
# Short string constants and long non-translated ones.

import os

HOME    = os.path.expanduser("~")
DIR     = os.path.join(HOME, ".quodlibet")
CONTROL = os.path.join(DIR,  "control")
CONFIG  = os.path.join(DIR,  "config")
CURRENT = os.path.join(DIR,  "current")
LIBRARY = os.path.join(DIR,  "songs")
ACCELS  = os.path.join(DIR,  "accels")

CREDITS = ["Joe Wreschnig",
           "Michael Urman",
           "Iñigo Serna",
           "Bastian Kleineidam",
           "Michal Nowikowski",

           "Anders Carlsson",
           "Sun Microsystems, Inc.",
           "Lee Willis",
           "Jan Arne Petersen",
           "Gustavo J. A. M. Carneiro"]

TBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
<artist> - <album>/<tracknumber>. <title>
<artist>/<album>/<tracknumber> - <title>"""

NBP_EXAMPLES = """\
<tracknumber>. <title>
<tracknumber|<tracknumber>. ><title>
<tracknumber> - <title>
<tracknumber> - <artist> - <title>
/path/<artist> - <album>/<tracknumber>. <title>
/path/<artist>/<album>/<tracknumber> - <title>"""

COPYRIGHT = """\
<u><span weight="bold" size="xx-large">Quod Libet</span></u>
&lt;quodlibet@lists.sacredchao.net&gt;
Copyright © 2004-2005"""
