from flask import render_template, url_for, request
import siegel_core
import input_parser
import dimensions
import pickle
import urllib
from sage.all_cmdline import *
import os
import sample

from lmfdb.base import app
from lmfdb.siegel_modular_forms import smf_page
from lmfdb.siegel_modular_forms import smf_logger
DATA = 'http://data.countnumber.de/Siegel-Modular-Forms/'
# DATA = '/home/nils/Sandbox/Siegel-Modular-Forms/'
# DATA = os.path.expanduser("~/data/Siegel-Modular-Forms/")


@app.route('/ModularForm/GSp/Q')
@app.route('/ModularForm/GSp/Q/<group>')
@app.route('/ModularForm/GSp/Q/<group>/<page>')
@app.route('/ModularForm/GSp/Q/<group>/<page>/<weight>')
@app.route('/ModularForm/GSp/Q/<group>/<page>/<weight>/<form>')
def ModularForm_GSp4_Q_top_level(group=None, page=None, weight=None, form=None):
    args = request.args
    if group:
        args = {}
        for k in request.args:
            args[k] = request.args[k]
        args['group'] = group
        if None != weight:
            page = 'specimen'
        args['page'] = page
        if 'specimen' == page:
            args['weight'] = weight
            args['form'] = form
    return render_webpage(args)

##TODO just copied this from hilbert_modular_form.py, probably should be in a lmfdb.tex_utilities file
def teXify_pol(pol_str):  # TeXify a polynomial (or other string containing polynomials)
    o_str = pol_str.replace('*', '')
    ind_mid = o_str.find('/')
    while ind_mid != -1:
        ind_start = ind_mid - 1
        while ind_start >= 0 and o_str[ind_start] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_start -= 1
        ind_end = ind_mid + 1
        while ind_end < len(o_str) and o_str[ind_end] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_end += 1
        o_str = o_str[:ind_start + 1] + '\\frac{' + o_str[ind_start + 1:ind_mid] + '}{' + o_str[
            ind_mid + 1:ind_end] + '}' + o_str[ind_end:]
        ind_mid = o_str.find('/')

    ind_start = o_str.find('^')
    while ind_start != -1:
        ind_end = ind_start + 1
        while ind_end < len(o_str) and o_str[ind_end] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_end += 1
        o_str = o_str[:ind_start + 1] + '{' + o_str[ind_start + 1:ind_end] + '}' + o_str[ind_end:]
        ind_start = o_str.find('^', ind_end)

    return o_str

def render_webpage(args={}):
    """
    Configure and return a template for the Siegel modular forms pages.
    """
    info = dict(args)
    # info['learnmore'] = [ ('Siegel modular forms', 'http://en.wikipedia.org/wiki/Siegel_modular_form')]
    info['learnmore'] = []
    bread = [('Siegel modular forms', url_for('ModularForm_GSp4_Q_top_level'))]

    if len(args) == 0:
        return render_template("ModularForm_GSp4_Q_navigation.html",
                               title='Siegel Modular Forms',
                               bread=bread,
                               **info)

    # possible keys for the URL
    group = args.get('group')
    character = args.get('character')
    weight = args.get('weight')
    level = args.get('level')
    form = args.get('form')
    page = args.get('page')
    weight_range = args.get('weight_range')

    # set info
    info['group'] = group
    info['form'] = form
    info['level'] = level

    # We check first the key 'group' since it is needed always
    tmp_parent_as_tex = '%s'
    if args['group']:

        if 'Sp4Z' == args['group']:
            info['parent_as_tex'] = 'M_{k}\\big({\\rm Sp}(4,\\mathbb{Z})\\big)'
            # dimension = siegel_core._dimension_Sp4Z
            dimension = dimensions.dimension_Sp4Z
            info['generators'] = 'smf.Igusa_generators'

        elif 'Gamma0_2' == args['group']:
            info['parent_as_tex'] = 'M_{k}\\big(\\Gamma_0(2)\\big)'
            dimension = dimensions.dimension_Gamma0_2    

        elif 'Gamma1_2' == args['group']:
            info['parent_as_tex'] = 'M_{k}\\big(\\Gamma_1(2)\\big)'
            dimension = dimensions.dimension_Gamma1_2

        elif 'Gamma_2' == args['group']:
            info['parent_as_tex'] = 'M_{k}\\big(\\Gamma(2)\\big)'
            dimension = dimensions.dimension_Gamma_2

        elif 'Sp4Z_2' == args['group']:
            info['parent_as_tex'] = 'M_{k,2}\\big({\\rm Sp}(4,\\mathbb{Z})\\big)'
            dimension = siegel_core._dimension_Sp4Z_2

        elif 'Sp6Z' == args['group']:
            info['parent_as_tex'] = 'M_k\\big({\\rm Sp}(6,\\mathbb{Z})\\big)'
            # dimension = siegel_core._dimension_Sp6Z
            dimension = dimensions.dimension_Sp6Z

        elif 'Sp8Z' == args['group']:
            info['parent_as_tex'] = 'M_k\\big({\\rm Sp}(8,\\mathbb{Z})\\big)'
            # dimension = siegel_core._dimension_Sp8Z
            dimension = dimensions.dimension_Sp8Z

        elif 'Gamma0_4_half' == group:
            info['parent_as_tex'] = 'M_{k-1/2}\\big(\\Gamma_0(4)\\big)'
            # dimension = siegel_core._dimension_Gamma0_4_half
            dimension = dimensions.dimension_Gamma0_4_half

        elif 'Kp' == args['group']:
            info['parent_as_tex'] = 'M_k\\big(K(p)\\big)'
            info['learnmore'] += [('Paramodular forms', 'http://math.lfc.edu/~yuen/paramodular/')]
            info['generators'] = 'smf.Kp_generators'
            dimension = siegel_core._dimension_Kp

        elif 'Gamma0_2' == args['group']:
            info['parent_as_tex'] = 'M_k\\big(\\Gamma_0(2)\\big)'
            dimension = siegel_core._dimension_Gamma0_2

        elif 'Gamma0_3' == args['group']:
            info['parent_as_tex'] = 'M_k\\big(\\Gamma_0(3)\\big)'
            dimension = siegel_core._dimension_Gamma0_3

        elif 'Gamma0_3_psi_3' == args['group']:
            info['parent_as_tex'] = 'M_k\\big(\\Gamma_0(3,\\psi_3)\\big)'
            dimension = siegel_core._dimension_Gamma0_3_psi_3

        elif 'Gamma0_4' == args['group']:
            info['parent_as_tex'] = 'M_k\\big(\\Gamma_0(4)\\big)'
            dimension = siegel_core._dimension_Gamma0_4

        elif 'Gamma0_4_psi_4' == args['group']:
            info['parent_as_tex'] = 'M_k\\big(\\Gamma_0(4,\\psi_4)\\big)'
            dimension = siegel_core._dimension_Gamma0_4_psi_4

 

        else:
            info['error'] = 'Request for unavailable type of Siegel modular form'
            return render_template("None.html", **info)

        info['learnmore'] += [('The spaces \(' + info['parent_as_tex'] + '\)', url_for(
            'ModularForm_GSp4_Q_top_level', group=group, page='basic'))]
        bread += [('\(' + info['parent_as_tex'] + '\)', url_for('ModularForm_GSp4_Q_top_level',
                   group=group, page='forms'))]

    else:
        # some nonsense request came in, we answer by nonsense too
        return render_template("None.html")

        # We branch now according to the value of the key 'page'


    ##########################################################
    ## FORM COLLECTION REQUEST
    ##########################################################
    if page == 'forms':
        try:
            f = urllib.urlopen(DATA + group + '/available_eigenforms.p')
            go = pickle.load(f)
            f.close()
            forms_exist = True
        except (IOError, EOFError, KeyError):
            info['error'] = 'No data access'
            forms_exist = False
        if True == forms_exist:
            info['forms'] = [(k, [(form, go[k][form]) for form in go[k]]) for k in go]
        return render_template("ModularForm_GSp4_Q_forms.html",
                               title='Siegel modular forms \(' + info['parent_as_tex'] + '\)',
                               bread=bread, **info)

    if page == 'basic':
        bread += [('Basic information', url_for('ModularForm_GSp4_Q_top_level', group=group, page=page))]
        return render_template("ModularForm_GSp4_Q_basic.html",
                               title='Siegel modular forms basic information',
                               bread=bread, **info)


    ##########################################################
    ## DIMENSIONS REQUEST
    ##########################################################
    if page == 'dimensions':

        # We check whether the weight_range makes sense to us and, if so, dispatch it 
        info['weight_range'] = weight_range
        try:
            assert info['weight_range'], 'Please enter a valid argument'
            min_wt, max_wt, sym_pow = input_parser.kj_parser( weight_range)
            min_wt = Integer( min_wt)
            if None == max_wt or max_wt < min_wt:
                max_wt = min_wt
            if None == sym_pow:
                sym_pow = 0
            assert min_wt < 1000000 and (max_wt - min_wt + 1) * max_wt < 10000 and sym_pow < 1000, '%d-%d,%d: Input too large: Please enter smaller range or numbers.' % (max_wt, min_wt, sym_pow)
        except Exception as e:
            info['error'] = str(e)
            return render_template( "ModularForm_GSp4_Q_dimensions.html",
                                    title='Siegel modular forms dimensions \(' + info['parent_as_tex'] + '\)',
                                    bread=bread, **info)

        # A priori the request is reasonable, so we try to get the data for the answer 
        try:
            info['new_method'] = None
            if 'Gamma_2' == group or 'Gamma0_2' == group or 'Gamma1_2' == group or 'Sp4Z' == group or 'Sp6Z' == group or 'Sp8Z' == group or 'Gamma0_4_half' == group:
                info['sym_pow'] = sym_pow
                info['table_headers'], info['dimensions'] = dimension( range( min_wt, max_wt + 1), sym_pow)
                ####### a hack ########
                info['new_method'] = 'new_method'
                bread += [('Dimensions',
                           url_for('ModularForm_GSp4_Q_top_level', group=group, page=page, level=level, weight_range=weight_range))]
            elif 'Kp' == group:
                info['dimensions'] = [(k, dimension(k, tp=int(level))) for k in range(min_wt, max_wt + 1)]
                bread += [('Dimensions',
                           url_for('ModularForm_GSp4_Q_top_level', group=group, page=page, level=level, weight_range=weight_range))]               
            else:
                info['dimensions'] = [(k, dimension(k)) for k in range(min_wt, max_wt + 1)]
                bread += [('Dimensions',
                          url_for('ModularForm_GSp4_Q_top_level', group=group, page=page, weight_range=weight_range))]
        except Exception as e:
            info['error'] = 'Functional error: %s' % (str(e)) #(sys.exc_info()[0])
            return render_template( "ModularForm_GSp4_Q_dimensions.html",
                                    title='Siegel modular forms dimensions \(' + info['parent_as_tex'] + '\)',
                                    bread=bread, **info)

        # We provide some headers for the 'old' method and ask for rendering an answer
        if info['new_method']:
            info['table_headers'] = info['table_headers']

        # elif 'Sp8Z' == group:
        #     info['table_headers'] = ['Weight', 'Total', 'Ikeda lifts', 'Miyawaki lifts', 'Other']

        elif 'Sp6Z' == group:
            info['table_headers'] = ['Weight', 'Total', 'Miyawaki lifts I', 'Miyawaki lifts II', 'Other']

        elif group == 'Kp':
            info['table_headers'] = ["Weight", "Total", "Gritsenko Lifts", "Nonlifts", "Oldforms"]

        elif 'Sp4Z_2' == group or 'Gamma0_4_half' == group:
            info['table_headers'] = ['Weight', 'Total', 'Non cusp', 'Cusp']

        else:
            info['table_headers'] = ["Weight", "Total", "Eisenstein", "Klingen", "Maass", "Interesting"]

        return render_template("ModularForm_GSp4_Q_dimensions.html",
                               title='Siegel modular forms dimensions \(' + info['parent_as_tex'] + '\)',
                               bread=bread, **info)


    ##########################################################
    ## SPECIFIC FORM REQUEST
    ##########################################################
    if page == 'specimen':
        info['weight'] = weight
        ev_modulus = args.get('emod')
        fc_modulus = args.get('fcmod')
        erange = args.get('erange')
        fcrange = args.get('fcrange')

        # try to load data
        if 'Kp' == group or 'Sp4Z_2' == group or 'Sp4Z' == group:
            # fetch from mongodb
            try:
                smple = sample.Sample( [group], weight + '_' + form)
                f = (smple.field()(0), smple.explicit_formula(), smple.Fourier_coefficients() if smple.Fourier_coefficients() else {})
                g = (smple.field()(0), smple.eigenvalues() if smple.eigenvalues() else {})

                file_name = weight + '_' + form + '.sobj'
                f_url = DATA + group + '/eigenforms/' + file_name
                file_name = weight + '_' + form + '-ev.sobj'
                g_url = DATA + group + '/eigenvalues/' + file_name

                loaded = True
            except Exception as e:
                info['error'] = 'Data not available: %s %s' % (str(e), weight + '_' + form)
                loaded = False
        else:
            try:
                file_name = weight + '_' + form + '.sobj'
                f_url = DATA + group + '/eigenforms/' + file_name
                # print 'fafaf %s'%f_url
                f = load(f_url)
                file_name = weight + '_' + form + '-ev.sobj'
                g_url = DATA + group + '/eigenvalues/' + file_name
                # print 'gagag %s'%g_url
                g = load(g_url)
                loaded = True
            except:
                info['error'] = 'Data not available'
                loaded = False

        if True == loaded:

            # define specific methods for computing discriminant and ordering of form
            if 'Sp8Z' != group and 'Sp6Z' != group: # with current data this is all degree 2 SMFs
                __disc = lambda (a, b, c): 4 * a * c - b ** 2
                __cmp = lambda (
                    a, b, c), (A, B, C): cmp((4 * a * c - b ** 2, a, b, c), (4 * A * C - B ** 2, A, B, C))

            if 'Sp8Z' == group:
                # matrix index is given as [m11 m22 m33 m44 m12 m13 m23 m14 m24 m34]
                __mat = lambda (m11, m22, m33, m44, m12, m13, m23, m14, m24, m34): \
                    matrix(ZZ, 4, 4, [m11, m12, m13, m14, m12, m22, m23, m24,
                                      m13, m23, m33, m34, m14, m24, m34, m44])
                __disc = lambda i: __mat(i).det()
                __cmp = lambda f1, f2: cmp([__mat(f1).det()] + list(f1), [__mat(f2).det()] + list(f2))

            if 'Sp6Z' == group:
                # matrix index is given as [m11/2 m22/2 m33/2 m12 m13 m23]
                __mat = lambda (a, b, c, d, e, f): \
                    matrix(ZZ, 3, 3, [2 * a, d, e, d, 2 * b, f, e, f, 2 * c])
                __disc = lambda i: __mat(i).det()
                __cmp = lambda f1, f2: cmp([__mat(f1).det()] + list(f1), [__mat(f2).det()] + list(f2))

            # make the coefficients of the M_k(Sp(4,Z)) forms integral
            # if 'Sp4Z' == group:  # or 'Sp4Z_2' == group:
            #     d = lcm(map(lambda n: denominator(n), f[1].coefficients()))
            #     f = list(f)
            #     f[1] *= d
            #     for k in f[2]:
            #         f[2][k] *= d

            # replace generator with a to make things prettier 
            if isinstance(f[0].parent(), Field):
                if f[0].parent()!=QQ:
                    gen = str(f[0].parent().gen())
                    info['gen_coeff_field'] = teXify_pol(str(f[0].parent().gen()).replace(gen, 'a'))
                    info['poly_coeff_field'] = teXify_pol(str(f[0].parent().polynomial()).replace(gen, 'a'))
                    info['poly_in_gens'] = teXify_pol(str(f[1]).replace(gen, 'a'))
                else:
                    info['poly_in_gens'] = teXify_pol(str(f[1]))
            else:
                # coefficient field is not a sage field, so just assume its supposed to be rationals
                info['poly_in_gens'] = teXify_pol(str(f[1]))

            # isolate requested eigenvalue indices
            if erange=='all':
                filt_evals = g[1]
                eval_index = filt_evals.keys()
                info['erangedesc']= 'all available eigenvalues'
            else:
                if erange:
                    spliterange = erange.split('-')
                    if len(spliterange)>1 and spliterange[0].isdigit() and spliterange[1].isdigit():
                        elow, ehigh = int(spliterange[0]), int(spliterange[1])
                        # filter out to have eigenvalues in [elow, ehigh]
                        filt_evals = {n: lam for n, lam in g[1].iteritems() if int(n)>=elow and int(n)<=ehigh}
                        eval_index = filt_evals.keys()
                        info['erangedesc'] = 'eigenvalues with $n$ in [' + `elow` + ', ' + `ehigh` + ']'
                else:
                    # can't make sense of the range, return a default
                    info['erange'] = ''
                    filt_evals = g[1]
                    eval_index = filt_evals.keys()[0:20]
                    info['erangedesc'] = 'the first few eigenvalues'

            # prepare formatted eigenvalues
            ftd_evals = []
            try:
                if not ev_modulus:
                    m = 0
                else:
                    m = int(ev_modulus)
                info['ev_modulus'] = m
                K = g[0].parent().fraction_field()
                if m != 0:
                    if QQ == K:
                        for i in eval_index:
                            rdcd_eval = Integer(g[1][i]) % m
                            ftd_evals.append((str(i), teXify_pol(str(rdcd_eval))))
                    else:
                        I = K.ideal(m)
                        for i in eval_index:
                            rdcd_eval = I.reduce(g[1][i])
                            ftd_evals.append((str(i), teXify_pol(str(rdcd_eval).replace(gen, 'a'))))
                    info['emoddesc'] = 'reduced modulo ' + `m` + '.'
                else:
                    for i in eval_index:
                        if QQ == K:
                            ftd_evals.append((str(i), teXify_pol(str(g[1][i]))))
                        else:
                            ftd_evals.append((str(i), teXify_pol(str(g[1][i]).replace(gen, 'a'))))
                    info['emoddesc'] = 'with no reduction.'     
            except:
                pass

            if (fcrange=='all'):
                filt_fcs = f[2]
                fc_index = filt_fcs.keys()
                fc_index.sort(cmp=__cmp)
                info['fcrangedesc'] = 'all available Fourier coefficients'
            else:
                if fcrange:
                    splitfcrange = fcrange.split('-')
                    if len(splitfcrange)>1 and splitfcrange[0].isdigit() and splitfcrange[1].isdigit():
                        fclow, fchigh = int(splitfcrange[0]), int(splitfcrange[1])
                        filt_fcs = {n: fc for n, fc in f[2].iteritems() if __disc(n)>=fclow and __disc(n)<=fchigh}
                        fc_index = filt_fcs.keys()
                        fc_index.sort(cmp=__cmp)
                        info['fcrangedesc'] = 'Fourier coefficients with index such that $D$ is in [' + `fclow` + ', ' + `fchigh` + ']'
                else:
                    # can't make sense of the range, return a default
                    info['fcrange'] = '' 
                    filt_fcs = f[2]
                    fc_index = filt_fcs.keys()
                    fc_index.sort(cmp=__cmp)
                    fc_index = fc_index[0:20]
                    info['fcrangedesc'] = 'the first few Fourier coefficients'

            # prepare formatted fourier coefficients
            ftd_fcs = []
            try:
                if not fc_modulus:
                    m = 0
                else:
                    m = int(fc_modulus)
                info['fc_modulus'] = m
                K = g[0].parent().fraction_field()
                if m != 0:
                    if 'Sp4Z_2' == group:
                        if QQ == K:
                            for i in fc_index:
                                ftd_fc =  sum((v[0] % m) * v[1] for v in list(f[2][i]))
                                ftd_fcs.append((str(i), 
                                               teXify_pol(str(ftd_fc)), 
                                               str(__disc(i))))
                        else:
                            I = K.ideal(m)
                            for i in fc_index:
                                ftd_fc = sum(I.reduce(v[0]) * v[1] for v in list(f[2][i]))
                                ftd_fcs.append((str(i), 
                                                teXify_pol(str(ftd_fc).replace(gen, 'a')), 
                                                str(__disc(i))))
                    else:
                        if QQ == K:
                            for i in fc_index:
                                ftd_fc = Integer(f[2][i]) % m
                                ftd_fcs.append((str(i), 
                                                teXify_pol(str(ftd_fc)), 
                                                str(__disc(i))))
                        else:
                            I = K.ideal(m)
                            for i in fc_index:
                                ftd_fc = I.reduce(f[2][i])
                                ftd_fcs.append((str(i), 
                                                teXify_pol(str(ftd_fc).replace(gen, 'a')), 
                                                str(__disc(i))))
                    info['fcmoddesc'] = 'reduced modulo ' + `m` + '.'
                else:
                    for i in fc_index:
                        ftd_fc = f[2][i]
                        if QQ == K:
                            ftd_fcs.append((str(i),
                                            teXify_pol(str(ftd_fc)),
                                            str(__disc(i))))
                        else:
                            ftd_fcs.append((str(i), 
                                            teXify_pol(str(ftd_fc).replace(gen, 'a')), 
                                            str(__disc(i))))
                    info['fcmoddesc'] = 'with no reduction.'
            except:
                pass


            location = url_for('ModularForm_GSp4_Q_top_level', group=group, page=page, weight=weight, form=form)
            properties2 = [('Species', '$' + info['parent_as_tex'] + '$'),
                          ('Weight', '%s' % weight)]

            # if implemented, add L-function to friends
            if 'Sp4Z'== group:
                numEmbeddings = f[0].parent().degree()
                friends = []
                for embedding in range(0, numEmbeddings):
                    friends.append(('Spin L-function for ' 
                                           + str(weight) + '_' + form + '.' + str(embedding), 
                                           '/L/ModularForm/GSp/Q/Sp4Z/specimen/'
                                           + str(weight) + '/' + form + '/' + str(embedding))) 
            else:
                friends = []            
            #TODO implement remaining spin L-functions, standard L-functions,
            # and first Fourier-Jacobi coefficient

            downloads = [('Fourier coefficients', f_url),
                             ('Eigenvalues', g_url)]

            location = url_for('ModularForm_GSp4_Q_top_level', group=group, page=page, weight=weight, form=form)
            bread += [(weight + '_' + form, location)]

            info['ftd_evals'] = ftd_evals
            info['ftd_fcs'] = ftd_fcs
            info['location'] = location
            info['form_name'] = form

            return render_template("ModularForm_GSp4_Q_specimen.html", 
                 title = 'Siegel modular form ' + weight + '_' + form,
                 bread=bread, properties2=properties2, friends=friends, downloads=downloads, **info) 

    # if a nonexisting page was requested return the homepage of Siegel modular forms
    return render_webpage()



