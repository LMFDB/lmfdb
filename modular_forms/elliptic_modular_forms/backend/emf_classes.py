r"""

Contains basic classes for displaying holomorphic modular forms.

"""
from sage.all import vector,is_odd,DirichletGroup,is_even,Gamma1,dimension_new_cusp_forms,kronecker_character_upside_down,loads,Integer
from modular_forms.backend.mf_classes import  MFDisplay,MFDataTable
emf_dbname = 'modularforms'
from utils import *
from modular_forms.elliptic_modular_forms import emf_logger, emf

def connect_db():
    import base
    return base.getDBConnection()[emf_dbname]
def connect_mf_db():
    return

class DimensionTable(object):
    def __init__(self,group=0):
        self._group=group
        self._table=dict()
        db=connect_db()
        dims=db['dimensions']
        emf_logger.debug('group={0}'.format(group))
        try:
            if group == 0:
                rec=dims.find_one({'group':'gamma0'})
                self.dimension=self.dimension_gamma0
#                emf_logger.debug('rec={0}'.format(rec))
            elif group == 1:
                rec=dims.find_one({'group':'gamma1'})
                self.dimension=self.dimension_gamma1
        except:
            emf_logger.critical('Critical error: No dimension information for group={0}'.format(group))
        self._table=loads(rec['data'])

    def dimension_gamma0(self,N=1,k=4):
        if N in self._table.keys():
            tblN=self._table[N]
            if k in tblN.keys():
                dim=tblN[k]['dimension']
                return dim
        return "n/a"

    def dimension_gamma1(self,arg1,k=3):
        emf_logger.debug('Lookup dimension for Gamma1')
        if type(arg1)==sage.modular.dirichlet.DirichletCharacter:
            N=arg1.modulus()
            character=arg1.parent().list().index(arg1)
        else:
            if type(arg1)==int or type(arg1)==Integer:
                N=arg1
                character=-1
            else:
                return -1
        emf_logger.debug('Lookup dimension for Gamma1({0}), weight={1}, character={2}'.format(N,k,character))
        if N in self._table.keys():
            #emf_logger.debug('Have information for level {0}'.format(N))
            tblN=self._table[N]
            if k in tblN.keys() and character in tblN[k].keys():
                #emf_logger.debug('Lookup dimension for Gamma1({0}), weight={1}, character={2}'.format(N,k,character))
                dim=tblN[k][character]['dimension']
                #emf_logger.debug('Have dimension for Gamma1({0}), weight={1}, character={1}'.format(N,k,character))
                return dim
        return "n/a"

    def is_in_db(self,N=1,k=4,character=0):
        #emf_logger.debug("in is_in_db: N={0},k={1},character={2}".format(N,k,character))
        if N in self._table.keys():
            #emf_logger.debug("have information for level {0}".format(N))
            tblN=self._table[N]
            if k in tblN.keys():
                #emf_logger.debug("have information for weight {0}".format(k))
                if self._group==1:
                    if character in tblN[k].keys():
                        in_db=tblN[k][character]['in_db']
                        #emf_logger.debug("information for character {0}: {1}".format(character,in_db))
                        return in_db
                else:
                    in_db=tblN[k]['in_db']
                    return in_db
        return False
        return False

class ClassicalMFDisplay(MFDisplay):

    def __init__(self,dbname='',**kwds):
        MFDisplay.__init__(self,dbname,**kwds)
        
    
    def set_table_browsing(self,skip=[0,0],limit=[(2,16),(1,50)],keys=['Weight','Level'],character=0,dimension_table=None,dimension_fun=dimension_new_cusp_forms,title='Dimension of newforms',check_db=True):
        r"""
        Table of Holomorphic modular forms spaces.
        Skip tells you how many chunks of data you want to skip (from the geginning) and limit tells you how large each chunk is.
        INPUT:
        - dimension_fun should be a function which gives you the desired dimensions, as functions of level N and weight k
        - character = 0 for trivial character and 1 for Kronecker symbol.
          set to 'all' for all characters.
        - check_db=True means, that we will only link to spaces which are in the database
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
        emf_logger.debug("character: {0}".format(character))
        self._table['characters']=dict()
        if dimension_table != None:
            dimension_fun=dimension_table.dimension
            is_data_in_db=dimension_table.is_in_db
        else:
            def is_data_in_db(N,k,character):
                return False
        # fixed level
        if level_ll == level_ul:
            N = level_ll
            # specific character =0,1
            if character == 0 or character == 1:
                self._table['rowhead']='Weight'
                if character==0:
                    self._table['row_heads']=['Trivial character']
                else:
                    self._table['row_heads']=['\( \left( \\frac{\cdot}{N} \\right) \)']
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
                    if (not check_db) or is_data_in_db(N,k,character):
                        url = url_for('emf.render_elliptic_modular_forms',level=N,weight=k, character=character)
                    else: url=''
                    if not k in self._table['col_heads']:
                        self._table['col_heads'].append(k)
                    row.append({'N':N,'k':k,'url':url,'dim':d})
                self._table['rows'].append(row)
            else:
                D = DirichletGroup(N)
                G = D.galois_orbits()
                # A security check, if we have at least weight 2 and trivial character, otherwise don't show anything
                if check_db and not is_data_in_db(N,2,0):
                    emf_logger.debug("No data for level {0} and weight 2, trivial character".format(N))
                    self._table = None
                    return None
                self._table['rowhead']='Character&nbsp;\\&nbsp;Weight'
                for xi,x in enumerate(G):
                    row=[]
                    self._table['row_heads'].append(xi)
                    for k in range(wt_ll,wt_ul+1):
                        if not k in self._table['col_heads']:
                            #emf_logger.debug("Adding to col_heads:{0}s".format(k))                            
                            self._table['col_heads'].append(k)
                        try:
                            x=x[0]
                            d = dimension_fun(x,k)
                        except Exception as ex:
                            emf_logger.critical("Exception: {0} \n Could not compute the dimension with function {1}".format(ex,dimension_fun))
                        if (not check_db) or is_data_in_db(N,k,xi):
                            url = url_for('emf.render_elliptic_modular_forms',level=N,weight=k,character=xi)
                        else:
                            url=''
                        row.append({'N':N,'k':k,'chi':xi,'url':url,'dim':d})
                    self._table['rows'].append(row)
        # fixed weight
        elif wt_ll==wt_ul:
            k=wt_ll
            self._table['rowhead']="Level"
            for N in range(level_ll,level_ul+1):
                #self._table['characters'][N]=list()       
                if N==0: continue
                row=[]
                rowdim=0
                if character != 0 and character != 1:
                    self._table['colhead']="Index of character in DirichletGroup(N)"
                    D = DirichletGroup(N)
                    G = D.galois_orbits()
                    for xi,x in enumerate(G):
                        if not xi in self._table['col_heads']:
                            self._table['col_heads'].append(xi)
                            self._table['maxRowCount']=xi+1
                        #if not N in self._table['characters'][N]:              
                        #    self._table['characters'][N].append(xi)
                        if (x.is_even() and is_odd(k)) or (x.is_odd() and is_even(k)):
                            row.append({'N':N,'k':k,'chi':xi,'url':url,'dim':0})
                            continue
                        try:
                            x=x[0]
                            d = dimension_fun(x,k)
                        except Exception as ex:
                            emf_logger.critical("Exception: {0} \n Could not compute the dimension with function {0}".format(ex,dimension_fun))
                        if (not check_db) or is_data_in_db(N,k,xi):
                            url = url_for('emf.render_elliptic_modular_forms',level=N,weight=k,character=xi)
                        else:
                            url=''
                        row.append({'N':N,'k':k,'chi':xi,'url':url,'dim':d})
                        rowdim=rowdim+d
                    if (rowdim>0):
                        self._table['rows'].append(row)
                    self._table['row_heads'].append(N)
                # specific character = 0,1
                else:
                    self._table['rowhead']='Weight'
                    if character==0:
                        self._table['row_heads']=['Trivial character']
                    else:
                        self._table['row_heads']=['\( \\( \frac{\cdot}{N} \\)\)']
                    row=[]
                    if character == 0 and is_odd(k):
                        continue
                    try:
                        if character==0:
                            d = dimension_fun(N,k)
                        elif character==1:
                            x = kronecker_character_upside_down(N)
                            d = dimension_fun(x,k)
                    except Exception as ex:
                        emf_logger.critical("Exception: {0}. \n Could not compute the dimension with function {1}".format(ex,dimension_fun))
                    if (not check_db) or is_data_in_db(N,k,character):
                        url = url_for('emf.render_elliptic_modular_forms',level=N,weight=k, character=character)
                    else:
                        url=''
                    emf_logger.debug("url= {0}".format(url))
                    if not k in self._table['col_heads']:
                        self._table['col_heads'].append(k)
                    row.append({'N':N,'k':k,'url':url,'dim':d})
                self._table['rows'].append(row)
        else:
            for k in range(wt_ll,wt_ul+1):
                if character == 0 and is_odd(k):
                        continue
                row=[]
                for N in range(level_ll,level_ul+1):
                    if not N in self._table['col_heads']:
                        self._table['col_heads'].append(N)
                    try:
                        if character==0:
                            d = dimension_fun(N,k)
                        elif character==1:
                            x = kronecker_character_upside_down(N)
                            d = dimension_fun(x,k)
                        else:
                            d = dimension_fun(N,k)
                    except Exception as ex:
                        emf_logger.critical("Exception: {0}. \n Could not compute the dimension with function {0}".format(ex,dimension_fun))
                    #emf_logger.debug("N,k,char,dim: {0},{1},{2},{3}".format(N,k,character,d))
                    if character == 0 or character == 1:
                        if (not check_db) or is_data_in_db(N,k,character):
                            url = url_for('emf.render_elliptic_modular_forms',level=N,weight=k,character=character)
                        else:
                            url=''
                    else:
                        url = url_for('emf.render_elliptic_modular_forms',level=N,weight=k)
                    if not k in self._table['row_heads']:
                        self._table['row_heads'].append(k)
                    row.append({'N':N,'k':k,'url':url,'dim':d})
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
         

