from flask import render_template, url_for
import siegel_core
import pickle
import urllib
from sage.all_cmdline import *

DATA = 'http://data.countnumber.de/Siegel-Modular-Forms/'


def __trace( page, args = {}):
    """
    Return the path leading to the queried page
    in the form [(symbolic name 1, URL), (symbolic name 2, URL), ...]
    """
    parent = ''
    page = args.get('page')
    trace = [('Siegel modular forms', url_for( 'ModularForm_GSp4_Q_top_level'))]
    if 'forms' == page:
        trace += [( 'Spaces \(' + parent + '\)', \
                        url_for( 'ModularForm_GSp4_Q_top_level', page=page, group=args.get('group')))]
    elif 'basic' == page:
        trace += [( 'Spaces \(' + parent + '\)', \
                        url_for( 'ModularForm_GSp4_Q_top_level', page='forms', group=args.get('group')))]
        trace += [( 'Basic Information', \
                        url_for( 'ModularForm_GSp4_Q_top_level', page=page, group=args.get('group')))]
    elif 'dimensions' == page:
        trace += [( 'Spaces \(' + parent + '\)', \
                        url_for( 'ModularForm_GSp4_Q_top_level', page='forms', group=args.get('group')))]
        trace += [( 'Dimensions', \
                        url_for( 'ModularForm_GSp4_Q_top_level', page=page, group=args.get('group')))]
    elif 'specimen' == page:
        trace += [( 'Spaces \(' + parent + '\)', \
                        url_for( 'ModularForm_GSp4_Q_top_level', page='forms', group=args.get('group')))]
        trace += [( 'Form', \
                        url_for( 'ModularForm_GSp4_Q_top_level', page=page, group=args.get('group'), \
                        orbit=args.get('orbit'), form=args.get('form')))]
    return trace
    

def render_webpage( args = {}):
    """
    Configure and return a template for the Siegel modular forms pages.
    """
    info = dict(args)
    info['learnmore'] = [ ('Siegel modular forms', 'http://en.wikipedia.org/wiki/Siegel_modular_form')]

    if len(args) == 0:
        return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_navigation.html", \
                                   info = info, \
                                   title = 'Siegel Modular Forms of Degree 2', \
                                   bread = __trace( None))

    # possible keys for the URL
    group = args.get('group')
    character = args.get('character')
    weight = args.get('weight')
    level = args.get('level')
    form = args.get('form')
    page = args.get('page')
    orbit = args.get('orbit')
    weight_range = args.get('weight_range')

    # set info
    info['group'] = group
    info['form'] = form
    info['orbit']= orbit
    info['level']= level

    # Logic to set parameters depending on which group ---------

    if args['group']:
        if 'Sp4Z' == args['group']:
            info['parent_as_tex'] = 'M_*\\big({\\rm Sp}(4,\\mathbb{Z})\\big)'
            info['learnmore'] += [ ('Modular forms on \(\\text{Sp}(4,\\mathbb{Z})\)', url_for( 'ModularForm_GSp4_Q_top_level', group = group, page='basic'))]
            sage_group ='Sp(4,Z)';
            info['generators'] = 'smf.Igusa_generators'
        elif 'Gamma0_2' == args['group']:
            info['parent_as_tex'] = 'M_*\\big(\\Gamma_0(2)\\big)'
            sage_group ='Gamma_0(2)';
        elif 'Gamma0_3_psi_3' == args['group']:
            info['parent_as_tex'] = 'M_*\\big(\\Gamma_0(3,\\psi_3)\\big)'
            sage_group ='Gamma_0(3, psi_3)';
        elif 'Gamma0_4_psi_4' == args['group']:
            info['parent_as_tex'] = 'M_*\\big(\\Gamma_0(4,\\psi_3)\\big)'
            sage_group ='Gamma_0(4, psi_4)';
        elif 'Sp4Z_2' == args['group']:
            info['parent_as_tex'] = 'M_{*,2}\\big({\\rm Sp}(4,\\mathbb{Z})\\big)'
            sage_group ='Sp(4,Z)_2';
        elif 'Kp' == args['group']:
            info['parent_as_tex'] = 'S_*\\big(K(p)\\big)'
            info['learnmore'] += [ ('Paramodular forms', 'http://math.lfc.edu/~yuen/paramodular/')]
            info['generators'] = 'smf.Kp_generators'
            sage_group ='K(p)';
        elif 'Sp8Z' == args['group']:
            info['parent_as_tex'] = 'S_*\\big({\\rm Sp}(8,\\mathbb{Z})\\big)'
            sage_group ='Sp(8,Z)';
        else:
            return render_template("ModularForm_GSp4_Q/None.html")
        
        # Logic to render pages ----------------

        if page == 'forms':
            try:
                f = urllib.urlopen( DATA + group +'/available_eigenforms.p')
                go = pickle.load(f)
                f.close()
                forms_exist = True
            except (IOError, EOFError, KeyError ):
                forms_exist = False
            if True == forms_exist:
                info['forms'] = [ (k,[(form,go[k][form]) for form in go[k]]) for k in go]
            return render_template( "ModularForm_GSp4_Q/ModularForm_GSp4_Q_forms.html", \
                                        info = info, \
                                        title = 'Siegel modular forms spaces \(' + info['parent_as_tex'] + '\)', \
                                        bread = __trace( page, args))

        if page == 'basic':
            return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_basic.html", info = info, \
                                       title = 'Siegel modular forms basic information', \
                                       bread = __trace( page, args))
        
        if page == 'dimensions':
            if not weight_range:
                min_wt = 1; max_wt = 16
            else:
                info['weight_range'] = weight_range
                # parse weight_range
                wr = weight_range.split('-')
                try:
                    wr = map( int, wr)
                    min_wt = wr[0]
                    if len(wr) == 1:
                        max_wt = min_wt
                        if min_wt > 1000000:
                            info['error'] = 'Input too large: Please enter a smaller number.'
                            min_wt = 2; max_wt = 50
                    else:
                        max_wt = wr[1]
                        if max_wt-min_wt >= 0 and  (max_wt-min_wt + 1)*max_wt > 1000000:
                            min_wt = 2; max_wt = 50
                            info['error'] = 'Input too large: Please enter a smaller range.'
                            #raise ValueError('gaga')
                except ValueError, e:
                    info['error'] = 'Invalid input: ' + e.message
                    min_wt = 2; max_wt =50
            if info['group'] == "Sp8Z":
              info['table_headers'] = ["Weight", "Total", "Ikeda Lifts", "Miyawaki Lifts", "Other"]
            elif info['group'] == "Kp":
              # The following needs to be changed to logically deduce whether it is weight or level
              weight_or_level= "weight or level"
              info['table_headers'] = [weight_or_level, "Total", "Gritsenko Lifts", "Nonlifts", "Oldforms"]
            else:
                info['table_headers'] = ["Weight", "Total", "Eisenstein", "Klingen", "Maass", "Interesting"]
            # The following should be changed to add any new groups implemented in the core
            if group == 'Sp4Z':
                info['dimensions'] = [ (k, siegel_core.dimension( k, sage_group)) for k in range(min_wt, max_wt+1)]
            elif group == 'Kp':
                info['dimensions'] = [ (k, siegel_core.dimension( k, sage_group, tp = int(level))) for k in range(min_wt, max_wt+1)]
            return render_template( "ModularForm_GSp4_Q/ModularForm_GSp4_Q_dimensions.html", \
                                        info = info, \
                                        title = 'Siegel modular forms dimensions \(' + info['parent_as_tex'] + '\)', \
                                        bread = __trace( page, args))

        if page == 'specimen':
            info['weight'] = weight
            file_name = weight + '_' + form + '.sobj'
            f_url = DATA + group + '/eigenforms/' + file_name
            f =load(f_url)
            f_keys = f[2].keys()
            if  'Sp4Z' == group and 'E' != form and 'Klingen' != form:
                f_keys = filter( lambda (a,b,c): b^2<4*a*c, f_keys) 
            # we sort the table of Fourier coefficients by discriminant, forms in increasing lexicographic order
            our_cmp = lambda (a,b,c), (A,B,C) : cmp( (4*a*c - b**2,a,b,c), (4*A*C - B**2, A,B,C) )
            f_keys.sort( cmp = our_cmp)

            file_name = weight + '_' + form + '-ev.sobj'
            g_url = DATA + group +'/eigenvalues/' + file_name
            g =load( g_url)

            info['form'] = [ f[0].parent(), f[1], \
                                 [ (l,g[1][l]) for l in g[1]], \
                                 [(i,f[2][i]) for i in f_keys], \
                                 f_url, g_url]
##             info['friends'] = [ ('Spin L-function', url_for('not_yet_implemented')), \
##                                 ('Standard L-function', url_for('not_yet_implemented')), \
##                                 ('First Fourier-Jacobi coefficient', url_for('not_yet_implemented'))]
              
            return render_template( "ModularForm_GSp4_Q/ModularForm_GSp4_Q_specimen.html", \
                                        info = info,  \
                                        title = 'Siegel modular form ' + weight + '_' + form, \
                                        bread = __trace( page, args))            

        else:
            return render_webpage()

    else:
        return render_template("ModularForm_GSp4_Q/None.html")
