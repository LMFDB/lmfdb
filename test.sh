#!/usr/bin/env bash
# This script runs nosetests for the whole project.
# It also generates a coverage report when the "coverage" module is installed.
# When you specify the argument 'html', a HTML report will be generated, too.

# To run it, first install or upgrade "nose", "unittest2" and "coverage".
# e.g. $ pip install --user -U nose coverage unittest2
# or inside the Sage environment: $ easy_install -U nose
#                                 $ easy_install -U coverage
#                                 $ easy_install -U unittest2
# Second, call it in two ways, either $ ./test.sh for coverage to test all
# or to test only a part of LMFDB:    $ ./test.sh lmfdb/knowledge

cd `dirname "$0"`

# get rid of all cached .pyc files!
find . -name '*.pyc' -delete

HTML=''
WHAT=''
if [[ "$1" == "html" ]]; then
  rm -rf lmfdb/cover
  HTML='--cover-html'
else
  WHAT="$@"
fi

ARGS='-v -s --testmatch="(?:^|[\b_\./-])[Tt]est_"'

SAGE_COMMAND=$SAGE
if [[ "$SAGE_COMMAND" == "" ]]; then
  SAGE_COMMAND=sage
fi
echo "Using Sage command $SAGE_COMMAND"

if [[ -n $WHAT ]]; then
   eval "$SAGE_COMMAND -sh -c 'nosetests $ARGS $WHAT'"
else
   cd lmfdb
   eval "$SAGE_COMMAND -sh -c 'nosetests $ARGS --with-coverage --cover-erase --cover-package=lmfdb $HTML'"
fi

