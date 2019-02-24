# -*- coding: utf-8 -*-

import traceback, time, os, inspect
from types import MethodType
from datetime import datetime

from timeout_decorator import timeout, TimeoutError
from sage.all import Integer

from lmfdb.backend.database import db, SQL, Composable, IdentifierWrapper as Identifier, Literal

integer_types = (int, long, Integer)
def accumulate_failures(L):
    """
    Accumulates a list of bad labels
    """
    ans = []
    for a in L:
        if a:
            if not isinstance(a, list):
                a = [a]
            ans.extend(a)
    return ans

def pluralize(n, noun):
    if n == 1:
        return "1 %s"%(noun)
    else:
        return "%d %ss"%(n, noun)

class TooManyFailures(AssertionError):
    pass

class speed_decorator(object):
    """
    Transparently wraps a function, so that functions can be classified by "isinstance".  Allow keyword arguments
    """
    disabled = False # set to True to skip this check
    max_failures = 1 # maximum number of failures to show
    ratio = 1 # ratio of rows to run this test on
    def __init__(self, f=None, **kwds):
        self._kwds = kwds
        if f is not None:
            self.__name__ = f.__name__
            for key, val in kwds.items():
                setattr(self, key, val)
            if self.timeout is None:
                self.f = f
            else:
                self.f = timeout(self.timeout)(f)
        else:
            self.f = None
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
    report_slow = 0.1
    max_slow = 100

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
    ratio = 0.1 # slow tests are by default run on 10% of rows
    timeout = 3600

class fast(per_row):
    """
    A per-row check that is fast to run
    """
    timeout = 300

class overall(one_query):
    """
    An overall check that is fast to run
    """
    timeout = 300

class overall_long(one_query):
    """
    An overall check that is slow to run
    """
    timeout = 3600

class TableChecker(object):
    label_col = 'label' # default
    def __init__(self, logfile=None, default_typ=None):
        if logfile is None:
            logfile = "%s.%s" % (self.__class__.__name__, default_typ.__name__)
        self.logfile = logfile + '.log'
        self.errfile = logfile + '.errors'
        self.progfile = logfile + '.progress'
        self.startfile = logfile + '.started'
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
        timeouts = 0
        with open(self.startfile, 'w') as startfile:
            startfile.write("%s.%s started (pid %s)\n"%(self.__class__.__name__, typ.__name__, os.getpid()))
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
                    if issubclass(typ, per_row):
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
                        except Exception as err:

                            template = "An exception in {0} of type {1} occurred. Arguments:\n{2}"
                            message = template.format(name, type(err).__name__, '\n'.join(err.args))
                            self._report_error(message)
                            errors += 1
                            continue
                    try:
                        if issubclass(typ, per_row):
                            check_failures = 0
                            check_slow = 0
                            for rec_no, rec in enumerate(search_iter, 1):
                                if rec_no % progress_interval == 0:
                                    prog.write('%d/%d in %.2fs\n'%(rec_no, total, time.time() - check_start))
                                    prog.flush()
                                row_start = time.time()
                                check_success = check(rec)
                                row_time = time.time() - row_start
                                if not check_success:
                                    log.write('%s: %s\n'%(name, rec[self.label_col]))
                                    check_failures += 1
                                    if check_failures >= check.max_failures:
                                        raise TooManyFailures
                                if row_time >= check.report_slow:
                                    log.write('%s: %s (%d/%d) ok but took %.2fs\n'%(name, rec[self.label_col], rec_no, total, row_time))
                                    check_slow += 1
                                    if check_slow >= check.max_slow:
                                        raise TimeoutError
                                if time.time() - check_start >= check.timeout:
                                    raise TimeoutError
                        else:
                            # self._cur_limit controls the max number of failures returned
                            self._cur_limit = check.max_failures
                            bad_labels = check()
                            if bad_labels:
                                for label in bad_labels:
                                    log.write('%s: %s\n'%(name, label))
                                failures += len(bad_labels)
                    except TimeoutError:
                        timeouts += 1
                        msg = '%s timed out after %.2fs\n'%(name, time.time() - check_start)
                        prog.write(msg)
                        log.write(msg)
                    except TooManyFailures:
                        aborts += 1
                        msg = '%s aborted after %.2fs (too many failures)\n'%(name, time.time() - check_start)
                        prog.write(msg)
                        log.write(msg)
                    except Exception:
                        if issubclass(typ, per_row):
                            msg = 'Exception in %s (%s):\n'%(name, rec.get(self.label_col, ''))
                        else:
                            msg = 'Exception in %s\n'%(name)
                        errors += self._report_error(msg, log, prog)
                    else:
                        prog.write('%s finished after %.2fs\n'%(name, time.time() - check_start))
                    finally:
                        if issubclass(typ, per_row):
                            failures += check_failures
                        log.flush()
                        prog.flush()
        with open(self.donefile, 'a') as done:
            reports = []
            if failures:
                reports.append(pluralize(failures, "failure"))
            if aborts:
                reports.append(pluralize(aborts, "abort"))
            if timeouts:
                reports.append(pluralize(timeouts, "timeout"))
            if disabled:
                reports.append("%s disabled"%disabled)
            if errors:
                reports.append(pluralize(errors, "error"))
            status = "FAILED with " + ", ".join(reports) if reports else "PASSED"
            done.write("%s.%s %s in %.2fs\n"%(self.__class__.__name__, typ.__name__, status, time.time() - start))
            os.remove(self.startfile)

    #####################
    # Utility functions #
    #####################
    def _make_sql(self, s, tablename=None):
        """
        Create an SQL Composable object out of s.

        INPUT:

        - ``s`` -- a string, integer or Composable object
        - ``tablename`` -- a tablename prepended to the resulting object if ``s`` is a string
        """
        if isinstance(s, integer_types):
            return Literal(s)
        elif isinstance(s, Composable):
            return s
        elif tablename is None:
            return Identifier(s)
        else:
            return SQL(tablename + ".") + Identifier(s)

    def _make_join(self, join1, join2):
        if not isinstance(join1, list):
            join1 = [join1]
        if join2 is None:
            join2 = join1
        elif not isinstance(join2, list):
            join2 = [join2]
        if len(join1) != len(join2):
            raise ValueError("join1 and join2 must have the same length")
        join1 = [self._make_sql(j, "t1") for j in join1]
        join2 = [self._make_sql(j, "t2") for j in join2]
        return SQL(" AND ").join(SQL("{0} = {1}").format(j1, j2) for j1, j2 in zip(join1, join2))

    def _run_query(self, condition, constraint={}, values=[], table=None, ratio=1):
        """
        INPUT:

        - ``condition`` -- an SQL object giving a condition on the search table
        - ``constraint`` -- a dictionary, as passed to the search method, or an SQL object
        """
        if table is None:
            table = self.table.search_table
        if isinstance(table, basestring):
            if ratio == 1:
                table = Identifier(table)
            else:
                table = SQL("{0} TABLESAMPLE SYSTEM({1})").format(Identifier(table), Literal(ratio))
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
        col = self._make_sql(col, "t1")
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
        if real_cnt == cnt:
            return []
        else:
            return ['%s != %s (%s)' % (real_cnt, cnt, constraint)]

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
        numerator = self._make_sql(numerator)
        denominator = self._make_sql(denominator)
        return self._run_query(SQL("MOD({0}, {1}) != 0").format(
            numerator, denominator), constraint=constraint)

    def check_non_divisible(self, numerator, denominator, constraint={}):
        numerator = self._make_sql(numerator)
        denominator = self._make_sql(denominator)
        return self._run_query(SQL("MOD({0}, {1}) = 0").format(
            numerator, denominator), constraint=constraint)

    def check_values(self, values, constraint={}):
        if isinstance(values, Composable):
            vstr = values
            vvalues = []
        else:
            vstr, vvalues = self.table._parse_dict(values)
        if vstr is None:
            # Nothing to check
            return []
        else:
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
        return (self.check_values(condition1, condition2) +
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
        return self._run_query(SQL("NOT ({0} LIKE %s)").format(Identifier(col)), constraint=constraint, values = [value])

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
        return [constraint for constraint in self.uniqueness_constraints if tuple(sorted(constraint)) not in constraints]
