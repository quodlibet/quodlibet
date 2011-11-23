import os

import quodlibet.util
from quodlibet.const import LOGDIR

LOGS = {}
MAX_LOG_SIZE = 1000
GENERAL = _("General")

def log(string, log=None):
    if isinstance(string, unicode):
        string = string.encode("utf-8", "replace")

    log = log or GENERAL

    LOGS.setdefault(log, []).append(string)

    while len(LOGS[log]) > MAX_LOG_SIZE:
        LOGS[log].pop(0)

def names():
    names = sorted(LOGS.keys())
    if GENERAL in names:
        names.remove(GENERAL)
        names.insert(0, GENERAL)
    return names

def contents(name):
    return LOGS.get(name, [_("No log available.")])

def dump(path=LOGDIR):
    try:
        quodlibet.util.mkdir(path)
        for name in LOGS.keys():
            filename = os.path.join(path, name + ".log")
            fileobj = file(filename, "w")
            fileobj.write("\n".join(LOGS[name]) + "\n")
            fileobj.close()
            
    except (IOError, OSError):
        print_w("Unable to dump logs.")
    
