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

AUTHOR: Fredrik Strömberg

"""
from flask import render_template, url_for, request, redirect, make_response, send_file
import tempfile
import os
import re
from lmfdb.utils import ajax_more, ajax_result, make_logger, to_dict
from sage.all import *
from sage.modular.dirichlet import DirichletGroup
from lmfdb.base import app, db
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modforms import WebModFormSpace, WebNewForm,connect_to_modularforms_db
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_classes import ClassicalMFDisplay, DimensionTable
from lmfdb.modular_forms import MF_TOP
from lmfdb.modular_forms.elliptic_modular_forms import N_max_comp, k_max_comp, N_max_db, k_max_db
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_core import *
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import *
from lmfdb.modular_forms.elliptic_modular_forms.backend.plot_dom import *
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf, EMF_TOP
###
##use_db = True  # Should be decided intelligently
###


def render_elliptic_modular_form_space(level=None, weight=None, character=None, label=None, **kwds):
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
    # if kwds.has_key('character') and kwds['character']=='*':
    #    return render_elliptic_modular_form_space_list_chars(level,weight)
    if character == 0:
        dimtbl = DimensionTable()
    else:
        dimtbl = DimensionTable(1)
    if not dimtbl.is_in_db(level, weight, character):
        emf_logger.debug("Data not available")
        if character == 0:
            d = dimension_new_cusp_forms(level,weight)
        else:
            D = DirichletGroup(level)
            x = D.galois_orbits(reps_only=True)[character]
            d = dimension_new_cusp_forms(x,weight)
        if d>0:
            return render_template("not_available.html")
        else:
            info['is_empty'] = True 
            return render_template("emf_space.html", **info)
        
    emf_logger.debug("Created dimension table in render_elliptic_modular_form_space")
    info = set_info_for_modular_form_space(**info)
    emf_logger.debug("keys={0}".format(info.keys()))
    if 'download' in kwds and 'error' not in kwds:
        return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    if 'dimension_newspace' in kwds and kwds['dimension_newspace'] == 1:
        # if there is only one orbit we list it
        emf_logger.debug("Dimension of newforms is one!")
        info['label'] = 'a'
        return redirect(url_for('emf.render_elliptic_modular_forms', **info))
    info['title'] = "Newforms of weight %s on \(\Gamma_{0}(%s)\)" % (weight, level)
    bread = [(EMF_TOP, url_for('emf.render_elliptic_modular_forms'))]
    bread.append(("Level %s" % level, url_for('emf.render_elliptic_modular_forms', level=level)))
    bread.append(
        ("Weight %s" % weight, url_for('emf.render_elliptic_modular_forms', level=level, weight=weight)))
    # emf_logger.debug("friends={0}".format(friends))
    info['bread'] = bread
    return render_template("emf_space.html", **info)


def set_info_for_modular_form_space(level=None, weight=None, character=None, label=None, **kwds):
    r"""
    Set information about a space of modular forms.
    """
    info = dict()
    info['level'] = level
    info['weight'] = weight
    info['character'] = character
    emf_logger.debug("info={0}".format(info))
#    DB = connect_to_modularforms_db()
#    if level <> None and weight <> None and character <> None:
#        s = {'N':int(level),'k':int(weight),'chi':int(character)}
#        if DB.Newform_factors.files.find(s).count()==0:
#            
    #    if(level > N_max_db or weight > k_max_db):
#        info['error'] = "Currently not available"
#    
    WMFS = None
    if level <= 0:
        info['error'] = "Got wrong level: %s " % level
        return info
    try:
        WMFS = WebModFormSpace(N = level, k = weight, chi = character)
        if 'download' in info and 'tempfile' in info:
            WNF._save_to_file(info['tempfile'])
            info['filename'] = str(weight) + '-' + str(level) + '-' + str(character) + '-' + label + '.sobj'
            return info
    except Exception as e:
        if isinstance(e,IndexError):
            info['error'] = e.message
        WMFS = None
    if WMFS == None:
        info['error'] = "We are sorry. The sought space can not be found in the database."
        return info
    if WMFS.level() == 1:
        info['group'] = "\( \mathrm{SL}_{2}(\mathbb{Z})\)"
    else:
        info['group'] = "\( \Gamma_{{0}}( {0} ) \)".format(WMFS.level())
    if character == 0:
        info['name_new'] = "\(S_{ %s }^{new}(%s) \)" % (WMFS.weight(), WMFS.level())
        info['name_old'] = "\(S_{ %s }^{old}(%s) \)" % (WMFS.weight(), WMFS.level())
    else:
        conrey_char = WMFS.conrey_character()
        conrey_char_name = WMFS.conrey_character_name()
        info['conrey_character_name'] = '\( ' + conrey_char_name + '\)'
        info['character_url'] = url_for('characters.render_Dirichletwebpage', modulus=WMFS.level(), number=conrey_char.number())
        info['name_new'] = "\(S_{ %s }^{new}(%s,%s) \)" % (WMFS.weight(), WMFS.level(), conrey_char_name)
        info['name_old'] = "\(S_{ %s }^{old}(%s,%s) \)" % (WMFS.weight(), WMFS.level(), conrey_char_name)
    info['dimension_cusp_forms'] = WMFS.dimension_cusp_forms()
    info['dimension_mod_forms'] = WMFS.dimension_modular_forms()
    info['dimension_new_cusp_forms'] = WMFS.dimension_new_cusp_forms()
    info['dimension_newspace'] = WMFS.dimension_newspace()
    info['dimension_oldspace'] = WMFS.dimension_oldspace()
    info['dimension'] = WMFS.dimension()
    info['galois_orbits'] = WMFS.get_all_galois_orbit_info()
    lifts = list()
    if WMFS.dimension() == 0:  # we don't need to work with an empty space
        info['sturm_bound'] = 0
        info['new_decomposition'] = ''
        info['is_empty'] = 1
        lifts.append(('Half-Integral Weight Forms', '/ModularForm/Mp2/Q'))
        lifts.append(('Siegel Modular Forms', '/ModularForm/GSp4/Q'))
        info['lifts'] = lifts
        return info
    info['sturm_bound'] = WMFS.sturm_bound()
    info['new_decomposition'] = WMFS.print_galois_orbits()
    emf_logger.debug("new_decomp={0}".format(info['new_decomposition']))
    info['nontrivial_new'] = len(info['new_decomposition'])
    if info['new_decomposition']=='':
        if info['dimension_newspace'] >0:
            info['nontrivial_new_info'] = " is unfortunately not in the database yet!" 
        else:
            info['nontrivial_new_info'] = " is empty!"
    ## we try to catch well-known bugs...
    info['old_decomposition'] = "n/a"
    if level < N_max_comp:
        try:
            O = WMFS.print_oldspace_decomposition()
            info['old_decomposition'] = O
        except:
            emf_logger.critical("Error in computing oldspace decomposition")
            O = []
            info['old_decomposition'] = ""
            (A, B, C) = sys.exc_info()
            # build an error message...
            errtype = A.__name__
            errmsg = B
            s = "%s: %s  at:" % (errtype, errmsg)
            next = C.tb_next
            while(next):
                ln = next.tb_lineno
                filen = next.tb_frame.f_code.co_filename
                s += "\n line no. %s in file %s" % (ln, filen)
                next = next.tb_next
                info['error_note'] = "Could not construct oldspace!\n" + s
    # properties for the sidebar
    prop = []
    if WMFS._cuspidal == 1:
        prop = [('Dimension newforms', [info['dimension_newspace']])]
        prop.append(('Dimension oldforms', [info['dimension_oldspace']]))
    else:
        prop = [('Dimension modular forms', [info['dimension_mod_forms']])]
        prop.append(('Dimension cusp forms', [info['dimension_cusp_forms']]))
    prop.append(('Sturm bound', [WMFS.sturm_bound()]))
    info['properties2'] = prop
    ## Make parent spaces of S_k(N,chi) for the sidebar
    par_lbl = '\( S_{*} (\Gamma_0(' + str(level) + '),\cdot )\)'
    par_url = '?level=' + str(level)
    parents = [[par_lbl, par_url]]
    par_lbl = '\( S_{k} (\Gamma_0(' + str(level) + '),\cdot )\)'
    par_url = '?level=' + str(level) + '&weight=' + str(weight)
    parents.append((par_lbl, par_url))
    info['parents'] = parents
    if 'character' in info:
        info['character_order'] = WMFS.character_order()
        info['character_conductor'] = WMFS.character_conductor()
    friends = list()
    lifts = list()
    if(('label' not in info) and info['old_decomposition'] != 'n/a'):
        O = WMFS.oldspace_decomposition()
        try:
            for (old_level, chi, mult, d) in O:
                if chi != 0:
                    s = "\(S_{%s}(\Gamma_0(%s),\chi_{%s}) \) " % (weight, old_level, chi)
                    friends.append((
                        s, '?weight=' + str(weight) + '&level=' + str(old_level) + '&character=' + str(chi)))
                else:
                    s = "\(S_{%s}(\Gamma_0(%s)) \) " % (weight, old_level)
                    friends.append(
                        (s, '?weight=' + str(weight) + '&level=' + str(old_level) + '&character=' + str(0)))
        except:
            pass
    info['friends'] = friends
    lifts.append(('Half-Integral Weight Forms', '/ModularForm/Mp2/Q'))
    lifts.append(('Siegel Modular Forms', '/ModularForm/GSp4/Q'))
    info['lifts'] = lifts
    #emf_logger.debug("Info = {0}".format(info))
    return info
