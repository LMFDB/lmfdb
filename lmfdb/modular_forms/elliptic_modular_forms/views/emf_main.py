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
Main file for viewing elliptical modular forms.

AUTHOR: Fredrik Strömberg

"""
from flask import render_template, url_for, request, redirect, make_response, send_file, send_from_directory
import os
from lmfdb.base import app, db
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.utils import to_dict
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace_cached
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import render_fd_plot,extract_data_from_jump_to
from emf_render_web_newform import render_web_newform
from emf_render_web_modform_space import render_web_modform_space
from emf_render_web_modform_space_gamma1 import render_web_modform_space_gamma1

from emf_render_navigation import render_elliptic_modular_form_navigation_wp


emf_logger.setLevel(int(10))

@emf.context_processor
def body_class():
    return {'body_class': EMF}

#################
# Top level
#################

###########################################
# Search / Navigate
###########################################

met = ['GET', 'POST']

@emf.route("/", methods=met)
@emf.route("/<int:level>/", methods=met)
@emf.route("/<int:level>/<int:weight>/", methods=met)
@emf.route("/<int:level>/<int:weight>/<int:character>/", methods=met)
@emf.route("/<int:level>/<int:weight>/<int:character>/<label>", methods=met)
@emf.route("/<int:level>/<int:weight>/<int:character>/<label>/", methods=met)
def render_elliptic_modular_forms(level=0, weight=0, character=None, label='', **kwds):
    r"""
    Default input of same type as required. Note that for holomorphic modular forms: level=0 or weight=0 are non-existent.
    """
    if character is None and level == 0 and weight == 0:
        character = 1
    elif character is None:
        character = -1
    emf_logger.debug(
        "In render: level={0},weight={1},character={2},label={3}".format(level, weight, character, label))
    emf_logger.debug("args={0}".format(request.args))
    emf_logger.debug("args={0}".format(request.form))
    emf_logger.debug("met={0}".format(request.method))
    keys = ['download', 'jump_to']
    info = get_args(request, level, weight, character, label, keys=keys)
    level = info['level']
    weight = info['weight']
    character = info['character']
    label = info['label']
    emf_logger.debug("info={0}".format(info))
    emf_logger.debug("level=%s, %s" % (level, type(level)))
    emf_logger.debug("label=%s, %s" % (label, type(label)))
    emf_logger.debug("wt=%s, %s" % (weight, type(weight)))
    emf_logger.debug("character=%s, %s" % (character, type(character)))
    if 'download' in info:
        return get_downloads(**info)
    emf_logger.debug("info=%s" % info)
    ## Consistency of arguments>
    # if level<=0:  level=None
    # if weight<=0:  weight=None
    if 'jump_to' in info:  # try to find out which form we want to jump
        s = my_get(info, 'jump_to', '', str)
        emf_logger.info("info.keys1={0}".format(info.keys()))
        info.pop('jump_to')
        emf_logger.info("info.keys2={0}".format(info.keys()))
        args = extract_data_from_jump_to(s)
        emf_logger.debug("args=%s" % args)
        return redirect(url_for("emf.render_elliptic_modular_forms", **args), code=301)
        # return render_elliptic_modular_forms(**args)
    if level > 0 and weight > 0 and character > 0 and label != '':
        emf_logger.debug("info=%s" % info)
        return render_web_newform(**info)
    if level > 0 and weight > 0 and character > 0:
        return render_web_modform_space(**info)
    if level > 0 and weight > 0:
        return render_web_modform_space_gamma1(**info)
    # Otherwise we go to the main navigation page
    return render_elliptic_modular_form_navigation_wp(**info)

from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_download_utils import download_web_modform,get_coefficients

@emf.route("/Download/<int:level>/<int:weight>/<int:character>/<label>", methods=['GET', 'POST'])
def get_downloads(level=None, weight=None, character=None, label=None, **kwds):
    keys = ['download', 'download_file', 'tempfile', 'format', 'number','bitprec']
    info = get_args(request, level, weight, character, label, keys=keys)
    if 'download' not in info:
        emf_logger.critical("Download called without specifying what to download! info={0}".format(info))
        return ""
    emf_logger.debug("in get_downloads: info={0}".format(info))
    if info['download'] == 'file':
        # there are only a certain number of fixed files that we want people to download
        filename = info['download_file']
        if filename == "web_modforms.py":
            dirname = emf.app.root_static_folder
            try:
                emf_logger.debug("Dirname:{0}, Filename:{1}".format(dirname, filename))
                return send_from_directory(dirname, filename, as_attachment=True, attachment_filename=filename)
            except IOError:
                info['error'] = "Could not find  file! "
    if info['download'] == 'coefficients':
        info['tempfile'] = "/tmp/tmp_web_mod_form.txt"
        return get_coefficients(info)
    if info['download'] == 'object':
        return download_web_modform(info)
        info['error'] = "Could not find  file! "

@emf.route("/Plots/<int:grouptype>/<int:level>/")
def render_plot(grouptype=0, level=1):
    domain = render_fd_plot(level, {'grouptype': grouptype})
    if isinstance(domain, sage.plot.plot.Graphics):
        emf_logger.debug('Got a Graphics object')
        _, filename = tempfile.mkstemp('.png')
        domain.save(filename)
        data = open(filename).read()
        os.unlink(filename)
    else:
        data = domain
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response

@emf.route("/Qexp/<int:level>/<int:weight>/<int:character>/<label>/<int:prec>")
def get_qexp(level, weight, character, label, prec, latex=False, **kwds):
    emf_logger.debug(
        "get_qexp for: level={0},weight={1},character={2},label={3}".format(level, weight, character, label))
    #latex = my_get(request.args, "latex", False, bool)
    emf_logger.debug(
        "get_qexp latex: {0}, prec: {1}".format(latex, prec))
    #if not arg:
    #    return flask.abort(404)
    try:
        M = WebModFormSpace_cached(level=level,weight=weight,character=character)
        WNF = M.hecke_orbits[label]
        WNF.prec = prec
        if not latex:
            c = WNF.q_expansion
        else:
            c = WNF.q_expansion_latex(prec=prec, name = 'a')
        return c
    except Exception as e:
        return "<span style='color:red;'>ERROR: %s</span>" % e.message

@emf.route("/qexp_latex/<int:level>/<int:weight>/<int:character>/<label>/<int:prec>")
@emf.route("/qexp_latex/<int:level>/<int:weight>/<int:character>/<label>/")
def get_qexp_latex(level, weight, character, label, prec=10, **kwds):
    return get_qexp(level, weight, character, label, prec, latex=True, **kwds)

# If we don't match any arglist above we see if we have only a label
@emf.route("/<test>/")
def redirect_false_route(test=None):
    args = extract_data_from_jump_to(test)
    return redirect(url_for("emf.render_elliptic_modular_forms",**args), code=301)
    # return render_elliptic_modular_form_navigation_wp(**info)

def get_args(request, level=0, weight=0, character=-1, label='', keys=[]):
    r"""
    Use default input of the same type as desired output.
    """
    if request.method == 'GET':
        dd = to_dict(request.args)
    else:
        dd = to_dict(request.form)
    emf_logger.debug("REQUEST:{0}".format(dd))
    info = dict()
    info['level'] = my_get(dd, 'level', level, int)
    info['weight'] = my_get(dd, 'weight', weight, int)
    info['character'] = my_get(dd, 'character', character, int)
    info['label'] = my_get(dd, 'label', label, str)
    for key in keys:
        if key in dd:
            info[key] = my_get(dd, key, '', str)
    return info


