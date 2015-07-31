r"""

Contains basic classes for displaying holomorphic modular forms.

"""
from sage.all import vector, is_odd, DirichletGroup, is_even, Gamma1, dimension_new_cusp_forms, kronecker_character_upside_down, loads, Integer, latex
from lmfdb.modular_forms.backend.mf_classes import MFDisplay, MFDataTable
emf_dbname = 'modularforms2'
from lmfdb.utils import *
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger, emf
try:
    from dirichlet_conrey import *
except:
    emf_logger.critical("Could not import dirichlet_conrey!")
from sage.misc.cachefunc import cached_method

def connect_db():
    import lmfdb.base
    return lmfdb.base.getDBConnection()[emf_dbname]


def connect_mf_db():
    return


class DimensionTable(object):
    r"""
    Class which reads a table of dimensions from a database.

    NOTE: The assumed format of the database entry is:

    {'group':group,'data':data}
    where group is 'gamma0' or 'gamma1' and data is a dictionary
    of the form
    { N : k : i : d,t }
    where d is the dimension of cusp forms on Gamma0(N) or Gamma1(N)
    with weight k and character nr. i.
    """
    def __init__(self, group=0):
        self._group = group
        self._table = dict()
        db = connect_db()
        dims = db['dimensions']
        emf_logger.debug('dims table ={0}'.format(dims))
        emf_logger.debug('group={0}'.format(group))
        try:
            if group == 0:
                rec = dims.find_one({'group': 'gamma0'})
                self.dimension = self.dimension_gamma0
                emf_logger.debug('rec={0}'.format(rec['_id']))
            elif group == 1:
                rec = dims.find_one({'group': 'gamma1'})
                self.dimension = self.dimension_gamma1
        except:
            rec = None
            emf_logger.critical('Critical error: No dimension information for group={0}'.format(group))
        if rec<>None:
            self._table = loads(rec['data'])
        else:
            self._table = None
        if self._table <> None:
            emf_logger.debug('Have information for levels {0}'.format(self._table.keys()))
    ## We are now asuming that the entries of the table are tuples (d,t)
    ## where d is the dimension and t is True if the space is in the database (with its decomposition)
    @cached_method
    def dimension_gamma0(self, N=1, k=4):
        if self._table is None:
            return "n/a"
        if N in self._table.keys():
            if k in self._table[N]:
                dim = self._table[N][k][0][0]
                return dim
        return "n/a"
    @cached_method
    def dimension_gamma1(self, arg1, k=3):
        if self._table is None:
            return "n/a"
        if type(arg1) == sage.modular.dirichlet.DirichletCharacter:
            N = arg1.modulus()
            character = arg1.parent().galois_orbits().index(arg1.galois_orbit())
        else:
            if type(arg1) == int or type(arg1) == Integer:
                N = arg1
                character = -1
            else:
                return -1
#        emf_logger.debug(
#            'Lookup dimension for Gamma1({0}), weight={1}, character={2}'.format(N, k, character))
        if N in self._table:
            # emf_logger.debug('Have information for level {0}'.format(N))
            tblN = self._table[N]
            if k in tblN and character in tblN[k]:
                # emf_logger.debug('Lookup dimension for Gamma1({0}), weight={1},
                # character={2}'.format(N,k,character))
                dim = tblN[k][character][0]
                # character={1}'.format(N,k,character))
                return dim
        return "n/a"

    @cached_method
    def is_in_db(self, N=1, k=4, character=0):
        factors = connect_db()['Newform_factors.files']
        key = {'k': int(k), 'N': int(N), 'chi': int(character)}
        emf_logger.debug("in is_in_db: key:{0}".format(key))
        if factors.find(key).count()>0:
            t = True
        else:
            t= False
        emf_logger.debug("exist or not : {0}".format(t))
        return t
        if self._table is None:
            return "n/a"

        if N in self._table.keys():
            # emf_logger.debug("have information for level {0}".format(N))
            tblN = self._table[N]
            if k in tblN:
                # emf_logger.debug("have information for weight {0}".format(k))
                t = tblN[k].get(character,(0,False))
                in_db = t[1]
                emf_logger.debug("is_in_db: {0}".format(t)) 
                return in_db
        return False


class ClassicalMFDisplay(MFDisplay):
    r"""
    Display a table of holomorphic modular forms.

    """
    def __init__(self, dbname='', **kwds):
        emf_logger.debug("in ClassicalMFDisplay kwds={0}".format(kwds))
        MFDisplay.__init__(self, dbname, **kwds)
        import lmfdb.base
        Conn = lmfdb.base.getDBConnection()
        #if dbname == '':
        dbname = 'modularforms2'
        self._files = Conn[dbname].Newform_factors.files
        try:
            emf_logger.debug("files db : {0} with nr. of recs:{1}".format(self._files,self._files.find().count()))
        except:
            pass
            emf_logger.debug("Could not connect to pymongo!")
    def set_table_browsing(self, skip=[0, 0], limit=[(2, 16), (1, 50)], keys=['Weight', 'Level'], character=0, dimension_table=None, dimension_fun=dimension_new_cusp_forms, title='Dimension of newforms', check_db=True):
        r"""
        Table of Holomorphic modular forms spaces.
        Skip tells you how many chunks of data you want to skip (from the geginning) and limit tells you how large each chunk is.
        INPUT:
        - dimension_fun should be a function which gives you the desired dimensions, as functions of level N and weight k
        - character = 0 for trivial character and 1 for Kronecker symbol.
          set to 'all' for all characters.
        - check_db=True means, that we will only link to spaces which are in the database
        """
        self._keys = keys
        self._skip = skip
        self._limit = limit
        self._metadata = []
        self._title = ''
        self._cols = []
        self.table = {}
        self._character = character
        emf_logger.debug("skip= {0}".format(self._skip))
        emf_logger.debug("limit= {0}".format(self._limit))
        il = self._keys.index('Level')
        iwt = self._keys.index('Weight')
        level_len = self._limit[il][1] - self._limit[il][0] + 1
        level_ll = self._skip[il] * level_len + self._limit[il][0]
        level_ul = self._skip[il] * level_len + self._limit[il][1]
        wt_len = self._limit[iwt][1] - self._limit[iwt][0] + 1
        wt_ll = self._skip[iwt] * wt_len + self._limit[iwt][0]
        wt_ul = self._skip[iwt] * wt_len + self._limit[iwt][1]
        if level_ll < 1:
            level_l = 1
        self._table = {}
        self._table['rows'] = []
        self._table['col_heads'] = []  # range(wt_ll,wt_ul+1)
        self._table['row_heads'] = []  # range(level_ll,level_ul+1)
        emf_logger.debug("wt_range: {0} -- {1}".format(wt_ll, wt_ul))
        emf_logger.debug("level_range: {0} -- {1}".format(level_ll, level_ul))
        emf_logger.debug("character: {0}".format(character))
        self._table['characters'] = dict()
        if dimension_table is not None:
            dimension_fun = dimension_table.dimension
            is_data_in_db = dimension_table.is_in_db
        factors = connect_db()['Newform_factors.files']
        list_of_data = factors.distinct('hecke_orbit_label')
        #else:
        #def is_data_in_db(N, k, character):            
        #    n = self._files.find({'N':int(N),'k':int(k),'chi':int(character)}).count()
        #    emf_logger.debug("is_Data_in: N,k,character: {0} no. recs: {1} in {2}".format((N,k,character),n,self._files))
        #    return n>0
        # fixed level
        if level_ll == level_ul:
            N = level_ll
            # specific character =0,1
            if character == 0 or character == 1:
                self._table['rowhead'] = 'Weight'
                if character == 0:
                    cchi = 1 #xc = DirichletGroup_conrey(N)[1]
                else:
                    D = DirichletGroup_conrey(N)
                    for xc in D:
                        if xc.sage_character() == kronecker_character_upside_down(N):
                            cchi = xc.number()
                            break
                x = xc.sage_character()
                row = dict()
                row['head'] = "\(\chi_{" + str(N) + "}(" + str(cchi) + ",\cdot) \)"
                row['url'] = url_for('characters.render_Dirichletwebpage', modulus=N, number=cchi)
                row['cells'] = list()
                for k in range(wt_ll, wt_ul + 1):
                    if character == 0 and is_odd(k):
                        continue
                    try:
                        if character == 0:
                            d = dimension_fun(N, k)
                        elif character == 1:
                            d = dimension_fun(x, k)
                    except Exception as ex:
                        emf_logger.critical("Exception: {0}. \n Could not compute the dimension with function {0}".format(ex, dimension_fun))
                    if (not check_db) or "{0}.{1}.{2}a".format(N,k,cchi) in list_of_data: #is_data_in_db(N, k, character):
                        url = url_for(
                            'emf.render_elliptic_modular_forms', level=N, weight=k, character=character)
                    else:
                        url = ''
                    if not k in self._table['col_heads']:
                        self._table['col_heads'].append(k)
                    row['cells'].append({'N': N, 'k': k, 'url': url, 'dim': d})
                self._table['rows'].append(row)
            else:
                D = DirichletGroup(N)
                G = D.galois_orbits()
                Greps = [X[0] for X in G]
                Dc = DirichletGroup_conrey(N)
                Gcreps = dict()
                # A security check, if we have at least weight 2 and trivial character,
                # otherwise don't show anything
                #if check_db and not is_data_in_db(N, 2, 0):
                #    emf_logger.debug("No data for level {0} and weight 2, trivial character".format(N)#)
                #self._table = None
                #    return None
                Gc = dict()
                for xi, g in enumerate(G):
                    Gc[xi] = list()
                self._table['maxGalCount'] = 0
                for xc in Dc:
                    x = xc.sage_character()
                    xi = G.index(x.galois_orbit())
                    # emf_logger.debug('Dirichlet Character Conrey {0} = sage_char {1}, has
                    # Galois orbit nr. {2}'.format(xc,x,xi))
                    Gc[xi].append(xc)
                    if x == Greps[xi]:
                        Gcreps[xi] = xc
                emf_logger.debug('Gc={0}'.format(Gc))
                for xi in Gc:
                    g = Gc[xi]
                    if len(g) > self._table['maxGalCount']:
                        self._table['maxGalCount'] = len(g)
                    emf_logger.debug('xi,g={0},{1}'.format(xi, g))
                    x = Greps[xi]
                    xc = Gcreps[xi]
                    cchi = xc.number()
                    row = dict()
                    row['head'] = "\(\chi_{" + str(N) + "}(" + str(cchi) + ",\cdot) \)"
                    row['url'] = url_for('characters.render_Dirichletwebpage', modulus=N, number=cchi)
                    row['galois_orbit'] = [
                        {'chi': str(xc.number()),
                         'url': url_for('characters.render_Dirichletwebpage', modulus=N, number=cchi) }
                        for xc in g]
                    row['cells'] = []
                    for k in range(wt_ll, wt_ul + 1):
                        if not k in self._table['col_heads']:
                            # emf_logger.debug("Adding to col_heads:{0}s".format(k))
                            self._table['col_heads'].append(k)
                        try:
                            d = dimension_fun(x, k)
                        except Exception as ex:
                            emf_logger.critical("Exception: {0} \n Could not compute the dimension with function {1}".format(ex, dimension_fun))
                        if (not check_db) or  "{0}.{1}.{2}a".format(N,k,cchi) in list_of_data: #is_data_in_db(N, k, xi):
                            url = url_for(
                                'emf.render_elliptic_modular_forms', level=N, weight=k, character=xi)
                        else:
                            url = ''
                        row['cells'].append({'N': N, 'k': k, 'chi': xi, 'url': url, 'dim': d})
                    self._table['rows'].append(row)
        else:
            for k in range(wt_ll, wt_ul + 1):
                if character == 0 and is_odd(k):
                        continue
                row = []
                for N in range(level_ll, level_ul + 1):
                    if not N in self._table['col_heads']:
                        self._table['col_heads'].append(N)
                    try:
                        if character == 0:
                            d = dimension_fun(N, k)
                        elif character == 1:
                            x = kronecker_character_upside_down(N)
                            d = dimension_fun(x, k)
                        else:
                            d = dimension_fun(N, k)
                    except Exception as ex:
                        emf_logger.critical("Exception: {0}. \n Could not compute the dimension with function {0}".format(ex, dimension_fun))
                    # emf_logger.debug("N,k,char,dim: {0},{1},{2},{3}".format(N,k,character,d))
                    if character == 0 or character == 1:
                        if (not check_db) or "{0}.{1}.{2}a".format(N,k,1) in list_of_data: #is_data_in_db(N, k, character): 
                            url = url_for(
                                'emf.render_elliptic_modular_forms', level=N, weight=k, character=character)
                        else:
                            url = ''
                    else:
                        t1 =  "{0}.{1}.{2}a".format(N,k,1)
                        t2 =  "{0}.{1}.{2}a".format(N,k,2)
                        if (not check_db) or t1 in list_of_data or t2 in list_of_data: # is_data_in_db(N, k, character):
                            url = url_for('emf.render_elliptic_modular_forms', level=N, weight=k)
                        else:
                            url = ''
                    if not k in self._table['row_heads']:
                        self._table['row_heads'].append(k)
                    row.append({'N': N, 'k': k, 'url': url, 'dim': d})
                emf_logger.debug("row:{0}".format(row))
                self._table['rows'].append(row)

    def set_table_one_space(self, title='Galois orbits', **info):
        r"""
        Table of Galois orbits in a space of holomorphic modular forms.
        Skip tells you how many chunks of data you want to skip (from the geginning) and limit tells you how large each chunk is.
        INPUT:
        - dimension_fun should be a function which gives you the desired dimensions, as functions of level N and weight k
        - character = 0 for trivial character and 1 for Kronecker symbol.
          set to 'all' for all characters.
        """
        self._title = title
        self._cols = []
        self._table = {}
        self._table['rows'] = []
        self._table['col_heads'] = ['Label', 'q-expansion']
        self._table['row_heads'] = []  # range(level_ll,level_ul+1)
        level = info.get('level', '1')
        weight = info.get('weight', '1')
        character = info.get('character')
        sbar = ([], [], [], [], [])  # properties,parents,friends,siblings,lifts)
        (info, sbar) = set_info_for_modular_form_space(info, sbar)
