import flask
import bson
import lmfdb.base
import pymongo
from flask import render_template, url_for, request, redirect, make_response, send_file
from lmfdb.utils import *
from lmfdb.modular_forms.elliptic_modular_forms.backend.plot_dom import *
from lmfdb.modular_forms.maass_forms.maass_waveforms import MWF, mwf_logger, mwf
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db import MaassDB
from lmfdb.modular_forms.backend.mf_utils import my_get
# from knowledge.knowl import Knowl
# from psage.modform.maass.lpkbessel import *
# build extensions

#try:
#    #  from modular_forms.maass_forms.backend.lpkbessel import *
#    from lpkbessel import *
#except Exception as ex:
#    mwf_logger.critical("maass_waveforms/views/mwf_utils.py: couldn't load backend. Exception: '%s' To enable full Maass waveform functionality: compile the cython file lpkbessel.pyx with sage -c create_local_so('lpkbessel.pyx')" % ex)
    # try:
    #  # Builds the kbessel extension build_ext --inplace $*
    #  execfile("setup.py")
    # except Exception as ex1:

mwf_dbname = 'MaassWaveForm'
available_collections = ['FS', 'HT']

_DB = None


def connect_db():
    global _DB
    if _DB is None:
        # NB although base.getDBConnection().PORT works it gives the
        # default port number of 27017 and not the actual one!
        if pymongo.version_tuple[0] < 3:
            host = lmfdb.base.getDBConnection().host
            port = lmfdb.base.getDBConnection().port
        else:
            host, port = lmfdb.base.getDBConnection().address
        _DB = MaassDB(host=host, port=port, show_collection='all')
    return _DB

# def connect_db():
#    import base
#    return base.getDBConnection()[mwf_dbname]


def get_collection(collection=''):
    DB = connect_db()
    for i in range(len(DB._show_collection)):
        coll = DB._show_collection[i]
        if collection == coll.name:
            return coll
    else:
        return None  # raise ValueError,"Need Collection in


def get_args_mwf(**kwds):
    get_params = ['level', 'weight', 'character', 'id', 'db', 'search',
                  'search_all', 'eigenvalue', 'collection', 'browse',
                  'ev_skip', 'ev_range', 'maass_id', 'skip', 'limit',
                  'level_range', 'weight_range', 'ev_range', 'download']
    defaults = {'level': 0, 'weight': -1, 'character': 0, 'skip': 0, 'limit': 2000,
                'maass_id': None, 'search': None, 'collection': None,
                'eigenvalue': None, 'browse': None}
    if request.method == 'GET':
        req = to_dict(request.args)
        #print "req:get=", request.args
    else:
        req = to_dict(request.form)
        #print "req:post=", request.form
    res = {}
    if kwds.get('parameters', []) != []:
        get_params.extend(kwds['parameters'])
    for key in get_params:
        if key in kwds or key in req or key in defaults:
            res[key] = req.get(key, kwds.get(key, defaults.get(key, None)))
            mwf_logger.debug("res[{0}]={1}:{2}:{3}".format(key,
                                                           kwds.get(key, None), req.get(key, None), res[key]))
    return res


def get_collections_info():
    db = connect_db()
    dbmetadata = db.metadata()
    metadata = {}
    for c in db._show_collection_name:
        metadata[c] = dbmetadata.find({'c_name': c})
        mwf_logger.debug("METADATA: {0}".format(metadata[c]))
    return metadata


def GetNameOfPerson(DBname):
    if DBname == "FS":
        return "Fredrik Str&ouml;mberg"
    elif DBname == "HT":
        return "Holger Then"
    return None


def get_maassform_by_id(maass_id, fields=None):
    r"""
    """
    ret = []
    db = connect_db()  # Col = ConnectByName(DBname)
    try:
        obj = bson.ObjectId(str(maass_id))
    except bson.errors.InvalidId:
        data = dict()
        data['error'] = "Invalid id for object in database!"
        # return render_template("mwf_browse.html", info=info)
    else:
        data = None
        try:
            for collection_name in db.collection_names():
                c = pymongo.collection.Collection(db, collection_name)
                data = c.find_one({"_id": obj})
                if data is not None:
                    data['dbname'] = collection_name
                    data['num_coeffs'] = len(data['Coefficient'])
                    raise StopIteration()
        except StopIteration:
            pass
        if data is None:
            data = dict()
            data['error'] = "Invalid id for object in database!"
        # return render_template("mwf_browse.html", info=info)
    return data


def set_info_for_maass_form(data):
    ret = []
    ret.append(["Eigenvalue", "\(\\lambda=r^2 + \\frac{1}{4} \\ , \\quad r= \\ \)" + str(data['Eigenvalue'])])
    if data['Symmetry'] != "none":
        ret.append(["Symmetry", data['Symmetry']])
    if data['dbname'] == "HT":
        title = MakeTitle("1", "0", "0")
    else:
        title = MakeTitle(str(data['Level']), str(data['Weight']), str(data['Character']))
    if data['Coefficient']:
        idx = 0
        ANs = []
        for a in data['Coefficient']:
            if idx > 100:
                break
            ANs.append([idx, a])
            idx = idx + 1
        ret.append(["Coefficients", ANs])
    return [title, ret]


def make_table_of_coefficients(maass_id, number=100):
    c = get_maassform_by_id(maass_id, fields=['Coefficient'])['Coefficient']
    mwf_logger.info("ID=%s" % maass_id)
    mwf_logger.info("number=%s" % number)
    s = "<table border=\"1\">\n<thead><tr><td>\(n\)</td>"
    s += "<td>&nbsp;</td>"
    s += "<td>\(a(n)\)</td></tr></thead>\n"
    s += "<tbody>\n"
    number = min(number, len(c))
    for n in xrange(number):
        s += "<tr><td> %s </td><td></td><td>%s </td> \n" % (n + 1, c[n])
    s += "</tbody></table>\n"
    return s


def get_distinct_keys(key):
    res = []
    db = connect_db()
    for c in db.collection_names():
        res.extend(db[c].distinct(key))
    res = set(res)
    res = list(res)
    return res


def get_all_levels():
    return connect_db().levels()


def get_all_weights(Level):

    return connect_db().weights(Level)


def getallcharacters(Level, Weight):
    ret = []
    Col = ConnectToFS()
    for c in (Col.find({'Level': Level, 'Weight': Weight}, {'Character': 1}, sort=[('Weight', 1)])):
        ret.append(str(c['Character']))
    return set(ret)


def get_search_parameters(info):
    ret = dict()
    # if not info.has_key('search') or not info['search']:
    #    return ret
    level = my_get(info, 'level', 0)
    mwf_logger.debug("get_search param=%s" % info)
    mwf_logger.debug("level=%s" % level)
    if level > 0:
        ret['l1'] = int(level)
        ret['l2'] = int(level)
    else:
        level_range = my_get(info, 'level_range', '').split('..')
        if len(level_range) == 0:
            ret['l1'] = 0
            ret['l2'] = 0
        elif len(level_range) == 1:
            ret['l1'] = level_range[0]
            ret['l2'] = level_range[0]
        else:
            ret['l1'] = level_range[0]
            ret['l2'] = level_range[1]
    weight = my_get(info, 'weight', -1)
    if weight > -1:
        ret['wt1'] = float(weight)
        ret['wt2'] = float(weight)
    else:
        weight_range = my_get(info, 'weight_range', '').split('..')
        if len(weight_range) == 0:
            ret['wt1'] = 0
            ret['wt2'] = 0
        elif len(weight_range) == 1:
            ret['wt1'] = weight_range[0]
            ret['wt2'] = weight_range[0]
        else:
            ret['wt1'] = weight_range[0]
            ret['wt2'] = weight_range[1]

    ret['rec_start'] = my_get(info, 'rec_start', 1, int)
    ret['limit'] = my_get(info, 'limit', 2000, int)
    # ret['weight']=my_get(info,'weight',0,int)
    ev_range = my_get(info, 'ev_range', '').split('..')
    if len(ev_range) == 0:
        ret['r1'] = 0
        ret['r2'] = 0
    elif len(ev_range) == 1:
        mwf_logger.debug("ev_range=%s" % ev_range)
        # ev_range[0]=float(ev_range[0]); ev_range[1]=float(ev_range[1])
        ret['r1'] = ev_range[0]
        ret['r2'] = ev_range[0]
    else:
        ev_range[0] = float(ev_range[0])
        ev_range[1] = float(ev_range[1])
        ret['r1'] = ev_range[0]
        ret['r2'] = ev_range[1]
    return ret


# #from base import getDBConnection
# class MWFTable(object):
#     def __init__(self,collection='all',skip=[0,0],limit=[6,10],keys=['Level','Eigenvalue'],weight=0):
#         r"""
#         Skip tells you how many chunks of data you want to skip (from the beginning) and limit tells you how large each chunk is.
#         """
#         self.collection=collection
#         self.keys=keys
#         self.skip=skip
#         self.limit=limit
#         self.db = connect_db()
#         self.metadata=[]
#         self.title=''
#         self.cols=[]
#         self.get_collections()
#         self.table=[]
#         self.wt=weight
#     def set_collection(self,collection):
#         r"""
#         Change collection.
#         """
#         self.collection=collection
#         self.get_collections()
#     def shift(self,i=1,key='Level'):
#         if not key in self._keys:
#             mwf_logger.warning("{0} not a valid key in {1}".format(key,self._keys))
#         else:
#             ix = self._keys.index[key]
#             self.skip[ix]+=i
#     def get_collections(self):
#         cols = get_collection(self.collection)
#         if not cols:
#             cols=list()
#             for c in self.db.collection_names():
#                 if c<>'system.indexes' and c<>'metadata':
#                     print "cc=",c
#                 cols.append(self.db[c])
#         self.cols=cols
#     def get_metadata(self):
#         if not self.cols:
#             self.get_collections()
#         metadata=list()
#         for c in self.cols:
#             f=self.db.metadata.find({'c_name':c.name})
#             for x in f:
#                 print "x=",x
#                 metadata.append(x)
#         self.metadata=metadata
#     def set_table(self):
#         mwf_logger.debug("skip= {0}".format(self.skip))
#         mwf_logger.debug("limit= {0}".format(self.limit))
#         self.table=[]
#         level_ll=(self.skip[self.keys.index('Level')])*self.limit[self.keys.index('Level')]
#         level_ul=(self.skip[self.keys.index('Level')]+1)*self.limit[self.keys.index('Level')]
#         ev_limit=self.limit[self.keys.index('Eigenvalue')]
#         ev_skip=self.skip[self.keys.index('Eigenvalue')]*ev_limit
#         new_cols=[]
#         levels=get_all_levels()
#         mwf_logger.debug("levels= {0}".format(levels))
#         for N in levels:
#             N=int(N)
#             if N<level_ll:
#                 continue
#             if N>level_ul:
#                 break
#             evs=[]
#             for c in self.cols:
#                 finds=c.find({'Level':N,'Weight':self.wt}).sort('Eigenvalue',1).skip(ev_skip).limit(ev_limit);
#                 i=0
#                 for f in finds:
#                     i=i+1
#                     _id = f['_id']
#                     R = f['Eigenvalue']
#                     url = url_for('mwf.render_one_maass_waveform',id=str(_id),db=c.name)
#                     evs.append([R,url,c.name])
#                 if i>0 and c not in new_cols:
#                     new_cols.append(c)
#             evs.sort()
#             # If we have too many we delete the
#             while len(evs)>ev_limit:
#                 t=evs.pop()
#                 mwf_logger.debug("removes {0}".format(t))
#             #logger.debug("found eigenvalues in {0} is {1}".format(c.name,evs))
#             if len(evs)>0:
#                 self.table.append({'N':N,'evs':evs})
#         self.cols=new_cols
class MWFTable(object):
    def __init__(self, collection='all', skip=[0, 0], limit=[6, 10], keys=['Level', 'Eigenvalue'], weight=0):
        r"""
        Skip tells you how many chunks of data you want to skip (from the beginning) and limit tells you how large each chunk is.
        """
        import base
        self.DB = connect_db()
        self._collection_name = collection
        self.keys = keys
        if not isinstance(skip, list):
            self.skip = [skip, skip]
        if not isinstance(limit, list):
            self.limit = [limit, limit]
        mwf_logger.debug("count={0}".format(self.DB.count()))
        self.metadata = []
        self.title = ''
        self._collections = []
        self.get_collections()
        self.table = []
        self.wt = weight
        self.paging = []

    def weights(self):
        return self.wt

    def shift(self, i=1, key='Level'):
        if not key in self._keys:
            mwf_logger.warning("{0} not a valid key in {1}".format(key, self._keys))
        else:
            ix = self._keys.index[key]
            self.skip[ix] += i

    def get_collections(self):
        self._collections = []
        for col_name in available_collections:
            if self._collection_name == col_name or self._collection_name == 'all':
                if col_name in self.DB._mongo_db.collection_names():
                    self._collections.append(self.DB._mongo_db[col_name])

    def get_metadata(self):
        if not self.cols:
            self.get_collections()
        metadata = list()
        for c in self.cols:
            f = self.db.metadata().find({'c_name': c.name})
            for x in f:
                print "x=", x
                metadata.append(x)
        self.metadata = metadata

    def set_table(self, data={}):
        # data = self.DB.get_search_parameters(data,kwds
        mwf_logger.debug("set table, data =  {0}".format(data))
        mwf_logger.debug("skip= {0}".format(self.skip))
        mwf_logger.debug("limit= {0}".format(self.limit))
        self.table = []
        data['skip'] = self.skip
        data['limit'] = self.limit
        l1 = self.keys.index('Level')
        level_ll = (self.skip[l1]) * self.limit[l1]
        level_ul = (self.skip[l1] + 1) * self.limit[l1]
        ev_limit = self.limit[self.keys.index('Eigenvalue')]
        ev_skip = self.skip[self.keys.index('Eigenvalue')] * ev_limit
        new_cols = []
        levels = self.DB.levels()  # )get_all_levels()
        mwf_logger.debug("levels= {0}".format(levels))
        cur_level = data.get('level', None)
        cur_wt = data.get('weight', None)
        print "cur_level=", cur_level
        print "cur_wt=", cur_wt
        for N in levels:
            if cur_level and cur_level != N:
                continue
            N = int(N)
            if N < level_ll or N > level_ul:
                continue
            print "N=", N
            weights = self.DB.weights(N)
            print "weights=", weights
            self.wt = weights
            for k in weights:
                if cur_wt is not None and cur_wt != k:
                    continue
                print "k=", k
                k = int(k)
                evs = []
                totalc = self.DB.count({'Level': N, 'Weight': k})
                for c in self._collections:
                    find_data = {'Level': N, 'Weight': k,
                                 'skip': ev_skip, 'limit': ev_limit}
                    finds = self.DB.get_Maass_forms(find_data,
                                                    collection_name=c.name)
                    for rec in finds:
                        row = {}
                        maass_id = rec.get('_id', None)
                        row['R'] = rec.get('Eigenvalue', None)
                        row['st'] = rec.get("Symmetry")
                        row['cusp_evs'] = rec.get("Cusp_evs")
                        row['err'] = rec.get('Error', 0)
                        row['url'] = url_for('mwf.render_one_maass_waveform', maass_id=maass_id)
                        row['name'] = c.name
                        row['numc'] = rec.get('Numc', 0)
                        evs.append(row)
                kmax = int(totalc / ev_limit)
                paging = []
                for j in range(ev_skip, kmax):
                    k0 = (j) * ev_limit
                    k1 = (j + 1) * ev_limit
                    url = url_for(
                        'mwf.render_maass_waveforms', level=N, weight=k, skip=ev_skip + j, limit=ev_limit)
                    skip = {'url': url, 'k0': k0, 'k1': k1, 'cur_skip': ev_skip,
                            'cur_limit': ev_limit, "skip": j}
                    paging.append(skip)
                # s+="]"
                self.paging = paging
                smalltbl = {'N': N, 'k': k, 'evs': evs, 'paging': paging}
                if len(evs) > 0:
                    self.table.append(smalltbl)
        print "table=", self.table
        self.cols = new_cols

    def rows(self):
        return self.rows


def searchinDB(search, coll, filds):
    return coll.find(search, filds, sort=[('Eigenvalue', 1)])


def WriteEVtoTable(SearchResult, EV_Result, index):
    for ev in SearchResult:
        EV_Result.append([ev['Eigenvalue'], index, ev['Symmetry'], str(ev['_id'])])
        index = index + 1
    return index


def getEivenvalues(search, coll, index):
    ret = []
    sr = searchinDB(search, coll, {'Eigenvalue': 1, 'Symmetry': 1})
    WriteEVtoTable(sr, ret, index)
    #	for ev in sr:
    #                       ret.append([ev['Eigenvalue'],index,ev['Symmetry'],str(ev['_id'])])
    #                        index=index+1
    return [sr.distinct('Symmetry'), ret]


def getEigenvaluesFS(Level, Weight, Character, index):
    return getEivenvalues({'Level': Level, 'Weight': Weight, 'Character': Character}, ConnectToFS(), index)


def getEigenvaluesHT(Level, Weight, Character, index):
    if Level != 1 or Weight != 0.0 or Character != 0:
        return [0, []]
    return getEivenvalues({}, ConnectToHT(), index)


def getData(search, coll, index):
    ret = []
    sr = searchinDB(search, coll, {})
    for ev in sr:
        ret.append([ev['Eigenvalue'], index, ev['Symmetry'], str(ev['_id'])])
        index = index + 1
    return [sr.distinct('Symmetry'), ret]

# def SearchEigenvaluesFS(Level,Weight,Character,index,eigenvalue):


def MakeTitle(level, weight, character):
    ret = "Maass cusp forms for "
    if level:
        if level == "1":
            ret += "\(PSL(2,Z)\)"
        else:
            ret += "\(\Gamma_0(" + str(level) + ")\)"
    else:
        ret += "\(\Gamma_0(n)\)"
    if weight:
        if float(weight) != 0:
            ret += ",k=" + weight
    if character:
        if character != "0":
            ret += ",\(\chi_" + character + "\) (according to SAGE)"
    return ret


def searchforEV(eigenvalue, DBname):
    ret = []
    SearchLimit = 5
    Col = ConnectByName(DBname)
    ev = float(eigenvalue)
    #	return getEivenvalues({'Level':Level,'Weight':Weight,'Character':Character},ConnectToFS(),index)
    index = 0
    search1 = Col.find({"Eigenvalue": {"$gte": ev}}, {'Eigenvalue': 1, 'Symmetry': 1}, sort=[(
        'Eigenvalue', 1)], limit=SearchLimit)
    index = WriteEVtoTable(search1, ret, index)

    search2 = Col.find({"Eigenvalue": {"$lte": ev}}, {'Eigenvalue': 1, 'Symmetry': 1}, sort=[(
        'Eigenvalue', -1)], limit=SearchLimit)
    index = WriteEVtoTable(search2, ret, index)
    return [set(search1.distinct('Symmetry') + search2.distinct('Symmetry')), ret]

"""
search1 = Collection.find({"Eigenvalue" : {"$gte" : ev}},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',1)],limit=2)
                        search2 = Collection.find({"Eigenvalue" : {"$lte" : ev}},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',-1)],limit=2)
                        index=write_eigenvalues(reversed(list(search2)),EVs,index)
                        write_eigenvalues(search1,EVs,index)
"""


def search_for_eigenvalues(search):
    ev_l = float(search['ev_lower'])
    ev_u = float(search['ev_upper'])
    level_l = float(search['level_lower'])
    level_u = float(search['level_upper'])
    if level_l > 0 and level_u > 0:
        level_range = {"$gte": level_l, "$lte": level_u}
    elif level_u > 0:
        level_range = {"$lte": level_u}
    elif level_l > 0:
        level_range = {"$gte": level_l}
    if ev_l > 0 and ev_u > 0:
        ev_range = {"$gte": ev_l, "$lte": ev_u}
    elif ev_u > 0:
        ev_range = {"$lte": ev_u}
    elif ev_l > 0:
        ev_range = {"$gte": ev_l}
    weight = float(search['weight'])
    rec_start = search['rec_start']
    limit = search['limit']
    res = dict()
    res['weights'] = []
    # SearchLimit = limit_u
    db = connect_db()
    index = 0
    data = None
    searchp = {'fields': ['Eigenvalue', 'Symmetry', 'Level', 'Character', 'Weight', '_id'],
               'sort': [('Eigenvalue', pymongo.ASCENDING), ('Level', pymongo.ASCENDING)],
               'spec': {"Eigenvalue": ev_range}}
    if level_range:
        searchp['spec']["Level"] = level_range
    if limit > 0:
        searchp['limit'] = rec_start + limit

    # the limit of number of records is 'global', for all collections.
    # is this good?
    print "searchp=", searchp
    index = 0
    search['more'] = 0
    search['rec_start'] = rec_start
    search['rec_stop'] = -1
    for collection_name in db.collection_names():
        if collection_name in ['system.indexes', 'contributors']:
            continue
        c = pymongo.collection.Collection(db, collection_name)
        res[collection_name] = list()
        print "c=", c
        f = c.find(**searchp)
        search['num_recs'] = f.count()
        for rec in f:
            print "rec=", rec
            wt = my_get(rec, 'Weight', 0, float)
            # print "index=",index
            if index >= rec_start and index < limit + rec_start:
                res[collection_name].append(rec)
                if res['weights'].count(wt) == 0:
                    res['weights'].append(wt)
            index = index + 1
            if index > limit + rec_start:
                search['rec_stop'] = index - 1
                search['more'] = 1
                # if len(res[collection_name])<f.count():
                print "There are more to be displayed!"
                exit
    if search['rec_stop'] < 0:
        search['rec_stop'] = limit + rec_start
    return res


def ajax_once(callback, *arglist, **kwds):
    r"""
    """

    text = kwds.get('text', 'more')
    print "text=", text
    print "arglist=", arglist
    print "kwds=", kwds
    # print "req=",request.args
    nonce = hex(random.randint(0, 1 << 128))
    res = callback()
    url = ajax_url(ajax_once, arglist, kwds, inline=True)
    s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
    # s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s',
    # {'level':22,'weight':4},function() {
    # MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return
    # false;" href="#">%(text)s</a>""" % locals()
    s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {a:1},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
    return s0 + s1


def my_get(dict, key, default, f=None):
    r"""
    Improved version of dict.get where an empty string also gives default.
    and before returning we apply f on the result.
    """
    x = dict.get(key, default)
    if x == '':
        x = default
    if f is not None:
        try:
            x = f(x)
        except:
            pass
    return x


def eval_maass_form(R, C, M, x, y):
    r"""
    
    """
    raise NotImplementedError,""
    s = 0
    twopi = RR(2 * Pi)
    twopii = CC(I * 2 * Pi)
    sqrty = y.sqrt()
    for n in range(1, M):
        tmp = sqrty * besselk_dp(R, twopi * n * y) * exp(twopii * n * x)
        s = s + tmp * C[n]
    return s


def plot_maass_form(R, N, C, **kwds):
    r"""
    Plot a Maass waveform with eigenvalue R on Gamma_0(N), using coefficients from the vector C.

    """
