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

from lmfdb.modular_forms.elliptic_modular_forms import emf_version
from lmfdb.modular_forms.elliptic_modular_forms.backend import get_files_from_gridfs, connect_to_modularforms_db
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_character import WebChar
from sage.rings.power_series_poly import PowerSeries_poly

class WebProperty(object):
    r"""
    A meta data type for the properties of a WebObject.
    store: True if this property should be stored in gridfs
    meta: True if this property should be stored in the meta record (mongo)
    """

    def __init__(self, name, data_type, store=True, meta=False, default_value=None):
        self.name = name
        self.type = data_type
        self.store = store
        self.meta = meta
        self.default_value = default_value

    def to_meta(self, val=None):
        if val is None and self.default_value is not None:
            val = self.default_value
        if val is not None:
            return self.type(val)
        else:
            return None
    
    def to_store(self, val=None):
        if val is None and self.default_value is not None:
            val = self.default_value
        if val is not None:
            return self.type(val)
        else:
            return None

    def from_store(self, val):
        return val

    def from_meta(self, val):
        return val

    def __repr__(self):
        return self.name
        

class WebObject(object):
    r"""
    A base class for the object we store in the database.
    """

    def __init__(self, params, dbkey, collection_name, **kwargs):
        r"""
          Initialze self. Set default values.
          params: a dictionary - The parameters that are needed to initialize a WebObject of this type.
          dbkey: a string - the field in the database that is the unique identifier for this object
                 This can also be a list of strings if the key is a compound.
          collection_name: a database collection name to store the values in
                           We assume that the meta collection is given by collection_name.files
        """

        # This has to be overridden by classes that inherit from WebObject
        # Should be a list of WebProperty objects
        if not hasattr(self, '_properties') or self._properties == None:
            self._properties = []

        self._params = params
        self._collection_name = collection_name
        self._collection = connect_to_modularforms_db(collection_name + '.files')
        self._files = get_files_from_gridfs(collection_name)
        if isinstance(dbkey, str):
            self._dbkey = [dbkey]
        elif isinstance(dbkey, list):
            self._dbkey = dbkey
        else:
            raise ValueError("dbkey has to be a list or a string, got {0}".format(dbkey))

        # Initialize _properties, _store_properties and _meta_properties to be simpler
        self._store_properties = [p for p in self._properties if p.store]
        self._meta_properties = [p for p in self._properties if p.meta]

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        for p in self._properties:
            if not hasattr(self, p.name):
                setattr(self, p.name, p.default_value)
        

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

    def _check_if_all_stored(self):
        r"""
        We check if all properties have been stored.
        """
        # We recreate self from the db and check if everything is
        # contained in the new object.
        params = {key : getattr(self, key) for key in self._params}
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

    def key_dict(self):
        r"""
        Return a dictionary where the keys are the dbkeys of ``self``` and the values are the corresponding values of ```self```.
        """
        return { key : getattr(self, key) for key in self._dbkey }

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
        coll = self._collection
        rec = coll.find_one(self.key_dict())
        return { p.name: p.from_meta(rec[p.name]) for p in self._meta_properties if rec.has_key(p.name) }

    def save_to_db(self, update = True):
        r"""
        Saves ```self``` to the database, i.e.
        save the meta record and the file in the gridfs file system.
        """
        fs = self._files
        key = self.key_dict()
        coll = self._collection
        if fs.exists(key):
            if not update:
                return True
            else:
                fid = coll.find_one(key)['_id']
                fs.delete(fid)
        # insert
        meta = self.meta_dict()
        s = dumps(self.store_dict())
        fs.put(s, **meta)

    def delete_from_db(self):
        r"""
        Deletes ```self``` to the database, i.e.
        deletes the meta record and the file in the gridfs file system.
        """
        fs = self._files
        key = self.key_dict()
        coll = self._collection
        if fs.exists(key):
            fid = coll.find_one(key)['_id']
            fs.delete(fid)
        else:
            raise IndexError("Record does not exist")

    def update_from_db(self):
        r"""
        Updates the properties of ```self``` from the database using the dbkey.
        """
        fs = self._files
        key = self.key_dict()
        if fs.exists(key):
            coll = self._collection
            fid = coll.find_one(key)['_id']
            d = loads(fs.get(fid).read())
            for p in self._properties:
                if d.has_key(p.name):
                    setattr(self, p.name, p.from_store(d[p.name]))
        else:
            raise IndexError("Record does not exist")

    def __repr__(self):
        return "WebObject"

# Define some simple data types with reasonable default values
        
class WebInt(WebProperty):

    def __init__(self, name, store=True, meta=True, default_value=int(0)):
        super(WebInt, self).__init__(name, int, store, meta, default_value)

class WebFloat(WebProperty):

    def __init__(self, name, store=True, meta=True, default_value=int(0)):
        super(WebFloat, self).__init__(name, float, store, meta, default_value)

class WebStr(WebProperty):

    def __init__(self, name, store=True, meta=True, default_value=''):
        super(WebStr, self).__init__(name, str, store, meta, default_value)

class WebDict(WebProperty):

    def __init__(self, name, store=True, meta=False, default_value=None):
        if default_value == None:
            default_value = {}
        super(WebDict, self).__init__(name, dict, store, meta, default_value)

class WebList(WebProperty):

    def __init__(self, name, store=True, meta=False, default_value=None):
        if default_value == None:
            default_value = []
        super(WebList, self).__init__(name, list, store, meta, default_value)

class WebSageObject(WebProperty):

    def __init__(self, name, datatype=SageObject, store=True, meta=False, default_value=None):
        super(WebSageObject, self).__init__(name, datatype, store, meta, default_value)

    def to_store(self, f):
        return dumps(f)

    def from_store(self, f):
        return loads(f)

class NoStoreObject(WebProperty):

    def __init__(self, name, datatype, store=False, meta=False, default_value=None):
        super(NoStoreObject, self).__init__(name, datatype, store, meta, default_value)

class WebNewformProperty(WebSageObject):

    def __init__(self, name, store=False, meta=False, default_value=None):
        super(WebNewformProperty, self).__init__(name, PowerSeries_poly, store, meta, default_value)
        
        
class WebModFormSpace_test(WebObject):

    def __init__(self, level=1, weight=12, character=1, prec=10):
        self._properties = [
            WebInt('level', default_value=level),
            WebInt('weight', default_value=weight),
            WebInt('character', default_value=character),
            WebInt('dimension'),
            WebStr('galois_orbit_name'),
            WebStr('naming_scheme', default_value='Conrey'),
            WebList('character_galois_orbit', default_value=[character]),
            WebDict('character_galois_orbit_embeddings', default_value={}),
            WebInt('character_orbit_rep'),
            WebInt('character_used_in_computation'),
            NoStoreObject('web_character_used_in_computation', WebChar),
            WebInt('cuspidal', default_value=int(1)),
            WebInt('prec', default_value=int(prec)),
            WebList('ap'),
            WebSageObject('group'),
            WebInt('sturm_bound'),
            WebDict('newforms'),
            WebList('hecke_orbit_labels'),
            WebSageObject('oldspace_decomposition'),
            WebInt('bitprec'),
            WebInt('dimension'),
            WebInt('dimension_newspace'),
            WebInt('dimension_cup_forms'),
            WebInt('dimension_modular_forms'),
            WebInt('dimension_new_cusp_forms'),
            WebFloat('version', default_value=float(emf_version))
                    ]
        super(WebModFormSpace_test, self).__init__(params=['level', 'weight', 'conrey_character'],
                                                  dbkey=['galois_orbit_name'],
                                                  collection_name='webmodformspace_test')
