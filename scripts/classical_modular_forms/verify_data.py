from lmfdb.db_backend import db, SQL
from types import MethodType

class speed_decorator(object):
    """
    Transparently wraps a function, so that functions can be classified by "isinstance"
    """
    def __init__(self, f):
        self.f = f
        self.__name__ = f.__name__
    def __call__(self, *args, **kwds):
        return self.f(*args, **kwds)

class slow(speed_decorator):
    """
    Decorate a check as being slow to run
    """
    pass

class fast(speed_decorator):
    """
    Decorate a check as being fast to run
    """

class overall(speed_decorator):
    """
    Decorate a check as being one that's run once overall for the table, rather than once for each row
    """
    pass

class TableChecker(object):
    def __init__(self, logfile, id_limits=None):
        self.logfile = logfile
        self.id_limits = id_limits

    def _get_checks(self, typ):
        return [MethodType(f, self, self.__class__) for f in self.__class__.__dict__.values() if isinstance(f, typ)]

    def _run_checks(self, typ):
        table = self.table
        checks = self._get_checks(typ)
        logfile = self.logfile
        query = {}
        if self.id_limits:
            query = {'id': {'$gte': self.id_limits[0], '$lt': self.id_limits[1]}}
        with open(logfile, 'a') as log:
            for rec in table.search(query, sort=[]):
                for check in checks:
                    if not check(rec):
                        log.write('%s: %s\n'%(check.__name__, rec['label']))

    def run_slow_checks(self):
        self._run_checks(slow)

    def run_fast_checks(self):
        self._run_checks(fast)

    def run_overall_checks(self):
        checks = self._get_checks(overall)
        for check in checks:
            check()

class mf_newspaces(TableChecker):
    table = db.mf_newspaces

    @slow
    def check_hecke_orbit_dims_sorted(self, rec):
        return rec['hecke_orbit_dims'] == sorted(rec['hecke_orbit_dims'])

class mf_gamma1(TableChecker):
    table = db.mf_gamma1

class mf_newspace_portraits(TableChecker):
    table = db.mf_newspace_portraits

class mf_gamma1_portraits(TableChecker):
    table = db.mf_gamma1_portraits

class mf_subspaces(TableChecker):
    table = db.mf_subspaces

class mf_gamma1_subspaces(TableChecker):
    table = db.mf_gamma1_subspaces


class mf_newforms(TableChecker):
    table = db.mf_newforms

class mf_newform_portraits(TableChecker):
    table = db.mf_newform_portraits

class mf_hecke_nf(TableChecker):
    table = db.mf_hecke_nf

class mf_hecke_traces(TableChecker):
    table = db.mf_hecke_traces

class mf_hecke_lpolys(TableChecker):
    table = db.mf_hecke_lpolys

class mf_hecke_newspace_traces(TableChecker):
    table = db.mf_hecke_newspace_traces

class mf_hecke_cc(TableChecker):
    table = db.mf_hecke_cc

class char_dir_orbits(TableChecker):
    table = db.char_dir_orbits

class char_dir_values(TableChecker):
    table = db.char_dir_values
