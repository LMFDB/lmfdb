# -*- coding: utf-8 -*-

import random
from flask import url_for, request
from lmfdb.utils import to_dict, ajax_url
from lmfdb.modular_forms.maass_forms.maass_waveforms import mwf_logger
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db import maass_db
from lmfdb.modular_forms.backend.mf_utils import my_get

def get_args_mwf(**kwds):
    get_params = ['level', 'weight', 'character', 'id', 'db', 'search',
                  'search_all', 'eigenvalue', 'browse',
                  'ev_skip', 'ev_range', 'maass_id', 'skip', 'limit',
                  'level_range', 'weight_range', 'ev_range', 'download']
    defaults = {'level': 0, 'weight': -1, 'character': 0, 'skip': 0, 'limit': 2000,
                'maass_id': None, 'search': None,
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
    character = my_get(info, 'character', 1)
    mwf_logger.info("character: %s" % character)
    if character > 1:
        ret['ch1'] = int(character)
        ret['ch2'] = int(character)
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

class MWFTable(object):
    def __init__(self, skip=[0, 0], limit=[6, 10], keys=['Level', 'Eigenvalue'], weight=0):
        r"""
        Skip tells you how many chunks of data you want to skip (from the beginning) and limit tells you how large each chunk is.
        """
        self.keys = keys
        if not isinstance(skip, list):
            self.skip = [skip, skip]
        if not isinstance(limit, list):
            self.limit = [limit, limit]
        mwf_logger.debug("count={0}".format(maass_db.count()))
        self.title = ''
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

    def set_table(self, data={}):
        # data = maass_db.get_search_parameters(data,kwds
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
        levels = maass_db.levels()
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
            weights = maass_db.weights(N)
            print "weights=", weights
            self.wt = weights
            for k in weights:
                if cur_wt is not None and cur_wt != k:
                    continue
                print "k=", k
                k = int(k)
                evs = []
                query = {'Level': N, 'Weight': k}
                totalc = maass_db.count(query)
                finds = maass_db.get_Maass_forms(query, limit=ev_limit, offset=ev_skip)
                for rec in finds:
                    row = {}
                    maass_id = rec.get('_id', None)
                    row['R'] = rec.get('Eigenvalue', None)
                    row['st'] = rec.get("Symmetry")
                    row['cusp_evs'] = rec.get("Cusp_evs")
                    row['err'] = rec.get('Error', 0)
                    row['url'] = url_for('mwf.render_one_maass_waveform', maass_id=maass_id)
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

def WriteEVtoTable(SearchResult, EV_Result, index):
    for ev in SearchResult:
        EV_Result.append([ev['Eigenvalue'], index, ev['Symmetry'], str(ev['_id'])])
        index = index + 1
    return index

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


def eval_maass_form(R, C, M, x, y):
    r"""
    
    """
    raise NotImplementedError,""
    # the code below needs besselk_dp, see lpkbessel.pyx
    # s = 0
    # twopi = RR(2 * Pi)
    # twopii = CC(I * 2 * Pi)
    # sqrty = y.sqrt()
    # for n in range(1, M):
    #    tmp = sqrty * besselk_dp(R, twopi * n * y) * exp(twopii * n * x)
    #    s = s + tmp * C[n]
    # return s


def plot_maass_form(R, N, C, **kwds):
    r"""
    Plot a Maass waveform with eigenvalue R on Gamma_0(N), using coefficients from the vector C.

    """
