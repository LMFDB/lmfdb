
from collections import defaultdict

from sage.all import cached_function, psi, RR, Integer, prod

from lmfdb.backend.database import SQL, Identifier
from .verification import TableChecker, overall

@cached_function
def kbarbar(weight):
    # The weight part of the analytic conductor
    return psi(RR(weight)/2).exp() / (2*RR.pi())

def analytic_conductor(level, weight):
    return level * kbarbar(weight)**2

def check_analytic_conductor(level, weight, analytic_conductor_stored, verbose=False, threshold = 1e-12):
    success = (abs(analytic_conductor(level, weight) - analytic_conductor_stored)/analytic_conductor(level, weight)) < threshold
    if not success and verbose:
        print "Analytic conductor failure", analytic_conductor(level, weight), analytic_conductor_stored
    return success

@cached_function
def level_attributes(level):
    # returns level_radical, level_primes, level_is_prime, level_is_prime_power, level_is_squarefree, level_is_square
    fact = Integer(level).factor()
    level_primes = [elt[0] for elt in fact]
    level_radical = prod(level_primes)
    level_is_prime_power = len(fact) == 1
    level_is_prime = level_is_prime_power and level_radical == level
    level_is_square = all( elt[1] % 2 == 0 for elt in fact)
    level_is_squarefree = all( elt[1] == 1 for elt in fact)
    return [level_radical, level_primes, level_is_prime, level_is_prime_power, level_is_squarefree, level_is_square]

class MfChecker(TableChecker):
    def _box_query(self, box, extras={}, drop=[]):
        """
        INPUT:

        - ``box`` -- a dictionary, a row in mf_boxes
        - ``extras`` -- extra conditions to set on the returned query
            (e.g. dim <= 20, which would be {'dim':{'$lte':20}})
        """
        query = defaultdict(dict)
        for bcol, col in [('N','level'), ('k', 'weight'), ('o', 'char_order'), ('Nk2', 'Nk2'), ('D', 'dim')]:
            for mm, code in [('min', '$gte'), ('max', '$lte')]:
                constraint = box.get(bcol + mm)
                if constraint is not None:
                    query[col][code] = constraint
        for col, D in extras.items():
            for code, val in D.items():
                query[col][code] = val
        for col in drop:
            query.pop(col, None)
        return query

    def _check_level(self, rec, verbose=False):
        """
        check level_* attributes (radical,primes,is_prime,...)
        """
        attributes = ['level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square']
        stored = [rec[attr] for attr in attributes]
        computed = level_attributes(rec['level'])
        success = stored == computed
        if not success and verbose:
            for attr, a, b in zip(attributes, stored, computed):
                if a != b:
                    print attr, a, b
        return success

    hecke_orbit_code = []
    @overall
    def check_hecke_orbit_code(self):
        """
        hecke_orbit_code is as defined
        """
        if self.hecke_orbit_code != []:
            # test enabled
            assert len(self.hecke_orbit_code) == 2
            hoc_column = self.hecke_orbit_code[0]
            if len(self.hecke_orbit_code[1]) == 4:
                N_column, k_column, i_column, x_column = self.hecke_orbit_code[1]
            else:
                assert len(self.hecke_orbit_code[1]) == 3
                x_column = None
                N_column, k_column, i_column = self.hecke_orbit_code[1]
            # N + (k<<24) + ((i-1)<<36) + ((x-1)<<52)
            if x_column is None:
                return self._run_query(SQL("{0} != {1}::bigint + ({2}::integer::bit(64)<<24)::bigint + (({3}-1)::integer::bit(64)<<36)::bigint").format(*map(Identifier,[hoc_column, N_column, k_column, i_column])))
            else:
                return self._run_query(SQL("{0} != {1}::bigint + ({2}::integer::bit(64)<<24)::bigint + (({3}-1)::integer::bit(64)<<36)::bigint + (({4}-1)::integer::bit(64)<<52)::bigint").format(*map(Identifier, [hoc_column, N_column, k_column, i_column, x_column])))

class SubspacesChecker(MfChecker):
    @overall
    def check_sub_mul_positive(self):
        """
        sub_mult is positive
        """
        return self._run_query(SQL("{0} <= 0").format(Identifier('sub_mult')))

    @overall
    def check_sub_dim_positive(self):
        """
        sub_dim is positive
        """
        return self._run_query(SQL("{0} <= 0").format(Identifier('sub_dim')))

    @overall
    def check_level_divides(self):
        """
        check that sub_level divides level
        """
        return self.check_divisible('level', 'sub_level')

class TracesChecker(MfChecker):
    uniqueness_constraints = [['hecke_orbit_code', 'n']]
    label_col = 'hecke_orbit_code'

    @overall
    def check_total_count(self):
        """
        check that hecke_orbit_code is present in mf_newforms
        """
        return self.check_count(1000 * self.base_table.count(self.base_constraint))
