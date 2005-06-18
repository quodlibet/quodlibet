#!/bin/sh

if test "$1" = "--help" -o "$1" = "-h"; then
 echo "Usage: $0 [TestName] ..."
 exit 0
else
 python -c "import tests; tests.unit('$*'.split())"
fi
