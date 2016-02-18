# -*- coding: utf-8 -*-
# Copyright 2005-2010   Joshua Kwan <joshk@triplehelix.org>,
#                       Michael Ball <michael.ball@gmail.com>,
#                       Steven Robertson <steven@strobe.cc>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import config


def config_get(key, default=''):
    return config.getboolean('plugins', 'brainz_' + key, default)
