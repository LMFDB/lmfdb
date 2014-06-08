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

from lmfdb.modular_forms.elliptic_modular_forms.backend import get_files_from_gridfs, connect_to_modularforms_db


class WebObject(object):
    r"""
    A base class for the object we store in the database.
    """

    # This has to be overridden by classes that inherit from WebObject
    # Should be a dictionary of the form:
    # property: {'type': type, 'store': bool, 'meta': bool}
    # Here, store is True if this property should be stored in the database
    # and meta is true if this property should be stored in the mongodb directly as part of the meta record
    __properties = None

    def __init__(self, params, dbkey, collection_name, **kwargs):
        r"""
          Initialze self. Set default values.
          params: a dictionary - The parameters that are needed to initialize a WebObject of this type.
          dbkey: a string - the field in the database that is the unique identifier for this object
                 This can also be a list of strings if the key is a compound.
          collection_name: a database collection name to store the values in
                           We assume that the meta collection is given by collection_name.files
        """
        if self.__properties is None:
            self.__properties = {}
        self._params = params
        self._collection_name = collection_name
        self._collection = connect_to_modularforms_db(collection_name + '.files')
        self._files = get_files_from_gridfs(collection_name)
        if isinstance(dbkey, str):
            self._dbkey = [dbkey]
        elif isinstance(dbkey, list):
            self._dbkey = [dbkey]
        else:
            raise ValueError("dbkey has to be a list or a string, got {0}".format(dbkey))

        # Initialize _properties, _db_properties and _fs_properties
        self._properties = {p : self.__properties[p]['type'] for p in self.__properties.keys()}
        self._store_properties = {p : self.__properties[p]['type'] for p in self.__properties.keys() if self.__properties[p]['store']}
        self._meta_properties = {p : self.__properties[p]['type'] for p in self.__properties.keys() if self.__properties[p]['meta']}

        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        

    def _properties(self):
        r"""
         Return a dictionary with keys equal to the properties of self and values representing the data types.
        """
        return _properties
            

    def _db_properties(self):
        r"""
         Return a dictionary with keys equal to the properties of self
         which are stored in the database and values representing data types.
        """
        return _database_properties

    def _check_if_all_stored(self):
        r"""
        We check if all properties have been stored.
        """
        # We recreate self from the db and check if everything is
        # contained in the new object.
        params = {key : self.getattr(key) for key in self._params.keys()}
        f = self.__class__(**params)
        f._check_if_all_computed()
        # Now we check completeness and consistency of the meta record
        rec = f.get_meta_record()
        for p in self._meta_properties.keys():
            assert rec.has_key(p), "Missing property {0} in meta record.".format(p)
            v = f.getattr(p)
            got = type(v)
            expected = self._db_properties[p]['type']
            assert got is expected, "Property {0} has wrong type. Got {1}, expected {2}".format(got, expected)
            mf = f.property_to_meta(p)
            ms = self.property_to_meta(p)
            r = rec.getattr(p)
            assert mf == r and ms == r, \
                   "Evaluation of {0} failed. Meta record is {1} but property_to_eta returned {2}".format(p, m, r)
        return True
        
    def _check_if_all_computed(self):
        r"""
        We check if all properties in self._store_properties are set.
        """
        for p in self._store_properties.keys():
            assert hasattr(self, p), "Missing property {0}".format(p)
            v = self.getattr(p)
            got = type(v)
            expected = self._db_properties[p]['type']
            assert got is expected, "Property {0} has wrong type. Got {1}, expected {2}".format(got, expected)
            assert v is not None, "Did you store {0}? It has value {1}".format(p,v)
        return True

    def property_to_meta(self, p):
        return p

    def property_to_store(self, p):
        return p

    def key_dict(self):
        r"""
        Return a dictionary where the keys are the dbkeys of ``self``` and the values are the corresponding values of ```self```.
        """
        return { key : self.getattr(key) for key in self._dbkey }

    def meta_dict(self):
        r"""
        Return a dictionary with keys given by the keys of self._meta_properties and values given by the corresponding values of self. We also apply the function self.property_to_meta() to the values.
        """
        return { key : self.property_to_meta(key) for key in self._meta_properties }

    def store_dict(self):
        r"""
        Return a dictionary with keys given by the keys of self._store_properties and values given by the corresponding values of self. We also apply the self.property_to_store(key) function to the values.
        """
        return { key : self.property_to_store(key) for key in self._store_properties }

    def get_meta_record(self):
        r"""
          Get the meta record from the database. This is the mongodb record in collection_name.files.
        """
        coll = self._collection
        rec = coll.find_one(self.key_dict())
        return rec

    def save_to_db(self, update = True):
        r"""
        Saves ```self``` to the database, i.e.
        save the meta record and the file in the gridfs file system.
        """
        fs = self._files
        key = self.key_dict()
        if fs.exists(key) and not update:
            return True
        # insert
        meta = self.meta_dict()
        s = self.store_dict()
        fs.put(s, **meta)

    def remove_from_db(self):
        r"""
        Removes ```self``` to the database, i.e.
        delets the meta record and the file in the gridfs file system.
        """
        fs = self._files
        key = self.key_dict()
        if fs.exists(key):
            fs.delete(key)
        else:
            raise IndexError("Record does not exist")

    def update_from_db(self):
        r"""
        Updates the properties of ```self``` from the database using the dbkey.
        """
        fs = self._files
        key = self.key_dict()
        if fs.exists(key):
            d = fs.get(self.key_dict())
            for k, v in d.iteritems():
                setattr(self, k, v)
        else:
            raise IndexError("Record does not exist")
