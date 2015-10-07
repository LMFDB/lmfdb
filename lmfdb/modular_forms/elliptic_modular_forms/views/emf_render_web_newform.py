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

AUTHORS:
 - Fredrik Strömberg
 - Stephan Ehlen

"""
from flask import render_template, url_for,  send_file
from sage.all import version,uniq,ZZ,Cusp,Infinity,latex,QQ
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_newforms import WebNewForm_cached, WebNewForm
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import WebModFormSpace_cached
from lmfdb.utils import to_dict,ajax_more
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf, default_prec, default_bprec, default_display_bprec,EMF_TOP

def render_web_newform(level, weight, character, label, **kwds):
    r"""
    Renders the webpage for one elliptic modular form.

    """
    citation = ['Sage:' + version()]
    info = set_info_for_web_newform(level, weight, character, label, **kwds)
    emf_logger.debug("info={0}".format(info.keys()))
    err = info.get('error', '')
    ## Check if we want to download either file of the function or Fourier coefficients
    if 'download' in info and 'error' not in info:
        return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    return render_template("emf_web_newform.html", **info)


def set_info_for_web_newform(level=None, weight=None, character=None, label=None, **kwds):
    r"""
    Set the info for on modular form.

    """
    info = to_dict(kwds)
    info['level'] = level
    info['weight'] = weight
    info['character'] = character
    info['label'] = label
    if level is None or weight is None or character is None or label is None:
        s = "In set info for one form but do not have enough args!"
        s += "level={0},weight={1},character={2},label={3}".format(level, weight, character, label)
        emf_logger.critical(s)
    emf_logger.debug("In set_info_for_one_mf: info={0}".format(info))
    prec = my_get(info, 'prec', default_prec, int)
    bprec = my_get(info, 'bprec', default_display_bprec, int)
    emf_logger.debug("PREC: {0}".format(prec))
    emf_logger.debug("BITPREC: {0}".format(bprec))    
    try:
        WNF = WebNewForm_cached(level=level, weight=weight, character=character, label=label)
        emf_logger.critical("defined webnewform for rendering!")
        # if info.has_key('download') and info.has_key('tempfile'):
        #     WNF._save_to_file(info['tempfile'])
        #     info['filename']=str(weight)+'-'+str(level)+'-'+str(character)+'-'+label+'.sobj'
        #     return info
    except IndexError as e:
        WNF = None
        info['error'] = e.message
    url1 = url_for("emf.render_elliptic_modular_forms")
    url2 = url_for("emf.render_elliptic_modular_forms", level=level)
    url3 = url_for("emf.render_elliptic_modular_forms", level=level, weight=weight)
    url4 = url_for("emf.render_elliptic_modular_forms", level=level, weight=weight, character=character)
    bread = [(EMF_TOP, url1)]
    bread.append(("of level %s" % level, url2))
    bread.append(("weight %s" % weight, url3))
    if int(character) == 0:
        bread.append(("trivial character", url4))
    else:
        bread.append(("\( %s \)" % (WNF.character.latex_name), url4))
    info['bread'] = bread
    
    properties2 = list()
    friends = list()
    space_url = url_for('emf.render_elliptic_modular_forms',level=level, weight=weight, character=character)
    friends.append(('\( S_{%s}(%s, %s)\)'%(WNF.weight, WNF.level, WNF.character.latex_name), space_url))
    if WNF.coefficient_field_label(check=True):
        friends.append(('Number field ' + WNF.coefficient_field_label(), WNF.coefficient_field_url()))
    friends.append(('Number field ' + WNF.base_field_label(), WNF.base_field_url()))
    friends = uniq(friends)
    friends.append(("Dirichlet character \(" + WNF.character.latex_name + "\)", WNF.character.url()))
    
    if WNF.dimension==0:
        info['error'] = "This space is empty!"

#    emf_logger.debug("WNF={0}".format(WNF))    

    #info['name'] = name
    info['title'] = 'Modular Form ' + WNF.hecke_orbit_label
    
    if 'error' in info:
        return info
    # info['name']=WNF._name
    ## Until we have figured out how to do the embeddings correctly we don't display the Satake
    ## parameters for non-trivial characters....

    cdeg = WNF.coefficient_field.absolute_degree()
    bdeg = WNF.base_ring.absolute_degree()
    if WNF.coefficient_field.absolute_degree() == 1:
        rdeg = 1
    else:
        rdeg = WNF.coefficient_field.relative_degree()
    if cdeg==1:
        info['satake'] = WNF.satake
    info['qexp'] = WNF.q_expansion_latex(prec=10, name='a')
    info['qexp_display'] = url_for(".get_qexp_latex", level=level, weight=weight, character=character, label=label)
    
    # info['qexp'] = WNF.q_expansion_latex(prec=prec)
    #c_pol_st = str(WNF.absolute_polynomial)
    #b_pol_st = str(WNF.polynomial(type='base_ring',format='str'))
    #b_pol_ltx = str(WNF.polynomial(type='base_ring',format='latex'))
    #print "c=",c_pol_ltx
    #print "b=",b_pol_ltx
    if cdeg > 1: ## Field is QQ
        if bdeg > 1 and rdeg>1:
            p1 = WNF.coefficient_field.relative_polynomial()
            c_pol_ltx = latex(p1)
            lgc = p1.variables()[0]
            c_pol_ltx = c_pol_ltx.replace(lgc,'a')
            z = p1.base_ring().gens()[0]
            p2 = z.minpoly()
            b_pol_ltx = latex(p2)
            b_pol_ltx = b_pol_ltx.replace(latex(p2.variables()[0]),latex(z)) 
            info['polynomial_st'] = 'where \({0}=0\) and \({1}=0\).'.format(c_pol_ltx,b_pol_ltx)
        else:
            c_pol_ltx = latex(WNF.coefficient_field.relative_polynomial())
            lgc = str(latex(WNF.coefficient_field.relative_polynomial().variables()[0]))
            c_pol_ltx = c_pol_ltx.replace(lgc,'a')
            info['polynomial_st'] = 'where \({0}=0\)'.format(c_pol_ltx) 
    else:
        info['polynomial_st'] = ''
    info['degree'] = int(cdeg)
    if cdeg==1:
        info['is_rational'] = 1
    else:
        info['is_rational'] = 0
    # info['q_exp_embeddings'] = WNF.print_q_expansion_embeddings()
    # if(int(info['degree'])>1 and WNF.dimension()>1):
    #    s = 'One can embed it into \( \mathbb{C} \) as:'
        # bprec = 26
        # print s
    #    info['embeddings'] =  ajax_more2(WNF.print_q_expansion_embeddings,{'prec':[5,10,25,50],'bprec':[26,53,106]},text=['more coeffs.','higher precision'])
    # elif(int(info['degree'])>1):
    #    s = 'There are '+str(info['degree'])+' embeddings into \( \mathbb{C} \):'
        # bprec = 26
        # print s
    #    info['embeddings'] =  ajax_more2(WNF.print_q_expansion_embeddings,{'prec':[5,10,25,50],'bprec':[26,53,106]},text=['more coeffs.','higher precision'])
    # else:
    #    info['embeddings'] = ''
    emf_logger.debug("PREC2: {0}".format(prec))
    info['embeddings'] = WNF._embeddings['values'] #q_expansion_embeddings(prec, bprec,format='latex')
    info['embeddings_len'] = len(info['embeddings'])
    properties2 = []
    if (ZZ(level)).is_squarefree():
        info['twist_info'] = WNF.twist_info
        if isinstance(info['twist_info'], list) and len(info['twist_info'])>0:
            info['is_minimal'] = info['twist_info'][0]
            if(info['twist_info'][0]):
                s = '- Is minimal<br>'
            else:
                s = '- Is a twist of lower level<br>'
            properties2 = [('Twist info', s)]
    else:
        info['twist_info'] = 'Twist info currently not available.'
        properties2 = [('Twist info', 'not available')]
    args = list()
    for x in range(5, 200, 10):
        args.append({'digits': x})
    alev = None
    CM = WNF._cm_values
    if CM is not None:
        if CM.has_key('tau') and len(CM['tau']) != 0:
            info['CM_values'] = CM
    info['is_cm'] = WNF.is_cm
    if WNF.is_cm is None:
        s = '- Unknown (insufficient data)<br>'
    elif WNF.is_cm is True:
        s = '- Is a CM-form<br>'
    else:
        s = '- Is not a CM-form<br>'
    properties2.append(('CM info', s))
    alev = WNF.atkin_lehner_eigenvalues()
    info['atkinlehner'] = None
    if isinstance(alev,dict) and len(alev.keys())>0 and level != 1:
        s1 = " Atkin-Lehner eigenvalues "
        s2 = ""
        for Q in alev.keys():
            s2 += "\( \omega_{ %s } \) : %s <br>" % (Q, alev[Q])
        properties2.append((s1, s2))
        emf_logger.debug("properties={0}".format(properties2))
        # alev = WNF.atkin_lehner_eigenvalues_for_all_cusps() 
        # if isinstance(alev,dict) and len(alev.keys())>0:
        #     emf_logger.debug("alev={0}".format(alev))
        #     info['atkinlehner'] = list()
        #     for Q in alev.keys():
        #         s = "\(" + latex(c) + "\)"
        #         Q = alev[c][0]
        #         ev = alev[c][1]
        #         info['atkinlehner'].append([Q, c, ev])
    if(level == 1):
        poly = WNF.explicit_formulas.get('as_polynomial_in_E4_and_E6','')
        if poly <> '':
            d,monom,coeffs = poly
            emf_logger.critical("poly={0}".format(poly))

            info['explicit_formulas'] = '\('
            for i in range(d):
                c = QQ(coeffs[i])
                s = ""
                if d>1 and i >0 and c>0:
                    s="+"
                if c<0:
                    s="-"
                if c.denominator()>1:
                    cc = "\\frac{{ {0} }}{{ {1} }}".format(abs(c.numerator()),c.denominator())
                else:
                    cc = str(abs(c))
                s += "{0} \cdot ".format(cc)
                a = monom[i][0]; b = monom[i][1]
                if a == 0 and b<>0:
                    s+="E_6^{{ {0} }}".format(b)
                elif b ==0 and a<>0:
                    s+="E_4^{{ {0} }}".format(a)
                else:
                    s+="E_4^{{ {0} }}E_6^{{ {1} }}".format(a,b)
                info['explicit_formulas'] += s
            info['explicit_formulas'] += " \)"            
    cur_url = '?&level=' + str(level) + '&weight=' + str(weight) + '&character=' + str(character) + \
        '&label=' + str(label)
    if len(WNF.parent.hecke_orbits) > 1:
        for label_other in WNF.parent.hecke_orbits.keys():
            if(label_other != label):
                s = 'Modular form '
                if character:
                    s = s + str(level) + '.' + str(weight) + '.' + str(character) + str(label_other)
                else:
                    s = s + str(level) + '.' + str(weight) + str(label_other)
                url = url_for('emf.render_elliptic_modular_forms', level=level,
                              weight=weight, character=character, label=label_other)
                friends.append((s, url))

    s = 'L-Function '
    if character:
        s = s + str(level) + '.' + str(weight) + '.' + str(character) + str(label)
    else:
        s = s + str(level) + '.' + str(weight) + str(label)
    # url =
    # "/L/ModularForm/GL2/Q/holomorphic?level=%s&weight=%s&character=%s&label=%s&number=%s"
    # %(level,weight,character,label,0)
    url = '/L' + url_for(
        'emf.render_elliptic_modular_forms', level=level, weight=weight, character=character, label=label)
    if WNF.coefficient_field_degree > 1:
        for h in range(WNF.coefficient_field_degree):
            s0 = s + ".{0}".format(h)
            url0 = url + "{0}/".format(h)
            friends.append((s0, url0))
    else:
        friends.append((s, url))
    # if there is an elliptic curve over Q associated to self we also list that
    if WNF.weight == 2 and WNF.coefficient_field_degree == 1:
        llabel = str(level) + '.' + label
        s = 'Elliptic curve isogeny class ' + llabel
        url = '/EllipticCurve/Q/' + llabel
        friends.append((s, url))
    info['properties2'] = properties2
    info['friends'] = friends
    info['max_cn']=WNF.max_cn()
    return info

import flask


## @emf.route("/Qexp/<int:level>/<int:weight>/<int:character>/<label>")
## def get_qexp(level, weight, character, label, **kwds):
##     emf_logger.debug(
##         "get_qexp for: level={0},weight={1},character={2},label={3}".format(level, weight, character, label))
##     prec = my_get(request.args, "prec", default_prec, int)
##     latex = my_get(request.args, "latex", False, bool)
##     if not arg:
##         return flask.abort(404)
##     try:
##         WNF = WebNewForm(level, weight, chi=character, label=label, prec=prec, verbose=2)
##         nc = max(prec, 5)
##         if not latex:
##             c = WNF.print_q_expansion(nc)
##         else:
##             c = WNF.q_expansion_latex(nc)
##         return c
##     except Exception as e:
##         return "<span style='color:red;'>ERROR: %s</span>" % e.message

## @emf.route("/qexp_latex/<int:level>/<int:weight>/<int:character>/<label>")
## def get_qexp_latex(level, weight, character, label, **kwds):
##     return get_qexp(level, weight, character, label, latex=True, **kwds)
