import os

# Make a directory, including all directories below it.
def mkdir(dir):
    if not os.path.exists(dir):
        base = os.path.split(dir)[0]
        if base and not os.path.exists(base): mkdir(base)
        os.mkdir(dir)

# Escape a string in a manner suitable for XML/Pango.
def escape(str):
    return str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
