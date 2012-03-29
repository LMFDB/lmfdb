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
        
        try:
            self._props['Character'] = f['Character']
        except:  # Trivial charcter default
            self._props['Character'] = 0
            
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



class WebMaassForm(object):
    def __init__(self,db,maassid):
        r"""
        Setup a Maass form from maassid in the database db
        of the type MaassDB.
        """
        self._db=db
        self.R=None; self.symmetry=-1
        self.weight=0; self.character=0; self.level=1
        self.table={}
        if not isinstance(maassid,(bson.objectid.ObjectId,str)):
            ids=db.find_Maass_form_id(id=maassid)
            if len(ids)==0:
                return
            mwf_logger.debug("maassid is not an objectid! {0}".format(maassid))
            maassid=ids[0]
        self._maassid=bson.objectid.ObjectId(maassid)
        mwf_logger.debug("_id={0}".format(self._maassid))
        ff=db.get_Maass_forms(id=self._maassid)
        print "ff=",ff
        if len(ff)==0:
            return
        f=ff[0]
        print "f here=",f
        self.R=f.get('Eigenvalue',None)
        self.symmetry=f.get('Symmetry',-1)
        self.weight=f.get('Weight',0)
        self.character=f.get('Character',0)
        self.cusp_evs=f.get('Cusp_evs',[])
        self.error=f.get('Error',[])
        self.level=f.get('Level',None)
        if self.R ==None or self.level==None:
            return
        
        self.coeffs=f.get('Coefficient',[])
        coeff_id=f.get('coeff_id',None)
        if self.coeffs==[] and coeff_id:
            ## Let's see if we have coefficients stored
            C = self._db.get_coefficients({"_id":self._maassid})
            self.all_coeffs=C
            nc = Gamma0(self.level).ncusps()
            if len(C.keys())==nc:
                self.coeffs = C[0]
            else:
                self.coeffs=C
        self.nc = 1 #len(self.coeffs.keys())
        if isinstance(self.coeffs,list):
            self.num_coeff=len(self.coeffs)
        elif isinstance(self.coeffs,dict):
            self.num_coeff=len(self.coeffs.keys())
        else:
            self.num_coeff=0
        self.set_table()
        
    def get_all_coeffs(self):
        return self.all_coeffs
        
    def the_character(self):
        if self.character==0:
            return "trivial"
        else:
            return self.character
    def the_weight(self):
        if self.weight==0:
            return "0"
        else:
            return self.weight
    def fricke(self):
        if len(self.cusp_evs)>0:
            return self.cusp_evs[1]
        else:
            return "undefined"
    def even_odd(self):
        if self.symmetry==1:
            return "odd"
        elif self.symmetry==0:
            return "even"
        else:
            return "undefined"
        
    def set_table(self):
        table={'nrows':self.num_coeff,
               'ncols':1}
        table['data']=[]
        if self.symmetry<>-1:
            table['negc']=0
            for n in range(self.num_coeff):
                row=[]
                for k in range(table['ncols']):
                    row.append((n,self.coeffs[n]))
                table['data'].append(row)
        else:
            table['negc']=1
            # in this case we need to have coeffs as dict.
            if not isinstance(self.coeffs,dict):
                self.table={}
                return
            for n in range(len(self.coeffs.keys()/2)):
                row=[]
                for k in range(table['ncols']):
                   cp = self.coeffs.get(n,0)
                   cn = self.coeffs.get(-n,0)
                   row.append((n,cp,cn))
                table['data'].append(row)
        self.table=table
                    
