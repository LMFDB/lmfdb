import flask
import bson
import pymongo
from flask import render_template, url_for, request, redirect, make_response,send_file
from utils import *
from modular_forms.elliptic_modular_forms.backend.plot_dom import *
from modular_forms.maass_forms.picard import MWFP,mwfp_logger, mwfp
from knowledge.knowl import Knowl
from modular_forms.backend.mf_utils import *
from sage.all import dimension_new_cusp_forms,vector,dimension_modular_forms,dimension_cusp_forms,is_odd,DirichletGroup,is_even
import base

class MyDataTable(object):
    def __init__(self,dbname='',**kwds):
        self._skip = kwds.get('skip',[])
        self._limit= kwds.get('limit',[])
        self._keys= kwds.get('keys',[])
        self._db = base.getDBConnection()[dbname]
        self._collection=kwds.get('collection','all')
        if self._limit and self._skip:
            self._nrows = self._limit[0]
            self._ncols = self._limit[1]
            self._skip_rows=self._skip[0]
            self._skip_cols=self._skip[1]
        self._table=dict()
        if self._collection=='all'
        
    def ncols(self):
        return self._ncols
    def nrows(self):
        return self._rows 
    def get_element(self,i,j):
        return self._table[i][j]
    def set_table(self):
        raise NotImplementedError,"Method needs to be implemented in subclasses!"

class PicardDataTable(MyDataTable):
    def __init__(self,dbname='HTPicard',**kwds):
        MyDataTable.__init__(self,dbname,**kwds)    

    def set_table
    
