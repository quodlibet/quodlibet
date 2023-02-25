# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import datetime
from time import localtime, strftime
from typing import Text, Optional


def format_date(seconds: float, format_setting: Optional[Text] = None) -> Text:
    """Formats a date either with the default format,
     or the passed strftime-compatible format string"""
    try:
        date = datetime.fromtimestamp(seconds).date()
    except (OverflowError, ValueError, OSError):
        text = ""
    else:
        if format_setting:
            format_ = format_setting
        # use default behaviour-format
        else:
            today = datetime.now().date()
            days = (today - date).days
            if days == 0:
                format_ = "%X"
            elif days < 7:
                format_ = "%A"
            else:
                format_ = "%x"

        stamp = localtime(seconds)
        text = strftime(format_, stamp)
    return text
