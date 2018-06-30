## -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2014
#  Stephan Ehlen <stephan.j.ehlen@gmail.com>
# 
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
r""" Class to represent an object that we store in a database and want to present on the web


AUTHORS:

 - Stephan Ehlen
 - Fredrik Stromberg
"""
from flask import url_for
from copy import copy
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger
from lmfdb.WebNumberField import field_pretty
from lmfdb.utils import web_latex_split_on_pm

from sage.rings.power_series_poly import PowerSeries_poly
from sage.all import SageObject,dumps,loads, QQ, NumberField, latex

import re
from datetime import datetime

class WebProperty(object):
    r"""
    A base class for the data types for the properties of a WebObject.
    """

    _default_value = None

    def __init__(self, name, value=None, default_value=None, required = True):
        #emf_logger.debug("In WebProperty of {0}".format(name))
        self.name = name
        if default_value is not None:
            self._default_value = default_value
        if value is None:
            value = self._default_value
        self._value = value
        self.required = required

    def value(self):
        return self._value

    def set_value(self, val):
        self._value = val

    def default_value(self):
        if hasattr(self, '_default_value'):
            return self._default_value
        else:
            return None

    def set_extended_properties(self):
        pass

    def __repr__(self):
        return "{0}: {1}".format(self.name, self._value)

class WebProperties(object):
    r"""
    Collection of WebProperties for easy access by name.
    """

    def __init__(self, l=None, *args):
        if isinstance(l, list) and len(l) > 0:
            self._d = {p.name : p for p in l}
        elif isinstance(l, WebProperty):
            self._d = {l.name: l}
        else:
            self._d = {}
        for p in args:
            self._d[p.name] = p

    def names(self):
        return self._d.keys()

    def list(self):
        return self._d.values()

    def as_dict(self):
        return { p.name: p.value() for p in self }

    def __getitem__(self, n):
        return self._d[n]

    def add_property(self, p):
        self._d[p.name] = p

    def append(self, p):
        self.add_property(p)

    def __iter__(self):
        return self._d.itervalues()

    def __len__(self):
        return len(self._d.keys())

    def __contains__(self, a):
        if isinstance(a, str):
            return a in self._d
        elif isinstance(a, WebProperty):
            return a.name in self._d

    def __repr__(self):
        return "Collection of {0} WebProperties".format(len(self._d.keys()))

class WebObject(object):
    r"""
    A base class for the object we store in the database.
    """

    _collection_name = None
    _key = None
    _key_multi = None
    _properties = None
    r"""
          _key: a list - The parameters that are needed to initialize a WebObject of this type.
          _key_multi: a list or string - this is just added to the file key but these are properties 
                            that do not uniquely identify the
                           (mathematical) object and one mathematical object can have several files
                           with varying values of the keys in _key_multi (example "prec" of a q-expansion)
          _file_key:  a string - the field in the database that is the unique identifier for this object
                 This can also be a list of strings if the key is a compound.
          _file_key_multi: list or string - same as _key_multi but for the files
          _collection_name: a string -  a database collection name to use
    """

    _properties = WebProperties()

    def __init__(self,
                 init_dynamic_properties=True,
                 **kwargs):
        emf_logger.debug('Create web object!')

        # This has to be overridden by classes that inherit from WebObject
        # Should be a list of WebProperty objects
        if not hasattr(self, '_properties') or self._properties is None:
            self._properties = WebProperties()

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        for p in self._properties:
            #emf_logger.debug("Adding {0} : {1}".format(p.name,p))
            self.__dict__[p.name] = p

        if init_dynamic_properties:
            emf_logger.debug('init_dynamic_properties will be called')
            self.init_dynamic_properties()

    def __getattribute__(self, n):
        try:
            return object.__getattribute__(self, '_properties')[n].value()
        except:
            return object.__getattribute__(self, n)

    def __setattr__(self, n, v):
        try:
            self._properties[n].set_value(v)
        except:
            object.__setattr__(self, n, v)

    def collection_name(self):
        return self._collection_name

    def init_dynamic_properties(self):
        r"""
        This function is called after __init__
        and should be overriden to initialize
        any properties of self that should be generated on the fly.
        """
        pass

    def properties_as_dict(self):
        r"""
          Return all WebProperties of ```self``` in a dict.
        """
        return self._properties.as_dict()

    @classmethod
    def find(cls, query={}, projection = None, sort=[]):
        r'''
          Search the database using ```query``` and return
          an iterator over the set of matching objects of this WebObject
        '''
        coll = cls.connect_to_db(cls._collection_name)
        for s in coll.find(query, sort=sort, projection=projection):
            s.pop('_id')
            try:
                k = {key:s[key] for key in cls._key}
                o = cls(init_dynamic_properties=False, **k)
                #o.update_db_properties_from_dict(s)
                yield o
            except KeyError as e:
                emf_logger.critical("Malformed data in the database {}, {}".format(e,s))
                continue

    @classmethod
    def count(cls, query={}):
        r'''
          Search the database using ```query``` and return
          the number of results
        '''
        coll = cls.connect_to_db(cls._collection_name)
        return coll.find(query).count()

    def __repr__(self):
        return "WebObject"

# Define some simple data types with reasonable default values


class WebDate(WebProperty):
    _default_value = datetime.now()
    def __init__(self, name, value=None, **kwargs):
        date_fn = lambda t: datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
        super(WebDate, self).__init__(name, value, date_fn, date_fn, **kwargs)

class WebInt(WebProperty):
    _default_value = int(0)
    def __init__(self, name, value=None, **kwargs):
        super(WebInt, self).__init__(name, value, int, int, **kwargs)
        #print self.__class__

class WebBool(WebProperty):
    _default_value = True
    def __init__(self, name, value=None, **kwargs):
        super(WebBool, self).__init__(name, value, int, int, **kwargs)
        #print self.__class__

class WebFloat(WebProperty):
    _default_value = float(0)
    def __init__(self, name, value=None, **kwargs):
        super(WebFloat, self).__init__(name, value, float, float, **kwargs)

class WebStr(WebProperty):
    _default_value = ''
    def __init__(self, name, value=None, **kwargs):
        super(WebStr, self).__init__(name, value, str, str, **kwargs)

class WebDict(WebProperty):

    def __init__(self, name, value=None, **kwargs):
        self._default_value = {}
        super(WebDict, self).__init__(name, value, dict, dict, **kwargs)

class WebList(WebProperty):
    def __init__(self, name, value=None, **kwargs):
        self._default_value = []
        super(WebList, self).__init__(name, value, list, list, **kwargs)

class WebSageObject(WebProperty):
    _default_value = None

class WebPoly(WebProperty):
    pass

class WebNoStoreObject(WebProperty):
    pass

class WebNumberField(WebDict):
    def __init__(self, name, value=None, **kwargs):
        self._default_value = QQ
        ## set default values
        self.lmfdb_label = ''
        self.lmfdb_url = ''
        self.lmfdb_pretty = ''
        super(WebDict, self).__init__(name, value, dict, dict, **kwargs)

    def set_extended_properties(self):
        setattr(self._value, "lmfdb_label", self.lmfdb_label)
        if self.lmfdb_label is not None and self.lmfdb_label != '':
            label = self.lmfdb_label
            setattr(self._value, "lmfdb_pretty", field_pretty(label))
        else:
            if self._value == QQ:
                label = '1.1.1.1'
                setattr(self._value, "lmfdb_pretty", field_pretty(label))
                setattr(self._value, "lmfdb_label", label)
            else:
                emf_logger.critical("could not set lmfdb_pretty for the label")
                label = ''
        if label != '':
            try:
                url =  url_for("number_fields.by_label", label=label)
                setattr(self._value, "lmfdb_url", url)
            except RuntimeError:
                emf_logger.critical("could not set url for the label")
        try:
            if hasattr(self._value,'absolute_polynomial'):
                setattr(self._value, "absolute_polynomial_latex", lambda n: web_latex_poly(self._value.absolute_polynomial(), n))
            else:
                setattr(self._value, "absolute_polynomial_latex",'')
            if hasattr(self._value,'relative_polynomial'):
                setattr(self._value, "relative_polynomial_latex", lambda n: web_latex_poly(self._value.relative_polynomial(), n))
            else:
                setattr(self._value, "relative_polynomial_latex",'')
        except AttributeError as e:
            emf_logger.debug(e)
            pass

def web_latex_poly(pol, name='x', keepzeta=False):
    """
    Change the name of the variable in a polynomial.  If keepzeta, then don't change
    the name of zetaN in the defining polynomial of a cyclotomic field.
    (keepzeta not implemented yet)
    """
    # the next few lines were adapted from the lines after line 117 of web_newforms.py 
    oldname = latex(pol.parent().gen())
    subfrom = oldname.strip() 
    subfrom = subfrom.replace("\\","\\\\")  
    subfrom = subfrom.replace("{","\\{")   # because x_{0} means somethgn in a regular expression
    if subfrom[0].isalpha():
        subfrom = "\\b" + subfrom
    subto = name.replace("\\","\\\\")  
    subto += " "
#    print "converting from",subfrom,"to", subto, "of", latex(pol)
    newpol = re.sub(subfrom, subto, latex(pol))
#    print "result is",newpol
    return web_latex_split_on_pm(newpol)


def number_field_to_dict(F):

    r"""
    INPUT:
    - 'K' -- Number Field
    - 't' -- (p,gens) where p is a polynomial in the variable(s) xN with coefficients in K. (The 'x' is just a convention)

    OUTPUT:

    - 'F' -- Number field extending K with relative minimal polynomial p.
    """
    if F.base_ring().absolute_degree()==1:
        K = 'QQ'
    else:
        K = number_field_to_dict(F.base_ring())
    if F.absolute_degree() == 1:
        p = 'x'
        g = ('x',)
    else:
        p = F.relative_polynomial()
        g = str(F.gen())
        x = p.variables()[0]
        p = str(p).replace(str(x),str(g))
    return {'base':K,'relative polynomial':p,'gens':g}

QQdict = number_field_to_dict(QQ)
        

def number_field_from_dict(d):
    r"""
    INPUT:

    - 'd' -- {'base':F,'p':p,'g':g } where p is a polynomial in the variable(s) xN with coefficients in K. (The 'x' is just a convention)

    OUTPUT:

    - 'F' -- Number field extending K with relative minimal polynomial p.
    """
    K = d['base']; p=d['relative polynomial']; g=d['gens']
    if K=='QQ':
        K = QQ
    elif isinstance(K,dict):
        K = number_field_from_dict(K)
    else:
        raise ValueError,"Could not construct number field!"
    F = NumberField(K[g](p),names=g)
    if F.absolute_degree()==1:
        F = QQ
    return F
