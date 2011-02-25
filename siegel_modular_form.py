from flask import render_template, url_for
import siegel_core
import pickle
import urllib
from sage.all_cmdline import *

def render_webpage(args):
    if len(args) == 0:
        info = {}
        return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_navigation.html", info = info, title = 'Siegel Modular Forms')

    info = dict(args)
    group = args.get('group')
    character = args.get('character')
    weight = args.get('weight')
    form = args.get('form')
    page = args.get('page')
    weight_range = args.get('weight_range')
    info['group'] = group
    info['form'] = form
    info['orbit']=args.get('orbit')

    if args['group']:
        
	# Logic to set parameters depending on which group ---------

        if 'Sp4Z' == args['group']:
            info['parent_as_tex'] = 'M_*\\big({\\rm Sp}(4,\\mathbb{Z})\\big)'
            sage_group ='Sp(4,Z)';
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
            sage_group ='K(p)';
        elif 'Sp8Z' == args['group']:
            info['parent_as_tex'] = 'S_*\\big({\\rm Sp}(8,\\mathbb{Z})\\big)'
            sage_group ='Sp(8,Z)';
        else:
            return render_template("ModularForm_GSp4_Q/None.html")
        
        info['special_side'] = ['\(' + info['parent_as_tex'] + '\)', \
                                [ ('Basic information', url_for( 'ModularForm_GSp4_Q_top_level', group = group, page='basic')),\
                                  ('Generators and relations', url_for( 'ModularForm_GSp4_Q_top_level', group = group, page='gen_rel')),\
                                  ('Available forms', url_for( 'ModularForm_GSp4_Q_top_level', group = group, page='forms')),\
                                  ('Dimensions', url_for( 'ModularForm_GSp4_Q_top_level', group = group, page='dimensions'))]]
        sidebar = [info['special_side']]
        
	# Logic to render pages ----------------

        if page == 'basic':
            return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_basic.html", info = info, title = 'Siegel Modular Forms', sidebar = sidebar)

	if page == 'gen_rel':
            return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_gen_rel.html", info = info, title = 'Siegel Modular Forms', sidebar = sidebar)

	if page == 'forms':
            try:
                f = urllib.urlopen( 'http://data.countnumber.de/Siegel-Modular-Forms/'+ group +'/available_eigenforms.p')
                go = pickle.load(f)
                f.close()
            except (IOError, EOFError, KeyError ):
                return url_for( 'not_yet_implemented')
            # order alphabetically and supress 0 dimension
            info['forms'] = [ (k,[(form,go[k][form]) for form in go[k]]) for k in go]
            return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_forms.html", info = info, title = 'Siegel Modular Forms', sidebar = sidebar)

	if page == 'dimensions':
            if not weight_range:
                min_wt = 1; max_wt = 16
            elif not weight_range:
                min_wt = 2; max_wt = 50
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
              info['table_headers'] = [weight_or_level, "Total", "Gritsenko Lifts", "Nonlifts"]
	    else:
              info['table_headers'] = ["Weight", "Total", "Eisenstein", "Klingen", "Maass", "Interesting"]
# The following should be changed to add any new groups implemented in the core
	    if (group == 'Sp4Z') or (group == 'Sp8Z'):
	      info['dimensions'] = [ (k, siegel_core.dimension( k, sage_group)) for k in range(min_wt, max_wt+1)]
	    return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_dimensions.html", info = info, title = 'Siegel Modular Forms', sidebar = sidebar)

        if page == 'specimen':
            info['weight'] = weight
            file_name = weight + '_' + form + '.sobj'
            f_url = 'http://data.countnumber.de/Siegel-Modular-Forms/' + group + '/eigenforms/' + file_name
            f =load(f_url)
            f_keys = f[2].keys()
            # we sort the table of Fourier coefficients by discriminant, forms in increasing lexicographic order
            our_cmp = lambda (a,b,c), (A,B,C) : cmp( (4*a*c - b**2,a,b,c), (4*A*C - B**2, A,B,C) )
            f_keys.sort( cmp = our_cmp)

            file_name = weight + '_' + form + '-ev.sobj'
            g_url = 'http://data.countnumber.de/Siegel-Modular-Forms/'+ group +'/eigenvalues/' + file_name
            g =load( g_url)

            info['form'] = [ f[0].parent(), f[1], [ (l,g[1][l]) for l in g[1]], [(i,f[2][i]) for i in f_keys]]
            info['friends'] = [ ('Spin L-function', url_for('not_yet_implemented')), ('Standard L-function', url_for('not_yet_implemented')), ('First Fourier-Jacobi coefficient', url_for('not_yet_implemented'))]
            if group=="Kp":
              info['learnmore'] = [ ('Poor-Yuen paramodular forms website', 'http://math.lfc.edu/~yuen/paramodular/')]
            else:
              info['learnmore'] = [ ('Siegel modular forms', url_for('not_yet_implemented'))]
            info['downloads'] = [ ('Fourier coefficients', url_for('not_yet_implemented')), ('Hecke eigenvalues', url_for('not_yet_implemented'))]
            return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_specimen.html", info = info,  title = 'Siegel Modular Forms', sidebar = sidebar)            

	else:
            return render_template("ModularForm_GSp4_Q/ModularForm_GSp4_Q_basic.html", info = info, title = 'Siegel Modular Forms', sidebar = sidebar)
    else:
        return render_template("ModularForm_GSp4_Q/None.html")
