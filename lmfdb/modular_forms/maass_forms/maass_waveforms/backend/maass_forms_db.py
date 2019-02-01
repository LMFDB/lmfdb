# -*- coding: utf-8 -*-
### Class for computing and storing Maass waveforms.

from lmfdb.db_backend import db
from sage.all import Integer, loads
from lmfdb.modular_forms.maass_forms.maass_waveforms import mwf_logger
logger = mwf_logger

class MaassDB(object):
    r"""
    Compute and store Maass forms
    """
    def __repr__(self):
        return "Maass waveforms database"

    def lucky(self, *args, **kwds):
        return db.mwf_forms.lucky(*args, **kwds)

    def get_Maass_forms(self, query, projection=1, limit=50, offset=0, sort=None):
        query = arg_to_search_parameters(query)
        #sorting = ['Weight', 'Level', 'Character', 'Eigenvalue']
        return db.mwf_forms.search(query, projection, limit=limit, offset=offset, sort=sort)

    def get_next_maassform_id(self, level, character, weight, eigenvalue, maass_id):
        ID = db.mwf_forms.lucky({'maass_id':maass_id}, projection='id')
        if ID is None:
            raise ValueError("Maass form not found")
        query = {'id':{'$gt':ID}, 'Level': level, 'Character': character,
                 'Eigenvalue': {'$gte':eigenvalue-(1e-6)}, 'Newform' : None, 'Weight' : weight}
        forms = db.mwf_forms.search(query, projection='maass_id', limit=1)
        return forms[0] if forms else None

    def get_prev_maassform_id(self, level, character, weight, eigenvalue, maass_id):
        ID = db.mwf_forms.lucky({'maass_id':maass_id}, projection='id')
        if ID is None:
            raise ValueError("Maass form not found")
        query = {'id':{'$lt':ID}, 'Level': level, 'Character': character,
                 'Eigenvalue': {'$lte':eigenvalue+(1e-6)}, 'Newform' : None, 'Weight' : weight}
        forms = db.mwf_forms.search(query, projection='maass_id', limit=1, sort=[('Eigenvalue',-1)])
        return forms[0] if forms else None

    def get_maassform_plot_by_id(self, maass_id):
        return db.mwf_plots.lucky({'maass_id':maass_id}, projection='plot')

    def maassform_has_plot(self, maass_id):
        return db.mwf_plots.exists({'maass_id':maass_id})

    def get_coefficients(self, data={}, verbose=0, **kwds):
        if verbose > 0:
            print "data=", data
        maass_id = data.get('maass_id')
        if maass_id is None:
            raise ValueError
        if verbose > 0:
            print "id=", maass_id
        f = db.mwf_forms.lucky({'maass_id': maass_id})
        if f is None:
            return None
        nc = f.get('Numc', 0)
        if verbose > 0:
            print "f=", f
        if nc == 0:
            return None
        cid = f.get('coeff_label', None)
        if cid is None:
            return f.get('Coefficients', None)
        ff = db.mwf_coeffs.lucky({'label':cid}, 'coefficients')
        return None if ff is None else loads(str(ff))

    def count(self, query={}):
        query = arg_to_search_parameters(query)
        return db.mwf_forms.count(query)

    def levels(self):
        return db.mwf_forms.distinct('Level')

    def weights(self, Level=0):
        query = {'Level':int(Level)} if Level > 0 else {}
        return db.mwf_forms.distinct('Weight', query)

    def characters(self, Level=0, Weight=0):
        query = {'Level':int(Level), 'Weight':int(Weight)} if Level > 0 else {}
        return db.mwf_forms.distinct('Character', query)

    # def Dirchars(self, N, parity=0, verbose=0, refresh=False):
    #     r"""
    #     Returns a list of (Conrey) indices of representatives of
    #     even or odd  Dirichlet characters mod N
    #     """
    #     f = db.char_dirichlet.lucky({'Modulus': int(N), 'Parity': int(parity), 'Conrey': int(1)})
    #     if verbose > 0:

    #         print "f=", f
    #     if f is not None:
    #         return f.get('Chars')
    #     D = DirichletGroup(N)
    #     DG = D.galois_orbits()
    #     if parity == 0:
    #         DGG = filter(lambda x: x[0].is_even(), DG)
    #     else:
    #         DGG = filter(lambda x: x[0].is_odd(), DG)
    #     l = []
    #     if verbose > 0:
    #         print "DG=", DGG
    #     for x in DGG:
    #         xi = D.list().index(x[0])
    #         xi = self.getDircharConrey(N, xi)
    #         l.append(int(xi))
    #     db.char_dirichlet.insert_many([
    #         {'Modulus': int(N), 'Chars': l, 'Parity': int(parity), 'Conrey': int(1)}])
    #     return l

    # @cached_method
    # def getDircharConrey(self, N, j):
    #     f = db.char_dirichlet.lucky({'Modulus': int(N)})
    #     if not f:
    #         Dl = DirichletGroup(N).list()
    #         res = range(len(Dl))
    #         for k in range(len(Dl)):
    #             x = Dl[k]
    #             res[k] = self.getDircharConreyFromSageChar(x)
    #         db.char_dirichlet.insert_many([{'Modulus': int(N), 'chars': res}])
    #         return res[j]
    #     else:
    #         res = f.get('chars')[j]
    #         return res

    # def getDircharConreyFromSageChar(self, x):
    #     N = x.modulus()
    #     DC = DirichletGroup_conrey(N)
    #     for c in DC:
    #         if c.sage_character() == x:
    #             return c.number()

    # @cached_method
    # def getDircharSageFromConrey(self, N, j):
    #     f = db.char_dirichlet.lucky({'Modulus': int(N)})
    #     if not f:
    #         DC = DirichletGroup_conrey(N)
    #         maxn = 0
    #         for c in DC:
    #             if c.number() > maxn:
    #                 maxn = c.number()
    #         res = range(maxn + 1)
    #         for c in DC:
    #             k = c.number()
    #             res[k] = self.getOneDircharSageFromConreyChar(c)
    #         db.char_dirichlet.insert_many([{'Modulus': int(N), 'chars': res}])
    #         return res[j]
    #     else:
    #         res = f.get('chars')[j]
    #         return res

    # def getOneDircharSageFromConreyChar(self, x):
    #     N = x.modulus()
    #     DC = DirichletGroup(N)
    #     for j in range(len(DC.list())):
    #         c = DC.list()[j]
    #         if x.sage_character() == c:
    #             return j

    #def show_data(self):
    #    r"""
    #    Show which levels, characters and weights are in the database
    #    """
    #    # print "levels=",levels
    #    res = {}
    #    for coll in self._show_collection:
    #        res[coll.name] = {}
    #        # print "name=",coll.name
    #        # print "res=",res
    #        weights = coll.distinct('Weight')
    #        for k in weights:
    #            res[coll.name][k] = {}
    #            levels = coll.find({'Weight': k}).distinct('Level')
    #            # print "levels=",levels
    #            for N in levels:
    #                res[coll.name][k][N] = {}
    #                if is_even(int(k)):
    #                    lc = self.Dirchars(N, parity=0)
    #                else:
    #                    lc = self.Dirchars(N, parity=1)
    #                for x in lc:
    #                    numr = coll.find({'Level': N, 'Weight': k, 'Character': x}).count()
    #                    num_wc = coll.find(
    #                        {'Level': N, 'Weight': k, 'Character': x, 'Numc': {"$gt": int(0)}}).count()
    #                    res[coll.name][k][N][x] = numr, num_wc
    #    resm = {}
    #    for col in res.keys():
    #        for k in res[col].keys():
    #            if k not in resm:
    #                resm[k] = {}
    #            for N in res[col][k].keys():
    #                if N not in resm[k]:
    #                    resm[k][N] = {}
    #                for x in res[col][k][N].keys():
    #                    if x not in resm[k][N]:
    #                        resm[k][N][x] = res[col][k][N][x]
    #                    else:
    #                        numrm, num_wcm = resm[k][N][x]
    #                        numr, num_wc = res[col][k][N][x]
    #                        numrm += numr
    #                        num_wcm += num_wc
    #                        resm[k][N][x] = numrm, num_wcm
    #    return resm

    def set_table(self, refresh=False):
        self.table = db.mwf_tables.lucky({})
        self.table['keylist'] = map(tuple, self.table['keylist'])
        self.table['data'] = {tuple(map(int, k.split(','))):tuple(v) for k,v in self.table['data'].iteritems()}
        #data = self.show_data()
        #table = {}
        #table['weights'] = data.keys()
        #table['levels'] = self.levels()
        #res = {}
        #nrows = 0
        #keylist = []
        #for k in table['weights']:
        #    for N in table['levels']:
        #        r = (data.get(k, {})).get(N, {}).keys()
        #        if len(r) > nrows:
        #            nrows = len(r)
        #        for x in (data.get(k, {})).get(N, {}).keys():
        #            res[(k, N, x)] = data[k][N][x]
        #            keylist.append((k, N, x))
        #table['characters'] = range(nrows)
        #table['data'] = res
        #table['keylist'] = keylist
        #table['nrows'] = 20
        #table['ncols'] = 20  # =len(table['levels'])
        #self.table = table
        #f.put(dumps(table), filename='table')

    def display_header(self, date=0):
        if date == 1:
            s = "{0:^7}{1:^7}{2:^7}{3:^20}{4:^10}{5:^7}{6:^7}{7:^15}{8:^20}{9:^15} \n".format('Level', 'Weight', 'Char', 'R', 'Even/Odd', 'Dim', 'Error', 'Num. coeff.', 'Cusp symmetries', 'Date')
        else:
            s = "{0:^7}{1:^7}{2:^7}{3:^20}{4:^10}{5:^7}{6:^7}{7:^15}{8:^20} \n".format(
                'Level', 'Weight', 'Char', 'R', 'Even/Odd', 'Dim', 'Error', 'Num. coeff.', 'Cusp symmetries')
        return s

    def display_one_record(self, x, header=1, date=0):
        N = x.get('Level', 0)
        R = x.get('Eigenvalue', 0)
        k = x.get('Weight', 0)
        ch = x.get('Character', 0)
        st = x.get('Symmetry', -1)
        evs = x.get('Cusp_evs', [])
        err = x.get('Error', 0)
        nc = x.get('Numc', 0)
        dim = x.get('Dim', 0)
        rdate = x.get('date', '')
        sdate = str(rdate).split(".")[0]
        if header == 1:
            s = self.display_header(date=1)
        else:
            s = ""
        if date == 1:
            print "rdate=", rdate
            s += "{0:^7}{1:^7}{2:^7}{3:^20.15f}{4:^10}{5:^7}{6:^3.1e}{7:^15}{8:^20}{9} \n".format(
                N, k, ch, R, st, dim, err, nc, evs, sdate)
        else:
            s += "{0:^7}{1:^7}{2:^7}{3:^20.15f}{4:^10}{5:^7}{6:^3.1e}{7:^15}{8:^20}\n".format(
                N, k, ch, R, st, dim, err, nc, evs)
        return s

    def show_last(self):
        last = db.mwf_forms.search({}, sort=[('date',-1)], limit=1)[0]
        print self.display_one_record(last, date=1)

maass_db = MaassDB()

def lowercase_dict(data):
    for k in data.keys():
        if isinstance(k, basestring):
            data[k.lower()] = data.pop(k)

def arg_to_format_parameters(data={}, **kwds):
    res = {}
    if not isinstance(data, dict):
        res['skip'] = 0
        res['limit'] = 3000
        res['collection_name'] = ''
    else:
        res['skip'] = int(data.get('skip', kwds.get('skip', 0)))
        res['limit'] = int(data.get('limit', kwds.get('limit', 50)))
        res['collection_name'] = data.get('collection_name', kwds.get('collection_name', ''))
    return res


def arg_to_search_parameters(data={}, **kwds):
    r"""
    Try to extract any search parameters we can think of.
    """
    if isinstance(data, (int, Integer)):
        data = {'Level': data}
    lowercase_dict(data)
    lowercase_dict(kwds)
    tol = data.get('tol', kwds.get('tol', 1e-6))
    R = data.get('eigenvalue', data.get('r', kwds.get('eigenvalue', kwds.get('r', None))))
    R1 = data.get('eigenvalue1', data.get('r1', kwds.get('eigenvalue1', kwds.get('r1', R))))
    R2 = data.get('eigenvalue2', data.get('r2', kwds.get('eigenvalue2', kwds.get('r2', R))))
    level = data.get('level', data.get('N', kwds.get('level', kwds.get('N', None))))
    level1 = data.get('l1', data.get('level1', kwds.get('l1', kwds.get('level1', None))))
    level2 = data.get('l2', data.get('level2', kwds.get('l2', kwds.get('level2', None))))
    ch = data.get('char', data.get('ch', kwds.get('char', kwds.get('ch', None))))
    ch1 = data.get('ch1', data.get('char1', kwds.get('ch1', kwds.get('char1', ch))))
    ch2 = data.get('ch2', data.get('char2', kwds.get('ch2', kwds.get('char2', ch))))
    wt = data.get('wt', data.get('weight', kwds.get('wt', kwds.get('weight', None))))
    wt1 = data.get('wt1', data.get('weight1', kwds.get('wt1', kwds.get('weight1', wt))))
    wt2 = data.get('wt2', data.get('weight2', kwds.get('wt2', kwds.get('weight2', wt))))
    dim = data.get('d', data.get('dim', kwds.get('d', kwds.get('dim', None))))
    d1 = data.get('d1', data.get('dim1', kwds.get('d1', kwds.get('dim1', dim))))
    d2 = data.get('d2', data.get('dim2', kwds.get('d2', kwds.get('dim2', dim))))
    numc = data.get('nc', data.get('numc', kwds.get('nc', kwds.get('numc', None))))
    nc1 = data.get('nc1', data.get('numc1', kwds.get('nc1', kwds.get('numc1', numc))))
    nc2 = data.get('nc2', data.get('numc2', kwds.get('nc2', kwds.get('numc2', numc))))
    newf = data.get('newform', data.get('newf', kwds.get('newform', kwds.get('newf', 'notset'))))  #Allow None

    maass_id = data.get('maass_id', kwds.get('maass_id'))
    find = {}
    if level is not None:
        find['Level'] = level
    elif level1 is not None or level2 is not None:
        if level1 is not None and level1 != '':
            level1 = int(level1)
            if 'Level' not in find:
                find['Level'] = {}
            find['Level']["$gte"] = level1
        if level2 is not None and level2 != '':
            level2 = int(level2)
            if 'Level' not in find:
                find['Level'] = {}
            find['Level']["$lte"] = level2
    if R1 is not None or R2 is not None:
        if R1 is not None and R1 != '':
            R1 = float(R1)
            find['Eigenvalue'] = {}
            find['Eigenvalue']["$gte"] = R1 - tol
        if R2 is not None and R2 != '':
            R2 = float(R2)
            if 'Eigenvalue' not in find:
                find['Eigenvalue'] = {}
            find['Eigenvalue']["$lte"] = R2 + tol
    if wt is not None:
        find['Weight'] = wt
    elif wt1 is not None or wt2 is not None:
        if wt1 is not None and wt1 != '':
            find['Weight'] = {}
            wt1 = float(wt1)
            find['Weight']["$gte"] = wt1
        if wt2 is not None and wt2 != '':
            if 'Weight' not in find:
                find['Weight'] = {}
            wt2 = float(wt2)
            find['Weight']["$lte"] = wt2
    if maass_id is not None:
        find['maass_id'] = maass_id

    if ch is not None:
        find['Character'] = ch
    elif ch1 is not None or ch2 is not None:
        if ch1 is not None:
            ch1 = int(ch1)
            find['Character'] = {}
            find['Character']["$gte"] = ch1
        if ch2 is not None:
            ch2 = int(ch2)
            if 'Character' not in find:
                find['Character'] = {}
            find['Character']["$lte"] = ch2

    if dim is not None:
        find['Dim'] = dim
    elif d1 is not None or d2 is not None:
        find['Dim'] = {}
        if d1 is not None and d1 != '':
            d1 = int(d1)
            find['Dim']["$gte"] = d1
        if d2 is not None and d2 != '':
            d2 = int(d2)
            find['Dim']["$lte"] = d2

    if numc is not None:
        find['Numc'] = numc
    elif nc1 is not None or nc2 is not None:
        find['Numc'] = {}
        if nc1 is not None:
            find['Numc']["$gte"] = nc1
        if nc2 is not None:
            find['Numc']["$lte"] = nc2

    if newf != 'notset':
        find['Newform'] = newf

    return find
