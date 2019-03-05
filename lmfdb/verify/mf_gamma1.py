
from sage.all import (
    cached_function, floor, Gamma1, dimension_new_cusp_forms,
    dimension_eis, dimension_cusp_forms, dimension_modular_forms)

from lmfdb.backend.database import db, SQL
from .mf import MfChecker, check_analytic_conductor
from .verification import overall, slow, fast, accumulate_failures

@cached_function
def sturm_bound1(level, weight):
    return floor(weight * Gamma1(level).index()/12)

class mf_gamma1(MfChecker):
    table = db.mf_gamma1
    label = ['level', 'weight']
    uniqueness_constraints = [[table._label_col], label]

    @overall
    def check_box_count(self):
        """
        there should be a row present for every pair (N,k) satisfying a box constraint on N,k,Nk2
        """
        # TIME about 5s
        def make_query(box):
            query = self._box_query(box, drop=['char_order', 'dim'])
            # Have to remove small N if there are restrictions on the character order
            if 'omin' in box:
                if box['omin'] == 2:
                    if 'level' not in query:
                        query['level'] = {}
                    if '$gte' not in query['level'] or query['level']['$gte'] < 3:
                        query['level']['$gte'] = 3
                else:
                    raise NotImplementedError
            if 'Dmin' in box:
                query['newspace_dims']['$maxgte'] = box['Dmin']
            if 'Dmax' in box:
                query['newspace_dims']['$anylte'] = box['Dmax']

            return query
        return accumulate_failures(self.check_count(box['Nk_count'], make_query(box))
                   for box in db.mf_boxes.search())

    @overall
    def check_box_traces(self):
        """
        check that traces is set if space is in a box with traces set and no dimension/character constraint
        """
        return accumulate_failures(self.check_non_null(['traces'], self._box_query(box, drop=['char_order', 'dim']))
                   for box in db.mf_boxes.search({'omin':None, 'omax':None, 'Dmin':None, 'Dmax':None, 'straces':True}))

    @overall
    def check_dim_wt1(self):
        """
        for k = 1 check that dim = dihedral_dim + a4_dim + a5_dim + s4_dim
        """
        return self.check_sum(['dim'], ['dihedral_dim', 'a4_dim', 'a5_dim', 's4_dim'], {'weight': 1})

    @overall
    def check_trace_display(self):
        """
        check that trace_display is set whenever traces is set and dim > 0
        """
        return self.check_non_null(['trace_display'], {'traces':{'$exists': True}, 'dim':{'$gt': 0}})

    @overall
    def check_traces_len(self):
        """
        if present, check that traces has length at least 1000
        """
        # TIME about 5s
        return self.check_array_len_gte_constant('traces', 1000, {'traces':{'$exists': True}})

    @overall
    def check_mf_dim(self):
        """
        check that eis_dim + cusp_dim = mf_dim
        """
        return self.check_sum(['eis_dim','cusp_dim'],['mf_dim'])

    @overall
    def check_dim(self):
        """
        check that eis_new_dim + dim = mf_new_dim
        """
        return self.check_sum(['eis_new_dim','dim'], ['mf_new_dim'])

    @overall
    def check_Nk2(self):
        """
        check that Nk2 = N*k*k
        """
        return self.check_product('Nk2', ['level', 'weight', 'weight'])

    @overall
    def weight_parity_even(self):
        """
        check weight_parity
        """
        return self.check_divisible('weight', 2, {'weight_parity':1})

    @overall
    def weight_parity_odd(self):
        """
        check weight_parity
        """
        return self.check_non_divisible('weight', 2, {'weight_parity':-1})

    @overall
    def check_newspaces_numforms(self):
        """
        if num_forms is set verify that it is equal to the sum of num_forms over newspaces with matching level and weight
        """
        # TIME about 2s
        return self.check_crosstable_sum('mf_newspaces', 'num_forms', ['level', 'weight'])

    @overall
    def check_newspaces_hecke_orbit_dims(self):
        """
        if hecke_orbit_dims is set, verify that it is equal to the (sorted) concatenation of dim over newspaces with matching level and weight
        """
        # TIME about 10s
        return self.check_crosstable_aggregate('mf_newforms', 'hecke_orbit_dims', ['level', 'weight'], 'dim', sort=['char_orbit_index', 'hecke_orbit'])

    @overall
    def check_newspaces_newspace_dims(self):
        """
        check that newspace_dims is equal to the (sorted) concatenation of dim over newspaces with this level and weight
        """
        # TIME about 5s
        return self.check_crosstable_aggregate('mf_newspaces', 'newspace_dims', ['level', 'weight'], 'dim', sort=['char_orbit_index'])

    @overall
    def check_newspaces_num_spaces(self):
        """
        check that num_spaces matches the number of records in mf_newspaces with this level and weight and positive dimension
        """
        # TIME about 2s
        # TODO: check that the number of char_orbits of level N and weight k is the same as the number of rows in mf_newspaces with this weight and level.  The following doesn't work since num_spaces counts spaces with positive dimension
        # self.check_crosstable_count('char_dir_orbits', 'num_spaces', ['level', 'weight_parity'], ['modulus', 'parity']))
        return self._run_crosstable(SQL("COUNT(*)"), 'mf_newspaces', 'num_spaces', ['level', 'weight'], extra=SQL(" AND t2.dim > 0"))

    ### mf_gamma1_subspaces ###
    @overall
    def check_oldspace_decomposition_totaldim(self):
        """
        check that summing sub_dim * sub_mult over rows with a given label gives dim S_k(Gamma1(N))
        """
        # TIME about 1s
        return self.check_crosstable_dotprod('mf_gamma1_subspaces', 'cusp_dim', 'label', ['sub_mult', 'sub_dim'])


    ### mf_gamma1_portraits ###
    @overall
    def check_portraits_count(self):
        """
        check that there is a portrait present for every record in mf_gamma1 with `dim > 0` and `level <= 4000`
        """
        return self.check_crosstable_count('mf_gamma1_portraits', 1, 'label', constraint={'dim':{'$gt':0}, 'level':{'$lte':4000}})

    ### slow ###
    @slow(projection=['level', 'level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square'])
    def check_level(self, rec, verbose=False):
        """
        check level_* attributes
        """
        return self._check_level(rec, verbose=verbose)

    @slow(projection=['level', 'weight', 'analytic_conductor'])
    def check_analytic_conductor(self, rec, verbose=False):
        """
        check analytic_conductor
        """
        return check_analytic_conductor(rec['level'], rec['weight'], rec['analytic_conductor'], verbose=verbose)

    @slow(max_failures=2000, projection=['level', 'weight', 'sturm_bound'])
    def check_sturm_bound(self, rec, verbose=False):
        """
        check that sturm_bound is exactly floor(k*Index(Gamma1(N))/12)
        """
        return self._test_equality(rec['sturm_bound'], sturm_bound1(rec['level'], rec['weight']), verbose)

    @fast(constraint={'weight':{'$gt':1}}, projection=['level', 'weight', 'dim'])
    def check_Sk_dim_formula(self, rec, verbose=False):
        """
        check that dim = dim S_k^new(Gamma1(N))
        """
        # TIME about 60s
        return self._test_equality(rec['dim'], dimension_new_cusp_forms(Gamma1(rec['level']), rec['weight']), verbose)

    @fast(constraint={'weight':{'$gt':1}}, projection=['level', 'weight', 'eis_dim', 'cusp_dim', 'mf_dim'])
    def check_dims(self, rec, verbose=False):
        """
        for k > 1 check eis_dim, eis_new_dim, cusp_dim, mf_dim, mf_new_dim using Sage dimension formulas
        """
        # TIME about 30s
        G = Gamma1(rec['level'])
        k = rec['weight']
        for func, key in [(dimension_eis, 'eis_dim'), (dimension_cusp_forms, 'cusp_dim'), (dimension_modular_forms, 'mf_dim')]:
            if not self._test_equality(rec[key], func(G, k), verbose):
                return False
        return True
