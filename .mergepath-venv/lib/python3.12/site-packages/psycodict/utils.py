# -*- coding: utf-8 -*-
"""
Helpers shared across psycodict: :class:`DelayCommit` for batching many
writes into one transaction, the whitelist parser that admits limited raw
arithmetic into queries (:func:`filter_sql_injection`), identifier wrapping
with array slicers (:func:`IdentifierWrapper`), the exceptions raised during
query parsing and locking, and small formatting utilities.
"""
import os.path
import sys
import re
from collections import defaultdict

from psycopg.sql import SQL, Identifier, Placeholder


class SearchParsingError(ValueError):
    """
    Used for errors raised when parsing search boxes
    """
    def __init__(self, *args, **kwargs):
        trim_msg_error = kwargs.pop("trim_msg_error", False)
        self.trim_msg_error = trim_msg_error
        super().__init__(*args, **kwargs)


##################################################################
# query language                                                 #
##################################################################

# These operators are used in the filter_sql_injection function
# If you make any additions or changes, ensure that it doesn't
# open the LMFDB up to SQL injection attacks.
postgres_infix_ops = {
    "$lte": "<=",
    "$lt": "<",
    "$gte": ">=",
    "$gt": ">",
    "$ne": "!=",
    "$like": "LIKE",
    "$ilike": "ILIKE",
    "$regex": "~",
}

# This function is used to support the inclusion of limited raw postgres in queries
def filter_sql_injection(clause, col, col_type, op, table, join_context=None):
    """
    Build a comparison clause from an untrusted arithmetic expression,
    admitting only whitelisted column names, numbers and the arithmetic
    operators ``+-*/^()``.  Returns a pair of an SQL composable and the list
    of values to substitute into it.

    INPUT:

    - ``clause`` -- a plain string, obtained from the website UI so NOT SAFE
    - ``col`` -- an SQL Identifier for a column in a table
    - ``col_type`` -- a string giving the type of the column
    - ``op`` -- a string giving the operator to use
      (``=`` or one of the values in the ``postgres_infix_ops`` dictionary above)
    - ``table`` -- a PostgresTable object for determining which columns are valid
    - ``join_context`` -- when filtering an expression inside a joined query,
      a dictionary mapping joined table names to their table objects.  Names
      then resolve like query keys -- bare names are columns of ``table``,
      while "joinedtable.column" names a joined table's column -- and every
      identifier is emitted table-qualified.
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
    clause = re.sub(r"\s+", "", clause)
    # It's possible that some search columns include numbers (dim1_factor in av_fq_isog for example)
    # However, we don't support columns that are entirely numbers (such as some in smf_dims)
    # since there's no way to distinguish them from integers
    # We also want to include periods as part of the word/number character set, since they can appear in floats
    FLOAT_RE = r"^((\d+([.]\d*)?)|([.]\d+))([eE][-+]?\d+)?$"
    # The hyphen must come first: written as [+*-/^()] the "*-/" is a
    # character range covering * + , - . / , which let commas and periods
    # through a whitelist that is applied to untrusted input from the UI.
    ARITH_RE = r"^[-+*/^()]+$"
    processed = []
    values = []
    pieces = re.split(r"([A-Za-z_.0-9]+)", clause)
    for i, piece in enumerate(pieces):
        if not piece:  # skip empty strings at beginning/end
            continue
        if i % 2:  # a word/number
            resolved = None
            if join_context is not None and "." in piece:
                # A joined-table prefix names that table's column; the piece
                # arrives whole because the word class includes periods.  The
                # prefix is checked against the validated join specification
                # and the column against that table's own whitelist, so this
                # admits nothing an unjoined clause couldn't name in its table.
                prefix, _, rest = piece.partition(".")
                if prefix in join_context:
                    resolved = (prefix, rest, join_context[prefix])
            if resolved is not None:
                tname, cname, tbl = resolved
                if cname not in tbl.search_cols:
                    raise SearchParsingError("%s: %s is not a column of %s" % (clause, cname, tname))
                processed.append(Identifier(tname, cname))
            elif piece in table.search_cols:
                if join_context is None:
                    processed.append(Identifier(piece))
                else:
                    # in a joined query every identifier is emitted qualified
                    processed.append(Identifier(table.search_table, piece))
            elif re.match(FLOAT_RE, piece):
                processed.append(Placeholder())
                if any(c in piece for c in "Ee."):
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


def IdentifierWrapper(name, convert=True):
    """
    Returns a composable representing an SQL identifier.

    This is  wrapper for psycopg.sql.Identifier that supports ARRAY slicers
    and converts them (if desired) from the Python format to SQL,
    as SQL starts at 1, and it is inclusive at the end

    EXAMPLES::

        >>> IdentifierWrapper('name')
        Identifier('name')
        >>> print(IdentifierWrapper('name[:10]').as_string(db.conn))
        "name"[:10]
        >>> print(IdentifierWrapper('name[1:10]').as_string(db.conn))
        "name"[2:10]
        >>> print(IdentifierWrapper('name[1:10]', convert=False).as_string(db.conn))
        "name"[1:10]
        >>> print(IdentifierWrapper('name[1:10:3]').as_string(db.conn))
        "name"[2:10:3]
        >>> print(IdentifierWrapper('name[1:10:3][0:2]').as_string(db.conn))
        "name"[2:10:3][1:2]
        >>> print(IdentifierWrapper('name[1:10:3][0::1]').as_string(db.conn))
        "name"[2:10:3][1::1]
        >>> print(IdentifierWrapper('name[1:10:3][0]').as_string(db.conn))
        "name"[2:10:3][1]
    """
    if "[" not in name:
        return Identifier(name)
    else:
        i = name.index("[")
        knife = name[i:]
        name = name[:i]
        # convert python slicer to postgres slicer
        # SQL starts at 1, and it is inclusive at the end
        # so we just need to convert a:b:c -> a+1:b:c

        # first we remove spaces
        knife = knife.replace(" ", "")

        # assert that the knife is of the shape [*]
        if knife[0] != "[" or knife[-1] != "]":
            raise ValueError("%s is not in the proper format" % knife)
        chunks = knife[1:-1].split("][")
        # Prevent SQL injection
        # As in Python, an empty bound in a slice (e.g. [:10]) means open,
        # but a bare index (no colon present) must be a number
        if not all(all(x.isdigit() or (x == "" and ":" in chunk) for x in chunk.split(":")) for chunk in chunks):
            raise ValueError("%s must be numeric, brackets and colons" % knife)
        if convert:
            for i, s in enumerate(chunks):
                # each cut is of the format a:b:c
                # where a, b, c are either integers or empty strings
                split = s.split(":", 1)
                # nothing to adjust
                if split[0] == "":
                    continue
                else:
                    # we should increment it by 1
                    split[0] = str(int(split[0]) + 1)
                chunks[i] = ":".join(split)
            sql_slicer = "[" + "][".join(chunks) + "]"
        else:
            sql_slicer = knife

        return SQL("{0}{1}").format(Identifier(name), SQL(sql_slicer))


class LockError(RuntimeError):
    """
    Raised when a data-changing operation cannot proceed because another
    operation holds a conflicting lock on the table (for example, a reload
    in progress, or a staged ``_tmp`` copy awaiting its swap).
    """
    pass


class QueryLogFilter():
    """
    A filter used when logging slow queries.
    """

    def filter(self, record):
        """
        Keep only records emitted from base.py (the query-execution path).
        """
        if os.path.basename(record.pathname) == "base.py":
            return 1
        else:
            return 0


class DelayCommit():
    """
    Used to set default behavior for whether to commit changes to the database connection.

    Entering this context in a with statement will cause ``_execute`` calls to not commit by
    default.  When the final DelayCommit is exited, the connection will commit.

    Setting active=False disables the DelayCommit completely, which can be helpful since it's often used in a with context and conditionally entering that context is annoying to write with if statements.
    """

    def __init__(self, obj, final_commit=True, silence=None, active=True):
        self.obj = obj._db
        self.final_commit = final_commit
        self.active = active
        self._orig_silenced = obj._db._silenced
        # Gated on active: __exit__ only restores the flag when active, so
        # setting it for an inactive DelayCommit would silence the database
        # permanently (reload_all uses exactly silence=True, active=False).
        if active and silence is not None:
            obj._db._silenced = silence

    def __enter__(self):
        if self.active:
            self.obj._nocommit_stack += 1

    def __exit__(self, exc_type, exc_value, traceback):
        if self.active:
            self.obj._nocommit_stack -= 1
            self.obj._silenced = self._orig_silenced
            if exc_type is None and self.obj._nocommit_stack == 0 and self.final_commit:
                self.obj.conn.commit()
            if exc_type is not None:
                self.obj.conn.rollback()

# Reraise an exception, possibly with a different message, type, or traceback.
if sys.version_info.major < 3:  # Python 2?
    # Using exec avoids a SyntaxError in Python 3.
    exec("""def reraise(exc_type, exc_value, exc_traceback=None):
            # Reraise an exception, possibly with a different message, type, or traceback.
                raise exc_type, exc_value, exc_traceback""")
else:
    def reraise(exc_type, exc_value, exc_traceback=None):
        """
        Reraise an exception, possibly with a different message, type, or traceback.
        """
        if exc_value is None:
            exc_value = exc_type()
        if exc_value.__traceback__ is not exc_traceback:
            raise exc_value.with_traceback(exc_traceback)
        raise exc_value

def range_formatter(x):
    """
    Format a query-language range constraint for human display:
    ``{"$gte": 2, "$lte": 7}`` becomes ``"2-7"``, one-sided constraints
    become ``"2-"`` or ``"..7"``, and ``None`` becomes ``"Unknown"``.
    """
    if x is None:
        return 'Unknown'
    elif isinstance(x, dict):
        if '$gte' in x:
            a = x['$gte']
        elif '$gt' in x:
            a = x['$gt'] + 1
        else:
            a = None
        if '$lte' in x:
            b = x['$lte']
        elif '$lt' in x:
            b = x['$lt'] - 1
        else:
            b = None
        if a == b:
            return str(a)
        elif b is None:
            return "{0}-".format(a)
        elif a is None:
            return "..{0}".format(b)
        else:
            return "{0}-{1}".format(a,b)
    return str(x)

class KeyedDefaultDict(defaultdict):
    """
    A defaultdict where the default value takes the key as input.
    """
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError((key,))
        self[key] = value = self.default_factory(key)
        return value

def make_tuple(val):
    """
    Converts lists and dictionaries into tuples, recursively.  The main application
    is so that the result can be used as a dictionary key.
    """
    if isinstance(val, (list, tuple)):
        return tuple(make_tuple(x) for x in val)
    elif isinstance(val, dict):
        return tuple((make_tuple(a), make_tuple(b)) for a,b in val.items())
    else:
        return val
