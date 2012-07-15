#!/bin/bash

set +x

TEST_PACKAGES=$@

if [ x"$TEST_PACKAGES" = x ]; then

  TEST_PACKAGES=$(rpm -qal | grep "/tests.xml" | xargs rpm -qf)

fi

mkdir /tmp/results

FAIL=0

for PACKAGE in $TEST_PACKAGES; do

  TESTSFILE=$(rpm -ql $PACKAGE | grep "/tests.xml")

  testrunner-lite -v -a -f $TESTSFILE -o /tmp/results/$PACKAGE.xml
  
  [ $? -eq 0 ] || FAIL=1

done

exit $FAIL
