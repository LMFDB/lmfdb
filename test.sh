#!/usr/bin/env bash
# This script runs nosetests for the whole project.
# It also generates a coverage report.
# When you specify the argument 'html', a HTML report will be generated, too.

cd `dirname "$0"`

if [[ "$1" == "html" ]]; then
  rm -rf lmfdb/cover
  HTML='--cover-html'
else
  HTML=''
fi

cd lmfdb
nosetests -v -s --with-coverage --cover-erase --cover-package=lmfdb $HTML


