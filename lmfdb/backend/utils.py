#-*- coding: utf-8 -*-
from __future__ import print_function, absolute_import
import re

from psycopg2.sql import SQL, Identifier, Placeholder

from lmfdb.utils import SearchParsingError

##################################################################
# query language                                                 #
##################################################################

# These operators are used in the filter_sql_injection function
# If you make any additions or changes, ensure that it doesn't
# open the LMFDB up to SQL injection attacks.
postgres_infix_ops = {
    '$lte': '<=',
    '$lt': '<',
    '$gte': '>=',
    '$gt': '>',
    '$ne': '!=',
    '$like': 'LIKE',
    '$regex': '~'
}

# This function is used to support the inclusion of limited raw postgres in queries
def filter_sql_injection(clause, col, col_type, op, table):
    """
    INPUT:

    - ``clause`` -- a plain string, obtained from the website UI so NOT SAFE
    - ``col`` -- an SQL Identifier for a column in a table
    - ``col_type`` -- a string giving the type of the column
    - ``valid_cols`` -- the column names for this table
    - ``op`` -- a string giving the operator to use
      (`=` or one of the values in the ``postgres_infix_ops dictionary`` above)
    - ``table`` -- a PostgresTable object for determining which columns are valid
    """
    # Our approach:
    # * strip all whitespace: this makes some of the analysis below easier
    #   and is okay since we support implicit multiplication at a higher level
    # * Identify numbers (using a float regular expression) and call int or float on them as appropriate
    # * whitelist names of columns and wrap them all in identifiers;
    # * no other alphabetic characters allowed: this prevents the use
    #   of any SQL functions or commands
    # * The only other allowed characters are +-*^/().
    # * We also prohibit --, /* and */ since these are comments in SQL
    clause = re.sub(r'\s+', '', clause)
    # It's possible that some search columns include numbers (2adic_gens in ec_curves for example)
    # However, we don't support columns that are entirely numbers (such as some in smf_dims)
    # since there's no way to distinguish them from integers
    # We also want to include periods as part of the word/number character set, since they can appear in floats
    FLOAT_RE = r'^((\d+([.]\d*)?)|([.]\d+))([eE][-+]?\d+)?$'
    ARITH_RE = r'^[+*-/^()]+$'
    processed = []
    values = []
    pieces = re.split(r'([A-Za-z_.0-9]+)', clause)
    for i, piece in enumerate(pieces):
        if not piece: # skip empty strings at beginning/end
            continue
        if i % 2: # a word/number
            if piece in table.search_cols:
                processed.append(Identifier(piece))
            elif re.match(FLOAT_RE, piece):
                processed.append(Placeholder())
                if any(c in piece for c in 'Ee.'):
                    values.append(float(piece))
                else:
                    values.append(int(piece))
            else:
                raise SearchParsingError("%s: %s is not a column of %s" % (clause, piece, table.search_table))
        else:
            if re.match(ARITH_RE, piece) and not any(comment in piece for comment in ["--", "/*", "*/"]):
                processed.append(SQL(piece))
            else:
                raise SearchParsingError("%s: invalid characters %s (only +*-/^() allowed)" % (clause, piece))
    return SQL("{0} %s {1}" % op).format(col, SQL("").join(processed)), values



def IdentifierWrapper(name, convert = True):
    """
    Returns a composable representing an SQL identifer.

    This is  wrapper for psycopg2.sql.Identifier that supports ARRAY slicers
    and coverts them (if desired) from the Python format to SQL,
    as SQL starts at 1, and it is inclusive at the end

    EXAMPLES::

        sage: IdentifierWrapper('name')
        Identifier('name')
        sage: print(IdentifierWrapper('name[:10]').as_string(db.conn))
        "name"[:10]
        sage: print(IdentifierWrapper('name[1:10]').as_string(db.conn))
        "name"[2:10]
        sage: print(IdentifierWrapper('name[1:10]', convert = False).as_string(db.conn))
        "name"[1:10]
        sage: print(IdentifierWrapper('name[1:10:3]').as_string(db.conn))
        "name"[2:10:3]
        sage: print(IdentifierWrapper('name[1:10:3][0:2]').as_string(db.conn))
        "name"[2:10:3][1:2]
        sage: print(IdentifierWrapper('name[1:10:3][0::1]').as_string(db.conn))
        "name"[2:10:3][1::1]
        sage: print(IdentifierWrapper('name[1:10:3][0]').as_string(db.conn))
        "name"[2:10:3][1]
    """
    if '[' not in name:
        return Identifier(name)
    else:
        i = name.index('[')
        knife = name[i:]
        name = name[:i]
        # convert python slicer to postgres slicer
        # SQL starts at 1, and it is inclusive at the end
        # so we just need to convert a:b:c -> a+1:b:c

        # first we remove spaces
        knife = knife.replace(' ','')


        # assert that the knife is of the shape [*]
        if knife[0] != '[' or knife[-1] != ']':
            raise ValueError("%s is not in the proper format" % knife)
        chunks = knife[1:-1].split('][')
        # Prevent SQL injection
        if not all(all(x.isdigit() for x in chunk.split(':')) for chunk in chunks):
            raise ValueError("% is must be numeric, brackets and colons"%knife)
        if convert:
            for i, s in enumerate(chunks):
                # each cut is of the format a:b:c
                # where a, b, c are either integers or empty strings
                split = s.split(':',1)
                # nothing to adjust
                if split[0] == '':
                    continue
                else:
                    # we should increment it by 1
                    split[0] = str(int(split[0]) + 1)
                chunks[i] = ':'.join(split)
            sql_slicer = '[' + ']['.join(chunks) + ']'
        else:
            sql_slicer = knife

        return SQL('{0}{1}').format(Identifier(name), SQL(sql_slicer))

class LockError(RuntimeError):
    pass

class QueryLogFilter(object):
    """
    A filter used when logging slow queries.
    """
    def filter(self, record):
        if record.pathname.startswith('db_backend.py'):
            return 1
        else:
            return 0

class EmptyContext(object):
    """
    Used to simplify code in cases where we may or may not want to open an extras file.
    """
    name = None
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_value, traceback):
        pass

class DelayCommit(object):
    """
    Used to set default behavior for whether to commit changes to the database connection.

    Entering this context in a with statement will cause `_execute` calls to not commit by
    default.  When the final DelayCommit is exited, the connection will commit.
    """
    def __init__(self, obj, final_commit=True, silence=None):
        self.obj = obj._db
        self.final_commit = final_commit
        self._orig_silenced = obj._db._silenced
        if silence is not None:
            obj._silenced = silence
    def __enter__(self):
        self.obj._nocommit_stack += 1
    def __exit__(self, exc_type, exc_value, traceback):
        self.obj._nocommit_stack -= 1
        self.obj._silenced = self._orig_silenced
        if exc_type is None and self.obj._nocommit_stack == 0 and self.final_commit:
            self.obj.conn.commit()
        if exc_type is not None:
            self.obj.conn.rollback()
