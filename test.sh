#!/usr/bin/env bash
# This script runs nosetests for the whole project.
# It also generates a coverage report when the "coverage" module is installed.
# including a HTML report 

# Note: to run the tests, sage must be in your path.  If necessary do
# export PATH=$PATH:/path/to/sage
# To run it, first install or upgrade "nose", "unittest2" "coverage" and "pyflakes".
# e.g. $ pip install --user -U nose coverage unittest2 pyflakes
# or inside the Sage environment: $ easy_install -U nose
#                                 $ easy_install -U coverage
#                                 $ easy_install -U unittest2
#                                 $ easy_install -U pyflakes
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

WHAT=''
COVER=''
if [[ "$1" == "coverage" ]]; then
  rm -rf lmfdb/cover
  COVER='--with-coverage --cover-erase --cover-package=lmfdb --cover-html'
else
  WHAT="$@"
fi

echo "Running pyflakes..."
read PYFLAKES_ERRCNT < <(find . | grep "\.py$" | xargs pyflakes 2>&1 | tee /dev/stderr | grep "py:" -c)
if [[ $PYFLAKES_ERRCNT > 0 ]]; then
  echo "WARNING: pyflakes reported $PYFLAKES_ERRCNT error(s)"
else
  echo "pyflakes is happy"
fi

ARGS='-v -s --with-doctest --testmatch="(?:^|\/)[Tt]est_"'

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

if [[ $PYFLAKES_ERRCNT > 0 ]]; then
    printf "\nWARNING: pyflakes reported $PYFLAKES_ERRCNT error(s)\n"
fi
