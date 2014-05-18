# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import config


def get_puid_lookup():
    return config.get("plugins", "fingerprint_puid_lookup", "no_mbid")


def get_api_key():
    return config.get("plugins", "fingerprint_acoustid_api_key", "")
