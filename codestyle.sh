#!/usr/bin/env bash
# This script uses pep8 / autopep8 to find Python style errors
# or even fixes them.
# Usage: ./codestyle.sh or ./codestyle.sh [path/to/python/file ...]

# Note: When using this codestyle fixing utility, don't forget that it
# might introduce a lot of changes. That could be hard to merge!

# increased line length. might get shorter in time ... for now even ignored
ARGS='--max-line-length=120 --ignore=E501'

# WARN: we set the aggressive flag
AUTOPEP="autopep8 -i --aggressive $ARGS"

if [ -n "$1" ]; then
  $AUTOPEP "$@"
else
  cd `dirname "$0"`
  find lmfdb -iname '*.py' | xargs pep8 $ARGS
fi
