import os, time
from collections import defaultdict

class Follower(object):
    suffixes = ['log', 'progress', 'errors']
    def __init__(self, logdir, total_count, poll_interval=0.1):
        self.logdir = logdir
        if poll_interval <= 0:
            raise ValueError("Poll interval must be positive")
        self.interval = poll_interval
        self.active = defaultdict(dict)
        self.done_files = set()
        self.started_files = set()
        self.total_count = total_count

    def read(self, basename, suffix):
        if not self.active[basename].get(suffix):
            self.open_file(basename, suffix)
        # open_file adds None if the file doesn't exist
        F = self.active[basename][suffix]
        if F is not None:
            line = F.readline()
            while line:
                print line,
                line = F.readline()

    def open_file(self, basename, suffix):
        filename = os.path.join(self.logdir, basename + '.' + suffix)
        if os.path.exists(filename):
            F = open(filename)
            self.active[basename][suffix] = F
        else:
            self.active[basename][suffix] = None

    def close_file(self, basename, suffix):
        F = self.active[basename].pop(suffix)
        if F is not None:
            F.close()

    def close_all(self):
        for files in self.active.values():
            for suffix in list(files):
                files.pop(suffix).close()

    def update_file_lists(self):
        # There may be race condition problems here since the verification script will be writing
        # to these same files, but it's not a disaster if something
        # goes wrong since we produce a final report and the files will exist on the filesystem
        for filename in os.listdir(self.logdir):
            if filename.endswith('.done'):
                if filename not in self.done_files:
                    basename = filename[:-5]
                    self.done_files.add(filename)
                    for suffix in self.suffixes:
                        self.read(basename, suffix)
                        self.close_file(basename, suffix)
                    self.active.pop(basename)
            elif filename.endswith('.started'):
                if filename not in self.started_files:
                    basename = filename[:-8]
                    self.started_files.add(filename)
                    for suffix in self.suffixes:
                        self.open_file(basename, suffix)

    def is_done(self):
        self.update_file_lists()
        return len(self.done_files) == self.total_count

    def incremental_report(self):
        for basename in sorted(self.active):
            for suffix in self.suffixes:
                self.read(basename, suffix)

    def final_report(self):
        for donefile in sorted(self.done_files):
            with open(os.path.join(self.logdir, donefile)) as F:
                for line in F:
                    print line,

    def follow(self):
        """
        Print the files in logdir to standard out
        """
        try:
            while not self.is_done():
                time.sleep(self.interval)
                self.incremental_report()
            self.final_report()
        finally:
            # in case interrupted
            self.close_all()
