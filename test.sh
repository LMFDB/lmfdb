#!/usr/bin/env bash
# This script runs pytest for the whole project.
# It also generates a coverage report when the "pytest-cov" plugin is
# installed, including a HTML report

# Note: to run the tests, sage must be in your path.  If necessary do
# export PATH=$PATH:/path/to/sage
# To run it, first install or upgrade "pytest", "unittest2" "pytest-cov" and
# "pyflakes".  e.g. $ pip install --user -U pytest pytest-cov unittest2 pyflakes
# or $ sage -pip install --user -U pytest pytest-cov unittest2 pyflakes
# or inside the Sage environment: $ easy_install -U pytest
#                                 $ easy_install -U pytest-cov
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
# To run tests with 3 cores in parallel, use
# $ ./test.sh -n 3

cd `dirname "$0"`

# get rid of all cached .pyc files!
find . -name '*.pyc' -delete

WHAT=''
COVER=''

if [[ "$1" == "coverage" ]]; then
  rm -rf lmfdb/htmlcov
  shift
  COVER='--cov=lmfdb --cov-report html'
fi

WHAT="$@"

echo "Running pyflakes..."
read PYFLAKES_ERRCNT < <(find . | grep "\.py$" | xargs pyflakes 2>&1 | tee /dev/stderr | grep "py:" -c)
if [[ $PYFLAKES_ERRCNT > 0 ]]; then
  echo "WARNING: pyflakes reported $PYFLAKES_ERRCNT error(s)"
else
  echo "pyflakes is happy"
fi

ARGS='-v -s'

SAGE_COMMAND=$SAGE
if [[ "$SAGE_COMMAND" == "" ]]; then
  SAGE_COMMAND=sage
fi
echo "Using Sage command $SAGE_COMMAND"

if [[ -n $WHAT ]]; then
   eval "$SAGE_COMMAND -python -m pytest $ARGS $COVER $WHAT"
else
   eval "$SAGE_COMMAND -python -m pytest $ARGS $COVER lmfdb/"
fi

if [[ $PYFLAKES_ERRCNT > 0 ]]; then
    printf "\nWARNING: pyflakes reported $PYFLAKES_ERRCNT error(s)\n"
fi
