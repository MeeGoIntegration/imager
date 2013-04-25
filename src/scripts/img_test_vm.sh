#!/bin/bash

set -x

COUNT=0
while $(! systemctl --quiet is-active user-session@1000.service) ; do 
  if [[ $COUNT -le 60 ]]; then
    sleep 1
    COUNT=$(( COUNT + 1 ))
  else
    break
  fi
done

TEST_PACKAGES=$@

if [ -z "$TEST_PACKAGES" ]; then

  TEST_PACKAGES="$(rpm -qal | grep '/tests.xml' | xargs -r rpm -qf)"

fi


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

exit $FAIL
