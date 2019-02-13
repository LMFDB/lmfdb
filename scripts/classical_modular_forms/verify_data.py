from lmfdb.db_backend import db, SQL, IdentifierWrapper as Identifier
from types import MethodType
from collections import defaultdict
from sage.all import Integer, prod, factor, floor, abs, mod, euler_phi, prime_pi, cached_function

@cached_function
def analytic_conductor(level, weight):
    # TODO
    pass

def check_analytic_conductor(level, weight, analytic_conductor_stored, threshold = 1e-13):
    return (abs(analytic_conductor(level, weight) - analytic_conductor_stored)/analytic_conductor(level, weight)) < threshold

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

@cached_function
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
            for rec in table.search(query, projection=self.projection, sort=[]):
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
CREATE OR REPLACE FUNCTION to_base26(IN n integer) RETURNS varchar AS $$
DECLARE
    s varchar;
    m integer;
BEGIN:
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

CREATE OR REPLACE FUNCTION from_base26(IN s varchar) RETURNS integer AS $$
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

CREATE OR REPLACE FUNCTION from_newform_label_to_hecke_orbit_code(IN s varchar) RETURNS bigint AS $$
DECLARE
    v text[];
BEGIN
    v := regexp_split_to_array(s, '.');
    return v[1]::bigint + (v[2]::bigint::bit(64)<<24)::bigint + ((from_base26(v[3])::bit(64)<<36)::bigint + ((from_base26(v[4])::bit(64)<<52)::bigint;
END;
$$ LANGUAGE plpgsql;

//we could have only one function, but then we would play heavily for the if statement
CREATE OR REPLACE FUNCTION from_newspace_label_to_hecke_orbit_code(IN s varchar) RETURNS bigint AS $$
DECLARE
    v text[];
BEGIN
    v := regexp_split_to_array(s, '.');
    return v[1]::bigint + (v[2]::bigint::bit(64)<<24)::bigint + ((from_base26(v[3])::bit(64)<<36)::bigint;
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
        query = SQL("SELECT {0} FROM {1} WHERE {2}").format(
                Identifier(self.table._label_col),
                Identifier(self.table.search_table),
                condition)
        if cstr is None:
            cvalues = []
        else:
            query = SQL("{0} AND {1}").format(query, cstr)
        values = values + cvalues
        query = SQL("{0} LIMIT 1").format(query)
        cur = db._execute(query, values)
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    def check_count(self, cnt, constraint={}):
        real_cnt = self.table.count(constraint)
        if real_cnt != cnt:
            return '%s != %s (%s)' % (real_cnt, cnt, constraint)

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

    def check_null(self, columns, constraint={}):
        return self.check_values({col: None for col in columns}, constraint)

    def check_array_len_gte_constant(self, column, limit, constraint={}):
        """
        Length of array greater than or equal to limit
        """
        return self._run_query(SQL("array_length({0}, 1) < %s").format(Identifier(column)),
                               constraint, [limit])

    def check_array_len_eq_constant(self, column, limit, constraint={}, array_dim = 1):
        """
        Length of array greater than or equal to limit
        """
        return self._run_query(SQL("array_length({0}, %s) != %s").format(Identifier(column)),
                               constraint, [array_dim, limit])

    def check_array_len_col(self, array_column, len_column, constraint={}, shift=0):
        """
        Length of array_column matches len_column
        """
        return self._run_query(SQL("array_length({0}, 1) != {1} + {2}").format(
            Identifier(array_column), Identifier(len_column), Literal(int(shift))), constraint)

    def check_string_concatentation(self, label_col, other_columns, constraint={}, sep='.'):
        """
        Check that the label_column is the concatenation of the other columns with the given separator
        """
        # FIXME: we need to handle modifiers
        oc = [Identifier(other_columns[i//2]) if i%2 == 0 else Literal(sep) for i in range(2*len(other_columns)-1)]
        return self._run_query(SQL(" != ").join([SQL(" || ").join(oc), Identifier(label_col)]), constraint)

    def check_sorted(self, column):
        return self._run_query(SQL("{0} != sort({0})").format(Identifier(column)))

    def _make_join(self, join1, join2):
        if not isinstance(join1, list):
            join1 = [join1]
        if join2 is None:
            join2 = join1
        elif not isinstance(join2, list):
            join2 = [join2]
        if len(join1) != len(join2):
            raise ValueError("join1 and join2 must have the same length")
        return SQL(" AND ").join([SQL("t1.{0} = t2.{1}").format(Identifier(j1), Identifier(j2)) for j1, j2 in zip(join1, join2)])


    def check_crosstable(self, other_table, col1, join1, col2=None, join2=None):
        """
        Check that col1 and col2 are the same where col1 is a column in self.table, col2 is a column in other_table,
        and the tables are joined by the constraint that self.table.join1 = other_table.join2.

        Here col2 and join2 default to col1 and join1, and join1 and join2 are allowed to be lists of columns
        """
        join = self._make_join(join1, join2)
        if col2 is None:
            col2 = col1
        query = SQL("SELECT t1.{0} FROM {1} t1, {2} t2 WHERE {3} AND t1.{4} != t2.{5} LIMIT 1").format(
                Identifier(self.table._label_col),
                Identifier(self.table.search_table),
                Identifier(other_table),
                join,
                Identifier(col1),
                Identifier(col2))
        cur = db._execute(query)
        if cur.rowcount > 0:
            return cur.fetchone()[0]



    def check_crosstable_count(self, other_table, col, join1, join2=None, constraint={}):
        """
        Check that col stores the count of the rows in the other table joining with this one.

        col is allowed to be an integer, in which case a constant count is checked.
        """
        cstr, cvalues = self.table._parse_dict(constraint)
        if cstr is None:
            cstr = SQL("")
            cvalues = []
        else:
            cstr = SQL("{0} AND ").format(cstr)
        join = self._make_join(join1, join2)
        if isinstance(col, (int, Integer)):
            col = Literal(col)
        else:
            col = SQL("t1.{0}").format(Identifier(col))
        query = SQL("SELECT t1.{0} FROM {1} t1 WHERE {6}{2} != (SELECT COUNT(*) FROM {4} t2 WHERE {5}) LIMIT 1").format(
                Identifier(self.table._label_col),
                Identifier(self.table.search_table),
                col,
                Identifier(other_table),
                join,
                cstr)
        cur = db._execute(query, cvalues)
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    def check_crosstable_sum(self, other_table, col1, join1, col2=None, join2=None):
        """
        Check that col1 is the sum of the values in col2 where join1 = join2

        Here col2 and join2 default to col1 and join1, and join1 and join2 are allowed to be lists of columns
        """
        join = self._make_join(join1, join2)
        if col2 is None:
            col2 = col1
        query = SQL("SELECT t1.{0} FROM {1} t1 WHERE t1.{2} != (SELECT SUM(t2.{3}) FROM {4} t2 WHERE {5}) LIMIT 1").format(
                Identifier(self.table._label_col),
                Identifier(self.table.search_table),
                Identifier(col1),
                Identifier(col2),
                Identifier(other_table),
                join)
        cur = db._execute(query)
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    def check_crosstable_dotprod(self, other_table, col1, join1, col2, join2=None):
        """
        Check that col1 is the sum of the product of the values in the columns of col2 over rows of other_table with self.table.join1 = other_table.join2.

        There are some peculiarities of this method, resulting from its application to mf_subspaces.
        col1 is allowed to be a pair, in which case the difference col1[0] - col1[1] will be compared.

        col2 does not take value col1 as a default, since they are playing different roles.
        """
        join = self._make_join(join1, join2)
        if isinstance(col1, list):
            if len(col1) != 2:
                raise ValueError("col1 must have length 2")
            col1 = SQL("t1.{0} - t1.{1}").format(Identifier(col1[0]), Identifier(col1[1]))
        else:
            col1 = SQL("t1.{0}").format(Identifier(col1))
        col2 = SQL(" * ").join(SQL("t2.{0}").format(Identifier(col)) for col in col2)
        query = SQL("SELECT t1.label FROM {0} t1 WHERE {1} != (SELECT SUM({2}) FROM {3} t2 WHERE {4}) LIMIT 1").format(Identifier(self.table.search_table), col1, col2, Identifier(other_table), join)
        cur = db._execute(query)
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    def check_crosstable_aggregate(self, other_table, col1, join1, col2=None, join2=None, sort=None, truncate=None, constraint={}):
        """
        Check that col1 is the sorted array of values in col2 where join1 = join2

        Here col2 and join2 default to col1 and join1, and join1 and join2 are allowed to be lists of columns

        sort defaults to col2, but can be a list of columns in other_table
        """
        cstr, cvalues = self.table._parse_dict(constraint)
        if cstr is None:
            cstr = SQL("")
            cvalues = []
        else:
            cstr = SQL("{0} AND ").format(cstr)
        join = self._make_join(join1, join2)
        if col2 is None:
            col2 = col1
        if truncate is None:
            col1 = SQL("t1.{0}").format(Identifier(col1))
        else:
            col1 = SQL("t1.{0}[:%s]"%(int(truncate))).format(Identifier(col1))
        if sort is None:
            sort = SQL("t2.{0}").format(Identifier(col2))
        else:
            sort = SQL(", ").join(SQL("t2.{0}").format(Identifier(col)) for col in sort)
        query = SQL("SELECT t1.{0} FROM {1} t1 WHERE {7}{2} != ARRAY(SELECT t2.{3} FROM {4} t2 WHERE {5} ORDER BY {6}) LIMIT 1").format(
                Identifier(self.table._label_col),
                Identifier(self.table.search_table),
                col1,
                Identifier(col2),
                Identifier(other_table),
                join,
                sort,
                cstr)
        cur = db._execute(query, cvalues)
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    def check_array_union(self, a_columns, b_columns):
        # TODO
        pass

    def check_letter_code(self, index_column, letter_code_column, constraint = {}):
        return self._run_query(SQL("{0} != cremona_letter_code({1} - 1)").format(Identifier(letter_code_column), Identifier(index_column)), constraint)

    def _check_hecke_orbit_code(self, hoc_column, N_column, k_column, i_column, x_column = None, constraint = {}):
        # N + (k<<24) + ((i-1)<<36) + ((x-1)<<52)
        if x_column is None:
            return self._run_query(SQL("{0} != {1}::bigint + ({2}::bit(64)<<24)::bigint + (({3}-1)::bit(64)<<36)::bigint + (({4}-1)::bit(64)<<52)::bigint").format(hoc_column, N_column, k_column, i_column, x_column), constraint)
        else:
            return self._run_query(SQL("{0} != {1}::bigint + ({2}::bit(64)<<24)::bigint + (({3}-1)::bit(64)<<36)::bigint").format(hoc_column, N_column, k_column, i_column), constraint)

    def check_uniqueness_constraint(self, columns):
        # TODO
        # check there is a uniqueness constraint on the columns
        pass

    def _check_level(self, rec):
        # check level_* attributes (radical,primes,is_prime,...)
        # 'level', 'level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square'
        return [rec[elt] for elt in ['level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square']] == level_attributes(rec['level'])

    def _box_query(self, box, extras={}, drop=[]):
        """
        INPUT:

        - ``box`` -- a dictionary, a row in mf_boxes
        - ``extras`` -- extra conditions to set on the returned query
            (e.g. dim <= 20, which would be {'dim':{'$lte':20}})
        """
        query = defaultdict(dict)
        for bcol, col in [('N','level'), ('k', 'weight'), ('o', 'char_order'), ('Nk2', 'Nk2'), ('D', 'dim')]:
            for mod, code in [('min', '$gte'), ('max', '$lte')]:
                constraint = box.get(bcol + mod)
                if constraint is not None:
                    query[col][code] = constraint
        for col, D in extras.items():
            for code, val in D.items():
                query[col][code] = val
        for col in drop:
            del query[col]
        return query


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
        # there should be exactly one row for every newspace in mf_boxes; for each box performing mf_newspaces.count(box query) should match newspace_count for box, and mf_newspaces.count() should be the sum of these
        return any(self.check_count(box['newspace_count'], self._box_query(box))
                   for box in db.mf_boxes.search())

    @overall
    def check_box_hecke_cutter_primes(self):
        # check that hecke_cutter_primes is set whenever space is in a box with eigenvalues set and `min(dims) <= 20`
        return any(self.check_non_null(['hecke_cutter_primes'], self._box_query(box, {'dim':{'$lte':20}}))
                   for box in db.mf_boxes.search({'eigenvalues':True}))

    @overall
    def check_box_traces(self):
        # check that traces is set if space is in a box with straces set
        return any(self.check_non_null(['traces', 'trace_bound'], self._box_query(box))
                   for box in db.mf_boxes.search({'straces':True}))

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
        return self._check_hecke_orbit_code('hecke_orbit_code', 'level', 'weight', 'char_orbit_index')

    @overall
    def check_hecke_orbit_dims_sorted(self):
        # check that hecke_orbit_dims is sorted in increasing order
        return self.check_sorted('hecke_orbit_dims')

    @overall
    def check_oldspace_decomposition_totaldim(self):
        # check that summing sub_dim * sub_mult over rows with a given label gives dim of S_k^old(N,chi)
        return self.check_crosstable_dotprod('mf_subspaces', ['cusp_dim', 'dim'], 'label', ['sub_mult', 'sub_dim'])

    @overall
    def check_traces_count(self):
        # there should be exactly 1000 records in mf_hecke_traces for each record in mf_newspaces with traces set
        return self.check_crosstable_count('mf_hecke_newspace_traces', 1000, 'hecke_orbit_code', constraint={'traces':{'$exists':True}})

    @overall
    def check_traces_match(self):
        # check that traces[n] matches trace_an in mf_hecke_newspace_traces
        return self.check_crosstable_aggregate('mf_hecke_newspace_traces', 'traces', 'hecke_orbit_code', 'trace_an', sort='n', truncate=1000, constraint={'traces':{'$exists':True}})

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
    def check_trace_bound1(self, rec):
        # check that trace_bound = 1 if hecke_orbit_dims set and all dims distinct
        if 'hecke_orbit_dims' in rec:
            if len(set(rec['hecke_orbit_dims'])) == len(rec['hecke_orbit_dims']):
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
        # TODO
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
        # there should be a row present for every pair (N,k) satisfying a box constraint on N,k,Nk2
        return any(self.check_count(box['Nk_count'], self._box_query(box, drop=['char_order', 'dim']))
                   for box in db.mf_boxes.search())

    @overall
    def check_box_traces(self):
        # check that traces is set if space is in a box with traces set and no dimension constraint
        return any(self.check_non_null(['traces'], self._box_query(box, drop=['char_order', 'dim']))
                   for box in db.mf_boxes.search({'Dmin':None, 'Dmax':None, 'straces':True}))

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
        # if num_forms is set verify that it is equal to the sum of num_forms over newspaces with matching level and weight
        return self.check_crosstable_sum('mf_newspaces', 'num_forms', ['level', 'weight'])

    @overall
    def check_newspaces_hecke_orbit_dims(self):
        # if hecke_orbit_dims is set, verify that it is equal to the (sorted) concatenation of dim over newspaces with matching level and weight
        return self.check_crosstable_aggregate('mf_newforms', 'hecke_orbit_dims', ['level', 'weight'], 'dim', sort=['char_orbit_index', 'hecke_orbit'])

    @overall
    def check_newspaces_newspace_dims(self):
        # check that newspace_dims is equal to the (sorted) concatenation of dim over newspaces with this level and weight
        return self.check_crosstable_aggregate('mf_newspaces', 'newspace_dims', ['level', 'weight'], 'dim', sort=['char_orbit_index'])

    @overall
    def check_newspaces_num_spaces(self):
        # check that num_spaces matches number of char_orbits of level N and number of records in mf_newspaces with this level and weight
        return (self.check_crosstable_count('mf_newspaces', 'num_spaces', ['level', 'weight']) or
                self.check_crosstable_count('char_dir_orbits', 'num_spaces', ['level', 'weight_parity'], ['modulus', 'parity']))

    @overall
    def check_oldspace_decomposition_totaldim(self):
        # check that summing sub_dim * sub_mult over rows with a given label gives dim S_k^old(Gamma1(N))
        return self.check_crosstable_dotprod('mf_gamma1_subspaces', ['cusp_dim', 'dim'], 'label', ['sub_mult', 'sub_dim'])

    @slow
    def check_level(self, rec):
        return self._check_level(rec)

    @slow
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

class portraits(TableChecker):
    @overall
    def check_constraints_label(self):
        return self.check_uniqueness_constraint(['label'])

    @overall
    def check_constraints_expanded_label(self):
        return self.check_uniqueness_constraint(self.label)

    @overall
    def check_label(self):
        # check that label matches self.label
        # FIXME: need to use cremona_label at the appropriate places
        return self.check_string_concatentation('label', self.label)

class mf_newspace_portraits(portraits):
    table = db.mf_newspace_portraits
    projection = []
    label = ['level', 'weight', 'char_orbit_index']

    @overall
    def check_present(self):
        # check that there is a portrait present for every nonempty newspace in box where straces is set
        return any(self.check_count(box['newspace_count'], self._box_query(box))
                   for box in db.mf_boxes.search({'straces':True}))


class mf_gamma1_portraits(portraits):
    table = db.mf_gamma1_portraits
    projection = []
    label = ['level', 'weight']

    @overall
    def check_present(self):
        # TODO
        # check that there is a portrait present for every record in mf_gamma1 with `dim > 0` and `level <= 4000`
        pass

class mf_newform_portraits(portraits):
    table = db.mf_newform_portraits
    projection = []
    label = ['level', 'weight', 'char_orbit_index', 'hecke_orbit']

    @overall
    def check_present(self):
        # TODO
        # check that there is exactly one record in mf_newform_portraits for each record in mf_newforms, uniquely identified by label
        pass

class subspaces(TableChecker):
    @overall
    def check_constraints_label_sub_label(self):
        return self.check_uniqueness_constraint(['label','sub_label'])

    @overall
    def check_sub_mul_positive(self):
        # sub_mult is positive
        return self._run_query(SQL("{0} <= 0").format(Identifier('sub_mult')))

    @overall
    def check_sub_dim_positive(self):
        # sub_mult is positive
        return self._run_query(SQL("{0} <= 0").format(Identifier('sub_dim')))

    @overall
    def check_level_divides(self):
        # check that sub_level divides level
        return self.check_divisible('level', 'sub_level')

    @overall
    def check_decomposition_dimension(self):
        # TODO
        # check that summing sub_dim * sub_mult over rows with a given label gives S_k(N,chi) or S_k(Gamma1(N)) (old+new), for k=1 use cusp_dim in mf_newspaces/mf_gamma1 to do this check
        pass

class mf_subspaces(subspaces):
    table = db.mf_subspaces

    @overall
    def check_label(self):
        # check that label matches level, weight, char_orbit_index
        return self.check_string_concatenation('label', ['level', 'weight', 'char_orbit_label'])

    @overall
    def check_char_orbit_label(self):
        # check that char_orbit_label matches char_orbit_index
        return self.check_letter_code('char_orbit_index', 'char_orbit_label')

    @overall
    def check_sub_label(self):
        # check that sub_label matches sub_level, weight, sub_char_orbit_index
        return self.check_string_concatenation('sub_label', ['sub_level', 'weight', 'sub_char_orbit_label'])

    @overall
    def check_sub_char_orbit_label(self):
        # check that sub_char_orbit_label matches sub_char_orbit_index
        return self.check_letter_code('sub_char_orbit_index', 'sub_char_orbit_label')

    @overall
    def check_conrey_indexes(self):
        # check that conrey_indexes matches galois_orbit for char_orbit_label in char_dir_orbits
        return self.check_crosstable('char_dir_orbits', 'conrey_indexes', ['level', 'char_orbit_index'], 'galois_orbit', ['modulus', 'orbit_index'])

    @overall
    def check_sub_conrey_indexes(self):
        # check that sub_conrey_indexes matches galois_orbit for sub_char_orbit_label in char_dir_orbits
        return self.check_crosstable('char_dir_orbits', 'sub_conrey_indexes', ['sub_level', 'sub_char_orbit_index'], 'galois_orbit', ['modulus', 'orbit_index'])

    @overall
    def check_sub_dim(self):
        # check that sub_dim = dim S_k^new(sub_level, sub_chi)
        return self.check_crosstable('mf_subspaces', 'sub_dim', 'sub_label', 'dim', 'label')

class mf_gamma1_subspaces(subspaces):
    table = db.mf_gamma1_subspaces

    @overall
    def check_label(self):
        # check that label matches level, weight
        return self.check_string_concatenation('label', ['level', 'weight'])

    @overall
    def check_sub_label(self):
        # check that sub_label matches sub_level, weight
        return self.check_string_concatenation('sub_label', ['sub_level', 'weight'])

    @overall
    def check_sub_dim(self):
        # check that sub_dim = dim S_k^new(Gamma1(sub_level))
        return self.check_crosstable('mf_gamma1', 'sub_dim', ['sub_level', 'weight'], 'dim', ['level', 'weight'])

class mf_newforms(TableChecker):
    table = db.mf_newforms

    @overall
    def check_traces_count(self):
        # there should be exactly 1000 records in mf_hecke_traces for each record in mf_newforms
        return self.check_crosstable_count('mf_hecke_traces', 1000, 'hecke_orbit_code')

    @overall
    def check_traces_match(self):
        # check that traces[n] matches trace_an in mf_hecke_traces
        return self.check_crosstable_aggregate('mf_hecke_traces', 'traces', 'hecke_orbit_code', 'trace_an', sort='n', truncate=1000)

    @overall
    def check_lpoly_count(self):
        # there should be exactly 25 records in mf_hecke_lpolys for each record in mf_newforms with field_poly
        return self.check_crosstable_count('mf_hecke_lpolys', 25, 'hecke_orbit_code', constraint={'field_poly':{'$exists':True}})

    @overall
    def check_embeddings_count(self):
        # check that for such box with embeddings set, the number of rows in mf_hecke_cc per hecke_orbit_code matches dim
        return any(self.check_crosstable_count('mf_hecke_cc', 'dim', 'hecke_orbit_code', constraint=self._box_query(box) for box in db.mf_boxes.search({'embeddings':True})))

    @overall
    def check_embeddings_count(self):
        # check that for such box with embeddings set, that summing over `dim` matches embeddings_count
        return all(sum(self.table.search(self._box_query(box), 'dim')) == box['embeddings_count'] for box in db.mf_boxes.search({'embeddings':True}))

    @overall
    def check_roots(self):
        # check that embedding_root_real, and embedding_root_image present in mf_hecke_cc whenever field_poly is present
        # I didn't manage to write a generic one for this one
        join = self._make_join('hecke_orbit_code', None)
        query = SQL("SELECT t1.{0} FROM {1} t1, {2} t2 WHERE {3} AND t2.{4} is NULL AND t2.{5} is NULL AND t1.{6} is not NULL LIMIT 1").format(
                Identifier(self.table._label_col),
                Identifier(self.table.search_table),
                Identifier('mf_hecke_cc'),
                join,
                Identifier("embedding_root_real"),
                Identifier("embedding_root_imag"),
                Identifier("field_poly")
                )
        cur = db._execute(query, cvalues)
        if cur.rowcount > 0:
            return cur.fetchone()[0]

    @slow
    def check_roots_are_roots(self, rec):
        # check that  embedding_root_real, and embedding_root_image  approximate a root of field_poly
        if rec['field_poly'] is not None:
            poly = PolynomialRing(CC, "x")(rec['field_poly'])
            for root in db.mf_hecke_cc.search({'hecke_orbit_code': rec['hecke_orbit_code']}, ["embedding_root_real", "embedding_root_imag"]):
                r = CC(*[root[elt] for elt in ["embedding_root_real", "embedding_root_imag"]])
                if poly.evaluate(r) > 1e-13:
                    return False
        return True





class mf_hecke_nf(TableChecker):
    table = db.mf_hecke_nf

    @overall
    def check_bijection(self):
        # there should be a record present for every record in mf_newforms that has field_poly set (and no others, check count)
        return (self.check_crosstable_count('mf_newforms', 1, 'label') or
                self.check_count(db.mf_newforms.count({'field_poly':{'$exists':True}})))

    @overall
    def check_hecke_orbit_code(self):
        # check that label matches hecke_orbit_code and is present in mf_newforms
        return self.check_crosstable('mf_newforms', 'hecke_orbit_code', 'label')

    @overall
    def check_field_poly(self):
        # check that field_poly matches field_poly in mf_newforms
        return self.check_crosstable('mf_newforms', 'field_poly', 'label')

    @overall
    def check_hecke_ring_rank(self):
        # check that hecke_ring_rank = deg(field_poly)
        return self.check_array_len_col('field_poly', 'hecke_ring_rank', shift=1)

    @overall
    def check_hecke_ring_power_basis_set(self):
        # if hecke_ring_power_basis is set, check that hecke_ring_cyclotomic_generator is 0 and hecke_ring_numerators, ... are null
        return self.check_value({'hecke_ring_cyclotomic_generator':0,
                                 'hecke_ring_numerators':None,
                                 'hecke_ring_denominators':None,
                                 'hecke_ring_inverse_numerators':None,
                                 'hecke_ring_inverse_denominators':None},
                                {'hecke_ring_power_basis':True})

    @overall
    def check_hecke_ring_cyclotomic_generator(self):
        # TODO check field_poly_is_cyclotomic
        # if hecke_ring_cyclotomic_generator is greater than 0 check that hecke_ring_power_basis is false and hecke_ring_numerators, ... are null, and that field_poly_is_cyclotomic is set in mf_newforms record.
        return (self.check_value({'hecke_ring_power_basis':False,
                                  'hecke_ring_numerators':None,
                                  'hecke_ring_denominators':None,
                                  'hecke_ring_inverse_numerators':None,
                                  'hecke_ring_inverse_denominators':None},
                                 {'hecke_ring_cyclotomic_generator':{'$gt':0}}) or
                None)

    @slow
    def check_hecke_ring_character_values_and_an(self, rec):
        # check that hecke_ring_character_values has the correct format, depending on whether hecke_ring_cyclotomic_generator is set or not
        # check that an has length 100 and that each entry is either a list of integers of length hecke_ring_rank (if hecke_ring_cyclotomic_generator=0) or a list of pairs
        # check that ap has length pi(maxp) and that each entry is formatted correctly (as for an)
        an = rec['an']
        if len(an) != 100:
            return False
        ap = rec['ap']
        maxp = rec['maxp']
        if len(ap) != prime_pi(maxp):
            return False
        if maxp < 997:
            return False
        m = rec['hecke_ring_cyclotomic_generator']
        d = rec['hecke_ring_rank']
        def check_val(val):
            if not isinstance(val, list):
                return False
            if m == 0:
                if len(val) != d or not all(isinstance(c, (int, Integer)) for c in val):
                    return False
            else:
                for pair in val:
                    if len(pair) != 2:
                        return False
                    if not isinstance(pair[0], (int, Integer)):
                        return False
                    e = pair[1]
                    if not (isinstance(e, (int, Integer)) and 0 <= 2*e < m):
                        return False
        if not all(check_val(a) for a in an):
            return False
        if not all(check_val(a) for a in ap):
            return False
        for p, a in zip(prime_range(100), ap):
            if a != an[p-1]:
                return False
        N = Integer(rec['label'].split('.')[0])
        total_order = 1
        for g, val in rec['hecke_ring_character_values']:
            total_order *= mod(g, N).multiplicative_order()
            if not check_val(val):
                return False
        return total_order == euler_phi(N)

class mf_hecke_traces(TableChecker):
    table = db.mf_hecke_traces

    @overall
    def check_constraints_hecke_orbit_code_n(self):
        return self.check_uniqueness_constraint(['hecke_orbit_code', 'n'])

    @overall
    def check_total_count(self):
        # check that hecke_orbit_code is present in mf_newforms
        return self.check_count(1000 * db.mf_newforms.count())

class mf_hecke_lpolys(TableChecker):
    table = db.mf_hecke_lpolys

    @overall
    def check_constraint_hecke_orbit_code_p(self):
        return self.check_uniqueness_constraint(['hecke_orbit_code', 'p'])

    @overall
    def check_total_count(self):
        # check that hecke_orbit_code is present in mf_newforms
        return self.check_count(25 * db.mf_newforms.count({'field_poly':{'$exists':True}}))

    @overall
    def check_prime_count(self):
        # check that every prime p < 100 occurs exactly once for each hecke_orbit_code
        cnt = db.mf_newforms.count({'field_poly':{'$exists':True}})
        return any(self.check_count(cnt, {'p': p}) for p in prime_range(100))

    @overall
    def check_lpoly_degree(self):
        # TODO
        # check that degree of lpoly is twice the dimension in mf_newforms
        pass

    @overall
    def check_lpoly_trace_det(self):
        # TODO - should be possible with a three way join
        # check that linear coefficient of lpoly is -trace(a_p) and constant coefficient is 1

class mf_hecke_newspace_traces(TableChecker):
    table = db.mf_hecke_newspace_traces

    @overall
    def check_constraints_hecke_orbit_code_n(self):
        return self.check_uniqueness_constraint(['hecke_orbit_code', 'n'])

    @overall
    def check_total_count(self):
        # check that hecke_orbit_code is present in mf_newspaces
        return self.check_count(1000 * db.mf_newspaces.count({'traces':{'$exists':True}}))

class mf_hecke_cc(TableChecker):
    table = db.mf_hecke_cc

    @overall
    def check_uniqueness_lfunction_label(self):
        return self.check_uniqueness_constraint(['lfunction_label'])

    @overall
    def check_hecke_orbit_code_lfunction_label(self):
        # check that lfunction_label is consistent with hecke_orbit_code
        return self._run_query(SQL("{0} != from_newform_label_to_hecke_orbit_code({1})").format(Identifier('hecke_orbit_code'), Identifier('lfunction_label')))

    @overall
    def check_hecke_orbit_code_lfunction_label(self):
        # check that lfunction_label is consistent with conrey_lebel, embedding_index
        return self._run_query(SQL("regexp_split_to_array({0},'.')[5:6] != array({1}::text,{2}::text)").format(Identifier('lfunction_label'), Identifier('conrey_label'), Identifier('embedding_index')))

    @overall
    def check_an_pairs(self):
        # check that an_normalized is a list of pairs
        return self.check_array_len_eq_constant('an_normalized', 2, array_dim = 2)

    @overall
    def check_an_length(self):
        # check that an_normalized is of length at least 1000
        return self.check_array_len_eq_constant('an_normalized', 1000)



    @slow
    def check_angles(self, rec):
        # check that angles lie in (-0.5,0.5] and are null for p dividing the level
        level = int(rec['lfunction_label'].split('.')[0])
        for p, angle in zip(prime_range(1000), rec['angles']):
            if level % p == 0:
                if angle is not None:
                    return False
            elif not( angle <= 0.5 and angle > -0.5 ):
                return False
        else:
            return True

# Per row
# check that embedding_m is consistent with conrey_label and embedding_index (use conrey_indexes list in mf_newformes record to do this)
# (optional) check that summing (unnormalized) an over embeddings with a given hecke_orbit_code gives an approximation to tr(a_n) -- we probably only want to do this for specified newforms/newspaces, otherwise this will take a very long time.


class char_dir_orbits(TableChecker):
    table = db.char_dir_orbits

class char_dir_values(TableChecker):
    table = db.char_dir_values
