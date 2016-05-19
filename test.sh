#!/usr/bin/env bash
# This script runs nosetests for the whole project.
# It also generates a coverage report when the "coverage" module is installed.
# When you specify the argument 'html', a HTML report will be generated, too.

# Note: to run the tests, sage must be in your path.  If necessary do
# export PATH=$PATH:/path/to/sage
# To run it, first install or upgrade "nose", "unittest2" and "coverage".
# e.g. $ pip install --user -U nose coverage unittest2
# or inside the Sage environment: $ easy_install -U nose
#                                 $ easy_install -U coverage
#                                 $ easy_install -U unittest2
# Second, call it in three ways, either
# $ ./test.sh to test all
# or
# $ ./test.sh coverage
# to test all and report test coverage
# or (for example)
# $ ./test.sh  lmfdb/knowledge
# to test only a part of LMFDB

cd `dirname "$0"`

# get rid of all cached .pyc files!
find . -name '*.pyc' -delete

HTML=''
WHAT=''
COVER=''
if [[ "$1" == "coverage" ]]; then
  rm -rf lmfdb/cover
  HTML='--cover-html'
  COVER='--with-coverage --cover-erase --cover-package=lmfdb $HTML'
else
  WHAT="$@"
fi

ARGS='-v -s --testmatch="(?:^|\/)[Tt]est_"'

SAGE_COMMAND=$SAGE
if [[ "$SAGE_COMMAND" == "" ]]; then
  SAGE_COMMAND=sage
fi
echo "Using Sage command $SAGE_COMMAND"

if [[ -n $WHAT ]]; then
   eval "$SAGE_COMMAND -sh -c 'nosetests $ARGS $WHAT $COVER'"
else
   cd lmfdb
   eval "$SAGE_COMMAND -sh -c 'nosetests $ARGS $COVER'"
fi

