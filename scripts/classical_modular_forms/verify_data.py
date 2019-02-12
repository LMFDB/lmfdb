from lmfdb.db_backend import db, SQL, IdentifierWrapper as Identifier
from types import MethodType
from sage.rings.integer import Integer, prod, factor, floor, abs, cached_method

@cached_method
def analytic_conductor(level, weight):
    # TODO
    pass

def check_analytic_conductor(level, weight, analytic_conductor_stored, threshold = 1e-15):
    return (abs(analytic_conductor(level, weight) - analytic_conductor_stored)/analytic_conductor(level, weight)) < threshold

@cached_method
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

@cached_method
def sturm_bound(level, weight):
    return floor(weight * Gamma1(level).index()/12)

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
    def _cremona_letter_code(self):
    """
CREATE OR REPLACE FUNCTION cremona_letter_code(IN n integer) RETURNS varchar AS $$
DECLARE
    s varchar;
    m integer;
BEGIN
    m := n;
    IF m < 0 THEN
        s := 'NULL';
    ELSIF m = 0 THEN
        s := 'a';
    ELSE
        s := '';
        WHILE m != 0 LOOP
            s := chr(m%26+97) || s;
            m := m/26;
        END LOOP;
    END IF;

    RETURN s;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION class_to_int(IN s varchar) RETURNS integer AS $$
DECLARE
    k integer[];
    m integer := 0;
    p integer := 1;
BEGIN
    k := array(SELECT ascii(unnest(regexp_split_to_array(reverse(s),''))) - 97);
    FOR l in 1 .. array_length(k,1) LOOP
        m := m + p*k[l];
        p := p*26;
    END LOOP;
    return m;
END;
$$ LANGUAGE plpgsql;

"""
    def _run_query(self, condition, constraint, values=[]):
        """
        INPUT:

        - ``condition`` -- an SQL object giving a condition on the search table
        - ``constraint`` -- a dictionary, as passed to the search method
        """
        cstr, cvalues = self.table._parse_dict(constraint)
        # WARNING: the following is not safe from SQL injection, so be careful if you copy this code
        query = SQL("SELECT label FROM {0} WHERE {1}").format(
            Identifier(self.table.search_table), condition)
        if cstr is None:
            cvalues = []
        else:
            query = SQL("{0} AND {1}").format(query, cstr)
        values = values + cvalues
        query = SQL("{0} LIMIT 1").format(query)
        cur = db._execute(query, values)
        if cur.rowcount > 0:
            return cur.fetchone()[0]


    def _check_arith(self, a_columns, b_columns, constraint, op):
        return self._run_query(SQL(" != ").join([
            SQL(" %s "%op).join(map(Identifier, a_columns)),
            SQL(" %s "%op).join(map(Identifier, b_columns))]), constraint)

    def check_sum(self, a_columns, b_columns, constraint={}):
        return self._check_arith(a_columns, b_columns, constraint, '+')

    def check_product(self, a_columns, b_columns, constraint={}):
        return self._check_arith(a_columns, b_columns, constraint, '*')

    def check_array_sum(self, array_column, value_colum, constraint={})
        """
        Checks that sum(array_column) == value_column
        """
        return self._run_query(SQL("(SELECT SUM(s) FROM UNNEST({0}) s) != {1}").format(
            Identifier(array_column), Identifier(value_column)), constraint)

    def check_divisible(self, numerator, denominator, constraint={}):
        if isinstance(denominator, (Integer, int)):
            return self._run_query(SQL("{0} % %s != 0").format(Identifier(numerator)),
                                   constraint, [denominator])
        else:
            return self._run_query(SQL("{0} % {1} != 0").format(
                Identifier(numerator), Identifier(denominator)))

    def check_non_divisible(self, numerator, denominator, constraint={}):
        if isinstance(denominator, (Integer, int)):
            return self._run_query(SQL("{0} % %s = 0").format(Identifier(numerator)),
                                   constraint, [denominator])
        return self._run_query(SQL("{0} % {1} = 0").format(
            Identifier(numerator), Identifier(denominator)))

    def check_values(self, values, constraint={}):
        vstr, vvalues = self.table._parse_dict(values)
        if vstr is not None:
            # Otherwise no values, so nothing to check
            return self._run_query(SQL("NOT ({0})").format(vstr), constraint, values=vvalues)

    def check_non_null(self, columns, constraint={}):
        return self.check_values({col: {'$exists':True} for col in columns}, constraint)

    def check_array_len_gte_constant(self, column, limit, constraint={}):
        """
        Length of array greater than or equal to limit
        """
        return self._run_query(SQL("array_length({0}, 1) < %s").format(Identifier(column)),
                               constraint, [limit])

    def check_array_len_col(self, array_column, len_column, constraint={}):
        """
        Length of array_column matches len_column
        """
        return self._run_query(SQL("array_length({0}, 1) != {1}").format(
            Identifier(array_column), Identifier(len_column)), constraint)

    def check_string_concatentation(self, label_col, other_columns, constraint={}, sep='.'):
        """
        Check that the label_column is the concatenation of the other columns with the given separator
        """
        # FIXME: we need to handle modifiers
        oc = [Identifier(other_columns[i//2]) if i%2 == 0 else Literal(sep) for i in range(2*len(other_columns)-1)]
        return self._run_query(SQL(" != ").join([SQL(" || ").join(oc), Identifier(label_col)]), constraint)

    def check_box(self, box_column):
        # David, see check_box_* below
        pass

    def check_crosstable(self, table1, table2, col1, col2, join1, join2):
        """
        Check that col1 and col2 are the same where col1 is a column in table1, col2 is a column in table2,
        and the tables are joined by the constraint that table1.join1 = table2.join2
        """
        query = SQL("SELECT t1.label {0} t1, {1} t2 WHERE t1.{2} = t2.{3} AND t1.{4} != t2.{5} LIMIT 1").format(
            *map(Identifier, [table1, table2, join1, join2, col1, col2]))
        cur = db._execute(query)
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    def check_array_union(self, a_columns, b_columns):
        pass

    def check_letter_code(self, index_column, letter_code_column, constraint = {}):
        return self._run_query(SQL("{0} != cremona_letter_code({1} - 1)").format(Identifier(letter_code_column), Identifier(index_column)), constraint)

    def check_hecke_orbit_code(self, hoc_column, N_column, k_column, i_column, x_column = None, constraint = {}):
        # N + (k<<24) + ((i-1)<<36) + ((x-1)<<52)
        if x_column is None:
            return self._run_query(SQL("{0} != {1}::bigint + ({2}::bit(64)<<24)::bigint + (({3}-1)::bit(64)<<36)::bigint + (({4}-1)::bit(64)<<52)::bigint").format(hoc_column, N_column, k_column, i_column, x_column), constraint)
        else:
            return self._run_query(SQL("{0} != {1}::bigint + ({2}::bit(64)<<24)::bigint + (({3}-1)::bit(64)<<36)::bigint").format(hoc_column, N_column, k_column, i_column), constraint)

    def check_uniqueness_constraint(self, columns):
        # check there is a uniqueness constraint on the columns
        pass

    def _check_level(self, rec):
        # check level_* attributes (radical,primes,is_prime,...)
        # 'level', 'level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square'
        return [rec[elt] for elt in ['level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square']] == level_attributes(rec['level'])

class mf_newspaces(TableChecker):
    table = db.mf_newspaces

    projection = ['level', 'level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square', 'weight', 'analytic_conductor', 'hecke_orbit_dims', 'trace_bound', 'dim', 'num_forms', 'eis_dim', 'eis_new_dim', 'cusp_dim', 'mf_dim', 'mf_new_dim']

    @overall
    def check_constraints_label(self):
        return self.check_uniqueness_constraint(['label'])

    @overall
    def check_constraints_level_weight_char_orbit_index(self):
        return self.check_uniqueness_constraint(['level', 'weight', 'char_orbit_index'])

    @overall
    def check_constraints_level_weight_char_orbit_label(self):
        return self.check_uniqueness_constraint(['level', 'weight', 'char_orbit_label'])

    @overall
    def check_box_count(self):
        # TODO
        # there should be exactly one row for every newspace in mf_boxes; for each box performing mf_newspaces.count(box query) should match newspace_count for box, and mf_newspaces.count() should be the sum of these
        pass

    @overall
    def check_box_hecke_cutter_primes(self):
        # TODO
        # check that hecke_cutter_primes is set whenever space is in a box with eigenvalues set and `min(dims) <= 20`
        #return self.check_box('trace_bound','eigenvalues', extra_constraint)
        pass

    @overall
    def check_box_traces(self):
        # check that traces is set if space is in a box with straces set
        return self.check_box('traces','straces')

    @overall
    def check_box_trace_bound(self):
        return self.check_box('trace_bound','straces')


    @overall
    def check_label(self):
        # check that label matches level, weight, char_orbit_label
        return self.check_string_concatentation('label', ['level', 'weight', 'char_orbit_label'])

    @overall
    def check_char_orbit(self):
        return self.check_letter_code('char_orbit_index', 'char_orbit_label')

    @overall
    def check_traces_display(self):
        # check that traces_display is set whenever traces is set
        return self.check_non_null(['traces_display'], {'traces':{'$exists': True}})

    @overall
    def check_traces_len(self):
        return self.check_array_len_gte_constant('traces_display', 1000, {'traces':{'$exists': True}})

    @overall
    def check_trace_bound0(self):
        # check that trace_bound=0 if num_forms=1
        return self.check_values({'trace_bound': 0}, {'num_forms':1})

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
    def check_relative_dim(self):
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
        # TODO
        # check that char_* atrributes and prim_orbit_index match data in char_dir_orbits table (conrey_indexes should match galois_orbit)
        # mostlikely with check_crosstable
        pass

    @overall
    def check_hecke_orbit_code(self):
        # check  hecke_orbit_code matches level, weight, char_orbit_index
        # this can be done at postgres level
        return self.check_hecke_orbit_code('hecke_orbit_code', 'level', 'weight', 'char_orbit_index')

    @fast
    def check_analytic_conductor(self, rec):
        # check analytic_conductor
        return check_analytic_conductor(rec['level'], rec['weight'], rec['analytic_conductor'])

    @slow
    def check_level(self, rec):
        return self._check_level(rec)

    @slow
    def check_sturm_bound(self, rec):
        # check that sturm_bound is exactly floor(k*Index(Gamma0(N))/12)
        return rec['sturm_bound'] == sturm_bound(rec['level'], rec['weight'])

    @slow
    def check_hecke_orbit_dims_sorted(self, rec):
        # check that hecke_orbit_dims is sorted in increasing order
        return rec['hecke_orbit_dims'] == sorted(rec['hecke_orbit_dims'])

    @slow
    def check_trace_bound1(self, rec):
        # check that trace_bound = 1 if hecke_orbit_dims set and all dims distinct
        if 'hecke_orbit_dims' in rec:
            if len(set(rec['hecke_orbit_dims'])) == len(rec['hecke_orbit_dims'):
                    return rec['trace_bound'] == 1
        return True

    @slow
    def check_Skchi_dim_formula(self, rec):
        # TODO
        # for k > 1 check that dim is the Q-dimension of S_k^new(N,chi) (using sage dimension formula)
        # sample: dimension_new_cusp_forms(DirichletGroup(100).1^2,4)
        pass

    @slow
    def check_dims(self, rec):
        # for k > 1 check each of eis_dim, eis_new_dim, cusp_dim, mf_dim, mf_new_dim using Sage dimension formulas (when applicable)
        pass




class mf_gamma1(TableChecker):
    table = db.mf_gamma1
    projection = ['level', 'level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square', 'weight', 'analytic_conductor', 'sturm_bound', 'dim', 'eis_dim', 'eis_new_dim', 'cusp_dim', 'mf_dim', 'mf_new_dim']

    @overall
    def check_constraints_label(self):
        return self.check_uniqueness_constraint(['label'])

    @overall
    def check_constraints_level_weight(self):
        return self.check_uniqueness_constraint(['level', 'weight'])

    @overall
    def check_box_count(self):
        # TODO
        # there should be a row present for every pair (N,k) satisfying a box constraint on N,k,Nk2
        pass
    @overall
    def check_box_traces(self):
        # TODO
        # check that traces is set if space is in a box with traces set and no dimension constraint
        pass

    @overall
    def check_label(self):
        # check that label matches level and weight
        return self.check_string_concatentation('label', ['level', 'weight'])

    @overall
    def check_dim_wt1(self):
        # for k = 1 check that dim = dihedral_dim + a4_dim + a5_dim + s4_dim
        return self.check_sum(['dim'], ['dihedral_dim', 'a4_dim', 'a5_dim', 's4_dim'])

    @overall
    def check_traces_display(self):
        # check that traces_display is set whenever traces is set
        return self.check_non_null(['traces_display'], {'traces':{'$exists': True}})

    @overall
    def check_traces_len(self):
        # if present, check that traces has length at least 1000
        return self.check_array_len_gte_constant('traces_display', 1000, {'traces':{'$exists': True}})

    @overall
    def check_mf_dim(self):
        # check that eis_dim + cusp_dim = mf_dim
        return self.check_sum(['eis_dim','cusp_dim'],['mf_dim'])

    @overall
    def check_dim(self):
        # check that eis_new_dim + mf_new_dim = dim
        return self.check_sum(['eis_new_dim','mf_new_dim'], ['dim'])

    @overall
    def check_Nk2(self):
        # check that Nk2 = N*k*k
        return self.check_prod(['Nk2'], ['N', 'k', 'k'])

    @overall
    def weight_parity_even(self):
        # check weight_parity
        return self.check_divisible('weight', 2, {'weight_parity':1})

    @overall
    def weight_parity_odd(self):
        # check weight_parity
        return self.check_non_divisible('weight', 2, {'weight_parity':-1})

    @overall
    def check_newspaces_numforms(self):
        # TODO
        # if num_forms is set verify that it is equal to the sum of num_forms over newspaces with matching level and weight
        pass
    @overall
    def check_newspaces_hecke_orbit_dims(self):
        # TODO
        # if hecke_orbit_dims is set, verify that it is equal to the (sorted) concatenation of hecke_orbit_dims over newspaces with matching level and weight
        pass

    @overall
    def check_newspaces_newspace_dims(self):
        # TODO
        # check that newspace_dims is equal to the (sorted) concatenation of dim over newspaces with this level and weight
        pass
    @overall
    def check_newspaces_num_spaces(self):
        # TODO
        # check that num_spaces matches number of char_orbits of level N and number of records in mf_newspaces with this level and weight
        pass


    @slow
    def check_level(self, rec):
        return self._check_level(rec)

    @sloe
    def check_analytic_conductor(self, rec):
        return check_analytic_conductor(rec['level'], rec['weight'], rec['analytic_conductor'])

    @slow
    def check_sturm_bound(self, rec):
        # check that sturm_bound is exactly floor(k*Index(Gamma0(N))/12)
        return rec['sturm_bound'] == sturm_bound(rec['level'], rec['weight'])

    @slow
    def check_Sk_dim_formula(self, rec):
        # check that dim = dim S_k^new(Gamma1(N))
        if rec['weight'] > 1:
            return rec['dim'] == dimension_new_cusp_forms(Gamma1(rec['level']), rec['weight'])
        return True
    @slow
    def check_dims(self, rec):
        # TODO
        # for k > 1 check eis_dim, eis_new_dim, cusp_dim, mf_dim, mf_new_dim using Sage dimension formulas
        pass


class mf_newspace_portraits(TableChecker):
    table = db.mf_newspace_portraits


    @overall
    def check_constraints_label(self):
        return self.check_uniqueness_constraint(['label'])

    @overall
    def check_constraints_level_weight_char_orbit_index(self):
        return self.check_uniqueness_constraint(['level', 'weight', 'char_orbit_index'])

    @overall
    def check_label(self):
        # check that label matches level, weight, char_orbit_label
        # FIXME: no char_orbit_label column
        return self.check_string_concatentation('label', ['level', 'weight', 'char_orbit_label'])

    @overall
    def check_box(self):
        # TODO
        # check that there is a portrait present for every nonempty newspace in box where straces is set
        pass


class mf_gamma1_portraits(TableChecker):
    table = db.mf_gamma1_portraits
    projection = []

    @overall
    def check_constraints_label(self):
        return self.check_uniqueness_constraint(['label'])

    @overall
    def check_constraints_level_weight(self):
        return self.check_uniqueness_constraint(['level', 'weight'])

    @overall
    def check_label(self):
        # check that label matches level, weight, char_orbit_label
        return self.check_string_concatentation('label', ['level', 'weight'])

    @overall
    def check_portrait_is_set(self):
        # TODO
        # check that there is a portrait present for every record in mf_gamma1 with `dim > 0` and `level <= 4000`



class mf_subspaces(TableChecker):
    table = db.mf_subspaces

    @overall
    def check_constraints_label_sub_label(self):
        return self.check_uniqueness_constraint(['label','sub_label'])

    @overall
    def check_sub_mul_positive(self):
        # sub_mult is positive
        return self._run_query(SQL("{0} <= 0").format(Identifier('sub_mul')))


        # check that label matches level, weight char_orbit_index
        # check that char_orbit_label matches level, char_orbit_index
        # check that sub_label matches sub_level, weight, sub_char_orbit_index
        # check that sub_level divides level
        # check that sub_char_orbit_label matches sub_level, sub_char_orbit_index
        # Per row
        # char_dir_orbits
        # check that conrey_index matches galois_orbit for char_orbit_label in char_dir_orbits
        # check that sub_conrey_index matches galois_orbit for sub_char_orbit_label in char_dir_orbits
        # mf_newspaces
# check that summing sub_dim * sub_mult over rows with a given label gives S_k(N,chi) (old+new), for k=1 use cusp_dim in mf_newspaces to do this check




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
