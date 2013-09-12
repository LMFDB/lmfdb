#!/usr/bin/env bash
# This script runs nosetests for the whole project.
# It also generates a coverage report when the "coverage" module is installed.
# When you specify the argument 'html', a HTML report will be generated, too.

# To run it, first install or upgrade "nose", "unittest2" and "coverage".
# e.g. $ pip install --user -U nose coverage unittest2
# or inside the Sage environment: $ easy_install -U nose
#                                 $ easy_install -U coverage
#                                 $ easy_install -U unittest2
# Second, call it via sage -sh test.sh

cd `dirname "$0"`

if [[ "$1" == "html" ]]; then
  rm -rf lmfdb/cover
  HTML='--cover-html'
else
  HTML=''
fi

cd lmfdb
nosetests -v -s --with-coverage --cover-erase --cover-package=lmfdb $HTML


