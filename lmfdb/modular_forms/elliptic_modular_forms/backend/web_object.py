# -*- coding: utf-8 -*-
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
 
"""


from lmfdb.modular_forms.elliptic_modular_forms import emf_version, emf_logger
from lmfdb.modular_forms.elliptic_modular_forms.backend import get_files_from_gridfs, connect_to_modularforms_db
from lmfdb.number_fields.number_field import poly_to_field_label

from sage.rings.power_series_poly import PowerSeries_poly
from sage.all import SageObject,dumps,loads, QQ, NumberField

import pymongo
import gridfs

class WebProperty(object):
    r"""
    A meta data type for the properties of a WebObject.
    store: True if this property should be stored in gridfs
    meta: True if this property should be stored in the meta record (mongo)
    """

    _default_value = None

    def __init__(self, name, value=None, store_data_type=None, meta_data_type=None, store=True, meta=False, default_value=None, include_in_update=True):
        self.name = name
        if default_value is not None:
            self._default_value = default_value
        if value is None:
            value = self._default_value
        self._value = value
        # default to str
        if store_data_type is not None:
            self.store_data_type = store_data_type
        else:
            self.store_data_type = str
        if meta_data_type is not None:
            self.meta_data_type = meta_data_type
        else:
            self.meta_data_type = str
        self.store = store
        self.meta = meta

        self.include_in_update = include_in_update
        
    def value(self):
        return self._value

    def set_value(self, val):
        self._value = val
    
    def default_value(self):
        if hasattr(self, '_default_value'):
            return self._default_value
        else:
            return None

    def to_meta(self):
        val = self._value
        print val
        if val is not None:
            return self.meta_data_type(val)
        else:
            return None
    
    def to_store(self):
        val = self._value
        if val is not None:
            try:
                return self.store_data_type(val)
            except:
                raise TypeError("Error with value {0}".format(val))
        else:
            return None

    def from_store(self, val):
        return val

    def from_meta(self, val):
        return val

    def set_from_store(self, val):
        self._value = self.from_store(val)

    def set_from_meta(self, val):
        self._value = self.from_meta(val)

    def __repr__(self):
        return "{0}".format(self.name)#, self.value)

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
        return a in self._d

    def __repr__(self):
        return "Collection of {0} WebProperties".format(len(self._d.keys()))
        

class WebObject(object):
    r"""
    A base class for the object we store in the database.
    """

    _collection_name = None
    _params = None
    _dbkey = None
    _properties = None

    r"""
          _params: a dictionary - The parameters that are needed to initialize a WebObject of this type.
          _dbkey: a string - the field in the database that is the unique identifier for this object
                 This can also be a list of strings if the key is a compound.
          _collection_name: a database collection name to store the values in
                           We assume that the meta collection is given by 'collection_name.files'
                           And we keep a meta collection in 'collection_name.meta'
    """

    _properties = WebProperties()

    @staticmethod
    def connect_to_db(coll=''):
        return connect_to_modularforms_db(coll)

    @classmethod
    def get_files_from_gridfs(cls, coll):
        C = cls.connect_to_db()
        return gridfs.GridFS(C,coll)

    def __init__(self,
                 use_separate_meta = True,
                 use_gridfs = True,
                 update_from_db=False, **kwargs):

        print "in WebObject.__init__"
        print self._properties

        # This has to be overridden by classes that inherit from WebObject
        # Should be a list of WebProperty objects
        if not hasattr(self, '_properties') or self._properties == None:
            self._properties = WebProperties()

        if use_gridfs:
            self._file_collection = self.connect_to_db(self._collection_name + '.files')
        self.use_separate_meta = use_separate_meta
        if use_separate_meta:
            self._meta_collection = self.connect_to_db(self._collection_name + '.meta')
        else:
            if use_gridfs:
                self._meta_collection = self.connect_to_db(self._collection_name + '.files')
            else:
                self._meta_collection = self.connect_to_db(self._collection_name)
        self._files = self.get_files_from_gridfs(self._collection_name)

        # Initialize _store_properties and _meta_properties to be simpler
        self._store_properties = WebProperties([p for p in self._properties if p.store])
        self._meta_properties = WebProperties([p for p in self._properties if p.meta])

        #print hasattr(self, 'level')

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        for p in self._properties:
            emf_logger.debug("Adding {0}".format(p.name))
            self.__dict__[p.name] = p
                
        if update_from_db:
            #emf_logger.debug('Update requested for {0}'.format(self.__dict__))
            self.update_from_db()

        #emf_logger.debug('init_dynamic_properties will be called for {0}'.format(self.__dict__))
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
        
    def meta_properties(self):
        r"""
         Return a dictionary with keys equal to the properties of self and values representing the data types.
        """
        return self._meta_properties
            

    def store_properties(self):
        r"""
         Return a dictionary with keys equal to the properties of self
         which are stored in the database and values representing data types.
        """
        return self._store_properties

    def _check_if_all_saved(self):
        r"""
        We check if all properties have been saved.
        In the file store and in the meta record.
        """
        # We recreate self from the db and check if everything is
        # contained in the new object.
        params = { key : getattr(self, key) for key in self._params }
        f = self.__class__(**params)
        f.update_from_db()
        f._check_if_all_computed()
        # Now we check completeness and consistency of the meta record
        rec = f.get_meta_record()
        for p in self._meta_properties:
            assert rec.has_key(p.name), "Missing property {0} in meta record.".format(p)
            v = getattr(f, p.name)
            got = type(v)
            expected = p.meta_data_type
            assert got is expected, "Property {0} has wrong type. Got {1}, expected {2}".format(p.name, got, expected)
            s = getattr(self, p.name)
            assert v == s, "Error restoring Property {0}. Got {1}, expected {2}".format(p.name, v, s)
            mf = f._properties[p.name].to_meta()
            ms = p.to_meta()
            r = rec[p.name]
            assert mf == r and ms == r, \
                   "Evaluation of {0} failed. Meta record is {1} but property_to_eta returned {2}".format(p, m, r)
        return True
        
    def _check_if_all_computed(self):
        r"""
        We check if all properties in self._store_properties are set.
        """
        for p in self._store_properties:
            assert hasattr(self, p.name), "Missing property {0}".format(p)
            v = getattr(self, p.name)
            got = type(v)
            expected = p.store_data_type
            assert got is expected, "Property {0} has wrong type. Got {1}, expected {2}".format(got, expected)
            assert v is not None, "Did you store {0}? It has value {1}".format(p, v)
        return True

    def init_dynamic_properties(self):
        r"""
        This function is called after __init__
        and should be overriden to initialize
        any properties of self that should be generated on the fly.
        """
        pass
        
    def key_dict(self):
        r"""
        Return a dictionary where the keys are the dbkeys of ``self``` and
        the values are the corresponding values of ```self```.
        """
        emf_logger.debug('dbkey: {0}'.format(self._dbkey))
        emf_logger.debug('properties: {0}'.format(self._properties))
        return { key : self._properties[key].to_meta() for key in self._dbkey }       

    def params_dict(self):
        r"""
        Return a dictionary where the keys are the params of ``self``` and
        the values are the corresponding values of ```self```.
        """

        return { key : self._properties[key].to_meta() for key in self._params }

    def meta_dict(self):
        r"""
        Return a dictionary with keys given by the keys of self._meta_properties
        and values given by the corresponding values of self. We also apply the function to_meta() to the values
        to assure that we have the right data type (this is handy for complex conversions as well).
        """
        return { p.name : p.to_meta() for p in self._meta_properties }

    def store_dict(self):
        r"""
        Return a dictionary with keys given by the keys of self._store_properties
        and values given by the corresponding values of self. We also apply the to_store() function to the values
        to assure that we have the right data type (this is handy for complex conversions as well).
        """
        return { p.name : p.to_store() for p in self._store_properties }

    def get_meta_record(self):
        r"""
          Get the meta record from the database. This is the mongodb record in collection_name.files.
        """
        coll = self._meta_collection
        rec = coll.find_one(self.meta_dict())
        return { p.name: p.from_meta(rec[p.name]) for p in self._meta_properties if rec.has_key(p.name) }

    def save_to_db(self, update = True):
        r"""
        Saves ```self``` to the database, i.e.
        save the meta record and the file in the gridfs file system.
        """
        fs = self._files
        key = self.key_dict()
        coll = self._file_collection
        if fs.exists(key):
            if not update:
                return True
            else:
                fid = coll.find_one(key, fields=['_id'])['_id']
                fs.delete(fid)
        # insert
        s = dumps(self.store_dict())
        if not self.use_separate_meta:
            key.update(self.meta_dict())
        try:
            fs.put(s, **key)
        except Error, e:
            emf_logger.warn("Error inserting record: {0}".format(e))
        #fid = coll.find_one(key)['_id']
        # insert extended record
        if not self.use_separate_meta:
            return True
        coll = self._meta_collection
        meta_key = self.params_dict()
        meta_key.update(key)
        #print meta_key
        meta = self.meta_dict()
        #meta['fid'] = fid
        if coll.find(meta_key).count()>0:
            if not update:
                return True
            else:
                coll.update(meta_key, meta)
        else:
            coll.insert(meta)
        return True
        

    def delete_from_db(self, all=False):
        r"""
        Deletes ```self``` to the database, i.e.
        deletes the meta record and the file in the gridfs file system.
        """
        coll = self._meta_collection
        meta_key = self.params_dict()
        ct = coll.find(meta_key).count()
        if ct > 0:
            if ct ==1 or all:
                coll.remove(meta_key)
        if ct <= 1 or all:
            fs = self._files
            key = self.key_dict()
            coll = self._collection
            if fs.exists(key):
                fid = coll.find_one(key)['_id']
                fs.delete(fid)
            else:
                raise IndexError("Record does not exist")

    def update_from_db(self, meta = True, ignore_non_existent = True):
        r"""
        Updates the properties of ```self``` from the database using params and dbkey.
        """
        if meta:
            coll = self._meta_collection
            meta_key = self.params_dict()
            if coll.find(meta_key).count()>0:
                props_to_fetch = [p.name for p in self._meta_properties
                                  if (p.include_in_update and not p in self._store_properties)
                                  or p.name in self._params]
                rec = coll.find_one(meta_key, fields = props_to_fetch)
                for pn in props_to_fetch:
                    p = self._properties[pn]
                    if rec.has_key(pn):
                        try:
                            p.set_from_meta(rec[pn])
                        except NotImplementedError:
                            continue                           
            else:
                if not ignore_non_existent:
                    raise IndexError("Meta record does not exist")
        fs = self._files
        key = self.key_dict()
        if fs.exists(key):
            coll = self._file_collection
            fid = coll.find_one(key)['_id']
            d = loads(fs.get(fid).read())
            for p in self._store_properties:
                if p.include_in_update and d.has_key(p.name):
                    p.set_from_store(d[p.name])
        else:
            if not ignore_non_existent:
                raise IndexError("Record does not exist")

    def __repr__(self):
        return "WebObject"

class WebObjectTest(WebObject):

    #Needs to be set for this class to work
    DB = None

    @classmethod
    def connect_to_db(cls, c=''):
        if c != '':
            return cls.DB[c]
        else:
            return cls.DB
    
    _collection_name = 'test'
    _dbkey = ['id']
    _params = ['id']

    def __init__(self, **kwargs):

        self._properties = WebProperties([WebInt('test_property'), WebInt('id')])
        super(WebObjectTest, self).__init__(self, **kwargs)
    

# Define some simple data types with reasonable default values
        
class WebInt(WebProperty):

    _default_value = int(0)

    def __init__(self, name, value=None, store=True, meta=True, **kwargs):
        super(WebInt, self).__init__(name, value, int, int, store, meta, **kwargs)
        #print self.__class__

class WebBool(WebProperty):

    _default_value = True

    def __init__(self, name, value=None, store=True, meta=True, **kwargs):
        super(WebBool, self).__init__(name, value, int, int, store, meta, **kwargs)
        #print self.__class__

class WebFloat(WebProperty):

    _default_value = float(0)

    def __init__(self, name, value=None, store=True, meta=True, **kwargs):
        super(WebFloat, self).__init__(name, value, float, float, store, meta, **kwargs)

class WebStr(WebProperty):

    def __init__(self, name, value=None, store=True, meta=True, **kwargs):
        self._default_value = ''
        super(WebStr, self).__init__(name, value, str, str, store, meta, **kwargs)

class WebDict(WebProperty):

    def __init__(self, name, value=None, store=True, meta=False, **kwargs):
        self._default_value = {}
        super(WebDict, self).__init__(name, value, dict, dict, store, meta, **kwargs)

class WebList(WebProperty):

    def __init__(self, name, value=None, store=True, meta=False, **kwargs):
        self._default_value = []
        super(WebList, self).__init__(name, value, list, list, store, meta, **kwargs)

class WebSageObject(WebProperty):

    def __init__(self, name, value=None, datatype=SageObject, store=True,
                 meta=False, **kwargs):
        super(WebSageObject, self).__init__(name, value, store_data_type=datatype, meta_data_type=str, store=store, meta=meta, **kwargs)

    def to_store(self):
        return dumps(self._value)

    def from_store(self, f):
        return loads(f)

class WebPoly(WebProperty):
    def __init__(self, name, value=None, store=True, meta=True,
                 **kwargs):
        super(WebPoly, self).__init__(name, value, store_data_type=PowerSeries_poly, meta_data_type=str, store=store, meta=meta, **kwargs)

    def to_store(self):
        f = self._value
        if f is None:
            return None
        return f
    
    def from_store(self, f):
        return f

    def to_meta(self):
        return str(self._value)

    def from_meta(self, f):
        raise NotImplementedError

class WebNoStoreObject(WebProperty):

    def __init__(self, name, value=None, **kwargs):
        super(WebNoStoreObject, self).__init__(name, value, meta=False, store=False, **kwargs)


class WebNumberField(WebDict):
    
    def __init__(self, name, value=None,
                 store=True, meta=True, **kwargs):
        self._default_value = QQ
        super(WebDict, self).__init__(name, value, dict, dict, store, meta, **kwargs)

    def to_store(self):
        return number_field_to_dict(self._value)

    def from_store(self, k):
        return number_field_from_dict(k)

    def to_meta(self):
        r"""
        We store the LMFDB label of the absolute field
        in the meta collection.
        """
        K = self._value
        
        if K.absolute_degree() == 1:
            p = 'x'
        else:
            p = K.absolute_polynomial()

        l = poly_to_field_label(p)

        return l

    def from_meta(self, k):
        raise NotImplementedError
            

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
