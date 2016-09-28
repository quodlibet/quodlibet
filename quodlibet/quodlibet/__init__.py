# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from .compat import PY2

if PY2:
    # some code depends on utf-8 default encoding (pygtk used to set it)
    reload(sys)
    sys.setdefaultencoding("utf-8")

from . import senf
sys.modules["senf"] = senf

from .util.i18n import _, C_, N_, ngettext, npgettext
from .util.dprint import print_d, print_e, print_w
from ._init import init_cli, init
from ._main import get_base_dir, is_release, get_user_dir, app, \
    set_application_info, init_plugins, enable_periodic_save, main, \
    finish_first_session, get_image_dir, is_first_session, \
    get_build_description, get_build_version


_, C_, N_, ngettext, npgettext, is_release, init, init_cli, print_e, \
    get_base_dir, print_w, print_d, get_user_dir, app, set_application_info, \
    init_plugins, enable_periodic_save, main, finish_first_session, \
    get_image_dir, is_first_session, get_build_description, \
    get_build_version
