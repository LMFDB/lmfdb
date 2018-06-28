"""
This module provides functions for encoding data for storage in Postgres
and decoding the results.
"""
from psycopg2.extras import register_json, Json as pgJson
from psycopg2.extensions import adapt, register_type, register_adapter, new_type, UNICODE, UNICODEARRAY, AsIs, ISQLQuote
from sage.rings.real_mpfr import RealLiteral, RealField
from sage.rings.complex_number import ComplexNumber
from sage.rings.complex_field import ComplexField
from sage.rings.integer import Integer
from sage.rings.rational import Rational
from sage.rings.rational_field import QQ
from sage.rings.number_field.number_field_element import NumberFieldElement_absolute
from sage.rings.number_field.number_field import NumberField, CyclotomicField, NumberField_cyclotomic
from sage.rings.polynomial.polynomial_rational_flint import Polynomial_rational_flint
from sage.modules.free_module_element import vector, FreeModuleElement
from sage.arith.functions import lcm
import json

def setup_connection(conn):
    # We want to use unicode everywhere
    register_type(UNICODE, conn)
    register_type(UNICODEARRAY, conn)
    cur = conn.cursor()
    cur.execute("SELECT NULL::numeric")
    oid = cur.description[0][1]
    NUMERIC = new_type((oid,), "NUMERIC", numeric_converter)
    register_type(NUMERIC, conn)
    register_adapter(Integer, AsIs)
    register_adapter(RealLiteral, RealLiteralEncoder)
    register_adapter(list, Json)
    register_adapter(tuple, Json)
    register_adapter(dict, Json)
    register_json(conn, loads=Json.loads)

def numeric_converter(value, cur):
    """
    Used for converting numeric values from Postgres to Python.

    INPUT:

    - ``value`` -- a string representing a decimal number.
    - ``cur`` -- a cursor, unused

    OUTPUT:

    - either a sage integer (if there is no decimal point) or a real number whose precision depends on the number of digits in value.
    """
    if value is None:
        return None
    if '.' in value:
        prec = max(ceil(len(value)*3.322), 53)
        return RealLiteral(RealField(prec), value)
    else:
        return Integer(value)

class Array(object):
    """
    Since we use Json by default for lists, this class lets us
    get back the original behavior of encoding as a Postgres array when needed.
    """
    def __init__(self, seq):
        self._seq = seq
        self._conn = None

    def __conform__(self, protocol):
        if protocol == ISQLQuote:
            return self
        else:
            raise NotImplementedError

    def prepare(self, conn):
        self._conn = conn

    def getquoted(self):
        # this is the important line: note how every object in the
        # list is adapted and then how getquoted() is called on it
        pobjs = [adapt(o) for o in self._seq]
        if self._conn is not None:
            for obj in pobjs:
                if hasattr(obj, 'prepare'):
                    obj.prepare(self._conn)
        qobjs = [o.getquoted() for o in pobjs]
        return b'ARRAY[' + b', '.join(qobjs) + b']'

    def __str__(self):
        return str(self.getquoted())

class RealLiteralEncoder(object):
    def __init__(self, value):
        self._value = value
    def getquoted(self):
        return self._value.literal
    def __str__(self):
        return self._value.literal

class Json(pgJson):
    @classmethod
    def dumps(cls, obj):
        return json.dumps(cls.prep(obj))

    @classmethod
    def loads(cls, s):
        return cls.extract(json.loads(s))

    @classmethod
    def prep(cls, obj, escape_backslashes=False):
        """
        Returns a version of the object that is parsable by the standard json dumps function.
        For example, replace Integers with ints and RealLiterals with floats, encode complex
        numbers using a dictionary....
        """
        # For now we just hard code the encoding.
        # It would be nice to have something more abstracted/systematic eventually
        if isinstance(obj, tuple):
            return cls.prep(list(obj), escape_backslashes)
        elif isinstance(obj, list):
            # Lists of complex numbers occur, and we'd like to save space
            # We currently only support Python's complex numbers
            # but support for Sage complex numbers would be easy to add
            if all(isinstance(z, complex) for z in obj):
                return {'__ComplexList__': 0, # encoding version
                        'data': [[z.real, z.imag] for z in obj]}
            elif obj and all(isinstance(z, NumberFieldElement_absolute) for z in obj) and all(z.parent() is obj[0].parent() for z in obj[1:]):
                K = obj[0].parent()
                if isinstance(K, NumberField_cyclotomic):
                    ans = {'__CycList__': 0, # encoding version
                           'n': K._n()}
                else:
                    ans = {'__NFList__': 0, # encoding version
                           'poly': [[c.numerator(), c.denominator()] for c in K.polynomial().list()],
                           'vname': K.variable_name()}
                ans['data'] = [[[c.numerator(), c.denominator()] for c in z.list()] for z in obj]
            else:
                return [cls.prep(x, escape_backslashes) for x in obj]
        elif isinstance(obj, dict):
            if all(isinstance(k, (int, Integer)) for k in obj):
                return {'__IntDict__': 0, # encoding version
                        'data': [[int(k), cls.prep(v, escape_backslashes)] for k, v in obj.items()]}
            elif all(isinstance(k, basestring) for k in obj):
                return {k:cls.prep(v) for k,v in obj.iteritems()}
            else:
                raise TypeError("keys must be strings or integers")
        elif isinstance(obj, FreeModuleElement):
            if obj.base_ring() is QQ:
                base = 'QQ'
                data = [[int(c.numerator()), int(c.denominator())] for c in obj]
            else:
                raise NotImplementedError
            return {'__Vector__': 0, # encoding version
                    'base': base,
                    'data': data}
        elif isinstance(obj, Integer):
            return int(obj)
        elif isinstance(obj, Rational):
            return {'__Rational__': 0, # encoding version
                    'data': [int(obj.numerator()), int(obj.denominator())]}
        elif isinstance(obj, RealNumber):
            return {'__RealLiteral__': 0, # encoding version
                    'data': obj.literal if isinstance(obj, RealLiteral) else str(obj),
                    'prec': int(obj.parent().precision())}
        elif isinstance(obj, complex):
            # As noted above, support for Sage complex numbers
            # would be easy to add
            return {'__complex__': 0, # encoding version
                    'data': [obj.real, obj.imag]}
        elif isinstance(obj, ComplexNumber):
            return {'__Complex__': 0, # encoding version
                    'prec': int(obj.prec()),
                    'data': [str(obj.real()), str(obj.imag())]}
        elif isinstance(obj, Polynomial_rational_flint):
            return {'__RationalPoly__': 0, # encoding version
                    'vname': obj.variable_name(),
                    'data': [[c.numerator(), c.denominator()] for c in obj]}
        elif escape_backslashes and isinstance(obj, basestring):
            # For use in copy_dumps below
            return obj.replace('\\','\\\\\\\\').replace("\r", r"\r").replace("\n", r"\n").replace("\t", r"\t").replace('"',r'\"')
        else:
            return obj

    @classmethod
    def extract(cls, obj):
        """
        Takes an object extracted by the json parser and decodes the
        special-formating dictionaries used to store special types.
        """
        if isinstance(obj, dict) and 'data' in obj:
            if len(obj) == 2 and '__ComplexList__' in obj:
                return [complex(*v) for v in obj['data']]
            elif len(obj) == 2 and '__IntDict__' in obj:
                return {Integer(k): cls.extract(v) for k,v in obj['data']}
            elif len(obj) == 3 and '__Vector__' in obj and 'base' in obj:
                if base != 'QQ':
                    raise NotImplementedError
                return vector([QQ(*v) for v in obj['data']])
            elif len(obj) == 2 and '__Rational__' in obj:
                return Rational(*obj['data'])
            elif len(obj) == 3 and '__RealLiteral__' in obj and 'prec' in obj:
                return RealLiteral(RealField(obj['prec']), obj['data'])
            elif len(obj) == 2 and '__complex__' in obj:
                return complex(*obj['data'])
            elif len(obj) == 3 and '__Complex__' in obj and 'prec' in obj:
                return ComplexNumber(ComplexField(obj['prec']), *obj['data'])
            elif len(obj) == 3 and '__RationalPoly__' in obj and 'vname' in obj:
                return QQ[obj['vname']]([QQ(tuple(v)) for v in obj['data']])
            elif '__CycList__' in obj or '__NFList__' in obj:
                K = None
                if len(obj) == 3 and 'n' in obj:
                    K = CyclotomicField(obj['n'])
                elif len(obj) == 4 and 'fden' in obj and 'fnum' in obj:
                    R = QQ['x']
                    K = NumberField(R([QQ(tuple(v)) for v in obj['poly']]), name=obj['vname'])
                if K is not None:
                    return [K([QQ(tuple(v)) for v in z]) for z in obj['data']]
        return obj

def copy_dumps(inp, typ):
    """
    Output a string formatted as needed for loading by Postgres' COPY FROM.

    INPUT:

    - ``inp`` -- a Python or Sage object that directly translates to a postgres type (e.g. Integer, RealLiteral, dict...
    - ``typ`` -- the Postgres type of the column in which this data is being stored.
    """
    if inp is None:
        return ur'\N'
    elif typ in ('text', 'char', 'varchar'):
        if not isinstance(inp, basestring):
            inp = str(inp)
        return inp.replace('\\','\\\\').replace('\r',r'\r').replace('\n',r'\n').replace('\t',r'\t').replace('"',r'\"')
    elif typ in ('json','jsonb'):
        return json.dumps(Json.prep(inp, escape_backslashes=True))
    elif isinstance(inp, RealLiteral):
        return inp.literal
    elif isinstance(inp, (int, long, Integer, float)):
        return str(inp)
    elif typ=='boolean':
        return 't' if inp else 'f'
    elif isinstance(inp, (datetime.date, datetime.time, datetime.datetime)):
        return "%s"%(inp)
    elif typ == 'bytea':
        return r'\\x' + ''.join(c.encode('hex') for c in inp)
    else:
        raise TypeError("Invalid input %s (%s) for postgres type %s"%(inp, type(inp), typ))
