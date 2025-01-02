# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from .misc import get_ca_file

from urllib import request as request_module
from http.client import HTTPException


Request = request_module.Request

UrllibError = EnvironmentError


def urlopen(*args, **kwargs):
    try:
        return request_module.urlopen(*args, **kwargs)
    except HTTPException as e:
        # https://bugs.python.org/issue8823
        raise OSError(e) from e


def install_urllib2_ca_file():
    """Makes urllib2.urlopen and urllib2.build_opener use the ca file
    returned by get_ca_file()
    """

    try:
        import ssl
    except ImportError:
        return

    base = request_module.HTTPSHandler

    class MyHandler(base):
        def __init__(self, debuglevel=0, context=None):
            ca_file = get_ca_file()
            if context is None and ca_file is not None:
                context = ssl.create_default_context(
                    purpose=ssl.Purpose.SERVER_AUTH, cafile=ca_file
                )
            base.__init__(self, debuglevel, context)

    request_module.HTTPSHandler = MyHandler
