from lmfdb.db_backend import db, SQL, IdentifierWrapper
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

    This should take a row (dictionary) as input and return True if everything is okay, False otherwise
    """
    pass

class fast(speed_decorator):
    """
    Decorate a check as being fast to run

    This should take a row (dictionary) as input and return True if everything is okay, False otherwise
    """

class overall(speed_decorator):
    """
    Decorate a check as being one that's run once overall for the table, rather than once for each row

    This should take no input and return a bad label if there is a failure, or None otherwise.
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
        logfile = self.logfile
        with open(logfile, 'a') as log:
            for check in checks:
                bad_label = check()
                if bad_label:
                    log.write('%s: OVERALL\n'%(check.__name__))

    # Add uniqueness constraints

    #####################
    # Utility functions #
    #####################


    def _check_arith(self, a_columns, b_columns, constraint, op):
        cstr, values = self.table._parse_dict(constraint)
        # WARNING: the following is not safe from SQL injection, so be careful if you copy this code
        query = SQL("SELECT label FROM {0} WHERE {1} = {2}").format(
            self.table.search_table,
            SQL(" %s "%op).join(map(IdentifierWrapper, a_columns)),
            SQL(" %s "%op).join(map(IdentifierWrapper, b_columns)))
        if cstr is None:
            values = []
        else:
            query = SQL("{0} AND {1}").format(query, cstr)
        query = SQL("{0} LIMIT 1").format(query)
        cur = db._execute(query)
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    def check_sum(self, a_columns, b_columns, constraint={}):
        return self._check_arith(a_columns, b_columns, constraint, '+')

    def check_product(self, a_columns, b_columns, constraint):
        return self._check_arith(a_columns, b_columns, constraint, '*')

    def check_array_sum(self, array_column, value_colum, constraints={})
        # checks that sum(array_column) == value_column
        pass

    # also against constants
    def check_divisible(self, numerator, denominator, constraint):
        pass
    def check_non_divisible(self, numerator, denominator, constraint):
        pass


    def check_values(self, values, constraints):
        pass

    def check_non_null(self, columns, constraint):
        return self.check_values(dict([ (col, {'$exists':True}) for col in columns]), constraints)

    def check_conversion(self, numeric_column, letter_column):
        pass


    def check_array_len_gte_constant(self, column, limit, constraint):
        """
        Length of array greater than or equal to limit
        """
        pass

    def check_array_len_col(self, array_column, len_column, constraint):
        """
        Length of array_column matches len_column
        """
        pass

    def check_string_concatentation(self, label_col, other_columns, sep='.'):
        """
        Check that the label_column is the concatenation of the other columns with the given separator
        """
        pass

    def check_box(self, box_column):
        # David, see check_box_* below
        pass

    def check_crosstable(self, table1, table2, col1, col2, join1, join2):
        query = SQL("SELECT 1 FROM ")

    def check_array_union(self, a_columns, b_columns):
        pass

class mf_newspaces(TableChecker):
    table = db.mf_newspaces

    @overall
    def check_constraints(self):
        # check uniqueness on:
        # label
        # (level, weight, char_orbit)
        # (level, weight, char_orbit_label)
        pass

    @overall
    def check_box_count(self):
        # there should be exactly one row for every newspace in mf_boxes; for each box performing mf_newspaces.count(box query) should match newspace_count for box, and mf_newspaces.count() should be the sum of these
        pass

    @overall
    def check_box_hecke_cutter_primes(self):
        # check that hecke_cutter_primes is set whenever space is in a box with eigenvalues set and `min(dims) <= 20`
        #FIXME
        #return self.check_box('trace_bound','eigenvalues', extra_constraint)
        pass

    @overall
    def check_box_traces(self):
        # check that traces is set if space is in a box with straces set
        return self.check_box('traces','straces')

    @overall
    def check_box_traces_bound(self):
        return self.check_box('trace_bound','straces')


    @overall
    def check_label(self):
        # check that label matches level, weight, char_orbit_label
        return self.check_string_concatentation('label', ['level', 'weight', 'char_orbit_label'])

    @overall
    def check_char_orbit(self):
        # check that char_orbit matches char_orbit_label
        return self.check_conversion('char_orbit', 'char_orbit_label')

    @overall
    def check_traces_display(self):
        # check that traces_display is set whenever traces is set
        return self.check_non_null(['traces_display'], {'traces':{'$exists': True}})

    @overall
    def check_traces_len(self):
        return self.check_array_len_gte_constant('traces_display', 1000, {'traces':{'$exists': True}})

    @overall
    def check_traces_bound0(self):
        # check that trace_bound=0 if num_forms=1
        return self.check_values({'traces_bound': 0}, {'num_forms':1})

    @overall
    def check_AL_dims_plus_dim(self):
        # check that AL_dims and plus_dim is set whenever char_orbit_index=1
        return self.check_non_null(['AL_dims', 'plus_dim'], {'char_orbit':1})

    @overall
    def check_dim0_num_forms(self):
        # check that if dim = 0 then num_forms = 0 and hecke_orbit_dims = []
        return self.check_values({'num_forms': 0, 'hecke_orbit_dims':[]}, {'num_forms':0})

    @overall
    def check_mf_dim(self):
        # check that eis_dim + cusp_dim = mf_dim
        return self.check_sum(['eis_dim','cusp_dim'], ['mf_dim'])

    @overall
    def check_mf_new_dim(self):
        # check that eis_new_dim+dim=mf_new_dim
        return self.check_sum(['eis_new_dim','dim'], ['mf_new_dim'])

    @overall
    def check_dim_wt1(self):
        # for k = 1 check that dim = dihedral_dim + a4_dim + a5_dim + s4_dim
        return self.check_sum(['dim'], ['dihedral_dim', 'a4_dim', 'a5_dim', 's4_dim'])

    @overall
    def check_relate_dim(self):
        # check that char_degree * relative_dim = dim
        return self.check_prod(['dim'], ['char_degree', 'relative_degree'])

    @overall
    def check_len_hecke_orbit_dims(self):
        # if present, check that len(hecke_orbit_dims) = num_forms
        return self.check_array_len_col('hecke_orbit_dims', 'num_forms',{'hecke_orbit_dims':{'$exists':True}})

    @overall
    def check_sum_hecke_orbit_dims(self):
        # if present, check that sum(hecke_orbit_dims) = dim
        return self.check_array_sum('hecke_orbit_dims', 'dim', {'hecke_orbit_dims':{'$exists':True}})

    @overall
    def check_sum_AL_dims(self):
        # if AL_dims is set, check that AL_dims sum to dim
        return self.check_array_sum('AL_dims', 'dim', {'AL_dims':{'$exists':True}})
    @overall
    def check_Nk2(self):
        # check that Nk2 = N*k*k
        return self.check_prod(['Nk2'], ['N', 'k', 'k'])

    @overall
    def weight_parity_even(self):
        return self.check_divisible('weight', 2, {'weight_parity':1})

    @overall
    def weight_parity_odd(self):
        return self.check_non_divisible('weight', 2, {'weight_parity':-1})

    @overall
    def check_against_char_dir_orbits(self):
        # check that char_* atrributes and prim_orbit_index match data in char_dir_orbits table (conrey_indexes should match galois_orbit)
        # mostlikely with check_crosstable
        pass

    @overall
    def check_hecke_orbit_code(self):
        # check  hecke_orbit_code matches level, weight, char_orbit
        # this can be done at postgres level
        pass

    @fast
    def check_analytic_conductor(self, rec):
        # check analytic_conductor
        pass

    @slow
    def check_level(self, rec):
        # check level_* attributes (radical,primes,is_prime,...)
        pass

    @slow
    def check_sturm_bound(self, rec):
        # check that sturm_bound is exactly floor(k*Index(Gamma0(N))/12)
        # this could be moved to overall by looping over all (N, k) pairs
        pass

    @slow
    def check_hecke_orbit_dims_sorted(self, rec):
        return rec['hecke_orbit_dims'] == sorted(rec['hecke_orbit_dims'])

    @slow
    def check_traces_bound1(self, rec):
        # check that trace_bound=1 if hecke_orbit_dims set and all dims distinct
        if 'hecke_orbit_dims' in rec:
            if len(set(rec['hecke_orbit_dims'])) == len(rec['hecke_orbit_dims'):
                    return rec['traces_bound'] == 1
        return True

    @slow
    def check_Sk_dim_formula(self, rec):
        # for k > 1 check that dim is the Q-dimension of S_k^new(N,chi) (using sage dimension formula)
        pass

    @slow
    def check_dims(self, rec):
        # for k > 1 check each of eis_dim, eis_new_dim, cusp_dim, mf_dim, mf_new_dim using Sage dimension formulas (when applicable)
        pass




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
