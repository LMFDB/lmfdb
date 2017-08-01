#!/projects/sage/sage-7.3/local/bin/python
# -*- coding: utf-8 -*-
r""" Import abelian variety isogeny class data.

The main import function is do_import_yaml.  It requires creating
a yaml file with like

B_ready_to_upload:
    - 2:
        - 1
        - 2
        - 3
        - 4
        - 5
        - 6
    - 3:
        - 1
        - 2
        - 3
        - 4
    - 5:
        - 1
        - 2
        - 3
        - 4

This file will coordinate uploading among multiple processes.
As processes begin uploading, they will claim g and q, changing
the yaml file, and eventually marking them as completed.
"""

import os
import sys, time, datetime
import shutil
import re
import json
from subprocess import Popen
from itertools import izip_longest
from math import sqrt

#mypath = os.path.realpath(__file__)
#while os.path.basename(mypath) != 'lmfdb':
#    mypath = os.path.dirname(mypath)
## now move up one more time...
#mypath = os.path.dirname(mypath)
#sys.path.append(mypath)

from pymongo.mongo_client import MongoClient
import yaml

## Main importing function

def do_import(ll, db, saving):
    """
    INPUT:

    - ``ll`` -- a list of 19 entries, consisting of the data to be uploaded to the database.
    - ``db`` -- an authenticated connection to the abvar.fq collection.
    - ``saving`` -- a boolean: whether to actually perform the upsert.
    """
    label, g, q, polynomial, angle_numbers, angle_ranks, p_rank, slopes, A_counts, C_counts, known_jacobian, principally_polarizable, decomposition, brauer_invariants, places, primitive_models, number_field, galois_n, galois_t = ll
    mykeys = ['label', 'g', 'q', 'polynomial', 'angle_numbers', 'angle_ranks', 'p_rank', 'slopes', 'A_counts', 'C_counts', 'known_jacobian', 'principally_polarizable', 'decomposition', 'brauer_invariants', 'places', 'primitive_models', 'number_field', 'galois_n', 'galois_t']
    data = {}
    for key, val in zip(mykeys, ll):
        data[key] = val
    if saving:
        db.update({'label': label} , {"$set": data}, upsert=True)
    else:
        print data

class lock_yaml(object):
    """
    An object preventing simultaneous access to the yaml file
    using a coarse grained lock file.
    """
    def __init__(self, rootdir):
        self.lock_file = os.path.join(rootdir, 'yaml_lock')
    def __enter__(self):
        while True:
            if os.path.exists(self.lock_file):
                time.sleep(0.1)
            else:
                with open(self.lock_file, 'w') as F:
                    F.write('\n')
                break
    def __exit__(self, typ, value, tb):
        os.unlink(self.lock_file)

def do_import_one(g, q, db, status_file, datadir):
    """
    Imports all of the data from a single file.

    Intermediate progress is reported and stored in a file,
    so that uploading can be halted and resumed as desired.

    The file ``weil-all-g6-q2.txt`` (for example) must
    exist and contain json encoded lines with the relevant
    data (see the lmfdb inventory for more details on
    the data types).

    INPUT:

    - ``g`` -- the dimension of the isogeny class.
    - ``q`` -- the cardinality of the base field.
    - ``db`` -- an authenticated connection to the abvar.fq collection.
    - ``status_file`` -- the path to the yaml file coordinating the uploading.
    - ``datadir`` -- the folder where data is contained.
    """
    progress_file = os.path.join(datadir, 'weil-ultmp-g%s-q%s.txt'%(g, q))
    all_file = os.path.join(datadir, 'weil-all-g%s-q%s.txt'%(g, q))
    saving=True
    with open(all_file) as Fall:
        for num_lines, line in enumerate(Fall,1):
            pass
        # Now num_lines is the number of lines in Fall
    with open(all_file) as Fall:
        with open(progress_file, 'a+') as Fwrite:
            with open(progress_file) as Fprog:
                print_next_time = time.time()
                sum_of_times = float(0)
                sum_of_squares = float(0)
                start_line = None
                malformed = False
                for cur_line, (line_all, line_prog) in enumerate(izip_longest(Fall, Fprog, fillvalue=None), 1):
                    if line_prog is not None:
                        if line_all[2:line_all.find(',')-1] != line_prog.strip():
                            if malformed:
                                raise RuntimeError("Multiple malformed lines")
                            malformed = True
                            if not line_all[2:line_all.find(',')-1].startswith(line_prog.strip()):
                                raise RuntimeError("Label mismatch")
                        if cur_line % 1000 == 0:
                            print "Skipping previously uploaded (%s/%s)"%(cur_line, num_lines)
                        continue
                    if start_line is None:
                        start_line = cur_line
                    data = json.loads(line_all.strip())
                    t = time.time()
                    do_import(data, db, saving)
                    t = time.time()- t
                    sum_of_times += t
                    sum_of_squares += t**2
                    if time.time() > print_next_time:
                        print_next_time = time.time() + 15
                        to_print = "Uploaded (g=%s, q=%s) %s/%s."%(g, q, cur_line, num_lines)
                        if cur_line - start_line > 10:
                            elapsed_lines = cur_line - start_line + 1
                            scaling = float(num_lines - elapsed_lines - start_line + 1) / elapsed_lines
                            sigma = sqrt(sum_of_squares - sum_of_times**2 / elapsed_lines)
                            lower_bound = max(0, sum_of_times*scaling - 2*sigma*sqrt(scaling))
                            upper_bound = sum_of_times*scaling + 2*sigma*sqrt(scaling)
                            lower_bound = datetime.timedelta(seconds=int(lower_bound))
                            upper_bound = datetime.timedelta(seconds=int(upper_bound))
                            to_print += "  %s to %s remaining."%(lower_bound, upper_bound)
                        print to_print
                    Fwrite.write(data[0] + '\n')
    os.unlink(progress_file)
    print "Upload (g=%s, q=%s) finished."%(g, q)
    sys.stdout.flush()
    with lock_yaml():
        with open(status_file) as F:
            status = yaml.load(F)
        pid = os.getpid()
        in_progress = status.get('D_uploading_%s'%(pid), [])
        for qq, L in in_progress.iteritems():
            if q != qq:
                continue
            try:
                L.remove(g)
            except ValueError:
                raise RuntimeError("g not found")
            if not L:
                del in_progress[qq]
            break
        else:
            raise RuntimeError("q not found")
        done = status['A_uploaded']
        qfound = False
        for D in done:
            for qq, L in D.iteritems():
                if q != qq:
                    continue
                L.append(g)
                qfound = True
                break
            if qfound:
                break
        else:
            done.append({q: [g]})
        with open(status_file + '.tmp%s'%pid, 'w') as F:
            yaml.dump(status, F)
        shutil.move(status_file + '.tmp%s'%pid, status_file)

def authenticated_db(port=37010, rootdir=None):
    """
    Create a database connection to the abvar database,
    authenticated by the passwords yaml file in rootdir.
    """
    rootdir = rootdir or os.path.expanduser('~')
    C = MongoClient(port=port)
    with open(os.path.join(rootdir, "passwords.yaml")) as pw_file:
        pw_dict = yaml.load(pw_file)
    username = pw_dict['data']['username']
    password = pw_dict['data']['password']
    C['abvar'].authenticate(username, password)
    return C.abvar

def do_import_yaml(port=None, status_file=None, rootdir=None, datadir=None, reset=False):
    """
    This function is designed to allow multiple processes to upload data, controlled
    by a single yaml file.

    INPUT:

    - ``port`` -- an int, the port to connect to the database.
    - ``status_file`` -- the path to the yaml file controlling the uploading.
    - ``rootdir`` -- Folder in which to create various temporary files, and
                     which is assumed to contain status.yaml if status_file is
                     not specified.  Defaults to the user's home directory.
    - ``datadir`` -- Folder containing the data to be uploaded.  Defaults to
                     rootdir/root-unitary/data
    - ``reset`` -- Boolean.  If True, will reset status.yaml so that everything
                   not yet finished will be marked as ready-to-begin (rather than in-progress)
                   This function will then immediately return.
    """
    rootdir = rootdir or os.path.expanduser('~')
    status_file = status_file or os.path.join(rootdir, 'status.yaml')
    if reset:
        with lock_yaml():
            with open(status_file) as F:
                status = yaml.load(F)
            ready = status.get('B_ready_to_upload', [])
            for label, val in status.items():
                if label.startswith('D_uploading_'):
                    ready.append(val)
                    del status[label]
            ready.sort(key = lambda D: D.keys()[0])
            status['B_ready_to_upload'] = ready
            with open(status_file + '.tmpreset', 'w') as F:
                yaml.dump(status, F)
            shutil.move(status_file + '.tmpreset', status_file)
        print "Status file reset"
        return
    port_file = os.path.join(rootdir, 'curport')
    if port is None:
        with lock_yaml():
            if not os.path.exists(port_file):
                port = 37010
            else:
                with open(port_file) as F:
                    for line in F:
                        port = int(line.strip()) + 1
                        break
            with open(port_file, 'w') as F:
                F.write(str(port))
    datadir = datadir or os.path.join(rootdir, 'root-unitary', 'data')
    pid = os.getpid()
    port_forwarder = Popen(["ssh", "-o", "TCPKeepAlive=yes", "-o", "ServerAliveInterval=50", "-C", "-N", "-L", "%s:localhost:37010"%port, "mongo-user@lmfdb.warwick.ac.uk"])
    try:
        db = authenticated_db(port, rootdir).fq_isog
        db.create_index('g')
        db.create_index('q')
        db.create_index('label')
        db.create_index('polynomial')
        db.create_index('p_rank')
        db.create_index('slopes')
        db.create_index('A_counts')
        db.create_index('C_counts')
        db.create_index('known_jacobian')
        db.create_index('principally_polarizable')
        db.create_index('decomposition')
        print "finished indices"

        while True:
            with lock_yaml():
                with open(status_file) as F:
                    status = yaml.load(F)
                in_progress = status.get('D_uploading_%s'%(pid), {})
                if not in_progress:
                    ready = status.get('B_ready_to_upload', [])
                    if not ready:
                        print "No more data to upload"
                        break
                    in_progress = status['D_uploading_%s'%(pid)] = ready.pop(0)
                    with open(status_file + '.tmp%s'%pid, 'w') as F:
                        yaml.dump(status, F)
                    shutil.move(status_file + '.tmp%s'%pid, status_file)
            for q, L in in_progress.iteritems():
                for g in L:
                    do_import_one(g, q, db, status_file, datadir)
    finally:
        port_forwarder.kill()

def update_stats(port = 37010, datadir = None):
    """
    Updates the fq_isog.stats collection.

    INPUT:

    - ``port`` -- the port on which to open a connection to the database.  Defaults to 37010.
    - ``datadir`` -- the directory containing the data.  Defaults to $HOME/root-unitary/data
    """
    datadir = datadir or os.path.join(os.path.expanduser('~'), 'root-unitary', 'data')
    port_forwarder = Popen(["ssh", "-o", "TCPKeepAlive=yes", "-o", "ServerAliveInterval=50", "-C", "-N", "-L", "%s:localhost:37010"%port, "mongo-user@lmfdb.warwick.ac.uk"])
    allmatcher = re.compile(r"weil-all-g(\d+)-q(\d+).txt")
    try:
        C = authenticated_db(port)
        db = C.fq_isog
        stats_collection = C.fq_isog.stats
        qs = db.distinct('q')
        gs = db.distinct('g')
        maxg = max(gs)
        counts = {}
        mismatches = []
        for q in qs:
            counts[str(q)] = [0]
            found_zero = False
            for g in range(1, maxg+1):
                print "Counting g=%s, q=%s..."%(g, q),
                try:
                    n = db.find({'g': g, 'q': q}).count()
                except KeyError:
                    n = 0
                filename = os.path.join(datadir, 'weil-all-g%s-q%s.txt'%(g, q))
                num_lines = None
                if os.path.exists(filename):
                    with open(filename) as F:
                        for num_lines, line in enumerate(F, 1):
                            pass
                if n == 0:
                    found_zero = True
                    if num_lines:
                        print "File not uploaded!"
                        mismatches.append((g, q, 0, num_lines))
                    else:
                        print "OK."
                else:
                    if found_zero:
                        print "Nonzero count after zero count!",
                        mismatches.append((g, q, None, None))
                    if num_lines:
                        with open(filename) as F:
                            for num_lines, line in enumerate(F, 1):
                                pass
                        if num_lines == n:
                            print "OK."
                            counts[str(q)].append(n)
                        else:
                            print "Count mismatch!"
                            mismatches.append((g, q, n, num_lines))
                    else:
                        print "Extra data in database!"
                        mismatches.append((g, q, n, None))
        print "Checking for missing files...."
        missing = False
        for filename in os.listdir(datadir):
            match = allmatcher.match(filename)
            if match:
                g, q = map(int, match.groups())
                if g not in gs or q not in qs:
                    print filename, "not uploaded!"
                    missing = True
                    mismatches.append((g, q, None, -1))
        if not missing:
            print "No files missing."
        if mismatches:
            print "There were errors:"
            for g, q, n, num_lines in mismatches:
                print "g=%s, q=%s,"%(g, q),
                if n is None and num_lines is None:
                    print "nonzero count after zero count."
                elif n == 0:
                    print "file not uploaded."
                elif num_lines is None:
                    print "extra data in database."
                else:
                    print "mismatched count (%s in database, %s in file)"%(n, num_lines)
        else:
            stats_collection.update({'label': 'counts'} , {"$set": {'label': 'counts', 'counts': counts}}, upsert=True)
            print "Counts updated!"
    finally:
        port_forwarder.kill()

def label_progress(filename, label):
    """
    Utility function to look for a label within a file.
    """
    found = None
    counter = 0
    startcheck = '["%s"'%label
    with open(filename) as F:
        for line in F.readlines():
            counter += 1
            if line.startswith(startcheck):
                found = counter
    if found is None:
        print "Label %s not found" % label
    else:
        print "Label %s is at %s/%s"%(label, found, counter)

#if __name__ == '__main__':
#    do_import_yaml()
