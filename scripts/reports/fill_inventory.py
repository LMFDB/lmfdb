#! /usr/bin/env sage
import sys
import os
import argparse
import importlib
import json

debug = False
selected_dbs = None
selected_collections = None
action = False
file_output = None

def start_lmfdb_connection():
    scriptdir = os.path.join('.',os.path.dirname(__file__))
    up2 = os.path.abspath(os.path.join(scriptdir,os.pardir,os.pardir))
    sys.path.insert(0, up2)
    save_std_err = None
    if not debug:
        try:
            save_stderr = sys.stderr
            sys.stderr = open('/dev/null','w')
        except:
           #This is only for neatness, so no worries if it fails
            pass
    globals()['jdbs'] = importlib.import_module('jsonify_db_structure')
    if not debug:
        try:
            sys.stderr = save_stderr
        except:
            pass

def show_databases():

    global action
    action = True
    if not file_output:
        fh = sys.stdout
    else:
        fh = open(file_output, 'w')
    if selected_dbs:
        fh.write('Single database ' + selected_dbs[0] + ' specified\n')
        return

    start_lmfdb_connection()
    dbs = jdbs.get_lmfdb_databases()
    fh.write('')
    fh.write('Known good databases\n')
    fh.write('--------------------\n')
    for db in dbs:
        fh.write(db+'\n')

    if file_output: fh.close()

def show_collections():

    global action
    action = True
    if not file_output:
        fh = sys.stdout
    else:
        fh = open(file_output, 'w')
    if selected_dbs and selected_collections:
        fh.write('Single collection ' + selected_collections[0] + ' specified\n')
        return

    start_lmfdb_connection()
    dbs = selected_dbs
    if not dbs: dbs = jdbs.get_lmfdb_databases()
    colls = jdbs.get_lmfdb_collections(databases = dbs)
    fh.write('Known good collections\n')
    fh.write('--------------------\n')
    for db in colls:
        first = True
        for scol in colls[db]:
            pt = False
            if not selected_collections:
                pt = True
            else:
                if scol in selected_collections:
                    pt = True
            if pt and first:
                first = False
                fh.write('In database ' + db +':\n')
            if pt: fh.write(' ' * 4 + scol + '\n')
    if file_output: fh.close()

def generate_inventory():
    global action
    action = True
    if not file_output:
        fh = sys.stdout
    else:
        fh = open(file_output, 'w')

    start_lmfdb_connection()
    result = jdbs.parse_lmfdb_to_json(collections = selected_collections, databases = selected_dbs)
    fh.write(json.dumps(result, indent=4, sort_keys = True))
    if file_output: fh.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--list_databases', action='store_true', help = 'List available databases')
    parser.add_argument('--list_collections', action='store_true', help = 'List available collections')
    parser.add_argument('--file_output', action ='store', help = 'Redirect output to file')
    parser.add_argument('--generate_inventory', action='store_true', help = 'Generate the inventory data for the specified database and/or collections')
    parser.add_argument('--database', action='store', help='Set working database')
    parser.add_argument('--collection', action='store', help='Set working collection')
    args = parser.parse_args()

    print('LMFDB report tool')
    print('------------------------')
    if (len(sys.argv) == 1):parser.print_help()
    sys.argv = sys.argv[0]
    if args.database: selected_dbs = [args.database]
    if args.collection: selected_collections = [args.collection]
    if args.file_output: file_output = args.file_output
    if args.list_databases: show_databases()
    if args.list_collections: show_collections()
    if args.generate_inventory: generate_inventory()

    if not action:
        print('No action specified!')
        parser.print_help()
    else:
        if file_output: print('Run complete. All primary output written to file ' + file_output)
