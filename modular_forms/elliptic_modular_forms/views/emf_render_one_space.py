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
from flask import render_template, url_for, request, redirect, make_response,send_file
import tempfile, os,re
from utils import ajax_more,ajax_result,make_logger
from sage.all import *
from  sage.modular.dirichlet import DirichletGroup
from base import app, db
from modular_forms.elliptic_modular_forms.backend.web_modforms import WebModFormSpace,WebNewForm
from modular_forms.elliptic_modular_forms.backend.emf_classes import ClassicalMFDisplay
from modular_forms.backend.mf_utils import my_get
from modular_forms.elliptic_modular_forms.backend.emf_core import *
from modular_forms.elliptic_modular_forms.backend.emf_utils import *
from modular_forms.elliptic_modular_forms.backend.plot_dom import *
from modular_forms.elliptic_modular_forms import EMF, emf_logger, emf



def render_elliptic_modular_form_space(info):
    r"""
    Render the webpage for a elliptic modular forms space.
    """
    level  = my_get(info,'level', -1,int)
    weight = my_get(info,'weight',-1,int)
    character = my_get(info,'character', '',str) #int(info.get('weight',0))
    label = my_get(info,'label', 'a',str)
    if character=='':
        character=0
    properties=list(); parents=list(); friends=list(); lifts=list(); siblings=list()
    sbar=(properties,parents,friends,siblings,lifts)
    if info.has_key('character') and info['character']=='*':
        return render_elliptic_modular_form_space_list_chars(level,weight)
    ### This might take forever....
    info=set_info_for_modular_form_space(info)
    emf_logger.debug("keys={0}".format(info.keys()))
    if info.has_key('download') and not info.has_key('error'):
        return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    if info.has_key('dimension_newspace') and info['dimension_newspace']==1: # if there is only one orbit we list it
        emf_logger.debug("Dimension of newforms is one!")
        info =dict()
        info['level']=level; info['weight']=weight; info['label']='a'; info['character']=character
        return redirect(url_for('emf.render_elliptic_modular_forms', **info))
    info['title'] = "Holomorphic Cusp Forms of weight %s on \(\Gamma_{0}(%s)\)" %(weight,level)
    bread =[(MF_TOP,url_for('mf.modular_form_main_page'))]
    bread.append((EMF_TOP,url_for('emf.render_elliptic_modular_forms')))
    bread.append(("Level %s" %level,url_for('emf.render_elliptic_modular_forms',level=level)))
    bread.append(("Weight %s" %weight,url_for('emf.render_elliptic_modular_forms',level=level,weight=weight)))
    emf_logger.debug("friends={0}".format(friends))
    info['bread']=bread
    if info['dimension_newspace']==0:
        return render_template("emf_space.html", **info)
    else:
        return render_template("emf_space.html", **info)

