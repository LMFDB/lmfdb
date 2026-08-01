# -*- coding: utf-8 -*-
"""
This module provides functions for encoding data for storage in Postgres
and decoding the results.
"""
import binascii
import json
import datetime
import math
from psycopg.adapt import Dumper
try:
    try:
        # this fails in sage 9.3
        from sage.rings.complex_mpfr import ComplexNumber, ComplexField
    except ImportError:
        from sage.rings.complex_number import ComplexNumber, ComplexField
    from sage.rings.complex_double import ComplexDoubleElement
    from sage.rings.real_mpfr import RealLiteral, RealField, RealNumber
    from sage.rings.integer import Integer, IntegerWrapper
    from sage.rings.rational import Rational
    from sage.rings.integer_ring import ZZ
    from sage.rings.rational_field import QQ
    from sage.rings.infinity import infinity
    from sage.rings.number_field.number_field_element import NumberFieldElement
    from sage.rings.number_field.number_field import (
        NumberField,
        CyclotomicField,
        NumberField_generic,
        NumberField_cyclotomic,
    )
    from sage.rings.number_field.number_field_rel import NumberField_relative
    from sage.rings.polynomial.polynomial_element import Polynomial
    from sage.rings.power_series_poly import PowerSeries_poly
    from sage.modules.free_module_element import vector, FreeModuleElement
except ImportError:
    # Sage not installed
    SAGE_MODE = False
else:
    SAGE_MODE = True

    class LmfdbRealLiteral(RealLiteral):
        """
        A real number that prints using the string used to construct it.
        """

        def __init__(self, parent, x=0, base=10):
            if not isinstance(x, str):
                x = str(x)
            RealLiteral.__init__(self, parent, x, base)

        def __repr__(self):
            return self.literal

    class LmfdbDecimalZero(IntegerWrapper):
        """
        An exact zero constructed from an all-zero decimal string ("0.000").

        A zero stored with decimal places is still exactly zero, and an
        exact integer coerces into a real field at that field's precision,
        so sums with high-precision values lose nothing -- a floating zero
        of any fixed precision would drag them down to it instead.  The
        string used to construct it is kept so the value prints (and is
        serialized) as it was stored, like LmfdbRealLiteral.

        IntegerWrapper rather than Integer: plain Integer allocation hands
        out pooled instances for small values, bypassing subclasses.
        """

        def __init__(self, literal):
            IntegerWrapper.__init__(self, ZZ, 0)
            self.literal = literal

        def __repr__(self):
            return self.literal

        def __str__(self):
            return self.literal

    class RealEncoder():
        """
        A wrapper rendering a Sage RealNumber/RealLiteral as its literal
        text (the exact decimal string it was created from, when available).
        """
        def __init__(self, value):
            self._value = value

        def getquoted(self):
            """
            The wrapped real number's literal text.
            """
            if isinstance(self._value, RealLiteral):
                return self._value.literal
            else:
                return str(self._value)

        def __str__(self):
            return self.getquoted()

    class RealLiteralDumper(Dumper):
        """
        Dumps a Sage RealNumber/RealLiteral as its literal text, leaving the
        type unknown (oid 0) so that the server infers it from context,
        as psycopg2's client-side interpolation did.
        """
        def dump(self, obj):
            """
            Render the real number as its literal text.
            """
            if isinstance(obj, RealLiteral):
                return obj.literal.encode()
            return str(obj).encode()

    class SageIntegerDumper(Dumper):
        """
        Dumps a Sage Integer as its decimal text (replacing psycopg2's AsIs).
        """
        def dump(self, obj):
            """
            Render the integer as decimal text.
            """
            return str(obj).encode()


def numeric_precision(value):
    """
    The bit precision needed to faithfully represent a decimal string:
    log(10)/log(2) bits per significant digit, where the sign, the decimal
    point and leading zeros carry no information.  (Counting every character,
    as this function's predecessor did, manufactured phantom digits whenever
    the value was printed at full precision.)  At least 2, the smallest
    precision a RealField accepts.

    INPUT:

    - ``value`` -- a string representing a decimal number, as Postgres
      delivers the numeric type

    EXAMPLES::

        >>> numeric_precision("0.00459244230167")  # 12 significant digits
        40
    """
    digits = len(value.lstrip("+-").replace(".", "", 1).lstrip("0"))
    # All-zero decimals never reach this in Sage mode: numeric_converter
    # returns them as exact zeros, since no floating precision suits a zero.
    # log(10)/log(2) = 3.3219280948873626
    return max(math.ceil(digits * 3.3219280948873626), 2)


def numeric_converter(value, cur=None):
    """
    Used for converting numeric values from Postgres to Python.

    INPUT:

    - ``value`` -- a string representing a decimal number.
    - ``cur`` -- a cursor, unused

    OUTPUT:

    - either a sage integer (if there is no decimal point) or a real number whose precision depends on the number of significant digits in value.
    """
    if value is None:
        return None
    if "." in value:
        if SAGE_MODE:
            if not value.strip("+-0."):
                # An all-zero decimal is exactly zero, and an exact zero
                # coerces into any real field at that field's precision --
                # a floating zero of fixed precision would instead drag
                # sums with higher-precision values down to it.
                return LmfdbDecimalZero(value)
            # A good guess for the bit-precision; we use LmfdbRealLiterals
            # to ensure that our number prints the same as we got it.
            return LmfdbRealLiteral(RealField(numeric_precision(value)), value)
        else:
            # Sage isn't installed, so we fall back on Python floats
            return float(value)
    else:
        if SAGE_MODE:
            return Integer(value)
        else:
            return int(value)


class Array():
    """
    Since we use Json by default for lists, this class lets us
    get back the original behavior of encoding as a Postgres array when needed.
    """

    def __init__(self, seq):
        self._seq = seq

    def getquoted(self):
        """
        The Postgres array literal for the wrapped sequence, as bytes.
        """
        return _pg_array_literal(self._seq).encode()

    def __str__(self):
        return str(self.getquoted())


def _pg_array_literal(seq):
    """
    Render a (possibly nested) Python sequence as a Postgres array literal,
    e.g. ``{1,2,{"a","b"}}``.  Sent with unknown oid so that the server
    infers the array type from context.
    """
    parts = []
    for x in seq:
        if x is None:
            parts.append("NULL")
        elif isinstance(x, (list, tuple)):
            parts.append(_pg_array_literal(x))
        elif isinstance(x, bool):
            parts.append("t" if x else "f")
        elif isinstance(x, (int, float)):
            parts.append(str(x))
        else:
            s = str(x).replace("\\", "\\\\").replace('"', '\\"')
            parts.append('"' + s + '"')
    return "{" + ",".join(parts) + "}"


class ArrayDumper(Dumper):
    """
    Dumps an Array wrapper as a Postgres array literal with unknown oid.
    """
    def dump(self, obj):
        """
        Render the wrapped sequence as a Postgres array literal.
        """
        return _pg_array_literal(obj._seq).encode()


class Json():
    """
    A wrapper marking a value for storage as json/jsonb, encoded with
    psycodict's extended encoding (Sage types etc.).

    With psycopg2 this subclassed ``psycopg2.extras.Json``; with psycopg3
    adaptation happens through ``JsonWrapperDumper`` below instead.  The
    wrapped value is available as both ``.obj`` (psycopg3 convention) and
    ``.adapted`` (psycopg2 convention, kept for backward compatibility).
    """

    def __init__(self, obj):
        self.obj = obj
        self.adapted = obj

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.obj)

    @classmethod
    def dumps(cls, obj):
        """
        Serialize ``obj`` to json text using the extended encoding
        (see :meth:`prep`).
        """
        return json.dumps(cls.prep(obj))

    @classmethod
    def loads(cls, s):
        """
        Parse json text and decode the extended encoding back to Python
        and Sage objects (see :meth:`extract`).
        """
        return cls.extract(json.loads(s))

    @classmethod
    def prep(cls, obj, escape_backslashes=False):
        """
        Returns a version of the object that is parsable by the standard json dumps function.
        For example, replace Integers with ints, encode various Sage types using dictionaries....
        """
        # For now we just hard code the encoding.
        # It would be nice to have something more abstracted/systematic eventually
        if isinstance(obj, tuple):
            return cls.prep(list(obj), escape_backslashes)
        elif isinstance(obj, list):
            # Lists of complex numbers occur, and we'd like to save space
            # We currently only support Python's complex numbers
            # but support for Sage complex numbers would be easy to add
            if obj and all(isinstance(z, complex) for z in obj):
                return {
                    "__ComplexList__": 0,  # encoding version
                    "data": [[z.real, z.imag] for z in obj],
                }
            elif SAGE_MODE and obj and all(isinstance(z, Rational) for z in obj):
                return {
                    "__QQList__": 0,  # encoding version
                    "data": [[int(z.numerator()), int(z.denominator())] for z in obj],
                }
            elif (
                SAGE_MODE and obj
                and all(isinstance(z, NumberFieldElement) for z in obj)
                and all(z.parent() is obj[0].parent() for z in obj[1:])
            ):
                K = obj[0].parent()
                base = cls.prep(K, escape_backslashes)
                return {
                    "__NFList__": 0,  # encoding version
                    "base": base,
                    "data": [cls.prep(z, escape_backslashes)["data"] for z in obj],
                }
            else:
                return [cls.prep(x, escape_backslashes) for x in obj]
        elif isinstance(obj, dict):
            if obj and all(isinstance(k, int) or SAGE_MODE and isinstance(k, Integer) for k in obj):
                return {
                    "__IntDict__": 0,  # encoding version
                    "data": [
                        [int(k), cls.prep(v, escape_backslashes)]
                        for k, v in obj.items()
                    ],
                }
            elif all(isinstance(k, str) for k in obj):
                return {k: cls.prep(v, escape_backslashes) for k, v in obj.items()}
            else:
                raise TypeError("keys must be strings or integers")
        elif SAGE_MODE and isinstance(obj, FreeModuleElement):
            return {
                "__Vector__": 0,  # encoding version
                "base": cls.prep(obj.base_ring(), escape_backslashes),
                "data": [cls.prep(c, escape_backslashes)["data"] for c in obj],
            }
        elif SAGE_MODE and isinstance(obj, Integer):
            return int(obj)
        elif SAGE_MODE and isinstance(obj, Rational):
            return {
                "__Rational__": 0,  # encoding version
                "data": [int(obj.numerator()), int(obj.denominator())],
            }
        elif SAGE_MODE and isinstance(obj, RealNumber):
            return {
                "__RealLiteral__": 0,  # encoding version
                "data": obj.literal
                if isinstance(obj, RealLiteral)
                else str(obj),  # need truncate=False
                "prec": int(obj.parent().precision()),
            }
        elif isinstance(obj, complex):
            return {"__complex__": 0, "data": [obj.real, obj.imag]}  # encoding version
        elif SAGE_MODE and isinstance(obj, ComplexNumber):
            return {
                "__Complex__": 0,  # encoding version
                "prec": int(obj.prec()),
                "data": [str(obj.real()), str(obj.imag())],
            }
        elif SAGE_MODE and isinstance(obj, ComplexDoubleElement):
            return [float(obj.real()), float(obj.imag())]
        elif SAGE_MODE and isinstance(obj, NumberFieldElement):
            return {
                "__NFElt__": 0,  # encoding version
                "parent": cls.prep(obj.parent(), escape_backslashes),
                "data": [cls.prep(c, escape_backslashes)["data"] for c in obj.list()],
            }
        elif SAGE_MODE and isinstance(obj, NumberField_generic):
            if isinstance(obj, NumberField_relative):
                return {
                    "__NFRelative__": 0,  # encoding version
                    "vname": obj.variable_name(),
                    "data": cls.prep(obj.relative_polynomial(), escape_backslashes),
                }
            elif isinstance(obj, NumberField_cyclotomic):
                return {
                    "__NFCyclotomic__": 0,  # encoding version
                    "data": int(obj._n()),
                }
            else:
                return {
                    "__NFAbsolute__": 0,  # encoding version
                    "vname": obj.variable_name(),
                    "data": cls.prep(obj.absolute_polynomial(), escape_backslashes),
                }
        elif SAGE_MODE and obj is ZZ:
            return {
                "__IntegerRing__": 0,  # encoding version
                "data": 0,
            }  # must be present for decoding
        elif SAGE_MODE and obj is QQ:
            return {
                "__RationalField__": 0,  # encoding version
                "data": 0,
            }  # must be present for decoding
        elif SAGE_MODE and isinstance(obj, Polynomial):
            return {
                "__Poly__": 0,  # encoding version
                "vname": obj.variable_name(),
                "base": cls.prep(obj.base_ring(), escape_backslashes),
                "data": [cls.prep(c, escape_backslashes)["data"] for c in obj.list()],
            }
        elif SAGE_MODE and isinstance(obj, PowerSeries_poly):
            if obj.base_ring() is ZZ:
                data = [int(c) for c in obj.list()]
            else:
                data = [cls.prep(c, escape_backslashes)["data"] for c in obj.list()]
            return {
                "__PowerSeries__": 0,  # encoding version
                "vname": obj.variable(),
                "base": cls.prep(obj.base_ring(), escape_backslashes),
                "prec": "inf" if obj.prec() is infinity else int(obj.prec()),
                "data": data,
            }
        elif escape_backslashes and isinstance(obj, str):
            # For use in copy_dumps below
            return (
                obj.replace("\\", "\\\\")
                .replace("\r", r"\r")
                .replace("\n", r"\n")
                .replace("\t", r"\t")
                .replace('"', r"\"")
            )
        elif obj is None:
            return None
        elif isinstance(obj, datetime.datetime):
            # must come before the date branch, since datetime is a subclass of date
            return {"__datetime__": 0, "data": "%s" % (obj)}
        elif isinstance(obj, datetime.date):
            return {"__date__": 0, "data": "%s" % (obj)}
        elif isinstance(obj, datetime.time):
            return {"__time__": 0, "data": "%s" % (obj)}
        elif isinstance(obj, (str, bool, float, int)):
            return obj
        else:
            raise ValueError("Unsupported type: %s" % (type(obj)))

    @classmethod
    def _extract(cls, parent, obj):
        if parent is ZZ:
            return ZZ(obj)
        elif parent is QQ:
            return QQ(tuple(obj))
        elif isinstance(parent, NumberField_generic):
            base = parent.base_ring()
            obj = [cls._extract(base, c) for c in obj]
            return parent(obj)
        else:
            raise NotImplementedError("Cannot extract element of %s" % (parent))

    @classmethod
    def extract(cls, obj):
        """
        Takes an object extracted by the json parser and decodes the
        special-formating dictionaries used to store special types.
        """
        # prep recurses into lists and dicts, so extract must too
        if isinstance(obj, list):
            return [cls.extract(x) for x in obj]
        if isinstance(obj, dict) and "data" in obj:
            if len(obj) == 2 and "__ComplexList__" in obj:
                return [complex(*v) for v in obj["data"]]
            elif len(obj) == 2 and "__QQList__" in obj:
                assert SAGE_MODE
                return [QQ(tuple(v)) for v in obj["data"]]
            elif len(obj) == 3 and "__NFList__" in obj and "base" in obj:
                assert SAGE_MODE
                base = cls.extract(obj["base"])
                return [cls._extract(base, c) for c in obj["data"]]
            elif len(obj) == 2 and "__IntDict__" in obj:
                if SAGE_MODE:
                    return {Integer(k): cls.extract(v) for k, v in obj["data"]}
                else:
                    return {int(k): cls.extract(v) for k, v in obj["data"]}
            elif len(obj) == 3 and "__Vector__" in obj and "base" in obj:
                assert SAGE_MODE
                base = cls.extract(obj["base"])
                return vector([cls._extract(base, v) for v in obj["data"]])
            elif len(obj) == 2 and "__Rational__" in obj:
                assert SAGE_MODE
                # Rational's second positional argument is the base, so the
                # [numerator, denominator] pair must be passed as one tuple
                return Rational(tuple(obj["data"]))
            elif len(obj) == 3 and "__RealLiteral__" in obj and "prec" in obj:
                assert SAGE_MODE
                return LmfdbRealLiteral(RealField(obj["prec"]), obj["data"])
            elif len(obj) == 2 and "__complex__" in obj:
                return complex(*obj["data"])
            elif len(obj) == 3 and "__Complex__" in obj and "prec" in obj:
                assert SAGE_MODE
                return ComplexNumber(ComplexField(obj["prec"]), *obj["data"])
            elif len(obj) == 3 and "__NFElt__" in obj and "parent" in obj:
                assert SAGE_MODE
                return cls._extract(cls.extract(obj["parent"]), obj["data"])
            elif (
                len(obj) == 3
                and ("__NFRelative__" in obj or "__NFAbsolute__" in obj)
                and "vname" in obj
            ):
                assert SAGE_MODE
                poly = cls.extract(obj["data"])
                return NumberField(poly, name=obj["vname"])
            elif len(obj) == 2 and "__NFCyclotomic__" in obj:
                assert SAGE_MODE
                return CyclotomicField(obj["data"])
            elif len(obj) == 2 and "__IntegerRing__" in obj:
                assert SAGE_MODE
                return ZZ
            elif len(obj) == 2 and "__RationalField__" in obj:
                assert SAGE_MODE
                return QQ
            elif len(obj) == 3 and "__RationalPoly__" in obj and "vname" in obj:
                assert SAGE_MODE
                return QQ[obj["vname"]]([QQ(tuple(v)) for v in obj["data"]])
            elif (len(obj) == 4 and "__Poly__" in obj and "vname" in obj and "base" in obj):
                assert SAGE_MODE
                base = cls.extract(obj["base"])
                return base[obj["vname"]]([cls._extract(base, c) for c in obj["data"]])
            elif (
                len(obj) == 5
                and "__PowerSeries__" in obj
                and "vname" in obj
                and "base" in obj
                and "prec" in obj
            ):
                assert SAGE_MODE
                base = cls.extract(obj["base"])
                prec = infinity if obj["prec"] == "inf" else int(obj["prec"])
                return base[[obj["vname"]]]([cls._extract(base, c) for c in obj["data"]], prec=prec)
            elif len(obj) == 2 and "__date__" in obj:
                return datetime.date.fromisoformat(obj["data"])
            elif len(obj) == 2 and "__time__" in obj:
                # prep writes str(obj), which is isoformat with the space
                # separator; fromisoformat parses every shape that produces --
                # with or without microseconds, naive or timezone-aware.
                return datetime.time.fromisoformat(obj["data"])
            elif len(obj) == 2 and "__datetime__" in obj:
                return datetime.datetime.fromisoformat(obj["data"])
        if isinstance(obj, dict):
            return {k: cls.extract(v) for k, v in obj.items()}
        return obj


class JsonWrapperDumper(Dumper):
    """
    Dumps a ``Json`` wrapper as its json text.  We leave the oid unknown
    (0) rather than declaring json/jsonb, matching psycopg2's behavior of
    interpolating an untyped quoted literal so that the server casts by
    context (this works for both json and jsonb columns).
    """
    def dump(self, obj):
        """
        Render the wrapped value as json text.
        """
        return Json.dumps(obj.obj).encode()


class DictJsonDumper(Dumper):
    """
    Dumps a plain dict as json text with unknown oid (psycopg2 behavior via
    ``register_adapter(dict, Json)``).
    """
    def dump(self, obj):
        """
        Render the dict as json text.
        """
        return Json.dumps(obj).encode()


# Characters that can never serve as the COPY delimiter for files written by
# copy_dumps.  Postgres itself refuses backslash, newline, carriage return,
# lowercase letters, digits and dot (they would be read back as escape
# sequences or data; see ProcessCopyOptions), and refuses any character of the
# null marker, which is always \N here, so N is out too.  psycodict
# additionally refuses the double quote: copy_dumps writes \" for a quote
# inside a value but emits bare quotes around array elements and inside JSON
# text, so a quote delimiter could not be escaped coherently.
_COPY_SEP_REJECTED = frozenset('abcdefghijklmnopqrstuvwxyz0123456789.N\\\r\n"')


def check_copy_sep(sep):
    """
    Raise a ValueError if ``sep`` cannot be used as the column separator for
    a COPY (text format) file written by :func:`copy_dumps`.
    """
    if len(sep) != 1 or ord(sep) > 127 or sep in _COPY_SEP_REJECTED:
        raise ValueError(
            "Invalid COPY separator %r: must be a single ASCII character and not "
            'a lowercase letter, digit, or one of . \\ " N, newline, carriage return'
            % (sep,)
        )


def copy_dumps(inp, typ, recursing=False, *, sep="|"):
    """
    Output a string formatted as needed for loading by Postgres' COPY FROM.

    INPUT:

    - ``inp`` -- a Python or Sage object that directly translates to a postgres type (e.g. Integer, RealLiteral, dict...
    - ``typ`` -- the Postgres type of the column in which this data is being stored.
    - ``recursing`` -- used internally to format the elements of an array.  The value is
      rendered as an array member (quoted and escaped for the array parser as needed)
      rather than as a complete COPY field, and ``sep`` plays no role: the separator is
      escaped in a single pass over the assembled field by the top-level call.
    - ``sep`` -- (keyword only) the column separator that the resulting file will be
      loaded with (default ``"|"``).  Occurrences of this character anywhere in the
      formatted field -- inside text values, but also in dates and negative numbers for
      ``sep="-"``, times for ``sep=":"``, JSON text and the braces, commas and quotes of
      array literals -- are backslash-escaped, matching what Postgres' COPY (text format)
      does on output, so that they are not mistaken for column boundaries on the way back
      in.  This must agree with the separator eventually passed to COPY FROM.  Separators
      that cannot work (see :func:`check_copy_sep`) raise a ValueError.
    """
    if recursing:
        return _copy_dumps(inp, typ, True)
    if sep != "|":
        # One containment check per field; the default is known good.
        check_copy_sep(sep)
    out = _copy_dumps(inp, typ, False)
    if inp is None:
        # \N is the field-level null marker: it must reach COPY unescaped
        # (check_copy_sep keeps backslash and N out of sep in any case).
        return out
    if sep != "\t":
        # COPY's field-level escape of the delimiter, applied to the complete
        # formatted field just as COPY TO applies it on output, so that it covers
        # every type and the structural characters of array literals, not just
        # text values.  Tab needs no pass of its own: _copy_dumps has already
        # escaped every literal tab, so no raw tab remains in ``out``.
        out = out.replace(sep, "\\" + sep)
    return out


def _copy_dumps(inp, typ, recursing):
    if inp is None:
        # inside an array the null marker is the array literal NULL, since
        # COPY's field-level unescaping would turn \N into the letter N
        return "NULL" if recursing else "\\N"
    elif typ in ("text", "char", "varchar"):
        if not isinstance(inp, str):
            inp = str(inp)
        # As an array element, quote anything the array parser would misread:
        # array syntax, whitespace (trimmed when unquoted), the empty string
        # and the literal NULL.  The array-level escaping of backslashes and
        # double quotes must happen before the COPY field-level escaping below,
        # while the enclosing quotes are added after it, so that they reach
        # the array parser unescaped.
        quote = recursing and (
            not inp
            or inp.upper() == "NULL"
            or any(c in '{},"\\' or c.isspace() for c in inp)
        )
        if quote:
            inp = inp.replace("\\", "\\\\").replace('"', '\\"')
        inp = (
            inp.replace("\\", "\\\\")
            .replace("\r", r"\r")
            .replace("\n", r"\n")
            .replace("\t", r"\t")
            .replace('"', r"\"")
        )
        if quote:
            inp = '"' + inp + '"'
        return inp
    elif typ in ("json", "jsonb"):
        return json.dumps(Json.prep(inp, escape_backslashes=True))
    elif typ[-2:] == "[]":
        if not isinstance(inp, (list, tuple)):
            raise TypeError("You must use list or tuple for array columns")
        if not inp:
            return "{}"
        subtyp = None
        sublen = None
        for x in inp:
            if isinstance(x, (list, tuple)):
                if subtyp is None:
                    subtyp = typ
                elif subtyp != typ:
                    raise ValueError("Array dimensions must be uniform")
                if sublen is None:
                    sublen = len(x)
                elif sublen != len(x):
                    raise ValueError("Array dimensions must be uniform")
            elif subtyp is None:
                subtyp = typ[:-2]
            elif subtyp != typ[:-2]:
                raise ValueError("Array dimensions must be uniform")
        return "{" + ",".join(_copy_dumps(x, subtyp, True) for x in inp) + "}"
    elif typ == "boolean":
        # must come before the numeric branch, since bool is a subclass of int
        return "t" if inp else "f"
    elif SAGE_MODE and isinstance(inp, RealLiteral):
        return inp.literal
    elif isinstance(inp, (float, int)) or SAGE_MODE and isinstance(inp, (Integer, RealNumber)):
        return str(inp).replace("L", "")
    elif isinstance(inp, (datetime.date, datetime.time, datetime.datetime)):
        return "%s" % (inp)
    elif typ == "bytea":
        return r"\\x" + binascii.hexlify(inp).decode()
    else:
        raise TypeError("Invalid input %s (%s) for postgres type %s" % (inp, type(inp), typ))
