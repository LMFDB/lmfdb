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

from sage.all import SageObject,dumps,loads
from lmfdb.modular_forms.elliptic_modular_forms import emf_version
from lmfdb.modular_forms.elliptic_modular_forms.backend import get_files_from_gridfs, connect_to_modularforms_db
from sage.rings.power_series_poly import PowerSeries_poly

class WebProperty(object):
    r"""
    A meta data type for the properties of a WebObject.
    store: True if this property should be stored in gridfs
    meta: True if this property should be stored in the meta record (mongo)
    """

    def __init__(self, name, store_data_type=None, meta_data_type=None, store=True, meta=False, default_value=None):
        print 'Default:', default_value
        self.name = name
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
        self._default_value = default_value
        # Set if this Property
        # is updated from store/meta when updating from db
        # note that store always overrides meta
        self.update_from_meta = True
        self.update_from_store = True

    @property
    def default_value(self):
        return self._default_value

    def to_meta(self, val=None):
        if val is None and self.default_value is not None:
            val = self.default_value
        if val is not None:
            return self.meta_data_type(val)
        else:
            return None
    
    def to_store(self, val=None):
        if val is None and self.default_value is not None:
            val = self.default_value
        if val is not None:
            return self.store_data_type(val)
        else:
            return None

    def from_store(self, val):
        return val

    def from_meta(self, val):
        return val

    def __repr__(self):
        return self.name

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

    def __iter__(self):
        return self._d.itervalues()

    def __repr__(self):
        return "Collection of {0} WebProperties".format(len(self._d.keys()))

        

class WebObject(object):
    r"""
    A base class for the object we store in the database.
    """

    def __init__(self, params, dbkey, collection_name,
                 use_separate_meta = True,
                 use_gridfs = True,
                 update_from_db=False, **kwargs):
        r"""
          Initialze self. Set default values.
          params: a dictionary - The parameters that are needed to initialize a WebObject of this type.
          dbkey: a string - the field in the database that is the unique identifier for this object
                 This can also be a list of strings if the key is a compound.
          collection_name: a database collection name to store the values in
                           We assume that the meta collection is given by collection_name.files
                           And we keep a meta collection in collection_name.meta
        """

        # This has to be overridden by classes that inherit from WebObject
        # Should be a list of WebProperty objects
        if not hasattr(self, '_properties') or self._properties == None:
            self._properties = WebProperties()

        self._params = params
        self._collection_name = collection_name
        if use_gridfs:
            self._file_collection = connect_to_modularforms_db(collection_name + '.files')
        if use_separate_meta:
            self._meta_collection = connect_to_modularforms_db(collection_name + '.meta')
        else:
            if use_gridfs:
                self._meta_collection = connect_to_modularforms_db(collection_name + '.files')
            else:
                self._meta_collection = connect_to_modularforms_db(collection_name)
        self._files = get_files_from_gridfs(collection_name)
        if isinstance(dbkey, str):
            self._dbkey = [dbkey]
        elif isinstance(dbkey, list):
            self._dbkey = dbkey
        else:
            raise ValueError("dbkey has to be a list or a string, got {0}".format(dbkey))

        # Initialize _properties, _store_properties and _meta_properties to be simpler
        self._store_properties = WebProperties([p for p in self._properties if p.store])
        self._meta_properties = WebProperties([p for p in self._properties if p.meta])

        print hasattr(self, 'level')

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        for p in self._properties:
            if not hasattr(self, p.name):
                print "Setting {0} = {1}".format(p.name, p.default_value)
                setattr(self, p.name, p.default_value)

        if update_from_db:
            self.update_from_db()
            
        self.init_dynamic_properties()
        

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
        f._check_if_all_computed()
        # Now we check completeness and consistency of the meta record
        rec = f.get_meta_record()
        for p in self._meta_properties:
            assert rec.has_key(p.name), "Missing property {0} in meta record.".format(p)
            v = getattr(f, p)
            got = type(v)
            expected = p.type
            assert got is expected, "Property {0} has wrong type. Got {1}, expected {2}".format(got, expected)
            mf = p.to_meta(getattr(f, p.name))
            ms = p.to_meta(getattr(self, p.name))
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
            expected = p.type
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
        return { key : self._properties[key].to_meta(getattr(self, key)) for key in self._dbkey }       

    def params_dict(self):
        r"""
        Return a dictionary where the keys are the params of ``self``` and
        the values are the corresponding values of ```self```.
        """

        return { key : self._properties[key].to_meta(getattr(self, key)) for key in self._params }

    def meta_dict(self):
        r"""
        Return a dictionary with keys given by the keys of self._meta_properties
        and values given by the corresponding values of self. We also apply the function to_meta() to the values
        to assure that we have the right data type (this is handy for complex conversions as well).
        """
        return { p.name : p.to_meta(getattr(self, p.name)) for p in self._meta_properties }

    def store_dict(self):
        r"""
        Return a dictionary with keys given by the keys of self._store_properties
        and values given by the corresponding values of self. We also apply the to_store() function to the values
        to assure that we have the right data type (this is handy for complex conversions as well).
        """
        return { p.name : p.to_store(getattr(self, p.name)) for p in self._store_properties }

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
                fid = coll.find_one(key)['_id']
                fs.delete(fid)
        # insert
        s = dumps(self.store_dict())
        try:
            fs.put(s, **key)
        except Error, e:
            print "Error inserting record: {0}".format(e)
        #fid = coll.find_one(key)['_id']
        # insert extended record
        coll = self._meta_collection
        meta_key = self.params_dict()
        meta_key.update(key)
        print meta_key
        meta = self.meta_dict()
        #meta['fid'] = fid
        if coll.find(meta_key).count()>0:
            if not update:
                return True
            else:
                coll.update(meta_key, meta)
        else:
            coll.insert(meta)
        

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
                rec = coll.find_one(meta_key)
                for p in self._meta_properties:
                    # Note that we give preference to store_properties
                    if p.update_from_meta and rec.has_key(p.name) and not p in self._store_properties:
                        setattr(self, p.name, p.from_meta(rec[p.name]))
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
                if p.update_from_store and d.has_key(p.name):
                    setattr(self, p.name, p.from_store(d[p.name]))
        else:
            if not ignore_non_existent:
                raise IndexError("Record does not exist")

    def __repr__(self):
        return "WebObject"

# Define some simple data types with reasonable default values
        
class WebInt(WebProperty):

    def __init__(self, name, store=True, meta=True, default_value=int(0)):
        super(WebInt, self).__init__(name, int, int, store, meta, default_value)
        print self.__class__

class WebBool(WebProperty):

    def __init__(self, name, store=True, meta=True, default_value=True):
        super(WebBool, self).__init__(name, int, int, store, meta, default_value)
        print self.__class__

class WebFloat(WebProperty):

    def __init__(self, name, store=True, meta=True, default_value=int(0)):
        super(WebFloat, self).__init__(name, float, float, store, meta, default_value)

class WebStr(WebProperty):

    def __init__(self, name, store=True, meta=True, default_value=''):
        super(WebStr, self).__init__(name, str, str, store, meta, default_value)

class WebDict(WebProperty):

    def __init__(self, name, store=True, meta=False, default_value=None):
        if default_value == None:
            default_value = {}
        super(WebDict, self).__init__(name, dict, dict, store, meta, default_value)

class WebList(WebProperty):

    def __init__(self, name, store=True, meta=False, default_value=None):
        if default_value == None:
            default_value = []
        super(WebList, self).__init__(name, list, list, store, meta, default_value)

class WebSageObject(WebProperty):

    def __init__(self, name, datatype=SageObject, store=True,
                 meta=False, default_value=None):
        super(WebSageObject, self).__init__(name, store_data_type=datatype, meta_data_type=str, store=store, meta=meta, default_value=default_value)

    def to_store(self, f):
        return dumps(f)

    def from_store(self, f):
        return loads(f)

class WebPoly(WebProperty):
    def __init__(self, name, store=True, meta=True,
                 default_value=None):
        super(WebPoly, self).__init__(name, store_data_type=PowerSeries_poly, meta_data_type=str, store=store, meta=meta, default_value=default_value)

    def to_store(self, f):
        return dumps(f)

    def from_store(self, f):
        return loads(f)

    def to_meta(self, f):
        return str(f)

    def from_meta(self, f):
        raise NotImplementedError

class WebNoStoreObject(WebProperty):

    def __init__(self, name, default_value=None):
        super(WebNoStoreObject, self).__init__(name, meta=False, store=False, default_value=default_value)


class WebNumberField(WebDict):
    
    def __init__(self, name, store=True, meta=True, default_value=None):
        if default_value == None:
            default_value = {}
        super(WebDict, self).__init__(name, dict, dict, store, meta, default_value)

    def to_store(self, K):
        return number_field_to_dict(K)

    def from_store(self, k):
        return number_field_from_dict(k)

    def to_meta(self, K):
        r"""
        We store the LMFDB label of the absolute field
        in the meta collection.
        """
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
