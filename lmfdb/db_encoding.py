"""
This module provides functions for encoding data for storage in Postgres
and decoding the results.
"""
from psycopg2.extras import register_json, Json as pgJson
from psycopg2.extensions import adapt, register_type, register_adapter, new_type, UNICODE, UNICODEARRAY, AsIs, ISQLQuote
from sage.functions.other import ceil
from sage.rings.real_mpfr import RealLiteral, RealField, RealNumber
from sage.rings.complex_number import ComplexNumber
from sage.rings.complex_field import ComplexField
from sage.rings.integer import Integer
from sage.rings.rational import Rational
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.infinity import infinity
from sage.rings.number_field.number_field_element import NumberFieldElement
from sage.rings.number_field.number_field import NumberField, CyclotomicField, NumberField_generic, NumberField_cyclotomic
from sage.rings.number_field.number_field_rel import NumberField_relative
from sage.rings.polynomial.polynomial_element import Polynomial
from sage.rings.power_series_poly import PowerSeries_poly
from sage.modules.free_module_element import vector, FreeModuleElement
import json
import datetime

def setup_connection(conn):
    # We want to use unicode everywhere
    register_type(UNICODE, conn)
    register_type(UNICODEARRAY, conn)
    conn.set_client_encoding('UTF8')
    cur = conn.cursor()
    cur.execute("SELECT NULL::numeric")
    oid = cur.description[0][1]
    NUMERIC = new_type((oid,), "NUMERIC", numeric_converter)
    register_type(NUMERIC, conn)
    register_adapter(Integer, AsIs)
    register_adapter(RealNumber, RealEncoder)
    register_adapter(list, Json)
    register_adapter(tuple, Json)
    register_adapter(dict, Json)
    register_json(conn, loads=Json.loads)

class LmfdbRealLiteral(RealLiteral):
    """
    A real number that prints using the string used to construct it.
    """
    def __init__(self, parent, x=0, base=10):
        if not isinstance(x, basestring):
            x = str(x)
        RealLiteral.__init__(self, parent, x, base)
    def __repr__(self):
        return self.literal

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
        # The following is a good guess for the bit-precision,
        # but we use LmfdbRealLiterals to ensure that our number
        # prints the same as we got it.
        prec = ceil(len(value)*3.322)
        return LmfdbRealLiteral(RealField(prec), value)
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

class RealEncoder(object):
    def __init__(self, value):
        self._value = value
    def getquoted(self):
        if isinstance(self._value, RealLiteral):
            return self._value.literal
        else:
            return str(self._value)
    def __str__(self):
        return self.getquoted()

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
                return {'__ComplexList__': 0, # encoding version
                        'data': [[z.real, z.imag] for z in obj]}
            elif obj and all(isinstance(z, Rational) for z in obj):
                return {'__QQList__': 0, # encoding version
                        'data': [[int(z.numerator()), int(z.denominator())] for z in obj]}
            elif obj and all(isinstance(z, NumberFieldElement) for z in obj) and all(z.parent() is obj[0].parent() for z in obj[1:]):
                K = obj[0].parent()
                base = cls.prep(K, escape_backslashes)
                return {'__NFList__': 0, # encoding version
                        'base': base,
                        'data': [cls.prep(z, escape_backslashes)['data'] for z in obj]}
            else:
                return [cls.prep(x, escape_backslashes) for x in obj]
        elif isinstance(obj, dict):
            if obj and all(isinstance(k, (int, Integer)) for k in obj):
                return {'__IntDict__': 0, # encoding version
                        'data': [[int(k), cls.prep(v, escape_backslashes)] for k, v in obj.items()]}
            elif all(isinstance(k, basestring) for k in obj):
                return {k:cls.prep(v, escape_backslashes) for k,v in obj.iteritems()}
            else:
                raise TypeError("keys must be strings or integers")
        elif isinstance(obj, FreeModuleElement):
            return {'__Vector__': 0, # encoding version
                    'base': cls.prep(obj.base_ring(), escape_backslashes),
                    'data': [cls.prep(c, escape_backslashes)['data'] for c in obj]}
        elif isinstance(obj, Integer):
            return int(obj)
        elif isinstance(obj, Rational):
            return {'__Rational__': 0, # encoding version
                    'data': [int(obj.numerator()), int(obj.denominator())]}
        elif isinstance(obj, RealNumber):
            return {'__RealLiteral__': 0, # encoding version
                    'data': obj.literal if isinstance(obj, RealLiteral) else str(obj), # need truncate=False
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
        elif isinstance(obj, NumberFieldElement):
            return {'__NFElt__': 0, # encoding version
                    'parent': cls.prep(obj.parent(), escape_backslashes),
                    'data': [cls.prep(c, escape_backslashes)['data'] for c in obj.list()]}
        elif isinstance(obj, NumberField_generic):
            if isinstance(obj, NumberField_relative):
                return {'__NFRelative__': 0, # encoding version
                        'vname': obj.variable_name(),
                        'data': cls.prep(obj.relative_polynomial(), escape_backslashes)}
            elif isinstance(obj, NumberField_cyclotomic):
                return {'__NFCyclotomic__': 0, # encoding version
                        'data': int(obj._n())}
            else:
                return {'__NFAbsolute__': 0, # encoding version
                        'vname': obj.variable_name(),
                        'data': cls.prep(obj.absolute_polynomial(), escape_backslashes)}
        elif obj is ZZ:
            return {'__IntegerRing__': 0, # encoding version
                    'data': 0} # must be present for decoding
        elif obj is QQ:
            return {'__RationalField__': 0, # encoding version
                    'data': 0} # must be present for decoding
        elif isinstance(obj, Polynomial):
            return {'__Poly__': 0, # encoding version
                    'vname': obj.variable_name(),
                    'base': cls.prep(obj.base_ring(), escape_backslashes),
                    'data': [cls.prep(c, escape_backslashes)['data'] for c in obj.list()]}
        elif isinstance(obj, PowerSeries_poly):
            if obj.base_ring() is ZZ:
                data = [int(c) for c in obj.list()]
            else:
                data = [cls.prep(c, escape_backslashes)['data'] for c in obj.list()]
            return {'__PowerSeries__': 0, # encoding version
                    'vname': obj.variable(),
                    'base': cls.prep(obj.base_ring(), escape_backslashes),
                    'prec': 'inf' if obj.prec() is infinity else int(obj.prec()),
                    'data': data}
        elif escape_backslashes and isinstance(obj, basestring):
            # For use in copy_dumps below
            return obj.replace('\\','\\\\\\\\').replace("\r", r"\r").replace("\n", r"\n").replace("\t", r"\t").replace('"',r'\"')
        elif obj is None:
            return None
        elif isinstance(obj, datetime.date):
            return {'__date__': 0,
                    'data': "%s"%(obj)}
        elif isinstance(obj, datetime.time):
            return {'__time__': 0,
                    'data': "%s"%(obj)}
        elif isinstance(obj, datetime.datetime):
            return {'__datetime__': 0,
                    'data': "%s"%(obj)}
        elif isinstance(obj, (basestring, int, long, bool, float)):
            return obj
        else:
            raise ValueError("Unsupported type: %s"%(type(obj)))

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
            raise NotImplementedError("Cannot extract element of %s"%(parent))

    @classmethod
    def extract(cls, obj):
        """
        Takes an object extracted by the json parser and decodes the
        special-formating dictionaries used to store special types.
        """
        if isinstance(obj, dict) and 'data' in obj:
            if len(obj) == 2 and '__ComplexList__' in obj:
                return [complex(*v) for v in obj['data']]
            elif len(obj) == 2 and '__QQList__' in obj:
                return [QQ(tuple(v)) for v in obj['data']]
            elif len(obj) == 3 and '__NFList__' in obj and 'base' in obj:
                base = cls.extract(obj['base'])
                return [cls._extract(base, c) for c in obj['data']]
            elif len(obj) == 2 and '__IntDict__' in obj:
                return {Integer(k): cls.extract(v) for k,v in obj['data']}
            elif len(obj) == 3 and '__Vector__' in obj and 'base' in obj:
                base = cls.extract(obj['base'])
                return vector([cls._extract(base, v) for v in obj['data']])
            elif len(obj) == 2 and '__Rational__' in obj:
                return Rational(*obj['data'])
            elif len(obj) == 3 and '__RealLiteral__' in obj and 'prec' in obj:
                return LmfdbRealLiteral(RealField(obj['prec']), obj['data'])
            elif len(obj) == 2 and '__complex__' in obj:
                return complex(*obj['data'])
            elif len(obj) == 3 and '__Complex__' in obj and 'prec' in obj:
                return ComplexNumber(ComplexField(obj['prec']), *obj['data'])
            elif len(obj) == 3 and '__NFElt__' in obj and 'parent' in obj:
                return cls._extract(cls.extract(obj['parent']), obj['data'])
            elif len(obj) == 3 and ('__NFRelative__' in obj or '__NFAbsolute__' in obj) and 'vname' in obj:
                poly = cls.extract(obj['data'])
                return NumberField(poly, name=obj['vname'])
            elif len(obj) == 2 and '__NFCyclotomic__' in obj:
                return CyclotomicField(obj['data'])
            elif len(obj) == 2 and '__IntegerRing__' in obj:
                return ZZ
            elif len(obj) == 2 and '__RationalField__' in obj:
                return QQ
            elif len(obj) == 3 and '__RationalPoly__' in obj and 'vname' in obj:
                return QQ[obj['vname']]([QQ(tuple(v)) for v in obj['data']])
            elif len(obj) == 4 and '__Poly__' in obj and 'vname' in obj and 'base' in obj:
                base = cls.extract(obj['base'])
                return base[obj['vname']]([cls._extract(base, c) for c in obj['data']])
            elif len(obj) == 5 and '__PowerSeries__' in obj and 'vname' in obj and 'base' in obj and 'prec' in obj:
                base = cls.extract(obj['base'])
                prec = infinity if obj['prec'] == 'inf' else int(obj['prec'])
                return base[[obj['vname']]]([cls._extract(base, c) for c in obj['data']], prec=prec)
            elif len(obj) == 2 and '__date__' in obj:
                return datetime.datetime.strptime(obj['data'], "%Y-%m-%d").date()
            elif len(obj) == 2 and '__time__' in obj:
                return datetime.datetime.strptime(obj['data'], "%H:%M:%S.%f").time()
            elif len(obj) == 2 and '__datetime__' in obj:
                return datetime.datetime.strptime(obj['data'], "%Y-%m-%d %H:%M:%S.%f")
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
