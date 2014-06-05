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
from lmfdb.utils import ajax_more, ajax_result, make_logger, to_dict, url_character
from sage.all import uniq
from sage.modular.dirichlet import DirichletGroup
from lmfdb.base import app, db
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modforms import WebNewForm,connect_to_modularforms_db
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_classes import ClassicalMFDisplay, DimensionTable
from lmfdb.modular_forms import MF_TOP
from lmfdb.modular_forms.elliptic_modular_forms import N_max_comp, k_max_comp, N_max_db, k_max_db
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_core import *
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import *
from lmfdb.modular_forms.elliptic_modular_forms.backend.plot_dom import *
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf, EMF_TOP
###
###


def render_elliptic_modular_form_space(level=None, weight=None, character=None, label=None, **kwds):
    r"""
    Render the webpage for a elliptic modular forms space.
    """
    emf_logger.debug("In render_ellitpic_modular_form_space kwds: {0}".format(kwds))
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
    #if not dimtbl.is_in_db(level, weight, character):
    #    emf_logger.debug("Data not available")
    #    return render_template("not_available.html")
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
    info['title'] = "Newforms of weight %s for \(\Gamma_{0}(%s)\) with character \(\chi_{%s}(%s, \cdot)\)" % (weight, level, level, character)
    bread = [(EMF_TOP, url_for('emf.render_elliptic_modular_forms'))]
    bread.append(("Level %s" % level, url_for('emf.render_elliptic_modular_forms', level=level)))
    bread.append(
        ("Weight %s" % weight, url_for('emf.render_elliptic_modular_forms', level=level, weight=weight)))
    bread.append(
        ("Character \(\chi_{%s}(%s, \cdot)\)" % (level, character), url_for('emf.render_elliptic_modular_forms', level=level, weight=weight, character=character)))
    # emf_logger.debug("friends={0}".format(friends))
    info['bread'] = bread
    return render_template("emf_space.html", **info)


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
        WMFS = WebModFormSpace(N = level, k = weight, chi = character, get_all_newforms_from_db = True, get_from_db = True)
        emf_logger.debug("Created WebModFormSpace %s"%WMFS)
        if 'download' in info and 'tempfile' in info:
            WNF._save_to_file(info['tempfile'])
            info['filename'] = str(weight) + '-' + str(level) + '-' + str(character) + '-' + label + '.sobj'
            return info
    except Exception as e:
        emf_logger.debug(e)
        if isinstance(e,IndexError):
            info['error'] = e.message
        WMFS = None
    if WMFS is None:
        info['error'] = "We are sorry. The sought space can not be found in the database."
        return info
    else:
        info = WMFS.to_web_dict()

    ## we try to catch well-known bugs...
    info['old_decomposition'] = "n/a"
    # properties for the sidebar
    ## Make parent spaces of S_k(N,chi) for the sidebar
    par_lbl = '\( S_{*} (\Gamma_0(' + str(level) + '),\cdot )\)'
    par_url = '?level=' + str(level)
    parents = [[par_lbl, par_url]]
    par_lbl = '\( S_{k} (\Gamma_0(' + str(level) + '),\cdot )\)'
    par_url = '?level=' + str(level) + '&weight=' + str(weight)
    parents.append((par_lbl, par_url))
    info['parents'] = parents
    
    lifts = list()
    lifts.append(('Half-Integral Weight Forms', '/ModularForm/Mp2/Q'))
    lifts.append(('Siegel Modular Forms', '/ModularForm/GSp4/Q'))
    info['lifts'] = lifts

    friends = list()
    for f in WMFS.newforms().values():
        friends.append(('Number field ' + f.coefficient_field_label(), f.coefficient_field_url()))
    friends.append(('Number field ' + f.base_field_label(), f.base_field_url()))
    friends = uniq(friends)
    friends.append(("Dirichlet character \(" + WMFS.character().latex_name() + "\)", WMFS.character().url()))
    info['friends'] = friends
    
    return info
