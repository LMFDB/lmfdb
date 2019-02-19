##################################
# WARNING ## WARNING ## WARNING ##
##################################
#  Nothing in this file is safe  #
#       from SQL injection       #
##################################
import traceback, time, sys, os, inspect
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from lmfdb.db_backend import db, SQL, Composable, IdentifierWrapper as Identifier, Literal
from types import MethodType
from collections import defaultdict
from lmfdb.lfunctions.Lfunctionutilities import names_and_urls
from sage.all import Integer, prod, floor, mod, euler_phi, prime_pi, cached_function, ZZ, RR, CC, Gamma1, Gamma0, PolynomialRing, dimension_new_cusp_forms, dimension_eis, prime_range, dimension_cusp_forms, dimension_modular_forms, kronecker_symbol, NumberField, gap, psi
from dirichlet_conrey import DirichletGroup_conrey, DirichletCharacter_conrey
from datetime import datetime

def accumulate_failures(L):
    """
    Accumulates a list of bad labels
    """
    return sum(L, [])

@cached_function
def kbarbar(weight):
    # The weight part of the analytic conductor
    return psi(RR(weight/2)).exp() / (2*RR.pi())

def analytic_conductor(level, weight):
    return level * kbarbar(weight)**2

def check_analytic_conductor(level, weight, analytic_conductor_stored, threshold = 1e-12):
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
    return floor(weight * Gamma0(level).index()/12)

class speed_decorator(object):
    """
    Transparently wraps a function, so that functions can be classified by "isinstance".  Allow keyword arguments
    """
    disabled = False # set to True to skip this check
    max_failures = 1 # maximum number of failures to show
    def __init__(self, f=None, **kwds):
        self.f = f
        self._kwds = kwds
        if f is not None:
            self.__name__ = f.__name__
            for key, val in kwds.items():
                setattr(self, key, val)
    def __call__(self, *args, **kwds):
        if self.f is None:
            assert len(args) == 1 and len(kwds) == 0
            return self.__class__(args[0], **self._kwds)
        return self.f(*args, **kwds)

class per_row(speed_decorator):
    """
    A check that is run by iterating through each row in a sample of the table.

    The wrapped function should take a row (dictionary) as input and return True if everything is okay, False otherwise.
    """
    progress_interval = None # set to override the default interval for printing to the progress file
    constraint = {} # this test is only run on rows satisfying this constraint
    projection = 1 # default projection; override in order to not fetch large columns.  label_col is appended

class one_query(speed_decorator):
    """
    A check as being one that's run once overall for the table, rather than once for each row

    The wrapped function should take no input and return a list of bad labels (at most max_failures)
    """
    pass

class slow(per_row):
    """
    A per-row check that is slow to run
    """
    ratio = 0.1 # ratio of rows to run this test on

class fast(per_row):
    """
    A per-row check that is fast to run
    """
    ratio = 1 # ratio of rows to run this test on

class overall(one_query):
    """
    An overall check that is fast to run
    """
    pass

class overall_long(one_query):
    """
    An overall check that is slow to run
    """
    pass

class TableChecker(object):
    label_col = 'label' # default
    def __init__(self, logfile=None, default_typ=None):
        if logfile is None:
            logfile = "%s.%s" % (self.__class__.__name__, default_typ.__name__)
        self.logfile = logfile + '.log'
        self.errfile = logfile + '.errors'
        self.progfile = logfile + '.progress'
        self.donefile = logfile + '.done'
        self.default_typ = default_typ

    @classmethod
    def _get_checks_count(cls, typ):
        return len([f for fname, f in inspect.getmembers(cls) if isinstance(f, typ)])

    def _get_checks(self, typ):
        return [MethodType(f, self, self.__class__) for fname, f in inspect.getmembers(self.__class__) if isinstance(f, typ)]

    def _report_error(self, msg, log, prog):
        with open(self.errfile, 'a') as err:
            err.write(msg)
            err.write(traceback.format_exc() + '\n')
        log.write(msg)
        prog.write(msg)
        return 1

    def run(self, typ=None):
        if typ is None:
            typ = self.default_typ
        table = self.table
        checks = self._get_checks(typ)
        failures = 0
        disabled = 0
        errors = 0
        aborts = 0
        with open(self.logfile, 'a') as log:
            with open(self.progfile, 'a') as prog:
                start = time.time()
                for check_num, check in enumerate(checks, 1):
                    name = "%s.%s"%(self.__class__.__name__, check.__name__)
                    if check.disabled:
                        prog.write('%s (check %s/%s) disabled\n'%(name, check_num, len(checks)))
                        disabled += 1
                        continue
                    check_start = time.time()
                    prog.write('%s (check %s/%s) started at %s\n'%(name, check_num, len(checks), datetime.now()))
                    prog.flush()
                    if typ in [fast, slow]:
                        total = int(table.count(check.constraint) * check.ratio)
                        progress_interval = check.progress_interval
                        if progress_interval is None:
                            # Report about 100 times during run
                            if total < 10000:
                                progress_interval = 100 * (1 + total//10000)
                            else:
                                progress_interval = 1000 * (1 + total//100000)
                        projection = check.projection
                        if self.label_col not in projection:
                            projection = [self.label_col] + projection
                        try:
                            search_iter = table.random_sample(check.ratio, check.constraint, projection)
                        except Exception:
                            msg = "Exception in %s generating search results\n"%(me)
                            self._report_error(msg)
                            errors += 1
                            continue
                    try:
                        if typ in [fast, slow]:
                            for rec_no, rec in enumerate(search_iter, 1):
                                if rec_no % progress_interval == 0:
                                    prog.write('%s/%s in %ss\n'%(rec_no, total, time.time() - check_start))
                                    prog.flush()
                                if not check(rec):
                                    log.write('%s: %s\n'%(name, rec[self.label_col]))
                                    failures += 1
                                if failures >= check.max_failures:
                                    aborts += 1
                                    break
                        else:
                            # self._cur_limit controls the max number of failures returned
                            self._cur_limit = check.max_failures
                            bad_labels = check()
                            if bad_labels:
                                for label in bad_labels:
                                    log.write('%s: %s\n'%(name, bad_label))
                                log.flush()
                                failures += len(bad_labels)
                    except Exception:
                        if typ in [fast, slow]:
                            msg = 'Exception in %s (%s):\n'%(name, rec.get(self.label_col, ''))
                        else:
                            msg = 'Exception in %s\n'%(name)
                        errors += self._report_error(msg, log, prog)
                    else:
                        prog.write('%s finished after %ss\n'%(name, time.time() - check_start))
        with open(self.donefile, 'a') as done:
            status = "%s failures"%failures
            if disabled:
                status += ", %s disabled"%disabled
            if aborts:
                status += ", %s ABORTS"%aborts
            if errors:
                status += ", %s ERRORS"%errors
            done.write("%s.%s: %s in %ss\n"%(me, typ.__name__, status, time.time() - start))


    # Add uniqueness constraints

    #####################
    # Utility functions #
    #####################
    def _run_query(self, condition, constraint={}, values=[], table=None):
        """
        INPUT:

        - ``condition`` -- an SQL object giving a condition on the search table
        - ``constraint`` -- a dictionary, as passed to the search method, or an SQL object
        """
        if table is None:
            table = Identifier(self.table.search_table)
        elif isinstance(table, basestring):
            table = Identifier(table)
        label_col = Identifier(self.label_col)

        # WARNING: the following is not safe from SQL injection, so be careful if you copy this code
        query = SQL("SELECT {0} FROM {1} WHERE {2}").format(
                label_col,
                table,
                condition)
        if not isinstance(constraint, Composable):
            constraint, cvalues = self.table._parse_dict(constraint)
            if constraint is not None:
                values = values + cvalues
        if constraint is not None:
            query = SQL("{0} AND {1}").format(query, constraint)
        query = SQL("{0} LIMIT %s").format(query)
        cur = db._execute(query, values + [self._cur_limit])
        return [rec[0] for rec in cur]

    def _make_join(self, join1, join2):
        if not isinstance(join1, list):
            join1 = [join1]
        if join2 is None:
            join2 = join1
        elif not isinstance(join2, list):
            join2 = [join2]
        if len(join1) != len(join2):
            raise ValueError("join1 and join2 must have the same length")
        def identify(J, table):
            res = []
            for j in J:
                if isinstance(j, (int, Integer)):
                    res.append(Literal(j))
                elif isinstance(j, Composable):
                    res.append(j)
                else:
                    res.append(SQL(table + ".") + Identifier(j))
            return res
        join1 = identify(join1, "t1")
        join2 = identify(join2, "t2")
        return SQL(" AND ").join(SQL("{0} = {1}").format(j1, j2) for j1, j2 in zip(join1, join2))

    def _run_crosstable(self, quantity, other_table, col, join1, join2=None, constraint={}, values=[], subselect_wrapper="", extra=None):
        """
        Checks that `quantity` matches col

        INPUT:

        - ``quantity`` -- a column name or an SQL object giving some quantity from the ``other_table``
        - ``other_table`` -- the name of the other table
        - ``col`` -- an integer or the name of column to check against ``quantity``
        - ``join1`` -- a column or list of columns on self on which we will join the two tables
        - ``join2`` -- a column or list of columns (default: `None`) on ``other_table`` on which we will join the two tables. If `None`, we take ``join2`` = ``join1``, see `_make_join`
        - ``constraint`` -- a dictionary, as passed to the search method
        - ``subselect_wrapper`` -- a string, e.g., "ARRAY" to convert the inner select query
        - ``extra`` -- SQL object to append to the subquery.  This can hold additional constraints or set the sort order for the inner select query
        """
        # WARNING: since it uses _run_query, this whole function is not safe against SQL injection,
        # so should only be run locally in data validation
        join = self._make_join(join1, join2)
        if isinstance(col, (int, Integer)):
            col = Literal(col)
        elif isinstance(col, basestring):
            col = SQL("t1.{0}").format(Identifier(col))
        if isinstance(quantity, basestring):
            quantity = SQL("t2.{0}").format(Identifier(quantity))
        # This is unsafe
        subselect_wrapper = SQL(subselect_wrapper)
        if extra is None:
            extra = SQL("")
        condition = SQL("{0} != {1}(SELECT {2} FROM {3} t2 WHERE {4}{5})").format(
            col,
            subselect_wrapper,
            quantity,
            Identifier(other_table),
            join,
            extra)
        return self._run_query(condition, constraint, values, table=SQL("{0} t1").format(Identifier(self.table.search_table)))

    def check_count(self, cnt, constraint={}):
        real_cnt = self.table.count(constraint)
        if real_cnt != cnt:
            return '%s != %s (%s)' % (real_cnt, cnt, constraint)

    def check_eq(self, col1, col2, constraint={}):
        return self._run_query(SQL("{0} != {1}").format(Identifier(col1), Identifier(col2)), constraint)

    def _check_arith(self, a_columns, b_columns, constraint, op):
        if isinstance(a_columns, basestring):
            a_columns = [a_columns]
        if isinstance(b_columns, basestring):
            b_columns = [b_columns]
        return self._run_query(SQL(" != ").join([
            SQL(" %s "%op).join(map(Identifier, a_columns)),
            SQL(" %s "%op).join(map(Identifier, b_columns))]), constraint)

    def check_sum(self, a_columns, b_columns, constraint={}):
        return self._check_arith(a_columns, b_columns, constraint, '+')

    def check_product(self, a_columns, b_columns, constraint={}):
        return self._check_arith(a_columns, b_columns, constraint, '*')

    def check_array_sum(self, array_column, value_column, constraint={}):
        """
        Checks that sum(array_column) == value_column
        """
        return self._run_query(SQL("(SELECT SUM(s) FROM UNNEST({0}) s) != {1}").format(
            Identifier(array_column), Identifier(value_column)), constraint)

    def check_array_product(self, array_column, value_column, constraint={}):
        """
        Checks that prod(array_column) == value_column
        """
        return self._run_query(SQL("(SELECT PROD(s) FROM UNNEST({0}) s) != {1}").format(
            Identifier(array_column), Identifier(value_column)), constraint)

    def check_divisible(self, numerator, denominator, constraint={}):
        if isinstance(denominator, (Integer, int)):
            return self._run_query(SQL("MOD({0}, %s) != 0").format(Identifier(numerator)),
                                   constraint, [denominator])
        else:
            return self._run_query(SQL("MOD({0}, {1}) != 0").format(
                Identifier(numerator), Identifier(denominator)), constraint)

    def check_non_divisible(self, numerator, denominator, constraint={}):
        if isinstance(denominator, (Integer, int)):
            return self._run_query(SQL("MOD({0}, %s) = 0").format(Identifier(numerator)),
                                   constraint, [denominator])
        return self._run_query(SQL("MOD({0}, {1}) = 0").format(
            Identifier(numerator), Identifier(denominator)))

    def check_values(self, values, constraint={}):
        if isinstance(values, Composable):
            vstr = values
            vvalues = None
        else:
            vstr, vvalues = self.table._parse_dict(values)
        if vstr is not None:
            # Otherwise no values, so nothing to check
            return self._run_query(SQL("NOT ({0})").format(vstr), constraint, values=vvalues)

    def check_non_null(self, columns, constraint={}):
        if isinstance(columns, basestring):
            columns = [columns]
        return self.check_values({col: {'$exists':True} for col in columns}, constraint)

    def check_null(self, columns, constraint={}):
        if isinstance(columns, basestring):
            columns = [columns]
        return self.check_values({col: None for col in columns}, constraint)

    def check_iff(self, condition1, condition2):
        return (self.check_values(condition1, condition2) or
                self.check_values(condition2, condition1))

    def check_array_len_gte_constant(self, column, limit, constraint={}):
        """
        Length of array greater than or equal to limit
        """
        return self._run_query(SQL("array_length({0}, 1) < %s").format(Identifier(column)),
                               constraint, [limit])

    def check_array_len_eq_constant(self, column, limit, constraint={}, array_dim = 1):
        """
        Length of array equal to constant
        """
        return self._run_query(SQL("array_length({0}, {1}) != {2}").format(
            Identifier(column),
            Literal(int(array_dim)),
            Literal(int(limit))
            ),
            constraint)

    def check_array_len_col(self, array_column, len_column, constraint={}, shift=0, array_dim = 1):
        """
        Length of array_column matches len_column
        """
        return self._run_query(SQL("array_length({0}, {3}) != {1} + {2}").format(
            Identifier(array_column),
            Identifier(len_column),
            Literal(int(shift)),
            Literal(array_dim),
            ),
            constraint)

    def check_array_bound(self, array_column, bound, constraint={}, upper=True):
        """
        Check that all entries in the array are <= bound (or >= if upper is False)
        """
        op = '>=' if upper else '<='
        return self._run_query(SQL("NOT ({0} %s ALL({1}))" % op).format(Literal(bound), Identifier(array_column)), constraint=constraint)

    def check_array_concatenation(self, a_columns, b_columns, constraint={}):
        if isinstance(a_columns, basestring):
            a_columns = [a_columns]
        if isinstance(b_columns, basestring):
            b_columns = [b_columns]
        return self._run_query(SQL("{0} != {1}").format(
            SQL(" || ").join(map(Identifier, a_columns)),
            SQL(" || ").join(map(Identifier, b_columns))), constraint=constraint)

    def check_string_concatenation(self,
            label_col,
            other_columns,
            constraint={},
            sep='.',
            convert_to_base26 = {}):
        """
        Check that the label_column is the concatenation of the other columns with the given separator

        Input:

        - ``label_col`` -- the label_column
        - ``other_columns`` --  the other columns from which we can deduce the label
        - ``constraint`` -- a dictionary, as passed to the search method
        - ``sep`` -- the separator for the join
        - ``convert_to_base26`` -- a dictionary where the keys are columns that we need to convert to base26, and the values is that the shift that we need to apply
        """
        oc_converted = [SQL('to_base26({0} + {1})').format(Identifier(col), Literal(int(convert_to_base26[col])))
                if col in convert_to_base26
                else Identifier(col) for col in other_columns]
        #intertwine the separator
        oc = [oc_converted[i//2] if i%2 == 0 else Literal(sep) for i in range(2*len(oc_converted)-1)]

        return self._run_query(SQL(" != ").join([SQL(" || ").join(oc), Identifier(label_col)]), constraint)

    def check_string_startswith(self, col, head, constraint={}):
        value = head.replace('_',r'\_').replace('%',r'\%') + '%'
        return self._run_query(SQL("NOT ({0} LIKE {1}||{2})").format(Identifier(col)), constraint, values = [value])

    def check_sorted(self, column):
        return self._run_query(SQL("{0} != sort({0})").format(Identifier(column)))

    def check_crosstable(self, other_table, col1, join1, col2=None, join2=None, constraint={}):
        """
        Check that col1 and col2 are the same where col1 is a column in self.table, col2 is a column in other_table,
        and the tables are joined by the constraint that self.table.join1 = other_table.join2.

        Here col2 and join2 default to col1 and join1, and join1 and join2 are allowed to be lists of columns
        """
        if col2 is None:
            col2 = col1

        return self._run_crosstable(col2, other_table, col1, join1, join2, constraint=constraint)



    def check_crosstable_count(self, other_table, col, join1, join2=None, constraint={}):
        """
        Check that col stores the count of the rows in the other table joining with this one.

        col is allowed to be an integer, in which case a constant count is checked.
        """

        return self._run_crosstable(SQL("COUNT(*)"), other_table, col, join1, join2, constraint)

    def check_crosstable_sum(self, other_table, col1, join1, col2=None, join2=None, constraint={}):
        """
        Check that col1 is the sum of the values in col2 where join1 = join2

        Here col2 and join2 default to col1 and join1, and join1 and join2 are allowed to be lists of columns
        """
        if col2 is None:
            col2 = col1
        sum2 = SQL("SUM(t2.{0})").format(Identifier(col2))
        return self._run_crosstable(sum2, other_table, col1, join1, join2, constraint)

    def check_crosstable_dotprod(self, other_table, col1, join1, col2, join2=None, constraint={}):
        """
        Check that col1 is the sum of the product of the values in the columns of col2 over rows of other_table with self.table.join1 = other_table.join2.

        There are some peculiarities of this method, resulting from its application to mf_subspaces.
        col1 is allowed to be a pair, in which case the difference col1[0] - col1[1] will be compared.

        col2 does not take value col1 as a default, since they are playing different roles.
        """
        if isinstance(col1, list):
            if len(col1) != 2:
                raise ValueError("col1 must have length 2")
            col1 = SQL("t1.{0} - t1.{1}").format(Identifier(col1[0]), Identifier(col1[1]))
        dotprod = SQL("SUM({0})").format(SQL(" * ").join(SQL("t2.{0}").format(Identifier(col)) for col in col2))
        return self._run_crosstable(dotprod, other_table, col1, join1, join2, constraint)

    def check_crosstable_aggregate(self, other_table, col1, join1, col2=None, join2=None, sort=None, truncate=None, constraint={}):
        """
        Check that col1 is the sorted array of values in col2 where join1 = join2

        Here col2 and join2 default to col1 and join1, and join1 and join2 are allowed to be lists of columns

        sort defaults to col2, but can be a list of columns in other_table
        """
        if col2 is None:
            col2 = col1
        if truncate is not None:
            col1 = SQL("t1.{0}[:%s]"%(int(truncate))).format(Identifier(col1))
        if sort is None:
            sort = SQL(" ORDER BY t2.{0}").format(Identifier(col2))
        else:
            sort = SQL(" ORDER BY {0}").format(SQL(", ").join(SQL("t2.{0}").format(Identifier(col)) for col in sort))
        return self._run_crosstable(col2, other_table, col1, join1, join2, constraint, subselect_wrapper="ARRAY", extra=sort)

    def check_letter_code(self, index_column, letter_code_column, constraint = {}):
        return self._run_query(SQL("{0} != to_base26({1} - 1)").format(Identifier(letter_code_column), Identifier(index_column)), constraint)

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


    label = None
    label_conversion = {}
    @overall
    def check_label(self):
        # check that label matches self.label
        if self.label is not None:
            return self.check_string_concatenation(self.label_col, self.label, convert_to_base26 = self.label_conversion)

    uniqueness_constraints = []

    @overall
    def check_uniqueness_constraints(self):
        # check that the uniqueness constraints are satisfied
        constraints = set(tuple(sorted(D['columns'])) for D in self.table.list_constraints().values() if D['type'] == 'UNIQUE')
        for constraint in self.uniqueness_constraints:
            if tuple(sorted(constraint)) not in constraints:
                return ",".join(constraint)

    hecke_orbit_code = []

    @overall
    def check_hecke_orbit_code(self):
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
                return self._run_query(SQL("{0} != {1}::bigint + ({2}::bit(64)<<24)::bigint + (({3}-1)::bit(64)<<36)::bigint + (({4}-1)::bit(64)<<52)::bigint").format(*map(Identifier, [hoc_column, N_column, k_column, i_column, x_column])))
            else:
                return self._run_query(SQL("{0} != {1}::bigint + ({2}::bit(64)<<24)::bigint + (({3}-1)::bit(64)<<36)::bigint").format(*map(Identifier,[hoc_column, N_column, k_column, i_column])))

class mf_newspaces(TableChecker):
    table = db.mf_newspaces

    uniqueness_constraints = [
       ['label'],
       ['level', 'weight', 'char_orbit_index'],
       ['level', 'weight', 'char_orbit_label']]

    label = ['level', 'weight', 'char_orbit_label']

    hecke_orbit_code = ['hecke_orbit_code', ['level', 'weight', 'char_orbit_index']]

    @overall
    def check_box_count(self):
        # there should be exactly one row for every newspace in mf_boxes; for each box performing mf_newspaces.count(box query) should match newspace_count for box, and mf_newspaces.count() should be the sum of these
        return accumulate_failures(self.check_count(box['newspace_count'], self._box_query(box))
                   for box in db.mf_boxes.search())

    @overall
    def check_box_hecke_cutter_primes(self):
        # check that hecke_cutter_primes is set whenever space is in a box with eigenvalues set and `min(dims) <= 20`
        return accumulate_failures(self.check_non_null(['hecke_cutter_primes'], self._box_query(box, {'dim':{'$lte':20}}))
                   for box in db.mf_boxes.search({'eigenvalues':True}))

    @overall
    def check_box_straces(self):
        # check that traces, trace_bound, num_forms, and hecke_orbit_dims are set if space is in a box with straces set
        return accumulate_failures(
                self.check_non_null([
                        'traces',
                        'trace_bound',
                        'num_forms',
                        'hecke_orbit_dims'], self._box_query(box))
                   for box in db.mf_boxes.search({'straces':True}))

    @overall
    def check_char_orbit(self):
        # check that char_orbit matches char_orbit_label
        return self.check_letter_code('char_orbit_index', 'char_orbit_label')

    @overall
    def check_trace_display(self):
        # check that trace_display is set whenever traces is set and dim > 0
        return self.check_non_null(['trace_display'], {'traces':{'$exists': True}, 'dim':{'$gt': 0}})

    @overall
    def check_traces_len(self):
        # if present, check that traces has length at least 1000
        return self.check_array_len_gte_constant('traces', 1000, {'traces':{'$exists': True}})

    @overall
    def check_trace_bound0(self):
        # check that trace_bound=0 if num_forms=1
        return self.check_values({'trace_bound': 0}, {'num_forms':1})

    @overall
    def check_trace_bound1(self):
        # check that trace_bound = 1 if hecke_orbit_dims set and all dims distinct
        return self._run_query(SQL("hecke_orbit_dims!= ARRAY(SELECT DISTINCT UNNEST(hecke_orbit_dims) ORDER BY 1)"), {'trace_bound':1})

    @overall
    def check_trace_bound1_from_dims(self):
        # check that trace_bound = 1 if hecke_orbit_dims set and all dims distinct
        return self._run_query(SQL("hecke_orbit_dims IS NOT NULL AND hecke_orbit_dims = ARRAY(SELECT DISTINCT UNNEST(hecke_orbit_dims) ORDER BY 1) AND num_forms > 1 AND trace_bound != 1"))

    @overall
    def check_AL_dims_plus_dim(self):
        # check that AL_dims and plus_dim is set whenever char_orbit_index=1
        return self.check_non_null(['AL_dims', 'plus_dim'], {'char_orbit_index':1})

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
        return self.check_sum(['dim'], ['dihedral_dim', 'a4_dim', 'a5_dim', 's4_dim'],{'weight':1})

    @overall
    def check_relative_dim(self):
        # check that char_degree * relative_dim = dim
        return self.check_product('dim', ['char_degree', 'relative_dim'])

    @overall
    def check_len_hecke_orbit_dims(self):
        # if present, check that len(hecke_orbit_dims) = num_forms
        return self.check_array_len_col('hecke_orbit_dims', 'num_forms',{'hecke_orbit_dims':{'$exists':True}})

    @overall
    def check_sum_hecke_orbit_dims(self):
        # if present, check that sum(hecke_orbit_dims) = dim
        return self.check_array_sum('hecke_orbit_dims', 'dim', {'hecke_orbit_dims':{'$exists':True}})

    @overall(disabled=True)
    def check_sum_AL_dims(self):
        # if AL_dims is set, check that AL_dims sum to dim
        return self._run_query(SQL("{0} != (SELECT SUM(s) FROM (SELECT (x->2)::integer FROM jsonb_array_elements({1})) s)").format(Identifier('dim'), Identifier('AL_dims')), constraint={'AL_dims':{'$exists':True}})
    @overall
    def check_Nk2(self):
        # check that Nk2 = N*k*k
        return self.check_product('Nk2', ['level', 'weight', 'weight'])

    @overall
    def weight_parity_even(self):
        # check weight_parity
        return self.check_divisible('weight', 2, {'weight_parity':1})

    @overall
    def weight_parity_odd(self):
        # check weight_parity
        return self.check_non_divisible('weight', 2, {'weight_parity':-1})

    @overall
    def check_against_char_dir_orbits(self):
        # check that char_* atrributes and prim_orbit_index match data in char_dir_orbits table (conrey_indexes should match galois_orbit)
        return accumulate_failures(self.check_crosstable('char_dir_orbits', col, ['level', 'char_orbit_label'], charcol, ['modulus', 'orbit_label']) for col, charcol in [('char_orbit_index', 'orbit_index'), ('conrey_indexes', 'galois_orbit'), ('char_order', 'order'), ('char_conductor', 'conductor'), ('char_degree', 'char_degree'), ('prim_orbit_index', 'prim_orbit_index'), ('char_parity', 'parity'), ('char_is_real', 'is_real')])

    @overall
    def check_hecke_orbit_dims_sorted(self):
        # check that hecke_orbit_dims is sorted in increasing order
        return self.check_sorted('hecke_orbit_dims')

    ### mf_hecke_newspace_traces ###
    @overall_long
    def check_traces_count(self):
        # there should be exactly 1000 records in mf_hecke_traces for each record in mf_newspaces with traces set
        return self.check_crosstable_count('mf_hecke_newspace_traces', 1000, 'hecke_orbit_code', constraint={'traces':{'$exists':True}})

    @overall_long
    def check_traces_match(self):
        # check that traces[n] matches trace_an in mf_hecke_newspace_traces
        return self.check_crosstable_aggregate('mf_hecke_newspace_traces', 'traces', 'hecke_orbit_code', 'trace_an', sort=['n'], truncate=1000, constraint={'traces':{'$exists':True}})

    ### mf_subspaces ###
    @overall
    def check_oldspace_decomposition_totaldim(self):
        # from mf_subspaces
        # check that summing sub_dim * sub_mult over rows with a given label gives dim of S_k^old(N,chi)
        return self.check_crosstable_dotprod('mf_subspaces', ['cusp_dim', 'dim'], 'label', ['sub_mult', 'sub_dim'])

    ### mf_newspace_portraits ###
    @overall
    def check_portraits_count(self):
        # check that there is a portrait present for every nonempty newspace in box where straces is set
        return accumulate_failures(
                self.check_crosstable_count('mf_newspace_portraits', 1, 'label',
                    constraint=self._box_query(box, extras = {'dim':{'$gt':1}}))
                for box in db.mf_boxes.search({'straces':True}))

    ### mf_newforms ###
    @overall
    def check_hecke_orbit_dims_newforms(self):
        # check that dim is present in hecke_orbit_dims array in newspace record and that summing dim over rows with the same space label gives newspace dim
        return (self.check_crosstable_aggregate('mf_newforms', 'hecke_orbit_dims', ['level', 'weight','char_orbit_index'], 'dim', constraint={'num_forms':{'$exists':True}}) or
                self.check_crosstable_sum('mf_newforms', 'dim', 'label', 'dim', 'space_label', constraint={'num_forms':{'$exists':True}}))

    @fast(projection=['level', 'weight', 'analytic_conductor'])
    def check_analytic_conductor(self, rec):
        # check analytic_conductor
        return check_analytic_conductor(rec['level'], rec['weight'], rec['analytic_conductor'])

    @slow(projection=['level', 'level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square'])
    def check_level(self, rec):
        return self._check_level(rec)

    @slow(projection=['sturm_bound', 'level', 'weight'])
    def check_sturm_bound(self, rec):
        # check that sturm_bound is exactly floor(k*Index(Gamma0(N))/12)
        return rec['sturm_bound'] == sturm_bound(rec['level'], rec['weight'])


    @slow(constraint={'weight':{'$gt':1}}, projection=['level', 'weight', 'relative_dim', 'conrey_indexes'])
    def check_Skchi_dim_formula(self, rec):
        # for k > 1 check that dim is the Q-dimension of S_k^new(N,chi) (using sage dimension formula)
        # sample: dimension_new_cusp_forms(DirichletGroup(100).1^2,4)
        dirchar = DirichletGroup_conrey(rec['level'])[rec['conrey_indexes'][0]].sage_character()
        return dimension_new_cusp_forms(dirchar, rec['weight']) == rec['relative_dim']

    @slow(constraint={'weight':{'$gt':1}}, projection=['level', 'weight', 'char_degree', 'eis_dim', 'cusp_dim', 'mf_dim', 'conrey_indexes'])
    def check_dims(self, rec):
        # for k > 1 check each of eis_dim, eis_new_dim, cusp_dim, mf_dim, mf_new_dim using Sage dimension formulas (when applicable)
        dirchar = DirichletGroup_conrey(rec['level'])[rec['conrey_indexes'][0]].sage_character()
        k = rec['weight']
        m = rec['char_degree']
        return (dimension_eis(dirchar, k)*m == rec['eis_dim'] and
                dimension_cusp_forms(dirchar, k)*m == rec['cusp_dim'] and
                dimension_modular_forms(dirchar, k)*m == rec['mf_dim'])

class mf_gamma1(TableChecker):
    table = db.mf_gamma1
    label = ['level', 'weight']
    uniqueness_constraints = [[table._label_col], label]



    @overall
    def check_box_count(self):
        # there should be a row present for every pair (N,k) satisfying a box constraint on N,k,Nk2
        def make_query(box):
            query = self._box_query(box, drop=['char_order', 'dim'])
            # Have to remove small N if there are restrictions on the character order
            if 'omin' in box:
                if box['omin'] == 2:
                    if 'level' not in query:
                        query['level'] = {}
                    if '$gte' not in query['level'] or query['level']['gte'] < 3:
                        query['level']['$gte'] = 3
                else:
                    raise NotImplementedError
        return accumulate_failures(self.check_count(box['Nk_count'], make_query(box))
                   for box in db.mf_boxes.search())

    @overall
    def check_box_traces(self):
        # check that traces is set if space is in a box with traces set and no dimension/character constraint
        return accumulate_failures(self.check_non_null(['traces'], self._box_query(box, drop=['char_order', 'dim']))
                   for box in db.mf_boxes.search({'omin':None, 'omax':None, 'Dmin':None, 'Dmax':None, 'straces':True}))

    @overall
    def check_dim_wt1(self):
        # for k = 1 check that dim = dihedral_dim + a4_dim + a5_dim + s4_dim
        return self.check_sum(['dim'], ['dihedral_dim', 'a4_dim', 'a5_dim', 's4_dim'], {'weight': 1})

    @overall
    def check_trace_display(self):
        # check that trace_display is set whenever traces is set and dim > 0
        return self.check_non_null(['trace_display'], {'traces':{'$exists': True}, 'dim':{'$gt': 0}})

    @overall
    def check_traces_len(self):
        # if present, check that traces has length at least 1000
        return self.check_array_len_gte_constant('traces', 1000, {'traces':{'$exists': True}})

    @overall
    def check_mf_dim(self):
        # check that eis_dim + cusp_dim = mf_dim
        return self.check_sum(['eis_dim','cusp_dim'],['mf_dim'])

    @overall
    def check_dim(self):
        # check that eis_new_dim + dim = mf_new_dim
        return self.check_sum(['eis_new_dim','dim'], ['mf_new_dim'])

    @overall
    def check_Nk2(self):
        # check that Nk2 = N*k*k
        return self.check_product('Nk2', ['level', 'weight', 'weight'])

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
        # check that num_spaces matches the number of records in mf_newspaces with this level and weight and positive dimension
        # TODO: check that the number of char_orbits of level N and weight k is the same as the number of rows in mf_newspaces with this weight and level.  The following doesn't work since num_spaces counts spaces with positive dimension
        # self.check_crosstable_count('char_dir_orbits', 'num_spaces', ['level', 'weight_parity'], ['modulus', 'parity']))
        return self._run_crosstable(SQL("COUNT(*)"), 'mf_newspaces', 'num_spaces', ['level', 'weight'], extra=SQL(" AND t2.dim > 0"))

    ### mf_gamma1_subspaces ### 
    @overall
    def check_oldspace_decomposition_totaldim(self):
        # check that summing sub_dim * sub_mult over rows with a given label gives dim S_k(Gamma1(N))
        return self.check_crosstable_dotprod('mf_gamma1_subspaces', 'cusp_dim', 'label', ['sub_mult', 'sub_dim'])


    ### mf_gamma1_portraits ###
    @overall
    def check_portraits_count(self):
        # check that there is a portrait present for every record in mf_gamma1 with `dim > 0` and `level <= 4000`
        return self.check_crosstable_count('mf_gamma1_portraits', 1, 'label', constraint={'dim':{'$gt':0}, 'level':{'$lte':4000}})

    ### slow ###
    @slow(projection=['level', 'level_radical', 'level_primes', 'level_is_prime', 'level_is_prime_power',  'level_is_squarefree', 'level_is_square'])
    def check_level(self, rec):
        # check level_* attributes
        return self._check_level(rec)

    @slow(projection=['level', 'weight', 'analytic_conductor'])
    def check_analytic_conductor(self, rec):
        # check analytic_conductor
        return check_analytic_conductor(rec['level'], rec['weight'], rec['analytic_conductor'])

    @slow(projection=['level', 'weight', 'sturm_bound'])
    def check_sturm_bound(self, rec):
        # check that sturm_bound is exactly floor(k*Index(Gamma0(N))/12)
        return rec['sturm_bound'] == sturm_bound(rec['level'], rec['weight'])

    @slow(constraint={'weight':{'$gt':1}}, projection=['level', 'weight', 'dim'])
    def check_Sk_dim_formula(self, rec):
        # check that dim = dim S_k^new(Gamma1(N))
        return rec['dim'] == dimension_new_cusp_forms(Gamma1(rec['level']), rec['weight'])

    @slow(constraint={'weight':{'$gt':1}}, projection=['level', 'weight', 'eis_dim', 'cusp_dim', 'mf_dim'])
    def check_dims(self, rec):
        # for k > 1 check eis_dim, eis_new_dim, cusp_dim, mf_dim, mf_new_dim using Sage dimension formulas
        G = Gamma1(rec['level'])
        k = rec['weight']
        return(dimension_eis(G, k) == rec['eis_dim'] and
               dimension_cusp_forms(G, k) == rec['cusp_dim'] and
               dimension_modular_forms(G, k) == rec['mf_dim'])

class mf_newspace_portraits(TableChecker):
    table = db.mf_newspace_portraits
    label = ['level', 'weight', 'char_orbit_index']
    uniqueness_constraints = [[table._label_col], label]
    label_conversion = {'char_orbit_index': -1}

    # attached to mf_newspaces:
    # check that there is a portrait present for every nonempty newspace in box where straces is set

class mf_gamma1_portraits(TableChecker):
    table = db.mf_gamma1_portraits
    label = ['level', 'weight']
    uniqueness_constraints = [[table._label_col],label]

    # attached to mf_gamma1:
    # check that there is a portrait present for every record in mf_gamma1 with `dim > 0` and `level <= 4000`



class SubspacesChecker(TableChecker):
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

class mf_subspaces(SubspacesChecker):
    table = db.mf_subspaces
    label = ['level', 'weight', 'char_orbit_label']
    uniqueness_constraints = [['label', 'sub_label']]

    @overall
    def check_sub_label(self):
        # check that sub_label matches matches sub_level, weight, sub_char_orbit_index
        return self.check_string_concatenation('sub_label', ['sub_level', 'weight', 'sub_char_orbit_label'])

    @overall
    def check_char_orbit_label(self):
        # check that char_orbit_label matches char_orbit_index
        return self.check_letter_code('char_orbit_index', 'char_orbit_label')

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
        return self.check_crosstable('mf_spaces', 'sub_dim', 'sub_label', 'dim', 'label')

class mf_gamma1_subspaces(SubspacesChecker):
    table = db.mf_gamma1_subspaces
    label = ['level', 'weight']
    uniqueness_constraints = [['label', 'sub_level']]

    @overall
    def check_sub_dim(self):
        # check that sub_dim = dim S_k^new(Gamma1(sub_level))
        return self.check_crosstable('mf_gamma1', 'sub_dim', ['sub_level', 'weight'], 'dim', ['level', 'weight'])

class mf_newforms(TableChecker):
    table = db.mf_newforms
    label = ['level', 'weight', 'char_orbit_index', 'hecke_orbit']
    label_conversion = {'char_orbit_index': -1, 'hecke_orbit': -1}
    hecke_orbit_code = ['hecke_orbit_code', label]
    uniqueness_constraints = [[table._label_col], label, ['hecke_orbit_code']]

    @overall
    def check_box_count(self):
        # there should be exactly one row for every newform in a box listed in mf_boxes with newform_count set; for each such box performing mf_newforms.count(box query) should match newform_count for box, and mf_newforms.count() should be the sum of these
        total_count = 0
        for box in db.mf_boxes.search({'newform_count':{'$exists':True}}):
            bad_label = self.check_count(box['newform_count'], self._box_query(box))
            if bad_label:
                return bad_label
            total_count += box['newform_count']
        return self.check_count(total_count)

    @overall
    def check_hecke_ring_generator_nbound(self):
        # hecke_ring_generator_nbound > 0
        return self.check_values({'hecke_ring_generator_nbound': {'$gt': 0}})

    @overall
    def check_space_label(self):
        # check that space_label matches level, weight, char_orbit_index
        return self.check_string_concatenation('space_label', ['level', 'weight', 'char_orbit_label'])

    @overall
    def check_relative_dim(self):
        # check that char_degree * relative_dim = dim
        return self.check_product('dim', ['char_degree', 'relative_dim'])

    @overall
    def check_newspaces_overlap(self):
        # check that all columns mf_newforms has in common with mf_newspaces other than label, dim, relative_dim match (this covers all atributes that depend only on level, weight, char) (this implies) check that space_label is present in mf_newspaces
        bad_label = self.check_crosstable_count('mf_newspaces', 1, 'space_label', 'label')
        if bad_label:
            return bad_label
        for col in ['Nk2', 'analytic_conductor', 'char_conductor', 'char_degree', 'char_is_real', 'char_orbit_index', 'char_orbit_label', 'char_order', 'char_parity', 'char_values', 'conrey_indexes', 'dim', 'hecke_orbit_code', 'level', 'level_is_prime', 'level_is_prime_power', 'level_is_square', 'level_is_squarefree', 'level_primes', 'level_radical', 'prim_orbit_index', 'relative_dim', 'trace_display', 'traces', 'weight', 'weight_parity']:
            bad_label = self.check_crosstable('mf_newspaces', col, 'space_label', col, 'label')
            if bad_label:
                return bad_label + " (%s)"%col

    @overall
    def check_polredabs_set(self):
        # check that if nf_label is set, then is_polredabs is true
        return self.check_values({'is_polredabs':True}, {'nf_label':{'$exists':True}})

    @overall
    def check_field_poly_consequences(self):
        # check that is_polredabs is present whenever field_poly is
        # check that hecke_ring_generator_nbound is set whenever field_poly is set
        # check that qexp_display is present whenever field_poly is present
        return self.check_non_null(['is_polredabs', 'hecke_ring_generator_nbound', 'qexp_display'],
                                   {'field_poly': {'$exists':True}})

    @overall
    def check_field_poly(self):
        # if field_poly is set, check that is monic and of degree dim
        return self._run_query(SQL('array_length(field_poly, 1) = 1 AND field_poly[dim + 1]  = 1'), {'field_poly': {'$exists':True}})

    @overall
    def check_traces_length(self):
        # check that traces is present and has length at least 10000
        return (self.check_non_null(['traces']) or
                self.check_array_len_gte_constant('traces', 1000))

    @overall
    def check_trace_display(self):
        # check that trace_display is present and has length at least 4
        return (self.check_non_null(['trace_display']) or
                self.check_array_len_gte_constant('traces', 4))

    @overall
    def check_number_field(self):
        # if nf_label is present, check that there is a record in nf_fields and that mf_newforms field_poly matches nf_fields coeffs, and check that is_self_dual agrees with signature, and field_disc agrees with disc_sign * disc_abs in nf_fields
        nfyes = {'nf_label':{'exists':True}}
        selfdual = {'nf_label':{'exists':True}, 'is_self_dual':True}
        return (self.check_crosstable_count('nf_fields', 1, 'nf_label', 'label', constraint=nfyes) or
                # FIXME: coeffs is jsonb instead of numeric[]
                self.check_crosstable('nf_fields', 'field_poly', 'nf_label', 'coeffs', 'label', constraint=nfyes) or
                self.check_crosstable('nf_fields', 0, 'nf_label', 'r2', 'label', constraint=selfdual) or
                self.check_crosstable_dotprod('nf_fields', 'field_disc', 'nf_label', ['disc_sign', 'disc_abs'], constraint=nfyes))

    @overall
    def check_field_disc(self):
        # if hecke_ring_index_proved is set, verify that field_disc is set
        return self.check_non_null(['field_disc'], {'hecke_ring_index_proved':{'$exists':True}})

    @overall(max_failures=1000)
    def check_analytic_rank_proved(self):
        # check that analytic_rank_proved is true when analytic rank set (log warning if not)
                  return ', '.join(self.table.search({'analytic_rank_proved':False, 'analytic_rank': {'$exists':True}}, 'label'))

    @overall
    def check_self_twist_type(self):
        # check that self_twist_type is in {0,1,2,3} and matches is_cm and is_rm
        return (self.check_non_null(['is_cm', 'is_rm']) or
                self.check_iff({'self_twist_type':0}, {'is_cm':False, 'is_rm':False}) or
                self.check_iff({'self_twist_type':1}, {'is_cm':True, 'is_rm':False}) or
                self.check_iff({'self_twist_type':2}, {'is_cm':False, 'is_rm':True}) or
                self.check_iff({'self_twist_type':3}, {'is_cm':True, 'is_rm':True}))

    @overall
    def check_cmrm_discs(self):
        # check that self_twist_discs is consistent with self_twist_type (e.g. if self_twist_type is 3, there should be 3 self_twist_discs, one pos, two neg)
        return (self.check_array_len_eq_constant('rm_discs', 0, {'is_rm': False}) or
                self.check_array_len_eq_constant('rm_discs', 1, {'is_rm': True}) or
                self.check_array_len_eq_constant('cm_discs', 0, {'is_cm': False}) or
                self.check_array_len_eq_constant('cm_discs', 1, {'self_twist_type': 1}) or
                self.check_array_len_eq_constant('cm_discs', 2, {'self_twist_type': 3}))

    @overall
    def check_self_twist_discs(self):
        # check that cm_discs and rm_discs have correct signs and that their union is self_twist_discs
        return (self.check_array_bound('cm_discs', -1) or
                self.check_array_bound('rm_discs', 1, upper=False) or
                self.check_array_concatenation('self_twist_discs', ['cm_discs', 'rm_discs']))

    @overall
    def check_self_twist_proved(self):
        # check that self_twist_proved is set (log warning if not, currently there are 10-20 where it is not set)
        return self.check_values({'self_twist_proved':True})

    @overall
    def check_fricke_eigenval(self):
        # if present, check that fricke_eigenval is product of atkin_lehner_eigenvals
        return self._run_query(SQL('fricke_eigenval != prod2(atkin_lehner_eigenvals)'), {'fricke_eigenval':{'$exists':True}})

    @overall
    def check_sato_tate_set(self):
        # for k>1 check that sato_tate_group is set
        return self.check_non_null(['sato_tate_group'], {'weight':{'$gt':1}})

    @overall
    def check_sato_tate_value(self):
        # for k>1 check that sato_tate_group is consistent with is_cm and char_order (it should be 1.2.3.cn where n=char_order if is_cm is false, and 1.2.1.dn if is_cm is true)
        return (self._run_query(SQL("sato_tate_group != {0} || char_order").format(Literal("1.2.3.c")), constraint={'is_cm':False, 'weight':{'$gt':1}}) or
                self._run_query(SQL("sato_tate_group != {0} || char_order").format(Literal("1.2.1.d")), constraint={'is_cm':True, 'weight':{'$gt':1}}))

    @overall
    def check_projective_image_type(self):
        # for k=1 check that projective_image_type is present,
        return self.check_non_null('projective_image_type', {'weight':1})

    @overall
    def check_projective_image(self):
        # if present, check that projective_image is consistent with projective_image_type
        return (self.check_eq('projective_image_type', 'projective_image', {'projective_image_type':{'$ne':'Dn'}}) or
                self.check_string_startswith('projective_image', 'D', {'projective_image_type':'Dn'}))

    @overall
    def check_projective_field(self):
        # if present, check that projective_field_label identifies a number field in nf_fields with coeffs = projective_field
        return (self.check_crosstable_count('nf_fields', 1, 'projective_field_label', 'label', constraint={'projective_field_label':{'$exists':True}}) or
                # FIXME: coeffs is jsonb instead of numeric[]
                self.check_crosstable('nf_fields', 'projective_field', 'projective_field_label', 'coeffs', 'label'))

    @overall
    def check_artin_field(self):
        # if present, check that artin_field_label identifies a number field in nf_fields with coeffs = artin_field
        return (self.check_crosstable_count('nf_fields', 1, 'artin_field_label', 'label', constraint={'artin_field_label':{'$exists':True}}) or
                # FIXME: coeffs is jsonb instead of numeric[]
                self.check_crosstable('nf_fields', 'artin_field', 'artin_field_label', 'coeffs', 'label'))

    @overall
    def check_artin_degree(self):
        # if present, check that artin_field has degree equal to artin_degree
        return self.check_array_len_col('artin_field', 'artin_degree', constraint={'artin_field':{'$exists':True}}, shift=1)

    @overall
    def check_trivial_character_cols(self):
        # check that atkin_lehner_eigenvals, atkin_lehner_string, and fricke_eigenval are present if and only if char_orbit_index=1 (trivial character)
        yes = {'$exists':True}
        return self.check_iff({'atkin_lehner_eigenvals':yes, 'atkin_lehner_string':yes, 'fricke_eigenval':yes}, {'char_orbit_index':1})

    @overall
    def check_inner_twists(self):
        # check that inner_twists is consistent with inner_twist_count and that both are present if field_poly is set
        return (self.check_array_len_col('inner_twists', 'inner_twist_count', constraint={'inner_twist_count':{'$gt':0}}) or
                self.check_values({'inner_twists':{'$exists':True}, 'inner_twist_count':{'$gt':0}}, {'field_poly':{'$exists':True}}))

    @overall
    def check_has_non_self_twist(self):
        # TODO - is there a better way to do this?
        # check that has_non_self_twist is consistent with inner_twist_count and self_twist_type
        return (self.check_iff({'inner_twist_count':-1}, {'has_non_self_twist':-1}) or
                self.check_values({'inner_twist_count':1}, {'has_non_self_twist':0, 'self_twist_type':0}) or
                self.check_values({'inner_twist_count':2}, {'has_non_self_twist':0, 'self_twist_type':1}) or
                self.check_values({'inner_twist_count':2}, {'has_non_self_twist':0, 'self_twist_type':2}) or
                self.check_values({'inner_twist_count':4}, {'has_non_self_twist':0, 'self_twist_type':3}) or
                self.check_values({'inner_twist_count':{'$gt':1}}, {'has_non_self_twist':1, 'self_twist_type':0}) or
                self.check_values({'inner_twist_count':{'$gt':2}}, {'has_non_self_twist':1, 'self_twist_type':1}) or
                self.check_values({'inner_twist_count':{'$gt':2}}, {'has_non_self_twist':1, 'self_twist_type':2}) or
                self.check_values({'inner_twist_count':{'$gt':4}}, {'has_non_self_twist':1, 'self_twist_type':3}))

    @overall
    def check_portraits(self):
        # from mf_newform_portraits
        # check that there is a portrait present for every nonempty newspace in box where straces is set
        return self.check_crosstable_count('mf_newform_portraits', 1, 'label')



    @overall
    def check_field_disc_factorization(self):
        # if present, check that field_disc_factorization matches field_disc
        return self._run_query(SQL('field_disc != prod_factorization(field_disc_factorization)'), {'field_disc':{'$exists':True}});

    @overall
    def check_hecke_ring_index_factorization(self):
        # if present, verify that hecke_ring_index_factorization matches hecke_ring_index
        return self._run_query(SQL('hecke_ring_index != prod_factorization(hecke_ring_index_factorization)'), {'hecke_ring_index_factorization':{'$exists':True}});


    @overall
    def check_analytic_rank_set(self):
        return accumulate_failures(self.check_non_null(['analytic_rank'], self._box_query(box))
                for box in db.mf_boxes.search({'lfunctions':True}))


    @overall
    def check_analytic_rank(self):
        # if analytic_rank is present, check that matches order_of_vanishing in lfunctions record, and is are constant across the orbit
        db._execute(SQL("CREATE TEMP TABLE temp_mftbl AS SELECT label, string_to_array(label,'.'), analytic_rank, dim FROM mf_newforms WHERE analytic_rank is NOT NULL"))
        db._execute(SQL("CREATE TEMP TABLE temp_ltbl AS SELECT order_of_vanishing,(string_to_array(origin,'/'))[5:8],degree FROM lfunc_lfunctions WHERE origin LIKE 'ModularForm/GL2/Q/holomorphic%' and degree=2"))
        db._execute(SQL("CREATE INDEX temp_ltbl_string_to_array_index on temp_ltbl using HASH(string_to_array)"))
        db._execute(SQL("CREATE INDEX temp_mftbl_string_to_array_index on temp_mftbl using HASH(string_to_array)"))
        cur = db._execute(SQL("SELECT label FROM temp_mftbl t1 WHERE array_fill(t1.analytic_rank::smallint, ARRAY[t1.dim]) != ARRAY(SELECT t2.order_of_vanishing FROM temp_ltbl t2 WHERE t2.string_to_array = t1.string_to_array )  LIMIT %s"), [self._cur_limit])
        res = [rec[0] for rec in cur]
        db._execute(SQL("DROP TABLE tem_mftbl"))
        db._execute(SQL("DROP TABLE temp_ltbl"))
        return res

    @overall_long
    def check_self_dual_by_embeddings(self):
        # if is_self_dual is present but field_poly is not present, check that embedding data in mf_hecke_cc is consistent with is_self_dual
        # I expect this to take about 3/4h
        # we a create a temp table as we can't use aggregates under WHERE
        db._execute(SQL("CREATE TEMP TABLE tmp_cc AS SELECT t1.hecke_orbit_code, every(0 = all(t1.an_normalized[:][2:2] )) self_dual FROM mf_hecke_cc t1, mf_newforms t2 WHERE t1.hecke_orbit_code=t2.hecke_orbit_code AND t2.is_self_dual AND t2.field_poly is NULL GROUP BY t1.hecke_orbit_code"))
        query = SQL("SELECT t1.label FROM mf_newforms t1, tmp_cc t2 WHERE NOT t2.self_dual AND t1.hecke_orbit_code = t2.hecke_orbit_code LIMIT %s")
        # alternative query, but most likely equally slow
        #query = SQL("WITH foo AS (SELECT t1.label, t1.hecke_orbit_code FROM mf_newforms t1 WHERE t1.field_poly is NULL AND t1.is_self_dual) SELECT foo.label FROM foo, mf_hecke_cc t2 WHERE 0 != all( t2.an_normalized[:][2:2] ) LIMIT %s")
        cur = db._execute(query, [self._cur_limit])
        return [rec[0] for rec in cur]

    @overall
    def check_self_dual_lfunctions(self):
        # check that the lfunction self_dual attribute is consistent with newforms
        db._execute(SQL("CREATE TEMP TABLE temp_mftbl AS SELECT label, string_to_array(label,'.'), is_self_dual FROM mf_newforms"))
        db._execute(SQL("CREATE TEMP TABLE temp_ltbl AS SELECT (string_to_array(origin,'/'))[5:8], every(self_dual) self_dual FROM lfunc_lfunctions WHERE origin LIKE 'ModularForm/GL2/Q/holomorphic%' and degree=2 GROUP BY (string_to_array(origin,'/'))[5:8]"))
        db._execute(SQL("CREATE INDEX temp_ltbl_string_to_array_index on temp_ltbl using HASH(string_to_array)"))
        db._execute(SQL("CREATE INDEX temp_mftbl_string_to_array_index on temp_mftbl using HASH(string_to_array)"))
        cur = db._execute(SQL("SELECT t1.label FROM temp_mftbl t1, temp_ltbl t2 WHERE t1.is_self_dual != t2.self_dual AND t2.string_to_array = t1.string_to_array LIMIT %s"), [self._cur_limit])
        res = [rec[0] for rec in cur]
        db._execute(SQL("DROP TABLE temp_mftbl"))
        db._execute(SQL("DROP TABLE temp_ltbl"))
        return res

    @fast(projection=['projective_field', 'projective_image', 'projective_image_type'])
    def check_projective_field_degree(self, rec):
        # if present, check that projective_field has degree matching projective_image (4 for A4,S4, 5 for A5, 2n for Dn)
        coeffs = rec.get('projective_field')
        if coeffs is None: return True
        deg = Integer(rec['projective_image'][1:])
        if rec['projective_image_type'] == 'Dn':
            deg *= 2
        return deg == len(coeffs) - 1


    #### slow ####

    @slow(projection=['self_twist_discs', 'inner_twists'])
    def check_self_twist_disc(self, rec):
        # check that self_twist_discs = [elt[6] for elt in inner_twists if elt[6] is not None]
        return set(rec['self_twist_discs']) == set([elt[6] for elt in rec['inner_twists'] if elt[6] is not None])


    @slow(projection=['level', 'self_twist_discs', 'traces'])
    def check_inert_primes(self, rec):
        # for each discriminant D in self_twist_discs, check that for each prime p not dividing the level for which (D/p) = -1, check that traces[p] = 0 (we could also check values in mf_hecke_nf and/or mf_hecke_cc, but this would be far more costly)
        N = rec['level']
        traces = [0] + rec['traces'] # shift so indexing correct
        primes = [p for p in prime_range(len(traces)) if N % p != 0]
        for D in rec['self_twist_discs']:
            for p in primes:
                if kronecker_symbol(D, p) == -1 and traces[p] != 0:
                    return False
        return True

    ZZx = PolynomialRing(ZZ, 'x')

    @slow(constraint={'field_poly':{'$exists':True}}, projection=['field_poly', 'field_poly_is_cyclotomic'])
    def check_field_poly_properties(self, rec):
        # if present, check that field_poly is irreducible
        if 'field_poly' not in rec:
            return True
        else:
            f = self.ZZx(rec['field_poly'])
            if not f.is_irreducible():
                return False
            # if field_poly_is_cyclotomic, verify this
            if rec['field_poly_is_cyclotomic']:
                if not f.is_cyclotomic():
                    return False
            return True

    @slow(projection=['level', 'weight', 'char_orbit_index', 'dim', 'related_objects'])
    def check_related_objects(self, rec):
        # check that URLS in related_objects are valid and identify objects present in the LMFDB
        names = names_and_urls(rec['related_objects'])
        if len(names) != len(rec['related_objects']):
            return False
        # if related_objects contains an Artin rep, check that k=1 and that conductor of artin rep matches level N
        for name, url in names:
            if name.startswith('Artin representation '):
                if rec['weight'] != 1:
                    return False
                artin_label = name.split()[-1]
                conductor_string = artin_label.split('.')[1]
                conductor = [a**b for a, b in [map(int, elt.split('e')) for elt in conductor_string.split('_')]]
                if conductor != rec['level']:
                    return False

        # if k=2, char_orbit_index=1 and dim=1 check that elliptic curve isogeny class of conductor N is present in related_objects
            if url.startswith('/EllipticCurve/Q/'):
                if rec['weight'] != 2:
                    return False
                if rec['level'] != int(name.split()[-1].split('.')[0]):
                    return False
        if (rec['weight'] == 2 and rec['char_orbit_index'] == 1 and rec['dim'] == 1 and
            not any(url.startswith('/EllipticCurve/Q/') for name, url in names)):
            return False
        return True

    #### extra slow ####

    @slow(constraint={'nf_label':None, 'field_poly':{'$exists':True}}, projection=['field_poly', 'is_self_dual'])
    def check_self_dual_by_poly(self, rec):
        # if nf_label is not present and field_poly is present, check whether is_self_dual is correct (if feasible)
        f = ZZx(rec['field_poly'])
        K = NumberField(f, 'a')
        return (rec.get('is_self_dual') == K.is_totally_real())

    #@slow(constraint={'is_self_dual':{'$exists':True}, 'field_poly':None}, projection=['hecke_orbit_code', 'is_self_dual'])
    #def check_self_dual_by_embeddings_old(self, rec):
    #    # FIXME see check_self_dual_by_embeddings and  check_self_dual_lfunctions
    #    # TODO - is there a way to write this without 73993 mf_hecke_cc/lfunc_lfunction searches
    #    # if is_self_dual is present but field_poly is not present, check that embedding data in mf_hecke_cc is consistent with is_self_dual and/or check that the lfunction self_dual attribute is consistent
    #    embeddings = mf_hecke_cc.search({'hecke_orbit_code':rec['hecke_orbit_code']}, ['embedding_root_imag', 'an_normalized'])
    #    for emb in embeddings:
    #        imag = emb.get('embedding_root_imag')
    #        if rec['is_self_dual']:
    #            if imag is not None and imag != 0:
    #                return False
    #            if not all(y == 0 for x,y in emb['an_normalized']):
    #                return False
    #        elif imag is not None:
    #            if imag != 0:
    #                return True
    #        else:
    #            if any(y != 0 for x,y in emb['an_normalized']):
    #                return True
    #    return rec['is_self_dual']

    @slow(constraint={'artin_image':{'$exists':True}}, projection=['projective_image', 'artin_image', 'artin_degree'])
    def check_artin_image(self, rec):
        # if present, check that artin_image is consistent with artin_degree and projective_image (quotient of artin_image by its center should give projective_image)
        aimage = rec['artin_image']
        pimage = rec.get('projective_image')
        if pimage is None:
            return False
        aid = map(ZZ, aimage.split('.'))
        if aid[0] != rec['artin_degree']:
            return False
        if pimage == 'A4':
            pid = [12,3]
        elif pimage == 'S4':
            pid = [24,12]
        elif pimage == 'A5':
            pid = [60,5]
        else:
            pid = gap.DihedralGroup(2*ZZ(pimage[1:])).IdGroup().sage()
        qid = gap.SmallGroup(*aid).CommutatorFactorGroup().IdGroup().sage()
        return pid == qid

    #### char_dir_orbits ####

    @slow(disabled = True)
    def check_(self, rec):
        # TODO - use zipped table
        # check that each level M in inner twists divides the level and that M.o identifies a character orbit in char_dir_orbits with the listed parity
        return True

    #### mf_hecke_traces ####

    @overall
    def check_traces_count(self):
        # there should be exactly 1000 records in mf_hecke_traces for each record in mf_newforms
        return self.check_crosstable_count('mf_hecke_traces', 1000, 'hecke_orbit_code')

    @overall
    def check_traces_match(self):
        # check that traces[n] matches trace_an in mf_hecke_traces
        return self.check_crosstable_aggregate('mf_hecke_traces', 'traces', 'hecke_orbit_code', 'trace_an', sort=['n'], truncate=1000)

    #### mf_hecke_lpolys ####

    @overall
    def check_lpoly_count(self):
        # there should be exactly 25 records in mf_hecke_lpolys for each record in mf_newforms with field_poly
        return self.check_crosstable_count('mf_hecke_lpolys', 25, 'hecke_orbit_code', constraint={'field_poly':{'$exists':True}})


    #### mf_hecke_cc ####

    @overall
    def check_embeddings_count(self):
        # check that for such box with embeddings set, the number of rows in mf_hecke_cc per hecke_orbit_code matches dim
        return accumulate_failures(self.check_crosstable_count('mf_hecke_cc', 'dim', 'hecke_orbit_code', constraint=self._box_query(box)) for box in db.mf_boxes.search({'embeddings':True}))

    @overall
    def check_embeddings_count_boxcheck(self):
        # check that for such box with embeddings set, that summing over `dim` matches embeddings_count
        return all(sum(self.table.search(self._box_query(box), 'dim')) == box['embedding_count'] for box in db.mf_boxes.search({'embeddings':True}))

    @overall
    def check_roots(self):
        # check that embedding_root_real, and embedding_root_image present in mf_hecke_cc whenever field_poly is present
        # I didn't manage to write a generic one for this one
        join = self._make_join('hecke_orbit_code', None)
        query = SQL("SELECT t1.{0} FROM {1} t1, {2} t2 WHERE {3} AND t2.{4} is NULL AND t2.{5} is NULL AND t1.{6} is not NULL LIMIT %s").format(
                Identifier(self.table._label_col),
                Identifier(self.table.search_table),
                Identifier('mf_hecke_cc'),
                join,
                Identifier("embedding_root_real"),
                Identifier("embedding_root_imag"),
                Identifier("field_poly")
                )
        cur = db._execute(query, [self._cur_limit])
        return [rec[0] for rec in cur]

    @slow(constraint={'field_poly':{'$exists':True}}, projection=['field_poly', 'hecke_orbit_code'])
    def check_roots_are_roots(self, rec):
        # check that  embedding_root_real, and embedding_root_image  approximate a root of field_poly
        poly = PolynomialRing(CC, "x")(rec['field_poly'])
        for root in db.mf_hecke_cc.search({'hecke_orbit_code': rec['hecke_orbit_code']}, ["embedding_root_real", "embedding_root_imag"]):
            r = CC(*[root[elt] for elt in ["embedding_root_real", "embedding_root_imag"]])
            if poly.evaluate(r) > 1e-13:
                return False
        return True

    @slow(disabled=True)
    def check_an_embedding(self, rec):
        # TODO - zipped table
        # When we have exact an, check that the inexact values are correct
        pass

    @overall_long
    def check_traces(self):
        # check that summing (unnormalized) an over embeddings with a given hecke_orbit_code gives an approximation to tr(a_n) -- we probably only want to do this for specified newforms/newspaces, otherwise this will take a very long time.
        howmany = 200
        query = SQL("WITH foo AS (  SELECT hecke_orbit_code, traces(array_agg(an_normalized[1:%s])) traces FROM mf_hecke_cc GROUP BY hecke_orbit_code) SELECT t1.label FROM mf_newforms t1, foo WHERE t1.hecke_orbit_code = foo.hecke_orbit_code AND NOT compare_traces(t1.traces[1:%s], foo.traces, -0.5*(t1.weight - 1)) LIMIT %s")
        cur = db._execute(query, [howmany, howmany, self._cur_limit])
        return [rec[0] for rec in cur]

class mf_newform_portraits(TableChecker):
    table = db.mf_newform_portraits
    label = ['level', 'weight', 'char_orbit_index', 'hecke_orbit']
    label_conversion = {'char_orbit_index':-1, 'hecke_orbit':-1}
    uniqueness_constraints = [[table._label_col], label]

    # attached to mf_newforms
    # check that there is exactly one record in mf_newform_portraits for each record in mf_newforms, uniquely identified by label

class mf_hecke_nf(TableChecker):
    table = db.mf_hecke_nf

    @overall
    def check_bijection(self):
        # there should be a record present for every record in mf_newforms that has field_poly set (and no others, check count)
        return (self.check_crosstable_count('mf_newforms', 1, 'label') or
                self.check_count(db.mf_newforms.count({'field_poly':{'$exists':True}})))

    @overall
    def check_hecke_orbit_code_newforms(self):
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
        return self.check_values({'hecke_ring_cyclotomic_generator':0,
                                  'hecke_ring_numerators':None,
                                  'hecke_ring_denominators':None,
                                  'hecke_ring_inverse_numerators':None,
                                  'hecke_ring_inverse_denominators':None},
                                 {'hecke_ring_power_basis':True})

    @overall
    def check_hecke_ring_cyclotomic_generator(self):
        # if hecke_ring_cyclotomic_generator is greater than 0 check that hecke_ring_power_basis is false and hecke_ring_numerators, ... are null, and that field_poly_is_cyclotomic is set in mf_newforms record.
        return (self.check_values({'hecke_ring_power_basis':False,
                                   'hecke_ring_numerators':None,
                                   'hecke_ring_denominators':None,
                                   'hecke_ring_inverse_numerators':None,
                                   'hecke_ring_inverse_denominators':None},
                                  {'hecke_ring_cyclotomic_generator':{'$gt':0}}) or
                None)

    @overall
    def check_field_poly_is_cyclotomic(self):
        # if hecke_ring_cyclotomic_generator > 0, check that field_poly_is_cyclotomic is set in mf_newforms record.
        # could be done with _run_crosstable from mf_newforms
        cur = db._execute(SQL("SELECT t1.label FROM mf_hecke_nf t1, mf_newforms t2 WHERE NOT t2.field_poly_is_cyclotomic AND t1.hecke_ring_cyclotomic_generator > 0 AND t1.label = t2.label LIMIT %s"), [self._cur_limit])
        return [rec[0] for rec in cur]

    @overall
    def check_maxp(self):
        # check that maxp is at least 997
        return self._run_query(SQL('maxp < 997'))

    @slow(projection=['label', 'an', 'ap', 'maxp', 'hecke_ring_cyclotomic_generator', 'hecke_ring_rank', 'hecke_ring_character_values'])
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

class TracesChecker(TableChecker):
    uniqueness_constraints = [['hecke_orbit_code', 'n']]
    label_col = 'hecke_orbit_code'

    @overall
    def check_total_count(self):
        # check that hecke_orbit_code is present in mf_newforms
        return self.check_count(1000 * self.base_table.count(self.base_constraint))

class mf_hecke_traces(TracesChecker):
    table = db.mf_hecke_traces
    base_table = db.mf_newforms
    base_constraint = {}

    @overall
    def check_hecke_orbit_code_newforms(self):
        # check that hecke_orbit_code is present in mf_newforms
        return self.check_crosstable_count('mf_newforms', 1, 'hecke_orbit_code')

class mf_hecke_newspace_traces(TracesChecker):
    table = db.mf_hecke_newspace_traces
    base_table = db.mf_newspaces
    base_constraint = {'traces':{'$exists':True}}

class mf_hecke_lpolys(TableChecker):
    table = db.mf_hecke_lpolys
    label_col = 'hecke_orbit_code'
    uniqueness_constraints = [['hecke_orbit_code', 'p']]

    @overall
    def check_total_count(self):
        # check that hecke_orbit_code is present in mf_newforms
        return self.check_count(25 * db.mf_newforms.count({'field_poly':{'$exists':True}}))

    @overall
    def check_prime_count(self):
        # check that every prime p < 100 occurs exactly once for each hecke_orbit_code
        cnt = db.mf_newforms.count({'field_poly':{'$exists':True}})
        return accumulate_failures(self.check_count(cnt, {'p': p}) for p in prime_range(100))

    @overall
    def check_hecke_orbit_code_newforms(self):
        # check that hecke_orbit_code is present in mf_newforms
        return self.check_crosstable_count('mf_newforms', 1, 'hecke_orbit_code')

    @overall
    def check_lpoly(self):
        # check that degree of lpoly is twice the dimension in mf_newforms for good primes
        # check that linear coefficient of lpoly is -trace(a_p) and constant coefficient is 1
        query = SQL("SELECT t1.label FROM (mf_newforms t1 INNER JOIN mf_hecke_lpolys t2 ON t1.hecke_orbit_code = t2.hecke_orbit_code) INNER JOIN mf_hecke_traces t3 ON t1.hecke_orbit_code = t3.hecke_orbit_code AND t2.p = t3.n WHERE ((MOD(t1.level, t2.p) != 0 AND array_length(t2.lpoly, 1) != 2*t1.dim+1) OR t2.lpoly[1] != 1 OR t2.lpoly[2] != -t3.trace_an) LIMIT %s")
        cur = db._execute(query, [self._cur_limit])
        return [rec[0] for rec in cur]

class mf_hecke_cc(TableChecker):
    table = db.mf_hecke_cc
    label_col = 'lfunction_label'
    uniqueness_constraints = [['lfunction_label']]

    @overall
    def check_hecke_orbit_code_newforms(self):
        # check that hecke_orbit_code is present in mf_newforms
        return self.check_crosstable_count('mf_newforms', 1, 'hecke_orbit_code')

    @overall
    def check_dim(self):
        # check that we have dim embeddings per hecke_orbit_code
        query = SQL("WITH foo AS (  SELECT hecke_orbit_code, COUNT(*) FROM mf_hecke_cc GROUP BY hecke_orbit_code) SELECT t1.label FROM mf_newforms t1, foo WHERE t1.hecke_orbit_code = foo.hecke_orbit_code AND NOT t1.dim = foo.count LIMIT %s")
        cur = db._execute(query, [self._cur_limit])
        return [rec[0] for rec in cur]

    @overall
    def check_lfunction_label(self):
        # check that lfunction_label is consistent with hecke_orbit_code, conrey_label, and embedding_index
        query = SQL("SELECT t1.lfunction_label FROM mf_hecke_cc t1, mf_newforms t2 WHERE string_to_array(t1.lfunction_label,'.') != string_to_array(t2.label, '.') || ARRAY[t1.conrey_index::text, t1.embedding_index::text] AND t1.hecke_orbit_code = t2.hecke_orbit_code LIMIT %s")
        cur = db._execute(query, [self._cur_limit])
        return [rec[0] for rec in cur]

    @overall
    def check_embedding_index(self):
        # check that embedding_index is consistent with conrey_label and embedding_m
        query = SQL("WITH foo AS ( SELECT lfunction_label, embedding_index, ROW_NUMBER() OVER ( PARTITION BY hecke_orbit_code, conrey_index  ORDER BY embedding_m) FROM mf_hecke_cc) SELECT lfunction_label FROM foo WHERE embedding_index != row_number LIMIT %s")
        cur = db._execute(query, [self._cur_limit])
        return [rec[0] for rec in cur]

    @overall
    def check_embedding_m(self):
        # check that embedding_m is consistent with conrey_label and embedding_index
        query = SQL("WITH foo AS ( SELECT lfunction_label, embedding_m, ROW_NUMBER() OVER ( PARTITION BY hecke_orbit_code ORDER BY conrey_index, embedding_index) FROM mf_hecke_cc) SELECT lfunction_label FROM foo WHERE embedding_m != row_number LIMIT %s")
        cur = db._execute(query, [self._cur_limit])
        return [rec[0] for rec in cur]

    @overall
    def check_conrey_indexes(self):
        # when grouped by hecke_orbit_code, check that conrey_indexs match conrey_indexes,  embedding_index ranges from 1 to relative_dim (when grouped by conrey_index), and embedding_m ranges from 1 to dim
        # ps: In check_embedding_m and check_embedding_index, we already checked that embedding_m and  check_embedding_index are in an increasing sequence
        query = SQL("WITH foo as (SELECT hecke_orbit_code, sort(array_agg(DISTINCT conrey_index)) conrey_indexes, count(DISTINCT embedding_index) relative_dim, count(embedding_m) dim FROM mf_hecke_cc GROUP BY hecke_orbit_code) SELECT t1.label FROM mf_newforms t1, foo WHERE t1.hecke_orbit_code = foo.hecke_orbit_code AND (t1.conrey_indexes != foo.conrey_indexes OR t1.relative_dim != foo.relative_dim OR t1.dim != foo.dim) LIMIT %s")
        cur = db._execute(query, [self._cur_limit])
        return [rec[0] for rec in cur]

    @overall
    def check_an_length(self):
        # check that an_normalized is a list of pairs of doubles of length at least 1000
        return self._run_query(SQL("array_length({0}, 1) < 1000 OR array_length({0}, 2) != 2").format(
            Identifier("an_normalized")))



    @overall
    def check_lfunction_label_hoc(self):
        # check that lfunction_label is consistent with hecke_orbit_code
        return self._run_query(SQL("{0} != from_newform_label_to_hecke_orbit_code({1})").format(Identifier('hecke_orbit_code'), Identifier('lfunction_label')))

    @overall
    def check_lfunction_label_conrey(self):
        # check that lfunction_label is consistent with conrey_lebel, embedding_index
        return self._run_query(SQL("(string_to_array({0},'.'))[5:6] != array[{1}::text,{2}::text]").format(Identifier('lfunction_label'), Identifier('conrey_index'), Identifier('embedding_index')))

    @overall_long
    def check_amn(self):
        # Check a_{mn} = a_m*a_n when (m,n) = 1 and m,n < some bound
        pairs = [(2, 3), (2, 5), (3, 4), (2, 7), (3, 5), (2, 9), (4, 5), (3, 7), (2, 11), (3, 8), (2, 13), (4, 7), (2, 15), (3, 10), (5, 6), (3, 11), (2, 17), (5, 7), (4, 9), (2, 19), (3, 13), (5, 8), (3, 14), (6, 7), (4, 11), (5, 9), (3, 16), (3, 17), (4, 13), (5, 11), (7, 8), (3, 19), (3, 20), (4, 15), (5, 12)][:15]
        query = SQL(" AND ").join(SQL("check_cc_prod(an_normalized[{0}:{0}], an_normalized[{1}:{1}], an_normalized[{2}:{2}])").format(Literal(int(m)), Literal(int(n)), Literal(int(m*n))) for m, n in pairs)
        return self._run_query(query)

    @slow(projection=['lfunction_label', 'angles'])
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

    @slow(disabled=True)
    def check_ap2(self, rec):
        # TODO - zipped tables
        # Check a_{p^2} = a_p^2 - chi(p)*p^{k-1}a_p for primes up to 31
        pass






class char_dir_orbits(TableChecker):
    table = db.char_dir_orbits
    label_col = 'orbit_label'
    label = ['modulus', 'orbit_index']
    uniqueness_constraints = [[table._label_col], label]

    @overall
    def check_total_count(self):
        # there should be a record present for every character orbit of modulus up to 10,000 (there are 768,512)
        return self.check_count(768512)

    @overall
    def check_trivial(self):
        # check that orbit_index=1 if and only if order=1
        return self.check_iff({'orbit_index':1}, {'order':1})

    @overall
    def check_conductor_divides(self):
        # check that conductor divides modulus
        return self.check_divisible('modulus', 'conductor')

    @overall
    def check_primitive(self):
        # check that orbit specified by conductor,prim_orbit_index is present
        return self.check_crosstable_count('char_dir_orbits', 1, ['conductor', 'prim_orbit_index'], ['modulus', 'orbit_index'])

    @overall
    def check_is_real(self):
        # check that is_real is true if and only if order <= 2
        return self.check_iff({'is_real':True}, {'order':{'$lte':2}})

    @overall
    def check_galois_orbit_len(self):
        # check that char_degee = len(Galois_orbit)
        return self.check_array_len_col('galois_orbit', 'char_degree')

    @overall
    def check_char_dir_values_agg(self):
        # The number of entries in char_dir_values matching a given orbit_label should be char_degree
        return self.check_crosstable_count('char_dir_values', 'char_degree', 'orbit_label')

    @overall
    def check_is_primitive(self):
        # check that is_primitive is true if and only if modulus=conductor
        # Since we can't use constraint on modulus=conductor, we construct the constraint directly
        return self.check_iff({'is_primitive': True}, SQL("modulus = conductor"))

    @overall
    def check_galois_orbit(self):
        # galois_orbit should be the list of conrey_indexes from char_dir_values with this orbit_label Conrey index n in label should appear in galois_orbit for record in char_dir_orbits with this orbit_label
        return self.check_crosstable_aggregate('char_dir_values', SQL('t1.galois_orbit::smallint[]'), 'orbit_label', 'conrey_index')

    @overall
    def check_parity_value(self):
        # the value on -1 should agree with the parity for this char_orbit_index in char_dir_orbits
        return (self._run_crosstable(SQL("2*t2.values[1][2]"), 'char_dir_values', 'order', 'orbit_label', constraint={'parity':-1}, subselect_wrapper="ALL") or
                self._run_crosstable(SQL("t2.values[1][2]"), 'char_dir_values', 0, 'orbit_label', constraint={'parity':1}, subselect_wrapper="ALL"))

    @fast(projection=['char_degree', 'order'])
    def check_char_degree(self, rec):
        # check that char_degree = euler_phi(order)
        return rec['char_degree'] == euler_phi(rec['order'])

    @slow(projection=['modulus', 'conductor', 'order', 'parity', 'galois_orbit'])
    def check_order_parity(self, rec):
        # check order and parity by constructing a Conrey character in Sage (use the first index in galois_orbit)
        char = DirichletCharacter_conrey(rec['modulus'], rec['galois_orbit'][0])
        parity = 1 if char.is_even() else -1
        return parity == rec['parity'] and char.conductor() == rec['conductor'] and char.multiplicative_order() == rec['order']

class char_dir_values(TableChecker):
    table = db.char_dir_values
    label = ['modulus', 'conrey_index']
    uniqueness_constraints = [['label'], label]

    @overall
    def check_total_count(self):
        # Total number of records should be sum of len(galois_orbit) over records in char_dir_orbits,
        # Should be sum(euler_phi(n) for n in range(1,1001)) = 30397486
        return self.check_count(30397486)

    @overall
    def check_order_match(self):
        # order should match order in char_dir_orbits for this orbit_label
        return self.check_crosstable('char_dir_orbits', 'order', 'orbit_label')

    @slow(projection=['label', 'order', 'values', 'values_gens'])
    def check_character_values(self, rec):
        # The x's listed in values and values_gens should be coprime to the modulus N in the label
        # for x's that appear in both values and values_gens, the value should be the same.
        N, index = map(Integer, rec['label'].split('.'))
        v2, u2 = N.val_unit(2)
        if v2 == 1:
            # Z/2 doesn't contribute generators, but 2 divides N
            adjust2 = -1
        elif v2 >= 3:
            # Z/8 and above requires two generators
            adjust2 = 1
        else:
            adjust2 = 0
        ngens = len(N.factor()) + adjust2
        vals = rec['values']
        val_gens = rec['values_gens']
        val_gens_dict = dict(val_gens)
        if len(vals) != 12 or len(val_gens) != ngens:
            return False
        if vals[0][0] != N-1 or vals[1][0] != 1 or vals[1][1] != 0 or vals[0][1] not in [0, rec['order']//2]:
            return False
        if any(N.gcd(g) > 1 for g, gval in val_gens+vals):
            return False
        for g, val in vals:
            if g in val_gens_dict and val != val_gens_dict[g]:
                return False

validated_tables = [mf_newspaces, mf_gamma1, mf_newspace_portraits, mf_gamma1_portraits, mf_subspaces, mf_gamma1_subspaces, mf_newforms, mf_newform_portraits, mf_hecke_nf, mf_hecke_traces, mf_hecke_newspace_traces, mf_hecke_lpolys, mf_hecke_cc, char_dir_orbits, char_dir_values]
typs = [(overall, 'over'), (overall_long, 'long'), (fast, 'fast'), (slow, 'slow')]
def run_tests(basedir, m):
    cls_num = m // len(typs)
    if cls_num >= len(validated_tables) or cls_num < 0:
        print "No such table (requested %sth table of %s)"%(cls_num+1, len(validated_tables))
    else:
        typ_num = m % len(typs)
        cls = validated_tables[cls_num]
        typ, suffix = typs[typ_num]
        if cls._get_checks_count(typ) > 0:
            logfile = os.path.join(basedir, '%s.%s'%(cls.__name__, suffix))
            runner = cls(logfile, typ)
            runner.run()

if __name__ == '__main__':
    if len(sys.argv) != 3 or not os.path.isdir(sys.argv[1]) or not sys.argv[2].isdigit():
        print "Give an output directory and one integer argument, between 0 and %s.  See script for details on meaning." % (len(validated_tables) * len(typs) - 1)
    else:
        run_tests(sys.argv[1], int(sys.argv[2]))
