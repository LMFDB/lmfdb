# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
r"""
Routines for rendering webpages for holomorphic modular forms on GL(2,Q)

AUTHOR: Fredrik Strömberg <fredrik314@gmail.com>

"""
from flask import render_template, url_for, send_file
from lmfdb.utils import to_dict 
from sage.all import uniq
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf, EMF_TOP
#from lmfdb.modular_forms.elliptic_modular_forms.backend.cached_interfaces import WebModFormSpace_cached

###
###

def render_web_modform_space_gamma1(level=None, weight=None, character=None, label=None, **kwds):
    r"""
    Render the webpage for the space of elliptic modular forms on gamma1 as a table of spaces of spaces on gamma0 with associated characters.
    """
    emf_logger.debug("In render_elliptic_modular_form_space kwds: {0}".format(kwds))
    emf_logger.debug(
        "Input: level={0},weight={1},character={2},label={3}".format(level, weight, character, label))
    info = to_dict(kwds)
    info['level'] = level
    info['weight'] = weight
    info['character'] = character
    title = "Newforms of weight {0} for \(\Gamma_1({1})\)".format(weight, level)
    bread = [(EMF_TOP, url_for('emf.render_elliptic_modular_forms'))]
    bread.append(("Level %s" % level, url_for("emf.render_elliptic_modular_forms", level=level)))
    bread.append(
        ("Weight %s" % weight, url_for("emf.render_elliptic_modular_forms", level=level, weight=weight)))
    info['grouptype'] = 1
    info['show_all_characters'] = 1
    info['table'] = set_info_for_gamma1(level,weight)
    info['bread'] = bread
    info['title'] = title
    info['showGaloisOrbits']=1
    return render_template("emf_render_web_modform_space_gamma1.html", **info)


def set_info_for_gamma1(level,weight,weight2=None):
    from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import dimension_from_db,dirichlet_character_conrey_galois_orbits_reps
    from sage.all import DirichletGroup
    from dirichlet_conrey import DirichletGroup_conrey
    G = dirichlet_character_conrey_galois_orbits_reps(level)
    dim_table = dimension_from_db(level,weight,chi='all',group='gamma1')
    if weight<> None and weight2>weight:
        w1 = weight; w2 = weight2
    else:
        w1 = weight; w2 = weight
    table = {'galois_orbit':{},'galois_orbits_reps':{},'cells':{}}
    table['weights']=range(w1,w2+1)
    max_gal_count = 0
    from  lmfdb.base import getDBConnection
    db = getDBConnection()['modularforms2']['webmodformspace']
    for x in G:
        xi = x.number()
        table['galois_orbits_reps'][xi]= {'head' : "\(\chi_{" + str(level) + "}(" + str(xi) + ",\cdot) \)",
                                              'chi': str(x.number()),
                                              'url': url_for('characters.render_Dirichletwebpage', modulus=level, number=xi) }
        table['galois_orbit'][xi]= [
            {'head' : "\({0}\)".format(xc.number()),
             'chi': str(xc.number()),
             'url': url_for('characters.render_Dirichletwebpage', modulus=level, number=xc.number()) }
            for xc in x.galois_orbit()]
        tmp_gal_count = len(table['galois_orbit'][xi])
        if tmp_gal_count > max_gal_count:
            max_gal_count = tmp_gal_count
        table['cells'][xi]={}
        orbit = map(lambda x:x.number(),x.galois_orbit()) 
        for k in range(w1,w2+1):
            # try:
            #     d,t = dim_table[level][weight][xi]
            # except KeyError:
            #     d = -1; t = 0
            r = db.find_one({'level':int(level),'weight':int(k),'character':{"$in":orbit}})
            if not r is None:
                d = r.get('dimension',"n/a")
                url = url_for(
                    'emf.render_elliptic_modular_forms', level=level, weight=k, character=xi)
            else:
                url = ''
                d = "n/a"
            table['cells'][xi][k] ={'N': level, 'k': k, 'chi': xi, 'url': url, 'dim': d}
    table['galois_orbits_reps_numbers']=table['galois_orbits_reps'].keys()
    table['galois_orbits_reps_numbers'].sort()
    table['maxGalCount']=max_gal_count
    return table
