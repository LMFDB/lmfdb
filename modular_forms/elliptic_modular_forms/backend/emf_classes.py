r"""

Contains basic classes for displaying holomorphic modular forms.

"""
from sage.all import dimension_new_cusp_forms,vector,dimension_modular_forms,dimension_cusp_forms,is_odd,DirichletGroup,is_even
from modular_forms.backend.mf_classes import  MFDisplay,MFDataTable
emf_dbname = 'modularforms'
from utils import *
from modular_forms.elliptic_modular_forms import emf_logger, emf

def connect_db():
    import base
    return base.getDBConnection()[emf_dbname]
def connect_mf_db():
    return 




class ClassicalMFDisplay(MFDisplay):

    def __init__(self,dbname='',**kwds):
        MFDisplay.__init__(self,dbname,**kwds)
        
    
    def set_table_browsing(self,skip=[0,0],limit=[(2,16),(1,50)],keys=['Weight','Level'],character=0,dimension_fun=dimension_new_cusp_forms,title='Dimension of newforms'):
        r"""
        Table of Holomorphic modular forms spaces.
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
        self._character = character
        emf_logger.debug("skip= {0}".format(self._skip))
        emf_logger.debug("limit= {0}".format(self._limit))
        il  = self._keys.index('Level')
        iwt = self._keys.index('Weight')
        level_len = self._limit[il][1]-self._limit[il][0]+1
        level_ll=self._skip[il]*level_len+self._limit[il][0];   level_ul=self._skip[il]*level_len+self._limit[il][1]
        wt_len = self._limit[iwt][1]-self._limit[iwt][0]+1
        wt_ll=self._skip[iwt]*wt_len+self._limit[iwt][0]; wt_ul=self._skip[iwt]*wt_len+self._limit[iwt][1]
        if level_ll<1: level_l=1
        self._table={}
        self._table['rows']=[]
        self._table['col_heads']=[] #range(wt_ll,wt_ul+1)
        self._table['row_heads']=[] #range(level_ll,level_ul+1)
        emf_logger.debug("wt_range: {0} -- {1}".format(wt_ll,wt_ul))
        emf_logger.debug("level_range: {0} -- {1}".format(level_ll,level_ul))
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
            else:
                for N in range(level_ll,level_ul+1):
                    if not N in self._table['row_heads']:
                        self._table['row_heads'].append(N)
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
        elif character=='all':
            # make table with all characters.
            self._table['characters']=dict()
            if level_ll == level_ul:
                N = level_ll
                D = DirichletGroup(N)
                emf_logger.debug("I am here!")
                self._table['rowhead']='Character&nbsp;\&nbspWeight'
                for x in D:
                    xi = D.list().index(x)
                    row=[]
                    self._table['row_heads'].append(xi)
                    for k in range(wt_ll,wt_ul+1):
                        if not k in self._table['col_heads']:              
                            self._table['col_heads'].append(k)
                        try:
                            d = dimension_fun(x,k)
                        except Exception as ex:
                            emf_logger.critical("Exception: {0} \n Could not compute the dimension with function {0}".format(ex,dimension_fun))
                            d = -1
                        url = url_for('emf.render_elliptic_modular_form_space',level=N,weight=k,character=xi)
                        row.append({'N':N,'k':k,'chi':xi,'url':url,'dim':d})
                    self._table['rows'].append(row)                            
            else:
                for N in range(level_ll,level_ul+1):
                    self._table['row_heads'].append(N)
                    self._table['characters'][N]=list()
                    row=[]
                    if N==0: continue
                    D = DirichletGroup(N)
                    for k in range(wt_ll,wt_ul+1):
                        tbl=[]
                        for x in D:
                            xi = D.list().index(x)
                            if not N in self._table['characters'][N]:              
                                self._table['characters'][N].append(xi)
                            if x.is_even() and is_odd(k):
                                continue
                            if x.is_odd() and is_even(k):
                                continue
                            try:
                                d = dimension_fun(x,k)
                            except Exception as ex:
                                emf_logger.critical("Exception: {0} \n Could not compute the dimension with function {0}".format(ex,dimension_fun))
                            url = url_for('emf.render_elliptic_modular_form_browsing',level=N,weight=k)
                        if not k in self._table['col_heads']:
                            self._table['col_heads'].append(k)
                        tbl.append({'N':N,'k':k,'chi':xi,'url':url,'dim':d})
                        row.append(tbl)
                    self._table['rows'].append(row)            
                    





    def set_table_one_space(self,title='Galois orbits',**info):
        r"""
        Table of Galois orbits in a space of holomorphic modular forms.
        Skip tells you how many chunks of data you want to skip (from the geginning) and limit tells you how large each chunk is.
        INPUT:
        - dimension_fun should be a function which gives you the desired dimensions, as functions of level N and weight k
        - character = 0 for trivial character and 1 for Kronecker symbol.
          set to 'all' for all characters.
        """
        self._title=title
        self._cols=[]
        self._table={}
        self._table['rows']=[]
        self._table['col_heads']=['Label','q-expansion'] 
        self._table['row_heads']=[] #range(level_ll,level_ul+1)
        level=info.get('level','1')
        weight=info.get('weight','1')
        character=info.get('character')
        sbar=([],[],[],[],[]) #properties,parents,friends,siblings,lifts)
        (info,sbar)=set_info_for_modular_form_space(info,sbar)
         

