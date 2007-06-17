import os

import quodlibet.util
from quodlibet.const import ENCODING, LOGDIR

LOGS = {}
MAX_LOG_SIZE = 1000

def log(string, log=None):
    if isinstance(string, unicode):
        string = string.encode("utf-8", "replace")

    log = log or "General"

    LOGS.setdefault(log, []).append(string)

    while len(LOGS[log]) > MAX_LOG_SIZE:
        LOGS[log].pop(0)

def names():
    return sorted(LOGS.keys())

def contents(name):
    return LOGS.get(name, ["No log available."])

def dump(path=LOGDIR):
    try:
        quodlibet.util.mkdir(path)
        for name in LOGS.keys():
            filename = os.path.join(path, name + ".log")
            fileobj = file(filename, "w")
            fileobj.write("\n".join(LOGS[name]) + "\n")
            fileobj.close()
            
    except (IOError, OSError):
        print "Unable to dump logs, you're boned."
    
