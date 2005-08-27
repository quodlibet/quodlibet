#!/usr/bin/env python
# A quick implementation of zip, so we don't necessary depend on zip.

import sys
import zipfile
if __name__ == "__main__":
    try:
        z = zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED)
    except RuntimeError:
        print "W: Unable to deflate files. Using ZIP_STORED instead."
        z = zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_STORED)

    for fn in sys.argv[2:]:
        print "Adding", fn
        z.write(fn, arcname = fn)
    z.close()
