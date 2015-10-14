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
from flask import render_template, url_for, send_file
from lmfdb.utils import to_dict 
from sage.all import uniq
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace_cached, WebModFormSpace
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf, EMF_TOP
###
###

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
    info = set_info_for_modular_form_space(**info)
    emf_logger.debug("keys={0}".format(info.keys()))
    if 'download' in kwds and 'error' not in kwds:
        return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    if 'dimension_newspace' in kwds and kwds['dimension_newspace'] == 1:
        # if there is only one orbit we list it
        emf_logger.debug("Dimension of newforms is one!")
        info['label'] = 'a'
        return redirect(url_for('emf.render_elliptic_modular_forms', **info))
    info['title'] = "Newforms of weight %s for \(\Gamma_{0}(%s)\) with character \(\chi_{%s}(%s, \cdot)\)" % (weight, level, level, character)
    bread = [(EMF_TOP, url_for('emf.render_elliptic_modular_forms'))]
    bread.append(("Level %s" % level, url_for('emf.render_elliptic_modular_forms', level=level)))
    bread.append(
        ("Weight %s" % weight, url_for('emf.render_elliptic_modular_forms', level=level, weight=weight)))
    bread.append(
        ("Character \(\chi_{%s}(%s, \cdot)\)" % (level, character), url_for('emf.render_elliptic_modular_forms', level=level, weight=weight, character=character)))
    # emf_logger.debug("friends={0}".format(friends))
    info['bread'] = bread
    emf_logger.debug("info={0}".format(info))
    if info.has_key('space'):
        emf_logger.debug("space={0}".format(info['space']))        
        emf_logger.debug("dimension={0}".format(info['space'].dimension))    
    return render_template("emf_web_modform_space.html", **info)



    
def set_info_for_modular_form_space(level=None, weight=None, character=None, label=None, **kwds):
    r"""
      Set information about a space of modular forms.
    """
    info = dict()
    emf_logger.debug("info={0}".format(info))    
    WMFS = None
    if level <= 0:
        info['error'] = "Got wrong level: %s " % level
        return info
    try:
        WMFS = WebModFormSpace_cached(level = level, weight = weight, cuspidal=True,character = character)
        emf_logger.debug("Created WebModFormSpace %s"%WMFS)
        if 'download' in info and 'tempfile' in info:
            save(WNF,info['tempfile'])
            info['filename'] = str(weight) + '-' + str(level) + '-' + str(character) + '-' + label + '.sobj'
            return info
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
        #if WMFS.dimension_new_cusp_forms()<>len(WMFS.hecke_orbits):
        #    ## Try to add them here... 
        #    for d in range(len(WMFS.dimension_new_cusp_forms())):
        #        F = 
        #        WMFS.hecke_orbits.append(F)
        info = {'space':WMFS}
#    info['old_decomposition'] = WMFS.oldspace_decomposition()

    ## For side-bar
    lifts = list()
    lifts.append(('Half-Integral Weight Forms', '/ModularForm/Mp2/Q'))
    lifts.append(('Siegel Modular Forms', '/ModularForm/GSp4/Q'))
    info['lifts'] = lifts
    friends = list()
    for label in WMFS.hecke_orbits:
        f = WMFS.hecke_orbits[label]
        friends.append(('Number field ' + f.base_field_label(), f.base_field_url()))
        if f.coefficient_field_label(check=True):
            friends.append(('Number field ' + f.coefficient_field_label(), f.coefficient_field_url()))
    friends.append(("Dirichlet character \(" + WMFS.character.latex_name + "\)", WMFS.character.url()))
    friends = uniq(friends)
    info['friends'] = friends
    
    return info
