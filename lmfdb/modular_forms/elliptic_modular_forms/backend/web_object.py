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
    A base class for the data types for the properties of a WebObject.
    """

    _default_value = None

    def __init__(self, name, value=None, fs_data_type=None, db_data_type=None,
                 save_to_fs=True, save_to_db=False, default_value=None, include_in_update=True,
                 required = True):
        r"""
        INPUT:
            - save_to_fs -- bool: True if this property should be stored in gridfs
            - save_to_db -- bool: True if this property should be stored in the db record (mongo)
        """
        #emf_logger.debug("In WebProperty of {0}".format(name))
        self.name = name
        if default_value is not None:
            self._default_value = default_value
        if value is None:
            value = self._default_value
            self._has_been_set = False
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
        
    def value(self):
        return self._value

    def set_value(self, val):
        self._value = val
        self._has_been_set = True
    
    def default_value(self):
        if hasattr(self, '_default_value'):
            return self._default_value
        else:
            return None

    def has_been_set(self):
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

    def set_from_fs(self, val):
        self._value = self.from_fs(val)

    def set_from_db(self, val):
        self._value = self.from_db(val)

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
    _file_key = None
    _properties = None
    _has_updated_from_db = False
    
    r"""
          _key: a list - The parameters that are needed to initialize a WebObject of this type.
          _file_key:  a string - the field in the database that is the unique identifier for this object
                 This can also be a list of strings if the key is a compound.
          _collection_name: a database collection name to use
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
        self._db_properties = self._properties.db_properties()
        self._fs_properties = self._properties.fs_properties()

        # check that the file key is contained in the _db_properties
        for k in self._file_key:
            assert k in self._db_properties, \
                   "The file key has to be contained in self._db_properties. This is not the case for {0}".format(k)

        #print hasattr(self, 'level')

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        for p in self._properties:
            #emf_logger.debug("Adding {0} : {1}".format(p.name,p))
            self.__dict__[p.name] = p

        if not hasattr(self, '_add_to_db_query'):
            self._add_to_db_query = None
        if not hasattr(self, '_add_to_fs_query'):
            self._add_to_fs_query = None
                
        if update_from_db:
            #emf_logger.debug('Update requested for {0}'.format(self.__dict__))
            emf_logger.debug('Update requested')
            try:
                self.update_from_db()
                self._has_updated_from_db = True
            except:
                # update failed, we may need to compute instead.
                # I return here since init_dynamic_properties() may need something from the database
                return 
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
            v = getattr(self, p.name)
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
        
    def file_key_dict(self):
        r"""
        Return a dictionary where the keys are the dbkeys of ``self``` and
        the values are the corresponding values of ```self```.
        """
        emf_logger.debug('key: {0}'.format(self._key))
        emf_logger.debug('properties: {0}'.format(self._properties))
        return { key : self._properties[key].to_db() for key in self._file_key }

    def key_dict(self):
        r"""
        Return a dictionary where the keys are the keys of ``self``` and
        the values are the corresponding values of ```self```.
        """

        return { key : self._properties[key].to_db() for key in self._key }

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

    def get_db_record(self):
        r"""
          Get the db record from the database. This is the mongodb record in self._collection_name.
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
        file_key = self.file_key_dict()
        coll = self._file_collection
        if fs.exists(file_key):
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
            emf_logger.debug("Inserted file t={0}, filekey={1}".format(t,file_key))
        except Exception, e:
            emf_logger.warn("Error inserting record: {0}".format(e))
        #fid = coll.find_one(key)['_id']
        # insert extended record
        if not self._use_separate_db:
            return True
        coll = self._collection
        key = self.key_dict()
        #key.update(file_key)
        #print meta_key
        dbd = self.db_dict()
        emf_logger.debug("update with dbd={0}".format(dbd.keys()))
        #meta['fid'] = fid
        if coll.find(key).count()>0:
            if not update:
                return True
            else:
                coll.update(key, dbd)
        else:
            coll.insert(dbd)
        return True
        

    def delete_from_db(self, all=False):
        r"""
        Deletes ```self``` to the database, i.e.
        deletes the meta record and the file in the gridfs file system.
        """
        coll = self._collection
        key = self.key_dict()
        if all:
            r = coll.delete_many(key) # delete meta records
        else:
            r = coll.delete_one(key) # delete meta records
        if r.deleted_count == 0:
            emf_logger.debug("There was no meta record present matching {0}".format(key))
        fs = self._files
        file_key = self.file_key_dict()
        r = self._file_collection.find_one(file_key)
        if r is None:
            raise IndexError("Record does not exist")
        fid = r['_id']
        fs.delete(fid)
                

    def update_from_db(self, ignore_non_existent = True, \
                       add_to_fs_query=None, add_to_db_query=None):
        r"""
        Updates the properties of ```self``` from the database using params and dbkey.
        """
        if add_to_db_query is None:
            add_to_db_query = self._add_to_db_query
        elif self._add_to_db_query is not None:
            q=add_to_db_query
            add_to_db_query = copy(self._add_to_db_query)
            add_to_db_query.update(q)

        if add_to_fs_query is None:
            add_to_fs_query = self._add_to_fs_query
        elif self._add_to_fs_query is not None:
            q=add_to_fs_query
            add_to_fs_query = copy(self._add_to_fs_query)
            add_to_fs_query.update(q)
            
        #emf_logger.debug("add_to_fs_query: {0}".format(add_to_fs_query))
        #emf_logger.debug("self._add_to_fs_query: {0}".format(self._add_to_fs_query))
        emf_logger.debug("db_properties: {0}".format(self._db_properties))
        if self._use_separate_db or not self._use_gridfs:
            coll = self._collection
            key = self.key_dict()
            if add_to_db_query is not None:
                key.update(add_to_db_query)
            emf_logger.debug("key: {0} for {1}".format(key,self._collection_name))
            if coll.find(key).count()>0:
                props_to_fetch = { }  #p.name:True for p in self._key}
                for p in self._db_properties:
                    if p.include_in_update and not p.name in self._fs_properties:
                        props_to_fetch[p.name] = True
#                props_to_fetch = {p.name:True for p in self._db_properties
#                                  if (p.include_in_update and not p.name in self._fs_properties)
#                                  or p.name in self._key}
                emf_logger.debug("props_to_fetch: {0}".format(props_to_fetch))                
                rec = coll.find_one(key, projection = props_to_fetch)
                for pn in props_to_fetch:
                    p = self._properties[pn]
                    if rec.has_key(pn):
                        try:
                            p.set_from_db(rec[pn])
                        except NotImplementedError:
                            continue                           
            else:
                emf_logger.critical("record with key:{0} was not found!".format(key))
                if not ignore_non_existent:
                    raise IndexError("DB record does not exist")
        if self._use_gridfs:
            fs = self._files
            file_key = self.file_key_dict()
            if add_to_fs_query is not None:
                file_key.update(add_to_fs_query)
            emf_logger.debug("add_to_fs_query: {0}".format(add_to_fs_query))
            emf_logger.debug("file_key: {0}".format(file_key))
            if fs.exists(file_key):
                coll = self._file_collection
                fid = coll.find_one(file_key)['_id']
                #emf_logger.debug("col={0}".format(coll))
                #emf_logger.debug("rec={0}".format(coll.find_one(file_key)))
                try: 
                    d = loads(fs.get(fid).read())
                except ValueError as e:
                    raise ValueError("Wrong format in database! : {0}".format(e))
                #emf_logger.debug("type(d)={0}".format(type(d)))                                
                #emf_logger.debug("d.keys()={0}".format(d.keys()))                
                for p in self._fs_properties:
                    #emf_logger.debug("p={0}, update:{1}".format(p,p.include_in_update))
                    #emf_logger.debug("d[{0}]={1}".format(p.name,type(d.get(p.name))))
                    if p.include_in_update and d.has_key(p.name):
                        p.set_from_fs(d[p.name])
            else:
                if not ignore_non_existent:
                    raise IndexError("File does not exist")

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
        super(WebDict, self).__init__(name, value, dict, dict, save_to_fs=save_to_fs, save_to_db=save_to_db, **kwargs)

    def to_fs(self):
        return number_field_to_dict(self._value)

    def from_fs(self, k):
        return number_field_from_dict(k)

    def to_db(self):
        r"""
        We store the LMFDB label of the absolute field
        in the db.
        """
        K = self._value
        
        if K.absolute_degree() == 1:
            p = 'x'
        else:
            p = K.absolute_polynomial()

        l = poly_to_field_label(p)

        return l

    def from_db(self, k):
        return k
            

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
