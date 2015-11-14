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
    from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import dimension_from_db,dirichlet_character_conrey_galois_orbits_reps,conrey_character_from_number
    
    from sage.all import DirichletGroup,dimension_new_cusp_forms
    from dirichlet_conrey import DirichletGroup_conrey
   
    dim_table = dimension_from_db(level,weight,chi='all',group='gamma1')
    if weight != None and weight2>weight:
        w1 = weight; w2 = weight2
    else:
        w1 = weight; w2 = weight
    table = {'galois_orbit':{},'galois_orbits_reps':{},'cells':{}}
    table['weights']=range(w1,w2+1)
    max_gal_count = 0
    from  lmfdb.base import getDBConnection
    db_dim = getDBConnection()['modularforms2']['dimension_table']
    s = {'level':int(level),'weight':{"$lt":int(w2+1),"$gt":int(w1-1)},'cchi':{"$exists":True}}
    q = db_dim.find(s).sort([('cchi',int(1)),('weight',int(1))])
    if q.count() == 0:
        # If the record for level N exists then we have data for all galois orbits
        # otherwise we need to find the representatives anyway
        #G = dirichlet_character_conrey_galois_orbits_reps(level)
        return {}
    else:
        table['maxGalCount']=1
        for r in q:
            xi = r['cchi']
            orbit = r['character_orbit']
            k = r['weight']
            if not table['galois_orbits_reps'].has_key(xi):
                table['galois_orbits_reps'][xi]={
                    'head' : "\(\chi_{{0}}({1},\cdot) \)".format(level,xi),
                    'chi': "{0}".format(xi),
                    'url': url_for('characters.render_Dirichletwebpage', modulus=level, number=xi) }
                table['galois_orbit'][xi]= [
                    {'head' : "\({0}\)".format(xci),
                     'chi': "{0}".format(xci),
                     'url': url_for('characters.render_Dirichletwebpage', modulus=level, number=xci) }
                    for xci in orbit]
            if len(orbit)>table['maxGalCount']:
                table['maxGalCount']=len(orbit)
            table['cells'][xi]={}
            d = r.get('d_newf',"n/a")
            url = url_for('emf.render_elliptic_modular_forms', level=level, weight=k, character=xi)
            table['cells'][xi][k] ={'N': level, 'k': k, 'chi': xi, 'url': url, 'dim': d}
    table['galois_orbits_reps_numbers']=table['galois_orbits_reps'].keys()
    table['galois_orbits_reps_numbers'].sort()
    return table
