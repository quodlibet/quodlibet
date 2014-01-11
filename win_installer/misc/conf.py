# this gets executed by const.py to override USERDIR

import os
import sys


_file_path = __file__.decode(sys.getfilesystemencoding())
USERDIR = os.path.join(os.path.dirname(os.path.realpath(_file_path)),
                       "..", "..", "..", "config")
