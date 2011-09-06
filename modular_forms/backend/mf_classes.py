from base import getDBConnection
from modular_forms import mf_logger

class MFDataTable(object):
    def __init__(self,dbname='',**kwds):
        r"""
        For 'one-dimensiona' data sets the second skip parameter does not have a meaning but should be present anyway...

        """
        self._skip = kwds.get('skip',[])
        self._limit= kwds.get('limit',[])
        self._keys= kwds.get('keys',[])
        self._db = getDBConnection()[dbname]
        self._collection_name=kwds.get('collection','all')
        self._collection = []
        self._skip_rec=0
        self._props = {}
        if self._limit and self._skip:
            self._nrows = self._limit[0]
            if len(self._limit)>1:
                self._ncols = self._limit[1]
            else:
                self._ncols = 1
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
        mf_logger.debug("Available collections : {0}".format(self._db.collection_names()))
        mf_logger.debug("Want : {0}".format(self._collection_name))
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



class MFDisplay(object):
    r"""
    Main class for displaying Modular forms objects.
    """

    def __init__(self,dbname='',**kwds):
        self._dbname = dbname
        self.db=None
        self._keys=[]
        self._skip=[]
        self._limit=[]
        self._metadata=[]
        self._title=''
        self._cols=[]
        self.table={}
        
    def connect(self):
        self.db = base.getDBConnection()[dbname]


    def set_table():
        raise NotImplementedError,"Needs to be overwritten in subclasses!"

    def table(self):
        if not self._table:
            self.set_table() ## If unset we set it using default parameters
        return self._table    
    
