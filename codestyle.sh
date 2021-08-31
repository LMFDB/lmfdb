#!/usr/bin/env bash
# This script uses pep8 / autopep8 to find Python style errors
# or even fixes them.
# Usage: ./codestyle.sh or ./codestyle.sh [path/to/python/file ...]

# Note: When using this codestyle fixing utility, don't forget that it
# might introduce a lot of changes. That could be hard to merge!

# increased line length. might get shorter in time ... for now even ignored
#ARGS='--max-line-length=120 --ignore=E501'
ARGS='--select=E703,E271,E272,E714,E722'

SAGE_COMMAND=$SAGE
if [[ "$SAGE_COMMAND" == "" ]]; then
  SAGE_COMMAND=sage
fi
echo "Using Sage command $SAGE_COMMAND"

# WARN: we set the aggressive flag
AUTOPEP="$SAGE_COMMAND -python -m autopep8 -i --aggressive $ARGS"
CODESTYLE="$SAGE_COMMAND -python -m pycodestyle $ARGS"

if [ -n "$1" ]; then
  $AUTOPEP "$@"
else
  cd `dirname "$0"`
  find lmfdb -iname '*.py' | xargs $CODESTYLE
fi
