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
from lmfdb.modular_forms.elliptic_modular_forms.backend import connect_to_modularforms_db
from lmfdb.WebNumberField import field_pretty
from lmfdb.utils import web_latex_split_on_pm

from sage.rings.power_series_poly import PowerSeries_poly
from sage.all import SageObject,dumps,loads, QQ, NumberField, latex

import gridfs
import re
from datetime import datetime

class WebProperty(object):
    r"""
    A base class for the data types for the properties of a WebObject.
    """

    _default_value = None

    def __init__(self, name, value=None, fs_data_type=None, db_data_type=None,
                 save_to_fs=True, save_to_db=False, default_value=None, include_in_update=True,
                 required = True, extend_fs_with_db = False):
        r"""
        INPUT:
            - save_to_fs -- bool: True if this property should be stored in gridfs
            - save_to_db -- bool: True if this property should be stored in the db record (mongo)
        """
        #emf_logger.debug("In WebProperty of {0}".format(name))
        self._db_value_has_been_set = False
        self.name = name
        if default_value is not None:
            self._default_value = default_value
        if value is None:
            value = self._default_value
            self._has_been_set = False
            self._db_value_has_been_set = False
        else:
            self._has_been_set = True
        self._value = value
        # default to str
        if fs_data_type is not None:
            self.fs_data_type = fs_data_type
        else:
            self.fs_data_type = str
            
        if db_data_type is not None:
            self.db_data_type = db_data_type
        else:
            self.db_data_type = str
        self.save_to_fs = save_to_fs
        self.save_to_db = save_to_db

        self.include_in_update = include_in_update

        self.required = required

        self._extend_fs_with_db = extend_fs_with_db
        
    def value(self):
        return self._value

    def set_value(self, val):
        self._value = val
        self._has_been_set = True

    def set_db_value(self, val):
        self._db_value = val
        self._db_value_has_been_set = True
    
    def default_value(self):
        if hasattr(self, '_default_value'):
            return self._default_value
        else:
            return None

    def has_been_set(self, s = None):
        if not s is None:
            self._has_been_set = s
        else:
            return self._has_been_set

    def to_db(self):
        r"""
          Returns the value of self in the db_data_type which then can be stored in the db.
        """
        val = self._value
        #print val, self.name
        if val is not None:
            return self.db_data_type(val)
        else:
            return None
    
    def to_fs(self):
        r"""
          Returns the value of self in the fs_data_type which then can be stored in gridfs.
        """
        val = self._value
        if val is not None:
            try:
                return self.fs_data_type(val)
            except:
                raise TypeError("Error with value {0}".format(val))
        else:
            return None

    def from_fs(self, val):
        return val

    def from_db(self, val):
        return val

    def extend_from_db(self):
        pass

    def set_from_fs(self, val):
        self.set_value(self.from_fs(val))
        if self._extend_fs_with_db:
            self.extend_from_db()
        self.set_extended_properties()

    def set_from_db(self, val):
        self._value = self.from_db(val)
        self.set_db_value(self.from_db(val))
        self.set_extended_properties()

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

    def db_properties(self):
        return WebProperties([p for p in self if p.save_to_db])

    def fs_properties(self):
        return WebProperties([p for p in self if p.save_to_fs])

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
    _file_key = None
    _file_key_multi = None
    _properties = None
    _has_updated_from_db = False
    _has_updated_from_fs = False
    _add_to_db_query = None
    _add_to_fs_query = None
    _sort = None
    _sort_files = None
    
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
                            We assume that the gridfs collection is given by 'collection_name.files'
    """

    _properties = WebProperties()

    @staticmethod
    def connect_to_db(coll=''):
        return connect_to_modularforms_db(coll)

    from sage.all import cached_method
    @classmethod
    @cached_method
    def get_files_from_gridfs(cls, coll):
        C = cls.connect_to_db()
        return gridfs.GridFS(C,coll)

    @classmethod
    def _find_document_in_db_collection(cls,search={},**kwds):
        r"""
        Searches the database for fields matching values in a dict containing
        values for the keys (or using keywords) in self._key without constructing the object. 
        """
        coll = cls.connect_to_db(cls._collection_name)
        search_pattern = { key : search[key] for key in search.keys() if key in cls._key }
        search_pattern.update(kwds) ## add keywords
        return coll.find(search_pattern) 
    
    def __init__(self,
                 use_separate_db = True,
                 use_gridfs = True,
                 update_from_db=False,
                 init_dynamic_properties=True,
                 **kwargs):
        r"""
        INPUT:
          - use_gridfs -- bool: If True we use gridfs to store (large) properties of self
          - use_separate_db -- bool: Only valid if use_gridfs.
                          If True, then we use the collection corresponding to self._collection_name
                          to store (relatively small, searchable) data instead of the gridfs collection (collection_name.files).
                          This is for instance useful if we would like to have several records in the db
                          pointing to the same file.
          - update_from_db -- bool: If True, we update self from db during init.
        """
        emf_logger.debug('Create web object!')
        # check consistency of parameters
        if not use_gridfs and use_separate_db:
            raise ValueError("Inconsistent parameters: do set use_seperate_db and not use_gridfs")

        # This has to be overridden by classes that inherit from WebObject
        # Should be a list of WebProperty objects
        if not hasattr(self, '_properties') or self._properties is None:
            self._properties = WebProperties()

        # set the collections and the gridfs
        self._use_gridfs = use_gridfs
        if use_gridfs:
            self._file_collection = self.connect_to_db(self._collection_name + '.files')
        self._use_separate_db = use_separate_db
        self._collection = self.connect_to_db(self._collection_name)
        emf_logger.debug('Connected to db!')
        if use_gridfs and not use_separate_db:
                self._collection = self._file_collection
                #self.connect_to_db(self._collection_name + '.files')
        emf_logger.debug('Connected to db 2!')                
#        self._files = self.get_files_from_gridfs(self._collection_name)
        self._files = self.get_files_from_gridfs(self._collection_name)
        emf_logger.debug('Connected to db and got files!')
        # Initialize _db_properties and _db_properties to be easily accesible
        for k in self._key:
            self._properties[k].save_to_db = True
        #for k in self._file_key:
        #    self._properties[k].save_to_fs = True
        self._db_properties = self._properties.db_properties()
        self._fs_properties = self._properties.fs_properties()

        #print hasattr(self, 'level')

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        for p in self._properties:
            #emf_logger.debug("Adding {0} : {1}".format(p.name,p))
            self.__dict__[p.name] = p

        if self._sort is None:
            self._sort = []
        if self._sort_files is None:
            self._sort_files = []
        emf_logger.debug("For {} have self._add_to_fs_query = {}".format(self.__class__, self._add_to_fs_query))
                
        if update_from_db:
            #emf_logger.debug('Update requested for {0}'.format(self.__dict__))
            emf_logger.debug('Update requested')
            #try:
            self.update_from_db(add_to_fs_query = self._add_to_fs_query, add_to_db_query = self._add_to_db_query)
            #except Exception as e:
            #    raise RuntimeError(str(e))
        #emf_logger.debug('init_dynamic_properties will be called for {0}'.format(self.__dict__))
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
        
    def db_properties(self):
        r"""
         Return a dictionary with keys equal to the properties of self and values representing the data types.
        """
        return self._db_properties
            

    def fs_properties(self):
        r"""
         Return a dictionary with keys equal to the properties of self
         which are stored in the file system (gridfs) and values representing the corresponding WebProperties.
        """
        return self._fs_properties

    def _check_if_all_saved(self):
        r"""
         We check if all properties have been saved.
         In gridfs and in the db record.
        """
        # We recreate self from the db and check if everything is
        # contained in the new object.
        params = { k : getattr(self, k) for k in self._key }
        emf_logger.debug("in check. params={0}".format(params))
        f = self.__class__(**params)
        f.update_from_db()
        f._check_if_all_computed()
        # Now we check completeness and consistency of the db record
        rec = f.get_db_record()
        for p in self._db_properties:
            assert rec.has_key(p.name), "Missing property {0} in meta record.".format(p)
            v = getattr(f, p.name)
            dbf = f._properties[p.name].to_db()
            got = type(dbf)
            expected = p.db_data_type
            assert got is expected, "Property {0} has wrong type. Got {1}, expected {2}".format(p.name, got, expected)
            s = getattr(self, p.name)
            assert v == s, "Error restoring Property {0}. Got {1}, expected {2}".format(p.name, v, s)
            dbs = p.to_db()
            r = rec[p.name]
            assert dbf == r and dbs == r, \
                   "Evaluation of {0} failed. DB record is {1}, property.to_db() returned {2} and the restored object property.to_db() returns {3}".format(p, r, dbs, dbf)
        for p in self._fs_properties:
            fsf = f._properties[p.name].to_fs()
            got = type(fsf)
            expected = p.fs_data_type
            assert got is expected, "Property {0} has wrong type. Got {1}, expected {2}".format(p.name, got, expected)
            fss = p.to_fs()
            assert dbs == fss, \
                   "Evaluation of {0} failed. Property.to_fs() returned {1} and the restored object property.to_fs() returns {2}".format(p, fsf, fss)
        return True
        
    def _check_if_all_computed(self):
        r"""
        We check if all properties in self._properties are set correctly.
        """
        for p in self._properties:
            if p.required:
                assert hasattr(self, p.name), "Missing property {0}".format(p)
            got = type(self._properties[p.name].to_fs())
            expected = p.fs_data_type
            assert p.has_been_set(), "Did we compute {0}? It has not been set yet.".format(p.name)
            assert got is expected, "Property {0} has wrong type. Got {1}, expected {2}".format(p.name, got, expected)
        return True

    def init_dynamic_properties(self):
        r"""
        This function is called after __init__
        and should be overriden to initialize
        any properties of self that should be generated on the fly.
        """
        pass
        
    def file_key_dict(self, include_multi = True):
        r"""
        Return a dictionary where the keys are the dbkeys of ``self``` and
        the values are the corresponding values of ```self```.
        """
        emf_logger.debug('key: {0}'.format(self._key))
        #emf_logger.debug('properties: {0}'.format(self._properties))
        keys = copy(self._file_key)
        if include_multi and self._file_key_multi is not None:
            keys +=  self._file_key_multi
        return { key : self._properties[key].to_db() for key in keys }

    def key_dict(self, include_multi = True):
        r"""
        Return a dictionary where the keys are the keys of ``self``` and
        the values are the corresponding values of ```self```.
        """
        keys = copy(self._key)
        if include_multi and self._key_multi is not None:
            keys +=  self._key_multi
        return { key : self._properties[key].to_db() for key in keys}

    def db_dict(self):
        r"""
        Return a dictionary with keys given by the keys of self._db_properties
        and values given by the corresponding values of self. We also apply the function to_db() to the values
        to assure that we have the right data type (this is handy for complex conversions as well).
        """
        return { p.name : p.to_db() for p in self._db_properties }

    def fs_dict(self):
        r"""
        Return a dictionary with keys given by the keys of self._fs_properties
        and values given by the corresponding values of self. We also apply the to_fs() function to the values
        to assure that we have the right data type (this is handy for complex conversions as well).
        """
        return { p.name : p.to_fs() for p in self._fs_properties }

    def get_db_record(self, add_to_db_query = None, projection = None):
        r"""
          Get the db record from the database. This is the mongodb record in self._collection_name.
        """
        coll = self._collection
        if add_to_db_query is None:
            add_to_db_query = self._add_to_db_query
        elif self._add_to_db_query is not None:
            q=add_to_db_query
            add_to_db_query = copy(self._add_to_db_query)
            add_to_db_query.update(q)
        if add_to_db_query is not None:
            key = self.key_dict()
            key = key.update(add_to_db_query)
        else:
            key = self.key_dict()
        sort = self._sort
        emf_logger.debug("add_to_db_query: {0}".format(add_to_db_query))
        emf_logger.debug("key: {0} coll={1}".format(key,self._collection))
        if projection is not None:
            rec = coll.find_one(key, sort = sort, projection = projection)
        else:
            rec = coll.find_one(key, sort = sort)
        return rec

    def get_file(self, add_to_fs_query=None, get_all=False, meta_only=False, ignore_multi_if_failed=True):
        r"""
          Get the file(s) from gridfs.
        """
        if not self._use_gridfs:
            raise ValueError('We do not use gridfs for this class.')
        fs = self._files
        emf_logger.debug("{} self._add_to_fs_query: {}".format(self.__class__, self._add_to_fs_query))
        if add_to_fs_query is None:
            add_to_fs_query = self._add_to_fs_query
        elif self._add_to_fs_query is not None:
            q=add_to_fs_query
            add_to_fs_query = copy(self._add_to_fs_query)
            add_to_fs_query.update(q)
        file_key = self.file_key_dict(include_multi = not get_all)
        if add_to_fs_query is not None and not get_all:
            file_key.update(add_to_fs_query)
        sort = self._sort_files
        emf_logger.debug("{} add_to_fs_query: {}".format(self.__class__, add_to_fs_query))
        emf_logger.debug("file_key: {0} fs={1}".format(file_key,self._file_collection))
        results = []
        if fs.exists(file_key):
            coll = self._file_collection
            if get_all:
                files = coll.find(file_key, sort = sort)
            else:
                files = [coll.find_one(file_key, sort = sort)]
            for m in files:
                fid = m['_id']
                #emf_logger.debug("col={0}".format(coll))
                #emf_logger.debug("rec={0}".format(coll.find_one(file_key)))
                if not meta_only:
                    try: 
                        d = loads(fs.get(fid).read())
                        results.append((d,m))
                    except ValueError as e:
                        raise ValueError("Wrong format in database! : {0} coll: {1} rec:{2}".format(e,coll,m))
                else:
                    results.append(m)
        else:
            raise IndexError("File not found with file_key = {}".format(file_key))
        emf_logger.debug("len(results) = {}".format(len(results)))
        if len(results) == 1 and not get_all:
            return results[0]
        else:
            return results

    def get_files(self, add_to_fs_query=None):
        if self._file_key_multi is None or add_to_fs_query is not None:
            l = self.get_file(add_to_fs_query)
            if isinstance(l,dict):
                l = [l]
            return l
        else:
            return self.get_file(add_to_fs_query, get_all=True)

    def get_file_list(self, add_to_fs_query=None):
        if self._file_key_multi is None or add_to_fs_query is not None:
            l = self.get_file(add_to_fs_query, meta_only=True)
            if isinstance(l,dict):
                l = [l]
            return l
        else:
            return self.get_file(add_to_fs_query, get_all=True, meta_only=True)

    @classmethod
    def authorize(cls):
        r"""
        Need to be authorized to insert data
        """
        from os.path import dirname, join
        pw_filename = join(dirname(dirname(__file__)), "password")
        user = 'editor'
        password = open(pw_filename, "r").readlines()[0].strip()
        emf_logger.debug("Authenticating user={0} password={1}".format(user,password))
        cls.connect_to_db().authenticate(user,password)
        emf_logger.debug("Authenticated with user:{0} and pwd:{1}".format(user,password))

    @classmethod
    def logout(cls):
        r"""
        Logout authorized user.
        """
        import lmfdb.base
        C = cls.connect_to_db()
        C.logout()
        # log back in with usual read-only access
        lmfdb.base._init(lmfdb.base.dbport)
        

    def has_updated_from_db(self):
        return self._has_updated_from_db

    def has_updated_from_fs(self):
        return self._has_updated_from_fs

    def has_updated(self):
        return self._has_updated_from_db and (self._has_updated_from_fs or not self._use_gridfs)
        
    def save_to_db(self, update = True):
        r"""
         Saves ```self``` to the database, i.e.
         save the meta record and the file in the gridfs file system.
        """
        import pymongo
        from pymongo.errors import OperationFailure
        fs = self._files
        try: 
            self.authorize()
        except OperationFailure:
            emf_logger.critical("Authentication failed. You are not authorized to save data to the database!")
            return False
        if self._use_gridfs:
            file_key = self.file_key_dict()
            coll = self._file_collection
            if fs.exists(file_key):
                emf_logger.debug("File exists with key={0}".format(file_key))
                if not update:
                    return True
                else:
                    fid = coll.find_one(file_key, projection=['_id'])['_id']
                    fs.delete(fid)
                    emf_logger.debug("Deleted file with fid={0}".format(fid))
            # insert
            s = dumps(self.fs_dict())
            if not self._use_separate_db:
                file_key.update(self.db_dict())
            try:
                t = fs.put(s, **file_key)
                emf_logger.debug("Inserted file with filekey={1}".format(t,file_key))
            except Exception, e:
                emf_logger.debug("Could not insert file with filekey={1}".format(s,file_key))
                emf_logger.warn("Error inserting record: {0}".format(e))
            #fid = coll.find_one(key)['_id']
            # insert extended record
            if not self._use_separate_db:
                self.logout()
                return True
        coll = self._collection
        key = self.key_dict()
        #key.update(file_key)
        #print meta_key
        dbd = self.db_dict()
        ## Add modification data
        dbd['modification_date'] = datetime.utcnow()
        #emf_logger.debug("update with dbd={0} and key:{1}".format(dbd,key))
        #meta['fid'] = fid
        if coll.find(key).count()>0:
            if not update:
                self.logout()
                return True
            else:
                if pymongo.version_tuple[0]>2:
                    coll.update_one(key,{"$set":dbd},upsert=True)
                else:
                    coll.update(key,{"$set":dbd},upsert=True)
        else:
            coll.insert(dbd)
        self.logout()
        return True
        

    def delete_from_db(self, delete_all=False):
        r"""
        Deletes ```self``` to the database, i.e.
        deletes the meta record and the file in the gridfs file system.
        """
        coll = self._collection
        key = self.key_dict()
        if self._use_separate_db or not self._use_gridfs:
            if delete_all:
                r = coll.delete_many(key) # delete meta records
            else:
                r = coll.delete_one(key) # delete meta record
                if r.deleted_count == 0:
                    emf_logger.debug("There was no meta record present matching {0}".format(key))
        files = self.get_file_list() if delete_all else [self.get_file(meta_only=True)]
        for f in files:
            try:
                self._files.delete(f['_id'])
            except:
                raise IndexError("Error deleting file {}".format(f['_id']))

    def update_db_properties_from_dict(self, d):
        for p in self.db_properties():
            pn = p.name
            if d.has_key(pn):
                try:
                    p.set_from_db(d[pn])
                    if not p.name in self._fs_properties:
                        p.has_been_set(True)
                except NotImplementedError:
                    continue
        return True

    def update_fs_properties_from_dict(self, d):
        for p in self.fs_properties():
            pn = p.name
            if d.has_key(pn):
                try:
                    p.set_from_fs(d[pn])
                    p.has_been_set(True)
                except NotImplementedError:
                    continue
        return True
    
    def update_from_db(self, ignore_non_existent = True, \
                       add_to_fs_query=None, add_to_db_query=None, \
                       update_from_fs=True, include_only=None):
        r"""
        Updates the properties of ```self``` from the database using params and dbkey.
        """
        self._has_updated_from_db = False
        self._has_updated_from_fs = False
            
        #emf_logger.debug("add_to_fs_query: {0}".format(add_to_fs_query))
        #emf_logger.debug("self._add_to_fs_query: {0}".format(self._add_to_fs_query))
        emf_logger.debug("db_properties: {0}".format(self._db_properties))
        succ_db = False
        succ_fs = False
        if self._use_separate_db or not self._use_gridfs:
            props_to_fetch = { }  #p.name:True for p in self._key}
            for p in self._db_properties:
                if p.include_in_update \
                  and (not p.name in self._fs_properties or p._extend_fs_with_db) \
                  and (include_only is None or p.name in include_only):
                    props_to_fetch[p.name] = True
                    p.has_been_set(False)
            emf_logger.debug("properties to fetch: {}".format(props_to_fetch))
            try:
                rec = self.get_db_record(add_to_db_query, projection = props_to_fetch)
                for pn in props_to_fetch:
                    p = self._properties[pn]
                    if rec.has_key(pn):
                        try:
                            p.set_from_db(rec[pn])
                            if not p.name in self._fs_properties:
                                p.has_been_set(True)
                        except NotImplementedError:
                            continue
                succ_db = True
            except Exception as e:
                if not ignore_non_existent:
                    raise IndexError("DB record does not exist")
                emf_logger.critical("Error occured while updating from db: {}".format(e))
                succ_db = False
        if self._use_gridfs and update_from_fs:
            try:
                d, m = self.get_file(add_to_fs_query)
                self._file_record_length = m['length']
                for p in self._fs_properties:
                    #emf_logger.debug("p={0}, update:{1}".format(p,p.include_in_update))
                    #emf_logger.debug("d[{0}]={1}".format(p.name,type(d.get(p.name))))
                    if p.include_in_update and d.has_key(p.name):
                        #emf_logger.debug("d[{0}]={1}".format(p.name,type(d.get(p.name))))
                        p.has_been_set(False)
                        p.set_from_fs(d[p.name])
                    if p.include_in_update and m.has_key(p.name):
                        #emf_logger.debug("d[{0}]={1}".format(p.name,type(m.get(p.name))))
                        p.has_been_set(False)
                        p.set_from_fs(m[p.name])
                succ_fs = True
                emf_logger.debug("loaded from fs")
            except IndexError as e:
                emf_logger.debug(e)
                if not ignore_non_existent:
                    raise IndexError(e)
                succ_fs = False
        if succ_db: self._has_updated_from_db = True
        if succ_fs: self._has_updated_from_fs = True

    def properties_as_dict(self):
        r"""
          Return all WebProperties of ```self``` in a dict.
        """
        return self._properties.as_dict()

    @classmethod
    def find(cls, query={}, projection = None, sort=[], gridfs_only=False):
        r'''
          Search the database using ```query``` and return
          an iterator over the set of matching objects of this WebObject
        '''
        if gridfs_only: # stupid hack, should be a property of the class or standard that way
            coll = cls.connect_to_db(cls._collection_name).files
        else:
            coll = cls.connect_to_db(cls._collection_name)
        for s in coll.find(query, sort=sort, projection=projection):
            s.pop('_id')
            try:
                k = {key:s[key] for key in cls._key}
                o = cls(update_from_db=False, init_dynamic_properties=False, **k)
                o.update_db_properties_from_dict(s)
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
    _key = ['id']
    _file_key = ['id']

    def __init__(self, **kwargs):

        self._properties = WebProperties([WebInt('test_property'), WebInt('id')])
        super(WebObjectTest, self).__init__(self, **kwargs)
    

# Define some simple data types with reasonable default values


class WebDate(WebProperty):
    _default_value = datetime.now()

    def __init__(self, name, value=None, save_to_fs=False, save_to_db=True, **kwargs):
        date_fn = lambda t: datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
        super(WebDate, self).__init__(name, value, date_fn, date_fn, save_to_fs=save_to_fs, save_to_db=save_to_db, **kwargs)
    
    
class WebInt(WebProperty):

    _default_value = int(0)

    def __init__(self, name, value=None, save_to_fs=False, save_to_db=True, **kwargs):
        super(WebInt, self).__init__(name, value, int, int, save_to_fs=save_to_fs, save_to_db=save_to_db, **kwargs)
        #print self.__class__

class WebBool(WebProperty):

    _default_value = True

    def __init__(self, name, value=None, save_to_fs=False, save_to_db=True, **kwargs):
        super(WebBool, self).__init__(name, value, int, int, save_to_fs=save_to_fs, save_to_db=save_to_db, **kwargs)
        #print self.__class__

class WebFloat(WebProperty):

    _default_value = float(0)

    def __init__(self, name, value=None, save_to_fs=False, save_to_db=True, **kwargs):
        super(WebFloat, self).__init__(name, value, float, float, save_to_fs=save_to_fs, save_to_db=save_to_db, **kwargs)

class WebStr(WebProperty):

    _default_value = ''

    def __init__(self, name, value=None, save_to_db=True, save_to_fs=False, **kwargs):
        super(WebStr, self).__init__(name, value, str, str, save_to_fs=save_to_fs, save_to_db=save_to_db, **kwargs)

class WebDict(WebProperty):

    def __init__(self, name, value=None, save_to_fs=True, save_to_db=False, **kwargs):
        self._default_value = {}
        super(WebDict, self).__init__(name, value, dict, dict, save_to_fs=save_to_fs, save_to_db=save_to_db, **kwargs)

class WebList(WebProperty):

    def __init__(self, name, value=None, save_to_fs=True, save_to_db=False, **kwargs):
        self._default_value = []
        super(WebList, self).__init__(name, value, list, list, save_to_db=save_to_db, save_to_fs=save_to_fs, **kwargs)

class WebSageObject(WebProperty):

    _default_value = None

    def __init__(self, name, value=None, datatype=SageObject, save_to_fs=True,
                 save_to_db=False, **kwargs):
        super(WebSageObject, self).__init__(name, value, fs_data_type=datatype, db_data_type=str, \
                                            save_to_db=save_to_db, save_to_fs=save_to_fs, **kwargs)

    def to_fs(self):
        return dumps(self._value)

    def from_fs(self, f):
        return loads(f)

class WebPoly(WebProperty):
    def __init__(self, name, value=None, save_to_fs=True, save_to_db=True,
                 **kwargs):
        super(WebPoly, self).__init__(name, value, fs_data_type=PowerSeries_poly, \
                                      db_data_type=str, save_to_fs=save_to_fs, save_to_db=save_to_db, **kwargs)

    def to_fs(self):
        f = self._value
        if f is None:
            return None
        return f
    
    def from_fs(self, f):
        return f

    def to_db(self):
        return str(self._value)

    def from_db(self, f):
        return f

class WebNoStoreObject(WebProperty):

    def __init__(self, name, value=None, **kwargs):
        super(WebNoStoreObject, self).__init__(name, value, save_to_fs=False, save_to_db=False, **kwargs)


class WebNumberField(WebDict):
    
    def __init__(self, name, value=None,
                 save_to_fs=True, save_to_db=True, **kwargs):
        self._default_value = QQ
        ## set default values
        self._db_value = None
        self.lmfdb_label = ''
        self.lmfdb_url = ''
        self.lmfdb_pretty = ''
        super(WebDict, self).__init__(name, value, dict, dict, save_to_fs=save_to_fs, save_to_db=save_to_db, extend_fs_with_db = 'lmfdb_label', **kwargs)

    def to_fs(self):
        return number_field_to_dict(self._value)

    def from_fs(self, k):
        return number_field_from_dict(k)

    def to_db(self):
        r"""
        We store the LMFDB label of the absolute field in the db.
        """

        K = self._value
        if hasattr(K, "lmfdb_label"):
            return K.lmfdb_label
        
        if self._db_value_has_been_set and not self._db_value is None:
            return self._db_value
        else:
            return ''

    def from_db(self, k):
        return k

    def extend_from_db(self):
        setattr(self._value, "lmfdb_label", self._db_value)
        if not self._db_value is None and self._db_value != '':
            label = self._db_value
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
            
    def set_extended_properties(self):
        if self._has_been_set:
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
