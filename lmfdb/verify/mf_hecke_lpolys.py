
from sage.all import prime_range

from lmfdb.backend.database import db, SQL
from .mf import MfChecker
from .verification import overall, overall_long, accumulate_failures

class mf_hecke_lpolys(MfChecker):
    table = db.mf_hecke_lpolys
    label_col = 'hecke_orbit_code'
    uniqueness_constraints = [['hecke_orbit_code', 'p']]

    @overall
    def check_total_count(self):
        """
        check that hecke_orbit_code is present in mf_newforms
        """
        return self.check_count(25 * db.mf_newforms.count({'field_poly':{'$exists':True}}))

    @overall
    def check_prime_count(self):
        """
        check that every prime p < 100 occurs exactly once for each hecke_orbit_code
        """
        # TIME about 30s
        cnt = db.mf_newforms.count({'field_poly':{'$exists':True}})
        return accumulate_failures(self.check_count(cnt, {'p': p}) for p in prime_range(100))

    @overall_long
    def check_hecke_orbit_code_newforms(self):
        """
        check that hecke_orbit_code is present in mf_newforms
        """
        # TIME about 200s
        return self.check_crosstable_count('mf_newforms', 1, 'hecke_orbit_code')

    @overall_long
    def check_lpoly(self):
        """
        check that degree of lpoly is twice the dimension in mf_newforms for good primes
        check that linear coefficient of lpoly is -trace(a_p) and constant coefficient is 1
        """
        # TIME > 3600s
        query = SQL("SELECT t1.label FROM (mf_newforms t1 INNER JOIN mf_hecke_lpolys t2 ON t1.hecke_orbit_code = t2.hecke_orbit_code) INNER JOIN mf_hecke_traces t3 ON t1.hecke_orbit_code = t3.hecke_orbit_code AND t2.p = t3.n WHERE ((MOD(t1.level, t2.p) != 0 AND array_length(t2.lpoly, 1) != 2*t1.dim+1) OR t2.lpoly[1] != 1 OR t2.lpoly[2] != -t3.trace_an)")
        return self._run_query(query=query)
