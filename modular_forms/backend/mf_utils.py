r"""

AUTHOR : Fredrik Stroemberg
"""

import base

class ModularFormDisplay(object):
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
    
