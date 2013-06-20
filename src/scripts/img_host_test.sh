#!/bin/bash

set -x

TEST_PACKAGES=$@

FAIL=0

if [ ! -z "$TEST_PACKAGES" ]; then

  mkdir -p /tmp/results
  
  for PACKAGE in $TEST_PACKAGES; do
  
    TESTFILES="$(rpm -ql $PACKAGE | grep '/tests.xml' | xargs)"
    for FILE in $TESTFILES ; do 
        if test -f "$FILE" ; then
  	  testrunner-lite -v -a -f $FILE -o /tmp/results/$PACKAGE.xml
  	  [ $? -eq 0 ] || FAIL=1 
        fi
    done
    
  done
fi

sleep 5

exit $FAIL
