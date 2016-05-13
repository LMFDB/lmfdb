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
from flask import render_template, url_for, send_file,flash
from lmfdb.utils import to_dict 
from sage.all import uniq
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf, EMF_TOP
#from lmfdb.modular_forms.elliptic_modular_forms.backend.cached_interfaces import WebModFormSpace_cached
from lmfdb.WebCharacter import ConreyCharacter
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
    table = set_info_for_gamma1(level,weight)
    if table is None:
        pass #info['error'] = 'The database does not currently contain any spaces matching these parameters!'
    else:
        info['table'] = table 
    info['bread'] = bread
    info['title'] = title
    info['showGaloisOrbits']=1
    emf_logger.debug("info={0}".format(info))
    return render_template("emf_render_web_modform_space_gamma1.html", **info)


def set_info_for_gamma1(level,weight,weight2=None):
    from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import dimension_from_db,dirichlet_character_conrey_galois_orbits_reps,conrey_character_from_number
    
    from sage.all import DirichletGroup,dimension_new_cusp_forms
    from dirichlet_conrey import DirichletGroup_conrey
    from lmfdb.modular_forms.elliptic_modular_forms import WebModFormSpace
    dimension_table_name = WebModFormSpace._dimension_table_name
    dim_table = dimension_from_db(level,weight,chi='all',group='gamma1')
    if weight != None and weight2>weight:
        w1 = weight; w2 = weight2
    else:
        w1 = weight; w2 = weight
    table = {'galois_orbit':{},'galois_orbits_reps':{},'cells':{}}
    table['weights']=range(w1,w2+1)
    max_gal_count = 0
    from  lmfdb.base import getDBConnection
    emf_logger.debug("dimension table name={0}".format(dimension_table_name))
    db_dim = getDBConnection()['modularforms2'][dimension_table_name]
    s = {'level':int(level),'weight':{"$lt":int(w2+1),"$gt":int(w1-1)},'cchi':{"$exists":True}}
    q = db_dim.find(s).sort([('cchi',int(1)),('weight',int(1))])
    if q.count() == 0:
        emf_logger.debug("No spaces in the database!")
        flash('The database does not currently contain any spaces matching these parameters. Please try again!')
        return None #'error':'The database does not currently contain any spaces matching these parameters!'}
    else:
        table['maxGalCount']=1
        for r in q:
            xi = r['cchi']
            orbit = r['character_orbit']
            k = r['weight']
            ## This is probably still quicker if it is in the database
            parity = r.get('character_parity','n/a')
            if parity == 'n/a':
                chi = ConreyCharacter(level,xi)
                if chi.is_odd():
                    parity = -1
                elif chi.is_even():
                    parity = 1
                else:
                    emf_logger.critical("Could not determine the parity of ConreyCharacter({0},{1})".format(xi,level))
                    trivial_trivially = ""
            if parity != 'n/a':
                if k % 2 == (1 + parity)/2:   # is space empty because of parity?
                    trivial_trivially = "yes"
                else:
                    trivial_trivially = ""
            if parity == 1:
                parity = 'even'
            elif parity == -1:
                parity = 'odd'
            d = r.get('d_newf',"n/a")
            indb = r.get('in_wdb',0)
            if d == 0:
                indb = 1
            if indb:
                url = url_for('emf.render_elliptic_modular_forms', level=level, weight=k, character=xi)
            else:
                url = ''
            if not table['galois_orbits_reps'].has_key(xi):
                table['galois_orbits_reps'][xi]={
                    'head' : "\(\chi_{{{0}}}({1},\cdot) \)".format(level,xi),  # yes, {{{ is required
                    'chi': "{0}".format(xi),
                    'url': url_for('characters.render_Dirichletwebpage', modulus=level, number=xi),
                    'parity':parity}
                table['galois_orbit'][xi]= [
                    {
                    #'head' : "\(\chi_{{{0}}}({1},\cdot) \)".format(level,xci),  # yes, {{{ is required
               ##     'head' : "\(S_{{{0}}}({1},\chi({2}, \cdot) ) \)".format(weight,level,xci),  # yes, {{{ is required
                ##    'head' : "\(S_{{{0}}}(\chi({1}, \cdot) ) \)".format(weight,xci),  # yes, {{{ is required
                    'head' : r"\(S_{{{0}}}(\chi_{{{1}}}({2}, \cdot)) \)".format(weight,level,xci),  # yes, {{{ is required
                    # 'head' : "\({0}\)".format(xci),
                     'chi': "{0}".format(xci),
                 #    'url': url_for('characters.render_Dirichletwebpage', modulus=level, number=xci)
                     'url': url_for('emf.render_elliptic_modular_forms', level=level, weight=k, character=xci) if indb else ''
                    }
                    for xci in orbit]
            if len(orbit)>table['maxGalCount']:
                table['maxGalCount']=len(orbit)
            table['cells'][xi]={}
            table['cells'][xi][k] ={'N': level, 'k': k, 'chi': xi, 'url': url, 'dim': d, 'trivial_trivially': trivial_trivially,}
    table['galois_orbits_reps_numbers']=table['galois_orbits_reps'].keys()
    table['galois_orbits_reps_numbers'].sort()
    #emf_logger.debug("Table:{0}".format(table))
    return table
