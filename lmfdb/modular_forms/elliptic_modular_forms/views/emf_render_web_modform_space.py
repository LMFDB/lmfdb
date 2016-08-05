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

AUTHOR: Fredrik Strömberg  <fredrik314@gmail.com>

"""
from flask import render_template, url_for, send_file,flash, redirect
from lmfdb.utils import to_dict
from lmfdb.base import getDBConnection
from sage.all import uniq
from lmfdb.modular_forms import MF_TOP
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace_cached, WebModFormSpace
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger, EMF_TOP, default_max_height


def render_web_modform_space(level=None, weight=None, character=None, label=None, **kwds):
    r"""
    Render the webpage for a elliptic modular forms space.
    """
    emf_logger.debug("In render_elliptic_modular_form_space kwds: {0}".format(kwds))
    emf_logger.debug(
        "Input: level={0},weight={1},character={2},label={3}".format(level, weight, character, label))
    info = to_dict(kwds)
    info['level'] = level
    info['weight'] = weight
    info['character'] = character
    try:
        info = set_info_for_modular_form_space(**info)
    except RuntimeError:
        errst = "The space {0}.{1}.{2} is not in the database!".format(level,weight,character)
        flash(errst,'error')
        info = {'error': ''}
    emf_logger.debug("keys={0}".format(info.keys()))
    if info.has_key('error'):
        emf_logger.critical("error={0}".format(info['error']))
    if 'download' in kwds and 'error' not in kwds:
        return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'], add_etags=False)
    if 'dimension_newspace' in kwds and kwds['dimension_newspace'] == 1:
        # if there is only one orbit we list it
        emf_logger.debug("Dimension of newforms is one!")
        info['label'] = 'a'
        return redirect(url_for('emf.render_elliptic_modular_forms', **info))
    if character>1:
        info['title'] = "Newforms of weight %s for \(\Gamma_{0}(%s)\) with character \(\chi_{%s}(%s, \cdot)\)" % (weight, level, level, character)
    else:
        info['title'] = "Newforms of weight %s for \(\Gamma_{0}(%s)\)" % (weight, level)
    bread = [(MF_TOP, url_for('mf.modular_form_main_page')), (EMF_TOP, url_for('emf.render_elliptic_modular_forms'))]
    bread.append(("Level %s" % level, url_for('emf.render_elliptic_modular_forms', level=level)))
    bread.append(
        ("Weight %s" % weight, url_for('emf.render_elliptic_modular_forms', level=level, weight=weight)))
    bread.append(
        ("Character \(\chi_{%s}(%s, \cdot)\)" % (level, character), url_for('emf.render_elliptic_modular_forms', level=level, weight=weight, character=character)))
    # emf_logger.debug("friends={0}".format(friends))
    info['bread'] = bread
    info['learnmore'] = [('History of modular forms', url_for('.holomorphic_mf_history'))]
    emf_logger.debug("info={0}".format(info))
    if info.has_key('space'):
        emf_logger.debug("space={0}".format(info['space']))        
        emf_logger.debug("dimension={0}".format(info['space'].dimension))
    if info.has_key('error'):
        emf_logger.debug("error={0}".format(info['error']))
    return render_template("emf_web_modform_space.html", **info)

    
def set_info_for_modular_form_space(level=None, weight=None, character=None, label=None, **kwds):
    r"""
      Set information about a space of modular forms.
    """
    info = dict()
    emf_logger.debug("info={0}".format(info))    
    WMFS = None
    if info.has_key('error'):
        return info
    if level <= 0:
        info['error'] = "Got wrong level: %s " % level
        return info
    try:
        WMFS = WebModFormSpace_cached(level = level, weight = weight, cuspidal=True, character = character, update_from_db=True)
        emf_logger.debug("Created WebModFormSpace %s"%WMFS)
        if not WMFS.has_updated():
            #get the representative we have in the db for this space (Galois conjugate)
            #note that this does not use the web_object infrastructure at all right now
            #which should be changed for sure!
            dimension_table_name = WebModFormSpace._dimension_table_name
            db_dim = getDBConnection()['modularforms2'][dimension_table_name]
            rep = db_dim.find_one({'level': level, 'weight': weight, 'character_orbit': {'$in': [character]}})
            if not rep is None and not rep['cchi'] == character: # don't link back to myself!
                info['wmfs_rep_url'] = url_for('emf.render_elliptic_modular_forms', level=level, weight=weight, character=rep['cchi'])
                info['wmfs_rep_number'] =  rep['cchi']
        # FIXME: the variable WNF is not defined above, so the code below cannot work (I don't think it is ever used)
        # if 'download' in info and 'tempfile' in info:
        #     save(WNF,info['tempfile'])
        #     info['filename'] = str(weight) + '-' + str(level) + '-' + str(character) + '-' + label + '.sobj'
        #     return info
    except ValueError as e:
        emf_logger.debug(e)
        emf_logger.debug(e.message)
        #if isinstance(e,IndexError):
        info['error'] = e.message
        WMFS = None
    if WMFS is None:
        info['error'] = "We are sorry. The sought space can not be found in the database. "+"<br> Detailed information: {0}".format(info.get('error',''))
        return info
    else:
        ### Somehow the Hecke orbits are sometimes not in the space...
        #if WMFS.dimension_new_cusp_forms()!=len(WMFS.hecke_orbits):
        #    ## Try to add them here... 
        #    for d in range(len(WMFS.dimension_new_cusp_forms())):
        #        F = 
        #        WMFS.hecke_orbits.append(F)
        info['space'] = WMFS
        info['max_height'] = default_max_height
#    info['old_decomposition'] = WMFS.oldspace_decomposition()
    info['oldspace_decomposition']=''
    try: 
        emf_logger.debug("Oldspace = {0}".format(WMFS.oldspace_decomposition))
        if WMFS.oldspace_decomposition != []:
            emf_logger.debug("oldspace={0}".format(WMFS.oldspace_decomposition))
            l = []
            for t in WMFS.oldspace_decomposition:
                emf_logger.debug("t={0}".format(t))
                N,k,chi,mult,d = t
                url = url_for('emf.render_elliptic_modular_forms', level=N, weight=k, character=chi)
                if chi != 1:
                    sname = "S^{{ new }}_{{ {k} }}(\\Gamma_0({N}),\\chi_{{ {N} }}({chi},\\cdot))".format(k=k,N=N,chi=chi)
                else:
                    sname = "S^{{ new }}_{{ {k} }}(\\Gamma_0({N}))".format(k=k,N=N)
                l.append("\href{{ {url} }}{{ {sname} }}^{{\oplus {mult} }}".format(sname=sname,mult=mult,url=url))
            if l != []:            
                s = "\\oplus ".join(l)
                info['oldspace_decomposition']=' $ {0} $'.format(s)
    except Exception as e:
        emf_logger.critical("Oldspace decomposition failed. Error:{0}".format(e))
    ## For side-bar
    lifts = list()
    lifts.append(('Half-Integral Weight Forms', '/ModularForm/Mp2/Q'))
    lifts.append(('Siegel Modular Forms', '/ModularForm/GSp4/Q'))
    info['lifts'] = lifts
    friends = list()
    for label in WMFS.hecke_orbits:
        f = WMFS.hecke_orbits[label]
        # catch the url being None or set to '':
        if hasattr(f.base_ring, "lmfdb_url") and f.base_ring.lmfdb_url:
            friends.append(('Number field ' + f.base_ring.lmfdb_pretty, f.base_ring.lmfdb_url))
        if hasattr(f.coefficient_field, "lmfdb_url") and f.coefficient_field.lmfdb_url:
            friends.append(('Number field ' + f.coefficient_field.lmfdb_pretty, f.coefficient_field.lmfdb_url))
    friends.append(("Dirichlet character \(" + WMFS.character.latex_name + "\)", WMFS.character.url()))
    friends = uniq(friends)
    info['friends'] = friends
    info['code'] = WMFS.code
    
    return info

