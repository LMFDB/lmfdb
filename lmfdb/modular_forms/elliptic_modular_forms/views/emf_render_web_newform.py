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
from sage.all import uniq,ZZ,latex,QQ
from lmfdb.utils import to_dict
from lmfdb.modular_forms import MF_TOP
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_newforms import WebNewForm_cached
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger, default_prec, default_display_bprec, EMF_TOP, default_max_height
#from lmfdb.number_fields.number_field import poly_to_field_label, field_pretty, nf_display_knowl
from lmfdb.WebNumberField import field_pretty, nf_display_knowl
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_object import web_latex_poly
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import newform_label
from lmfdb.base import getDBConnection

def render_web_newform(level, weight, character, label, **kwds):
    r"""
    Renders the webpage for one elliptic modular form.

    """
    # citation = ['Sage:' + version()] # never used
    info = set_info_for_web_newform(level, weight, character, label, **kwds)
    emf_logger.debug("info={0}".format(info.keys()))
    ## Check if we want to download either file of the function or Fourier coefficients
    if 'download' in info and 'error' not in info:
        return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'], add_etags=False)
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
        if not WNF.has_updated():
            raise IndexError("Unfortunately, we do not have this newform in the database.")
        info['character_order'] = WNF.character.order
        info['code'] = WNF.code
        emf_logger.debug("defined webnewform for rendering!")
    except IndexError as e:
        info['error'] = e.message
    url0 = url_for("mf.modular_form_main_page")
    url1 = url_for("emf.render_elliptic_modular_forms")
    url2 = url_for("emf.render_elliptic_modular_forms", level=level)
    url3 = url_for("emf.render_elliptic_modular_forms", level=level, weight=weight)
    url4 = url_for("emf.render_elliptic_modular_forms", level=level, weight=weight, character=character)
    bread = [(MF_TOP, url0), (EMF_TOP, url1)]
    bread.append(("Level %s" % level, url2))
    bread.append(("Weight %s" % weight, url3))
    bread.append(("Character \( %s \)" % (WNF.character.latex_name), url4))
    bread.append(("Newform %d.%d.%d.%s" % (level, weight, int(character), label),''))
    info['bread'] = bread
    
    properties2 = list()
    friends = list()
    space_url = url_for('emf.render_elliptic_modular_forms',level=level, weight=weight, character=character)
    friends.append(('\( S_{%s}(%s, %s)\)'%(WNF.weight, WNF.level, WNF.character.latex_name), space_url))
    if hasattr(WNF.base_ring, "lmfdb_url") and WNF.base_ring.lmfdb_url:
        friends.append(('Number field ' + WNF.base_ring.lmfdb_pretty, WNF.base_ring.lmfdb_url))
    if hasattr(WNF.coefficient_field, "lmfdb_url") and WNF.coefficient_field.lmfdb_label:
        friends.append(('Number field ' + WNF.coefficient_field.lmfdb_pretty, WNF.coefficient_field.lmfdb_url))
    friends = uniq(friends)
    friends.append(("Dirichlet character \(" + WNF.character.latex_name + "\)", WNF.character.url()))
    
    if WNF.dimension==0 and not info.has_key('error'):
        info['error'] = "This space is empty!"
    info['title'] = 'Newform ' + WNF.hecke_orbit_label
    info['learnmore'] = [('History of modular forms', url_for('.holomorphic_mf_history'))]    
    if 'error' in info:
        return info
    ## Until we have figured out how to do the embeddings correctly we don't display the Satake
    ## parameters for non-trivial characters....

    ## Example to illustrate the different cases
    ## base              = CyclotomicField(n) -- of degree phi(n) 
    ## coefficient_field = NumberField( p(x)) for some p in base['x'] of degree m
    ##   we would then have cdeg = m*phi(n) and bdeg = phi(n)
    ##   and rdeg = m
    ## Unfortunately, for e.g. base = coefficient_field = CyclotomicField(6)
    ## we get coefficient_field.relative_degree() == 2 although it should be 1
    cdeg = WNF.coefficient_field.absolute_degree()
    bdeg = WNF.base_ring.absolute_degree()
    if cdeg == 1:
        rdeg = 1
    else:
        ## just setting rdeg = WNF.coefficient_field.relative_degree() does not give correct result...
        ## 
        rdeg = QQ(cdeg)/QQ(bdeg)
    cf_is_QQ = (cdeg == 1)
    br_is_QQ = (bdeg == 1)
    if cf_is_QQ:
        info['satake'] = WNF.satake
    if WNF.complexity_of_first_nonvanishing_coefficients() > default_max_height:
        info['qexp'] = ""
        info['qexp_display'] = ''
        info['hide_qexp'] = True
        n,c = WNF.first_nonvanishing_coefficient()
        info['trace_nv'] = latex(WNF.first_nonvanishing_coefficient_trace())
        info['norm_nv'] = '\\approx ' + latex(WNF.first_nonvanishing_coefficient_norm().n())
        info['index_nv'] = n
    else:
        if WNF.prec < prec:
            #get WNF record at larger prec
            WNF.prec = prec
            WNF.update_from_db()
        info['qexp'] = WNF.q_expansion_latex(prec=10, name='\\alpha ')
        info['qexp_display'] = url_for(".get_qexp_latex", level=level, weight=weight, character=character, label=label)
        info["hide_qexp"] = False
    info['max_cn_qexp'] = WNF.q_expansion.prec()
    ## All combinations should be tested...
    ## 13/4/4/a -> base ring = coefficient_field = QQ(zeta_6)
    ## 13/3/8/a ->  base_ring = QQ(zeta_4), coefficient_field has poly x^2+(2\zeta_4+2x-3\zeta_$ over base_ring
    ## 13/4/3/a ->  base_ring = coefficient_field = QQ(zeta_3) 
    ## 13/4/1/a -> all rational
    ## 13/6/1/a/ -> base_ring = QQ, coefficient_field = Q(sqrt(17))
    ## These are variables which needs to be set properly below
    info['polvars'] = {'base_ring':'x','coefficient_field':'\\alpha'}
    if not cf_is_QQ:
        if rdeg>1: # not WNF.coefficient_field == WNF.base_ring:
            ## Here WNF.base_ring should be some cyclotomic field and we have an extension over this.
            p1 = WNF.coefficient_field.relative_polynomial()
            c_pol_ltx = web_latex_poly(p1, '\\alpha')  # make the variable \alpha
            c_pol_ltx_x = web_latex_poly(p1, 'x')
            zeta = p1.base_ring().gens()[0]
#           p2 = zeta.minpoly() #this is not used anymore
#           b_pol_ltx = web_latex_poly(p2, latex(zeta)) #this is not used anymore
            z1 = zeta.multiplicative_order() 
            info['coeff_field'] = [ WNF.coefficient_field.absolute_polynomial_latex('x'),c_pol_ltx_x, z1]
            if hasattr(WNF.coefficient_field, "lmfdb_url") and WNF.coefficient_field.lmfdb_url:
                info['coeff_field_pretty'] = [ WNF.coefficient_field.lmfdb_url, WNF.coefficient_field.lmfdb_pretty, WNF.coefficient_field.lmfdb_label]
            if z1==4:
                info['polynomial_st'] = '<div class="where">where</div> {0}\(\mathstrut=0\) and \(\zeta_4=i\).</div><br/>'.format(c_pol_ltx)
                info['polvars']['base_ring']='i'
            elif z1<=2:
                info['polynomial_st'] = '<div class="where">where</div> {0}\(\mathstrut=0\).</div><br/>'.format(c_pol_ltx)
            else:
                info['polynomial_st'] = '<div class="where">where</div> %s\(\mathstrut=0\) and \(\zeta_{%s}=e^{\\frac{2\\pi i}{%s}}\) '%(c_pol_ltx, z1,z1)
                info['polvars']['base_ring']='\zeta_{{ {0} }}'.format(z1)
                if z1==3:
                    info['polynomial_st'] += 'is a primitive cube root of unity.'
                else:
                    info['polynomial_st'] += 'is a primitive {0}-th root of unity.'.format(z1)
        elif not br_is_QQ:
            ## Now we have base and coefficient field being equal, meaning that since the coefficient field is not QQ it is some cyclotomic field
            ## generated by some \zeta_n 
            p1 = WNF.coefficient_field.absolute_polynomial()
            z1 = WNF.coefficient_field.gens()[0].multiplicative_order()
            c_pol_ltx = web_latex_poly(p1, '\\zeta_{{{0}}}'.format(z1))
            c_pol_ltx_x = web_latex_poly(p1, 'x')
            info['coeff_field'] = [ WNF.coefficient_field.absolute_polynomial_latex('x'), c_pol_ltx_x]
            if hasattr(WNF.coefficient_field, "lmfdb_url") and WNF.coefficient_field.lmfdb_url:
                info['coeff_field_pretty'] = [ WNF.coefficient_field.lmfdb_url, WNF.coefficient_field.lmfdb_pretty, WNF.coefficient_field.lmfdb_label]
            if z1==4:
                info['polynomial_st'] = '<div class="where">where \(\zeta_4=e^{{\\frac{{\\pi i}}{{ 2 }} }}=i \).</div>'.format(c_pol_ltx)
                info['polvars']['coefficient_field']='i'
            elif z1<=2:
                info['polynomial_st'] = '' 
            else:
                info['polynomial_st'] = '<div class="where">where \(\zeta_{{{0}}}=e^{{\\frac{{2\\pi i}}{{ {0} }} }}\) '.format(z1)
                info['polvars']['coefficient_field']='\zeta_{{{0}}}'.format(z1)
                if z1==3:
                    info['polynomial_st'] += 'is a primitive cube root of unity.</div>'
                else:
                    info['polynomial_st'] += 'is a primitive {0}-th root of unity.</div>'.format(z1)
    else:
        info['polynomial_st'] = ''
    if info["hide_qexp"]:
        info['polynomial_st'] = ''
    info['degree'] = int(cdeg)
    if cdeg==1:
        info['is_rational'] = 1
        info['coeff_field_pretty'] = [ WNF.coefficient_field.lmfdb_url, WNF.coefficient_field.lmfdb_pretty ]
    else:
        info['is_rational'] = 0
    emf_logger.debug("PREC2: {0}".format(prec))
    info['embeddings'] = WNF._embeddings['values'] #q_expansion_embeddings(prec, bprec,format='latex')
    info['embeddings_len'] = len(info['embeddings'])
    properties2 = [('Level', str(level)),
                       ('Weight', str(weight)),
                       ('Character', '$' + WNF.character.latex_name + '$'),
                       ('Label', WNF.hecke_orbit_label),
                       ('Dimension of Galois orbit', str(WNF.dimension))]
    if (ZZ(level)).is_squarefree():
        info['twist_info'] = WNF.twist_info
        if isinstance(info['twist_info'], list) and len(info['twist_info'])>0:
            info['is_minimal'] = info['twist_info'][0]
            if(info['twist_info'][0]):
                s = 'Is minimal<br>'
            else:
                s = 'Is a twist of lower level<br>'
            properties2 += [('Twist info', s)]
    else:
        info['twist_info'] = 'Twist info currently not available.'
        properties2 += [('Twist info', 'not available')]
    args = list()
    for x in range(5, 200, 10):
        args.append({'digits': x})
    alev = None
    CM = WNF._cm_values
    if CM is not None:
        if CM.has_key('tau') and len(CM['tau']) != 0:
            info['CM_values'] = CM
    info['is_cm'] = WNF.is_cm
    if WNF.is_cm == 1:
        info['cm_field'] = "2.0.{0}.1".format(-WNF.cm_disc)
        info['cm_disc'] = WNF.cm_disc
        info['cm_field_knowl'] = nf_display_knowl(info['cm_field'], getDBConnection(), field_pretty(info['cm_field']))
        info['cm_field_url'] = url_for("number_fields.by_label", label=info["cm_field"])
    if WNF.is_cm is None or WNF.is_cm==-1:
        s = '- Unknown (insufficient data)<br>'
    elif WNF.is_cm == 1:
        s = 'Yes<br>'
    else:
        s = 'No<br>'
    properties2.append(('CM', s))
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
        if poly != '':
            d,monom,coeffs = poly
            emf_logger.critical("poly={0}".format(poly))
            info['explicit_formulas'] = '\('
            for i in range(len(coeffs)):
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
                if a == 0 and b != 0:
                    s+="E_6^{{ {0} }}".format(b)
                elif b ==0 and a != 0:
                    s+="E_4^{{ {0} }}".format(a)
                else:
                    s+="E_4^{{ {0} }}E_6^{{ {1} }}".format(a,b)
                info['explicit_formulas'] += s
            info['explicit_formulas'] += " \)"            
    # cur_url = '?&level=' + str(level) + '&weight=' + str(weight) + '&character=' + str(character) + '&label=' + str(label) # never used
    if len(WNF.parent.hecke_orbits) > 1:
        for label_other in WNF.parent.hecke_orbits.keys():
            if(label_other != label):
                s = 'Modular form '
                if character:
                    s += newform_label(level,weight,character,label_other)
                else:
                    s += newform_label(level,weight,1,label_other)

                url = url_for('emf.render_elliptic_modular_forms', level=level,
                              weight=weight, character=character, label=label_other)
                friends.append((s, url))

    s = 'L-Function '
    if character:
        s += newform_label(level,weight,character,label)
    else:
        s += newform_label(level,weight,1,label)
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
    info['max_cn'] = WNF.max_available_prec()
    return info
