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

AUTHORS: 
 - Fredrik Strömberg
 - Stephan Ehlen

"""
from flask import render_template, url_for, request, redirect, make_response, send_file, send_from_directory,flash
import os
from lmfdb.base import app, db, getDBConnection
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.utils import to_dict, random_object_from_collection
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace_cached
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import (
    render_fd_plot,
    extract_data_from_jump_to,
    newform_label,
    parse_newform_label)
from emf_render_web_newform import render_web_newform
from emf_render_web_modform_space import render_web_modform_space
from emf_render_web_modform_space_gamma1 import render_web_modform_space_gamma1

from emf_render_navigation import render_elliptic_modular_form_navigation_wp

emf_logger.setLevel(int(100))

@emf.context_processor
def body_class():
    return {'body_class': EMF}

emfdb = None

def db_emf():
    global emfdb
    if emfdb is None:
        emfdb = getDBConnection().modularforms2.webnewforms
    return emfdb

#################
# Top level
#################

###########################################
# Search / Navigate
###########################################

met = ['GET', 'POST']

@emf.route("/ranges", methods=["GET"])
@emf.route("/ranges/", methods=["GET"])
def browse_web_modform_spaces_in_ranges(**kwds):
    r"""
    Browse spaces with level and weight within given ranges. level and weight should be of the form N1-N2 and k1-k2

    """
    emf_logger.debug("request.args={0}".format(request.args))
    level=request.args.getlist('level')
    weight=request.args.getlist('weight')
    group=request.args.getlist('group')
    return render_elliptic_modular_form_navigation_wp(level=level,weight=weight,group=group)


@emf.route("/", methods=met)
@emf.route("/<level>/", methods=met)
@emf.route("/<level>/<weight>/", methods=met)
@emf.route("/<level>/<weight>/<character>/", methods=met)
@emf.route("/<level>/<weight>/<character>/<label>", methods=met)
@emf.route("/<level>/<weight>/<character>/<label>/", methods=met)
def render_elliptic_modular_forms(level=None, weight=None, character=None, label=None,group=None, **kwds):
    r"""
    Default input of same type as required. Note that for holomorphic modular forms: level=0 or weight=0 are non-existent.
    """
    emf_logger.debug(
        "In render: level={0},weight={1},character={2},group={3},label={4}".format(level, weight, character, group, label))
    emf_logger.debug("args={0}".format(request.args))
    emf_logger.debug("args={0}".format(request.form))
    emf_logger.debug("met={0}".format(request.method))
    keys = ['download', 'jump_to']
    info = get_args(request, level, weight, character, group, label, keys=keys)
    valid = validate_parameters(level,weight,character,label,info)
    if isinstance(valid,basestring):
        return redirect(valid,code=301)
    level = info['level']; weight = info['weight']; character = info['character']
    #if info.has_key('error'):
    #    return render_elliptic_modular_form_navigation_wp(error=info['error'])
    emf_logger.debug("info={0}".format(info))
    emf_logger.debug("level=%s, %s" % (level, type(level)))
    emf_logger.debug("label=%s, %s" % (label, type(label)))
    emf_logger.debug("wt=%s, %s" % (weight, type(weight)))
    group = info.get('group',None)
    emf_logger.debug("group=%s, %s" % (group, type(group)))
    if group == 0:
        info['character'] = character = 1 # only trivial character for Gamma_0(N)
    try:
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
        emf_logger.debug("HERE! weight={0} level={1} char={2}".format(weight,level,character))
        if level > 0 and weight > 0 and character > 0:
            if label != '' and not label is None:
                return render_web_newform(**info)
            else:
                return render_web_modform_space(**info)
        if level > 0 and weight > 0 and (group != 0 or character == None):
            return render_web_modform_space_gamma1(**info)
        return render_elliptic_modular_form_navigation_wp(**info)
        # Otherwise we go to the main navigation page
    except IndexError as e: # catch everything here except KeyError below...
        emf_logger.debug("catching exceptions. info={0} e={1}".format(info,e))
        errst = str(e)
        ## Try to customise some of the error messages:
        if 'Character' and 'not exist' in errst:
            errst += " Please choose a character from the table below!"
            flash(errst,'error')
            return render_elliptic_modular_form_navigation_wp(**info)
        if 'WebNewForm_computing' in errst:
            errst = "The space {0}.{1}.{2} is not in the database!".format(level,weight,character)
            flash(errst)
        return render_elliptic_modular_form_navigation_wp()
    except KeyError as e:
        emf_logger.debug("catching exceptions. info={0} e={1}".format(info,e))
        errst = "The orbit {0} is not in the database!".format(newform_label(level,weight,character,label))
        flash(errst)
        return render_elliptic_modular_form_navigation_wp()


from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_download_utils import get_coefficients

@emf.route("/Download/<int:level>/<int:weight>/<int:character>/<label>", methods=['GET', 'POST'])
def get_downloads(level=None, weight=None, character=None, label=None, **kwds):
    keys = ['download', 'download_file', 'tempfile', 'format', 'number','bitprec']
    info = get_args(request, level=level, weight=weight, character=character, label=label, keys=keys)
    if 'download' not in info:
        emf_logger.critical("Download called without specifying what to download! info={0}".format(info))
        return ""
    emf_logger.debug("in get_downloads: info={0}".format(info))
    if info['download'] == 'coefficients':
        info['tempfile'] = "/tmp/tmp_web_mod_form.txt"
        return get_coefficients(info)
    if info['download'] == 'file':
        # there are only a certain number of fixed files that we want people to download
        filename = info['download_file']
        if filename == "web_modforms.py":
            dirname = emf.app.root_static_folder
            try:
                emf_logger.debug("Dirname:{0}, Filename:{1}".format(dirname, filename))
                return send_from_directory(dirname, filename, as_attachment=True, attachment_filename=filename)
            except IOError:
                info['error'] = "Could not find file! "

@emf.route("/random")
def random_form():
    label = random_object_from_collection( db_emf() )['hecke_orbit_label']
    level, weight, character, label = parse_newform_label(label)
    args={}
    args['level'] = level
    args['weight'] = weight
    args['character'] = character
    args['label'] = label
    return redirect(url_for(".render_elliptic_modular_forms", **args), 301)

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


###
###  Helper functions.
###

def get_args(request, level=0, weight=0, character=-1, group=2, label='', keys=[]):
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
    emf_logger.debug("group={0}".format(group))
    info['group'] = my_get(dd, 'group', group, int)
    emf_logger.debug("info[group]={0}".format(info['group']))
    info['label'] = my_get(dd, 'label', label, str)
    for key in keys:
        if key in dd:
            info[key] = my_get(dd, key, '', str)
    return info


from markupsafe import Markup
from ..backend.emf_utils import is_range

def validate_character(level, character):
    """Assumes level is a positive integer N, checks that 0<character<=N
    and gcd(character,N)=1.  Returns None if OK, else a suitable error
    message.
    """
    #print "validate_character(%s,%s)" % (level, character)
    if not isinstance(character,int):
        return "The character number should be an integer. You gave: %s" % character
    from sage.all import GCD
    if character <= 0 or character > level or GCD(level,character)!=1:
        return "The character number should be a positive integer less than or equal to and coprime to the level %s. You gave: %s" % (level, character)
    return 0

def validate_parameters(level=0,weight=0,character=None,label='',info={}):
    #print app.url_map
    emf_logger.debug("validating info={0}".format(info))
    level= info['level']; weight=info['weight']
    character = info['character']; label = info['label']
    t = True
    m = []
    if not info.get('jump_to',None) is None:
        return t
    if is_range(level) or is_range(weight):
        new_url = url_for("emf.browse_web_modform_spaces_in_ranges",**info)
        emf_logger.debug("level or weight is a range so we redirect! url={0}".format(new_url))
        return new_url

    if not level is None and (not isinstance(level,int) or level <= 0):
        m.append("Please provide a positive integer level! You gave: {0}".format(level)); t = False
        if level is None:
            info['level'] = None
        else:
            info['level'] = 0
    if not weight is None and (not isinstance(weight,int) or weight <=0):
        m.append("Please provide a positive integer weight! You gave: {0}".format(weight)); t = False
        if weight is None:
            info['weight']=None
        info['weight'] = 0
    if not character is None:
        res = validate_character(level, character)
        if res:
            m.append(res); t = False
            info['character'] = None
    if not label is None and (not isinstance(label,basestring)):
        m.append('Please provide a label in string format! You gave: {0}'.format(label)); t=False
        info['label']=''
        if label is None:
            info['label'] = None
    if not t:
        msg = "<br>".join(m)
        flash(Markup(msg),'error')
        emf_logger.debug("validate: {0}".format(msg))
        
# If we don't match any arglist above we see if we have only a label
# or else catch malformed urls
@emf.route("/<level>")
@emf.route("/<level>/")
@emf.route("/<level>/<weight>")
@emf.route("/<level>/<weight>/")
@emf.route("/<level>/<weight>/<character>")
@emf.route("/<level>/<weight>/<character>/")
@emf.route("/<level>/<weight>/<character>/<label>")
@emf.route("/<level>/<weight>/<character>/<label>/")
@emf.route("/<level>/<weight>/<character>/<label>/<emb>")
@emf.route("/<level>/<weight>/<character>/<label>/<emb>/")
def redirect_false_route(level=None,weight=None,character=None,label='',emb=None):
    ## jumps only have one field (here level)
    if weight is None:
        args = extract_data_from_jump_to(level)
        emf_logger.debug("args={0}".format(args))
    else:
        args = {'level':level,'weight':weight,'character':character,'label':label}
        #validate_parameters(level,weight,character,label,args)

    return redirect(url_for("emf.render_elliptic_modular_forms",**args), code=301)
    # return render_elliptic_modular_form_navigation_wp(**info)
