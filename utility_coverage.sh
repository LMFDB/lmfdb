#!/usr/bin/env bash
# This script gives coverage on just the modules specified.
# This option is not currently available on the main test.sh (which makes sense
# since other tests need to be performed holistically).

SAGE_COMMAND=$SAGE
if [[ "$SAGE_COMMAND" == "" ]]; then
  SAGE_COMMAND=sage
fi
echo "Using Sage command $SAGE_COMMAND"


WHAT="$@"
COVER='--with-coverage --cover-erase --cover-package=lmfdb --cover-html'

if [[ -n $WHAT ]]; then
  eval "$SAGE_COMMAND -sh -c 'nosetests -v -s $COVER $WHAT'"
else
  eval "$SAGE_COMMAND -sh -c 'nosetests -v -s $COVER lmfdb/test_utils.py'"
fi
