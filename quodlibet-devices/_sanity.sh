#!/bin/sh

if test "$1" = "--help" -o "$1" = "-h"; then
 echo "Usage: $0 --sanity | [TestName] ..."
 exit 0
elif [ "$1" = "--sanity" ]; then
 echo "Running static sanity checks."
 grep "except None:" *.py */*.py
 for J in browsers qltk; do
  for I in ${J}/*.py; do
   if [ ! -e "tests/test_${J}_`basename $I | sed s:/:_:`" ]; then
    echo "MISSING TESTS: $I"
   fi
  done
 done
else
 python2.4 -c "import tests; tests.unit('$*'.split())"
 if [ "$1" = "--trace" ]; then
   rm `grep -L '>>>>>>' coverage/*.cover`
 fi
fi
