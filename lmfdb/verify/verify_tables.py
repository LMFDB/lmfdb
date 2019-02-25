# -*- coding: utf-8 -*-
"""
This script is used to run verification jobs in parallel.  For more options (such as verifying only a single check or a single object) see the verify method of PosgresTable in lmfdb/backend/database.py.
"""

import argparse, os, subprocess, sys, tempfile, textwrap

try:
    # Make lmfdb available
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
except NameError:
    pass
from lmfdb.verify import db

def directory(path):
    if not os.path.isdir(path):
        raise TypeError('Not a directory')
    else:
        return path

def find_validated_tables():
    curdir = os.path.dirname(os.path.abspath(__file__))
    return [tablename for tablename in db.tablenames if os.path.exists(os.path.join(curdir, tablename + '.py'))]

if __name__ == '__main__':
    validated_tables = find_validated_tables()
    speedtypes = ['overall', 'overall_long', 'fast', 'slow']

    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent('''\
                LMFDB - The L-functions and modular forms database
                Verification scripts for classical modular forms
                '''),
            epilog=textwrap.dedent('''\
                You may ran multiple tests in parallel by running:
                 # parallel -j THREADS sage -python {0} LOGDIR ::: {{table names}} ::: {{types}}
                For example:
                 # parallel -j 8 sage -python {0} /scratch/logs ::: {{{1}}} ::: {{{2}}}
                '''.format(sys.argv[0],
                    ' '.join(validated_tables[:2]),
                    ' '.join(speedtypes))
            ))

    parser.add_argument(
        'logdir',
        metavar='LOGDIR',
        type=directory,
        help='log directory')

    parser.add_argument(
        'tablename',
        metavar='TABLENAME',
        type=str,
        help=('the table name to run the verification tests.' +
              ' Allowed values are: ' + ', '.join(['all'] + validated_tables)),
        choices=['all'] + validated_tables)
    parser.add_argument(
        'speedtype',
        metavar='TYPE',
        type=str,
        help=('the type of test to run on the chosen table.' +
              ' Allowed values are: ' + ', '.join(['all'] + speedtypes)),
        choices=['all'] + speedtypes + ['over', 'long'])

    args, parallel_args = parser.parse_known_args()
    options = vars(args)
    tablename = options.pop('tablename')
    if not (tablename == 'all' or options['speedtype'] == 'all'):
        options['parallel'] = False
        db[tablename].verify(**options)
    else:
        #use parallel to loop over all options
        tables = validated_tables if tablename == 'all' else [tablename]
        types = speedtypes if options['speedtype'] == 'all' else [options['speedtype']]

        with tempfile.NamedTemporaryFile() as tables_file:
            tables_file.write('\n'.join(tables) + '\n')
            tables_file.flush()
            with tempfile.NamedTemporaryFile() as types_file:
                types_file.write('\n'.join(types) + '\n')
                types_file.flush()
                cmd = ['parallel'] + parallel_args
                cmd += ['-a', tables_file.name, '-a', types_file.name] # inputs
                cmd += ['sage', '-python', os.path.realpath(__file__), options['logdir'] ]
                print "Running: {0}".format(subprocess.list2cmdline(cmd))
                exitcode = subprocess.call(cmd)


        sys.exit(exitcode)
