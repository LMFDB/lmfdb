from modular_forms.backend.mf_classes import MFDataTable
from mwf_utils import *
import bson

class MaassFormTable(MFDataTable):
    r"""
    To Display one form
    """
    def __init__(self,dbname='',**kwds):
        MFDataTable.__init__(self,dbname,**kwds)    
        self._id = kwds.get('id',None)
        if not self._id:
            mwf_logger.critical("You must supply an id!")
    
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
        mwf_logger.debug("rows: {0}".format(self._nrows))
        mwf_logger.debug("cols: {0}".format(self._ncols))
        mwf_logger.debug("In mwf.set_table: collections : {0}".format(self.collection()))
        mwf_logger.debug("skip: {0} rec_len:{1}".format(skip,rec_len))
        # only have one collection here...
        c = self.collection()[0]
        mwf_logger.debug("collection: {0}".format(c))
        limit = self._nrows
        skip = self._skip_rec
        mwf_logger.debug("limit: {0}, skip: {1}".format(limit,skip))
        f=c.find_one({'_id':bson.objectid.ObjectId(self._id)}) #.skip(skip).limit(limit)
        if not f:
            mwf_logger.critical("You did not supply a valid id! Got:{0}".format(self._id))
            return 
        self._props['Eigenvalue'] = f['Eigenvalue']
        self._props['Symmetry'] = f['Symmetry']
        self._props['Weight'] = f['Weight']
        self._props['Character'] = f['Character']
        self._props['Level'] = f['Level']        
        #self._props['prec'] = f['prec']
        metadata=dict()
        MD = self._db['metadata']
        mwf_logger.debug("metadata: {0}".format(MD))
        mdfind = MD.find_one({'c_name':self._collection_name})
        mwf_logger.debug("mdfind: {0}".format(mdfind))
        for x in mdfind:
            metadata[x]=mdfind[x]
        self._props['metadata']=metadata
        numc = len(f['Coefficient'])
        mwf_logger.debug("numc: {0}".format(numc))
        self._props['numc']=numc
        if numc == 0:
            self._table=[]
            return
        limit = min(numc,self._nrows)
        self._row_heads=range(limit)
        self._col_heads=['n','C(n)']
        row_min = self._nrows*skip
        mwf_logger.debug("numc: {0}".format(numc))
        self._table=[]
        for n in range(limit):
            self._table.append([0])
        for n in range(limit):
            self._row_heads[n]=n+row_min+1 # one is fbeacuse we have a cusp form
            c = f['Coefficient'][n+row_min]
            self._table[n][0]={'value':c}
            self._table.append(list())



