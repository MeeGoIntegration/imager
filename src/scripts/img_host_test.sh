#!/bin/bash

set -x

IP=$1;shift
PORT=$1;shift
USB_PORT=$1;shift
USB_PWR=$1;shift
ID=$1;shift

TEST_PACKAGES=$*

FAIL=0

if [ ! -z "$TEST_PACKAGES" ]; then

  mkdir -p /tmp/$ID/results
  
  for PACKAGE in $TEST_PACKAGES; do
  
    TESTFILES="$(rpm -ql $PACKAGE | grep '/tests.xml' | xargs)"
    for FILE in $TESTFILES ; do 
        if test -f "$FILE" ; then
  	  IP=$IP PORT=$PORT USB_PORT=$USB_PORT USB_PWR=$USB_PWR ID=$ID testrunner-lite -v -a -f $FILE -o /tmp/$ID/results/$PACKAGE.xml
  	  [ $? -eq 0 ] || FAIL=1 
        fi
    done
    
  done
fi

sleep 5

exit $FAIL
