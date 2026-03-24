# Copyright 2012 Christoph Reiter
#
# SPDX-License-Identifier: GPL-2.0-or-later

import sys
import os

if sys.platform == "win32":
    # To prevent us loading DLLs in the system directory which clash
    # with the ones we ship.
    # https://github.com/quodlibet/quodlibet/issues/2817
    from ctypes import windll

    windll.kernel32.SetDllDirectoryW(os.path.dirname(sys.executable))

from .util.i18n import _, C_, N_, ngettext, npgettext
from .util.dprint import print_d, print_e, print_w
from ._init import init_cli, init
from ._main import (
    get_base_dir,
    is_release,
    get_user_dir,
    app,
    set_application_info,
    init_plugins,
    enable_periodic_save,
    run,
    finish_first_session,
    get_image_dir,
    is_first_session,
    get_build_description,
    get_build_version,
    get_cache_dir,
)


(
    _,
    C_,
    N_,
    ngettext,
    npgettext,
    is_release,
    init,
    init_cli,
    print_e,
    get_base_dir,
    print_w,
    print_d,
    get_user_dir,
    app,
    set_application_info,
    init_plugins,
    enable_periodic_save,
    run,
    finish_first_session,
    get_image_dir,
    is_first_session,
    get_build_description,
    get_build_version,
    get_cache_dir,
)
