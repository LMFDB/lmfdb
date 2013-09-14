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
# or to test only a part of LMFDB:    $ ./test lmfdb/knowledge

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

if [[ -n $WHAT ]]; then
   eval "sage -sh -c 'nosetests -v -s $WHAT'"
else
   cd lmfdb
   eval "sage -sh -c 'nosetests -v -s --with-coverage --cover-erase --cover-package=lmfdb $HTML'"
fi

