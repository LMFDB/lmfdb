# -*- coding: utf-8 -*-
import os
import linecache
from flask import url_for
from lmfdb import db
from lmfdb.utils import raw_typeset

from sage.all import EllipticCurve, QQ

congruent_number_data_directory = os.path.expanduser('~/data/congruent_number_curves')

def CNfilename(file_suffix):
    return os.path.join(congruent_number_data_directory, "CN.{}".format(file_suffix))

def get_CN_data_old(fs, n):
    with open(CNfilename(fs)) as data:
        return data.readlines()[n-1].split()

def get_CN_data_new(fs, n):
    return linecache.getline(CNfilename(fs), n).split()

get_CN_data = get_CN_data_new

def parse_gens_string(s):
    if s == '[]':
        return []
    g = s[2:-2].split('],[')
    return [[QQ(c) for c in gi.split(',')] for gi in g if '?' not in gi]

def get_congruent_number_data(n):
    info = {'n': n}
    info['rank'] = rank = int(get_CN_data('rank', n)[1])
    info['is_congruent'] = cong = rank>0

    ainvs = [0,0,0,-n*n,0]
    E = EllipticCurve(ainvs)
    info['E'] = E

    gens_string = get_CN_data('MWgroup', n)[1]
    gens = [E(g) for g in parse_gens_string(gens_string)]
    info['gens'] = ", ".join([str(g) for g in gens])
    info['missing_generator'] =  len(gens) < rank

    # better typesetting of points
    info['gens'] = [raw_typeset(P.xy()) for P in gens]
    if len(gens)==1:
        info['gen'] = info['gens'][0]

    info['conductor'] = N = int(get_CN_data('conductor', n)[1])
    assert N == E.conductor()

    info['triangle'] = None
    if cong:
        P = 2*gens[0]
        x,y = P.xy()
        Z = 2*x.sqrt()
        XplusY = 2*(x+n).sqrt()
        XminusY = 2*(x-n).sqrt()
        X = (XplusY+XminusY)/2
        Y = XplusY -X
        assert X*X+Y*Y==Z*Z
        assert X*Y == 2*n
        assert X>0 and Y>0 and Z>0
        if X>Y:
            X,Y = Y,X
        info['triangle'] = {'X':X, 'Y':Y, 'Z':Z}

    res = db.ec_curvedata.search({'ainvs':ainvs})
    try:
        res = next(res)
        info['in_db'] = 'exact'
    except StopIteration:
        res = db.ec_curvedata.search({'jinv': [1728,1], 'conductor': N})
        try:
            res = next(res)
            info['in_db'] = 'isomorphic'
        except StopIteration:
            info['in_db'] = False

    if info['in_db']:
        info['label'] = label = res['lmfdb_label'] if res else None
        info['url'] = url_for(".by_ec_label", label=label)

    return info
