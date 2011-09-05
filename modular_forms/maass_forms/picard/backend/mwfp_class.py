import flask
import bson
import pymongo
from flask import render_template, url_for, request, redirect, make_response,send_file
from utils import *
from modular_forms.elliptic_modular_forms.backend.plot_dom import *
from modular_forms.maass_forms.picard import * #MWFP,mwfp_logger, mwfp
from modular_forms.backend.mf_utils import * 
from sage.all import dimension_new_cusp_forms,vector,dimension_modular_forms,dimension_cusp_forms,is_odd,DirichletGroup,is_even
import base

class MyDataTable(object):
    def __init__(self,dbname='',**kwds):
        r"""
        For 'one-dimensiona' data sets the second skip parameter does not have a meaning but should be present anyway...

        """
        self._skip = kwds.get('skip',[])
        self._limit= kwds.get('limit',[])
        self._keys= kwds.get('keys',[])
        self._db = base.getDBConnection()[dbname]
        self._collection_name=kwds.get('collection','all')
        self._collection = []
        self._skip_rec=0
        self._props = {}
        if self._limit and self._skip:
            self._nrows = self._limit[0]
            self._ncols = self._limit[1]
            if len(self._skip)==2:
                self._skip_rows=self._skip[0]
                self._skip_cols=self._skip[1]
            else:
                self._skip_rec = self._skip[0]
        self._table=dict()
        self._is_set=False
        self._set_collection()
        self._row_heads=[]
        self._col_heads=[]

    def ncols(self):
        return self._ncols
    def nrows(self):
        return self._nrows 
    def get_element(self,i,j):
        return self._table[i][j]
    def set_table(self,**kwds):
        raise NotImplementedError,"Method needs to be implemented in subclasses!"

    def _set_collection(self):
        mwfp_logger.debug("Available collections : {0}".format(self._db.collection_names()))
        mwfp_logger.debug("Want : {0}".format(self._collection_name))
        if self._collection_name in self._db.collection_names():
            self._collection = [self._db[self._collection_name] ]
        else:
            self._collection = list()
            for name in self._db.collection_names():
                if name in ['system.indexes','system.users']: continue
                self._collection.append(self._db[name])

    def collection(self):
        if not self._collection:
            self._set_collection()
        return self._collection
        
    def table(self):
        if not self._is_set:
            self.set_table()
        return self._table

    def row_heads(self):
        return self._row_heads

    def col_heads(self):
        return self._col_heads

    def prop(self,name=''):
        if name in self._props.keys():
            return self._props[name]
        else:
            return ''


    
class PicardDataTable(MyDataTable):
    def __init__(self,dbname='HTPicard',**kwds):
        MyDataTable.__init__(self,dbname,**kwds)    

    def set_table(self,**kwds):
        self._name = kwds.get('name','')
        self._table=dict()
        self._table=[]
        for r in range(self._nrows):
            self._table.append([])
            for k in range(self._ncols):
                self._table[r].append({})
        rec_len = self._ncols*self._nrows
        skip = rec_len*self._skip_rec
        mwfp_logger.debug("In mwfp.set_table: collections : {0}".format(self.collection()))
        mwfp_logger.debug("skip: {0} rec_len:{1}".format(skip,rec_len))
        # only have one collection here...
        c = self.collection()[0]
        finds=c.find().sort('ev',1).skip(skip).limit(rec_len)
        mwfp_logger.debug("finds: {0} no. {1}:".format(finds,finds.count()))
        i = 0
        for f in finds:
            mwfp_logger.debug("R: {0}".format(f['ev']))
            col = i % self._ncols
            row = i // self._ncols
            if row > self._nrows:
                mwfp_logger.debug("Got too large row {0} from i={1} and self._nrows={2}".format(row,i,self._nrows))
                break
            R = f['ev']; _id = f['_id']
            url = url_for('mwfp.render_picard_maass_forms_get_one',docid=str(_id))
            self._table[row][col]={'url':url,'name':R}
            #mwfp_logger.debug("table[{0}][{1}]={2}".format(row,col,self._table[r][col]))
            i = i+1
        self._is_set=True

class PicardFormTable(MyDataTable):
    r"""
    To Display one form
    """
    def __init__(self,dbname='HTPicard',**kwds):
        MyDataTable.__init__(self,dbname,**kwds)    
        self._docid = kwds.get('docid',None)
        if not self._docid:
            mwfp_logger.critical("You must supply an id!")
    
    def set_table(self,**kwds):
        self._name = kwds.get('name','')
        self._table=dict()
        self._table=[]
        self._is_set=True
        for r in range(self._nrows):
            self._table.append([])
            for k in range(self._ncols):
                self._table[r].append({})
                rec_len = self._ncols*self._nrows
        skip = rec_len*self._skip_rec
        mwfp_logger.debug("rows: {0}".format(self._nrows))
        mwfp_logger.debug("cols: {0}".format(self._ncols))
        mwfp_logger.debug("In mwfp.set_table: collections : {0}".format(self.collection()))
        mwfp_logger.debug("skip: {0} rec_len:{1}".format(skip,rec_len))
        # only have one collection here...
        c = self.collection()[0]
        f=c.find_one({'_id':self._docid})
        if not f:
            mwfp_logger.critical("You did not supply a valid id!")
            return 
        self._props['ev'] = f['ev']
        self._props['sym'] = f['sym']
        self._props['prec'] = f['prec']
        i = 0
        coeffs=list()
        self._row_heads=[]
        self._col_heads=[]
        row_min = self._nrows*skip
        col_min = self._ncols*skip
        for a,b,val in f['coef']:
            if a >= self._nrows or a < row_min:
                continue
            if b >= self._ncols or b < col_min:
                continue
            if a not in self._row_heads: self._row_heads.append(a)
            if b not in self._col_heads: self._col_heads.append(b)
            mwfp_logger.debug("a,b={0},{1}".format(a,b))
            self._table[a][b]={'value':latex(val)}
        self._row_heads.sort()
        self._col_heads.sort()
