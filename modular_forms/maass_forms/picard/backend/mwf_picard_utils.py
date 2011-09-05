#import flask
import bson
import pymongo
from flask import render_template, url_for, request, redirect, make_response,send_file
#from utils import *
from modular_forms.elliptic_modular_forms.backend.plot_dom import *
from modular_forms.maass_forms.picard import MWFP,mwfp_logger, mwfp
from modular_forms.backend.mf_utils import *
from sage.all import dimension_new_cusp_forms,vector,dimension_modular_forms,dimension_cusp_forms,is_odd,DirichletGroup,is_even

def connect_db(dbname):
    import base
    return base.getDBConnection()[dbname]

def get_collection(collection=''):
    db = connect_db()
    if collection in db.collection_names():
        return db.collection
    else:
        return None #raise ValueError,"Need Collection in :",db.collection_names()

def get_collections_info():
    db = connect_db()
    for c in db.collection_names():
        metadata=db.metadata[c]
        mwf_logger.debug("METADATA: {0}".format(metadata))
   


class MaassformsPicardDisplay(ModularFormDisplay):
    #def __init__(self,db_name,**kwds): #collection='all',skip=[0],limit=[50],keys=['Eigenvalue']):
    r"""
        Skip tells you how many chunks of data you want to skip (from the geginning) and limit tells you how large each chunk is.
        """
        
    def __init__(self,dbname='HTPicard',**kwds):
        ModularFormDisplay.__init__(self,dbname,**kwds)

    def table_browsing(**kwds):
        skip=kwds.get('skip',[0])
        if skip[0]<>0:
            set_table_browsing(self,skip=[0],limit=[50],keys=['Eigenvalue'],character=0,dimension_fun=dimension_new_cusp_forms,title='Dimension of newforms')
        return self._table
   
    def set_table_browsing(self,skip=[0],limit=[50],keys=['Eigenvalue'],character=0,dimension_fun=dimension_new_cusp_forms,title='Dimension of newforms'):
        r"""
        Table of Eigenvalues on the Picard group
        Skip tells you how many chunks of data you want to skip (from the geginning) and limit tells you how large each chunk is.
        INPUT:
        - dimension_fun should be a function which gives you the desired dimensions, as functions of level N and weight k
        - character = 0 for trivial character and 1 for Kronecker symbol.
        set to 'all' for all characters.
        """
        self._keys=keys
        self._skip=skip
        self._limit=limit
        self._metadata=[]
        self._title=''
        self._cols=[]
        self.table={}
        self._row_limit=10
        self._character = character
        mwfp_logger.debug("skip= {0}".format(self._skip))
        mwfp_logger.debug("limit= {0}".format(self._limit))
        iev  = 0 
        ev_len = self._limit[iev][1]-self._limit[iev][0]+1
        self._table={}
        self._table['rows']=[]
        self._table['col_heads']=[] #range(wt_ll,wt_ul+1)
        self._table['row_heads']=[] #range(level_ll,level_ul+1)
        emf_logger.debug("ev_range: {0} -- {1}".format(ev_ll,ev_ul))
        if character in [0,1]:
            if level_ll == level_ul:
                N=level_ll
                self._table['rowhead']='Weight'
                if character==0:
                    self._table['row_heads']=['Trivial character']
                else:
                    self._table['row_heads']=['\( \\( \frac{\cdot}{N} \\)\)']
                row=[]
                for k in range(wt_ll,wt_ul+1):
                    if character == 0 and is_odd(k):
                        continue
                    try:
                        if character==0:
                            d = dimension_fun(N,k)
                        elif character==1:
                            x = kronecker_character_upside_down(N)
                            d = dimension_fun(x,k)
                    except Exception as ex:
                        emf_logger.critical("Exception: {0}. \n Could not compute the dimension with function {0}".format(ex,dimension_fun))
                    url = url_for('emf.render_elliptic_modular_form_browsing',level=N,weight=k)
                    if not k in self._table['col_heads']:
                        self._table['col_heads'].append(k)
                    row.append({'N':N,'k':k,'url':url,'dim':d})
                self._table['rows'].append(row)                


                    
    


