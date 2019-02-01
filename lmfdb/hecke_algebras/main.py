# -*- coding: utf-8 -*-
import re
LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

from flask import render_template, request, url_for, redirect, make_response, flash,  send_file

from lmfdb.db_backend import db

from sage.all import latex, matrix, sqrt, sage_eval, prime_range

from lmfdb.hecke_algebras import hecke_algebras_page
from lmfdb.hecke_algebras.hecke_algebras_stats import hecke_algebras_summary
from lmfdb.search_parsing import parse_ints, clean_input
from lmfdb.search_wrapper import search_wrap

from markupsafe import Markup

import time
import ast
import StringIO

hecke_algebras_credit = 'Samuele Anni, Panagiotis Tsaknias and Gabor Wiese'
l_range=[ell for ell in prime_range(14)]

#breadcrumbs and links for data quality entries

def get_bread(breads=[]):
    bc = [("HeckeAlgebra", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels for Hecke Algebras', url_for(".labels_page")),
            ('History of Hecke Algebras', url_for(".history_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())


# webpages: main, random and search results

@hecke_algebras_page.route("/")
def hecke_algebras_render_webpage():
    args = request.args
    if len(args) == 0:
        weight_list= range(2, 20, 2)
        lvl_list_endpoints = [1, 100, 200, 300, 400, 500]
        lvl_list = ["%s-%s" % (start, end - 1) for start, end in zip(lvl_list_endpoints[:-1], lvl_list_endpoints[1:])]
        favourite_list = ["1.12.1","139.2.1","239.2.1","9.16.1"]
        info = {'lvl_list': lvl_list,'wt_list': weight_list, 'favourite_list': favourite_list}
        credit = hecke_algebras_credit
        t = 'Hecke Algebras'
        bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage"))]
        info['summary'] = hecke_algebras_summary()
        return render_template("hecke_algebras-index.html", info=info, credit=credit, title=t, learnmore=learnmore_list_remove('Completeness'), bread=bread)
    else:
        return hecke_algebras_search(args)

# Random hecke_algebras
@hecke_algebras_page.route("/random")
def random_hecke_algebra():
    label = db.hecke_algebras.random()
    return redirect(url_for(".render_hecke_algebras_webpage", label=label))



hecke_algebras_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d*)')
hecke_algebras_orbit_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_hecke_algebras_label(lab):
    return hecke_algebras_label_regex.match(lab).groups()

def split_hecke_algebras_orbit_label(lab):
    return hecke_algebras_orbit_label_regex.match(lab).groups()

def hecke_algebras_by_label(lab):
    if db.hecke_algebras.exists({'label':lab}):
        return render_hecke_algebras_webpage(label=lab)
    if hecke_algebras_label_regex.match(lab):
        flash(Markup("The Hecke Algebra <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No Hecke Algebras in the database has label <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".hecke_algebras_render_webpage"))

def hecke_algebras_by_orbit_label(lab):
    if db.hecke_orbits.exists({'orbit_label': lab}):
        sp=split_hecke_algebras_orbit_label(lab)
        ol=sp[0]+'.'+sp[1]+'.'+sp[2]
        return render_hecke_algebras_webpage(label=ol)
    if hecke_algebras_orbit_label_regex.match(lab):
        flash(Markup("The Hecke Algebra orbit <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No Hecke Algebras orbit in the database has label <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".hecke_algebras_render_webpage"))

def download_search(info):
    lang = info["submit"]
    filename = 'Hecke_algebras' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here

    if 'ell' in info["query"]:
        res = list(db.hecke_ladic.search(ast.literal_eval(info["query"])))
    else:
        res = list(db.hecke_orbits.search(ast.literal_eval(info["query"])))
    last = len(res)
    c = download_comment_prefix[lang]
    s =  '\n'
    if 'ell' in info["query"]:
        s += c + ' Hecke algebras downloaded from the LMFDB on %s. Found %s algebras. The data is given in the following format: it is a list of lists, each containing level, weight and the Hecke orbits for which l-adic data is available.\n\n'%(mydate, len(res))
    else:
        s += c + ' Hecke algebras downloaded from the LMFDB on %s. Found %s algebras. The data is given in the following format: it is a list of lists, each containing level, weight, list of the first 10 Hecke operators (to download more operators for a given algebra, please visit its webpage).\n\n'%(mydate, len(res))
    # The list entries are matrices of different sizes.  Sage and gp
    # do not mind this but Magma requires a different sort of list.
    list_start = '[*' if lang=='magma' else '['
    list_end = '*]' if lang=='magma' else ']'
    s += download_assignment_start[lang] + list_start + '\\\n'
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])
    # loop through all search results and grab the Hecke operators stored
    for c, rr in enumerate(res):
        s += list_start
        s += ",".join([str(rr['level']), str(rr['weight']),""])
        if 'ell' in info["query"]:
            s += '"%s"' % (str(rr['orbit_label']))
        else:
            s += ",".join([entry(r) for r in [sage_eval(rr['hecke_op'])[i] for i in range(0, min(10, rr['num_hecke_op']))]])
        if c != last:
            s += list_end + ',\\\n'
        else:
            s += list_end
    s += list_end
    s += download_assignment_end[lang]
    s += '\n'
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

def hecke_algebras_postprocess(res, info, query):
    if info.get('ell'):
        for v in res:
            v['label'] = ".".join(v['orbit_label'].split(".")[i] for i in [0,1,2])
    return res

@search_wrap(template="hecke_algebras-search.html",
             table=db.hecke_algebras, # note that if 'ell' is included, a different table is used
             title='Hecke Algebras Search Results',
             err_title='Hecke Algebras Search Error',
             shortcuts={'download':download_search,
                        'label':(lambda info: hecke_algebras_by_label(info.get('label')))},
             projection=['label','num_orbits','level','weight'],
             postprocess=hecke_algebras_postprocess,
             bread=lambda:[('HeckeAlgebras', url_for(".hecke_algebras_render_webpage")),('Search Results', ' ')],
             learnmore=learnmore_list,
             properties=lambda:[])
def hecke_algebras_search(info, query):
    for field, name in (('level','Level'),
                        ('weight','Weight'),
                        ('num_orbits', 'Number of Hecke orbits'),
                        ('ell','characteristic')):
        parse_ints(info, query, field, name)
    if info.get('ell'):
        if int(info.get('ell'))>13:
            flash(Markup("No data for primes or integers greater than $13$ is available"), "error")
            return redirect(url_for(".hecke_algebras_render_webpage"))
        elif int(info.get('ell')) not in [2,3,5,7,11,13]:
            flash(Markup("No data for integers which are not primes"), "error")
            return redirect(url_for(".hecke_algebras_render_webpage"))
    if info.get('orbit_label'):
        check=[int(i) for i in info['orbit_label'].split(".")]
        if 'level' in info and info.get('level'):
            try:
                for field in ['level','weight']:
                    if info.get(field):
                        int(info.get(field))
            except ValueError:
                flash(Markup("Orbit label <span style='color:black'>%s</span> and input Level or Weight are not compatible" %(info.get('orbit_label'))),"error")
                return redirect(url_for(".hecke_algebras_render_webpage"))
            if int(info.get('level'))!=check[0]:
                flash(Markup("Orbit label <span style='color:black'>%s</span> and Level <span style='color:black'>%s</span> are not compatible inputs" %(info.get('orbit_label'), info.get('level'))),"error")
                return redirect(url_for(".hecke_algebras_render_webpage"))
        if 'weight' in info and info.get('weight'):
            if int(info.get('weight'))!=check[1]:
                flash(Markup("Orbit label <span style='color:black'>%s</span> and Weight <span style='color:black'>%s</span> are not compatible inputs" %(info.get('orbit_label'), info.get('weight'))), "error")
                return redirect(url_for(".hecke_algebras_render_webpage"))
        if 'ell' in info and info.get('ell'):
            return render_hecke_algebras_webpage_l_adic(orbit_label=info.get('orbit_label'), prime=info.get('ell'))
        else:
            return hecke_algebras_by_orbit_label(info.get('orbit_label'))

    # If 'ell' is included, we use a different table
    if info.get('ell'):
        query['__table__'] = db.hecke_ladic
        query['__projection__'] = ['orbit_label','index','level','weight']

def search_input_error(info, bread=None):
    t = 'Hecke Algebras Search Error'
    if bread is None:
        bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),('Search Results', ' ')]
    return render_template("hecke_algebras-search.html", info=info, title=t, properties=[], bread=bread, learnmore=learnmore_list())


@hecke_algebras_page.route('/<label>')
def render_hecke_algebras_webpage(**args):
    data = None
    if 'label' in args:
        lab = clean_input(args.get('label'))
        if lab != args.get('label'):
            return redirect(url_for('.render_hecke_algebras_webpage', label=lab), 301)
        data = db.hecke_algebras.lookup(lab)
    if data is None:
        t = "Hecke Algebras Search Error"
        bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label for a Hecke Algebras in the database." % (lab)),"error")
        return render_template("hecke_algebras-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(data)

    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")), ('%s' % data['label'], ' ')]
    credit = hecke_algebras_credit
    info['level']=int(data['level'])
    info['weight']= int(data['weight'])
    info['num_orbits']= int(data['num_orbits'])
    dim_count = "not available"

    proj = ['orbit_label','hecke_op','num_hecke_op','Zbasis','discriminant','disc_fac','Qbasis','Qalg_gen']
    orb = list(db.hecke_orbits.search({'parent_label': data['label']}, proj))
    if orb:
        #consistency check
        if len(orb) != int(data['num_orbits']):
            return search_input_error(info)

        dim_count=0
        for v in orb:
            ops = sage_eval(v['hecke_op'])
            dim = int(matrix(ops[0]).nrows())
            dim_count += dim
            if dim > 4:
                v['hecke_op_display'] = []
            elif dim == 1:
                v['hecke_op_display'] = [[i+1, ops[i][0][0]] for i in range(10)]
            else:
                v['hecke_op_display'] = [[i+1, latex(matrix(ops[i]))] for i in range(5)]
            v['download_op'] = [(lang, url_for(".render_hecke_algebras_webpage_download", orbit_label=v['orbit_label'], lang=lang, obj='operators')) for lang in ['gp', 'magma','sage']]
            if v['Zbasis'] is None:
                for key in ['Zbasis','discriminant','disc_fac','Qbasis','Qalg_gen']:
                    del v[key]
            else:
                v['Zbasis'] = [[int(i) for i in j] for j in v['Zbasis']]
                v['disc_fac'] = [[int(i) for i in j] for j in v['disc_fac']]
                if dim > 4:
                    v['gen_display'] = []
                elif dim == 1:
                    v['gen_display'] = [v['Zbasis'][0][0]]
                else:
                    v['gen_display'] = [latex(matrix(dim,dim,v['Zbasis'][i])) for i in range(dim)]
                v['inner_twists'] = "not available" # not yet in the database
                v['download_gen'] = [(lang, url_for(".render_hecke_algebras_webpage_download", orbit_label=v['orbit_label'], lang=lang, obj='gen')) for lang in ['gp', 'magma','sage']]
        info['orbits'] = orb

    info['dim_alg'] = dim_count
    info['l_adic'] = l_range
    info['properties'] = [
        ('Label', '%s' %info['label']),
        ('Level', '%s' %info['level']),
        ('Weight', '%s' %info['weight'])]
    if info['num_orbits']!=0:
        info['friends'] = [('Newforms space ' + info['label'], url_for("cmf.by_url_space_label", level=info['level'], weight=info['weight'], char_orbit_label='a'))]
    else:
        info['friends'] = []
    t = "Hecke Algebra %s" % info['label']
    return render_template("hecke_algebras-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list(), friends=info['friends'])




hecke_algebras_orbit_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split(lab):
    return hecke_algebras_orbit_label_regex.match(lab).groups()

@hecke_algebras_page.route('/<orbit_label>/<prime>')
def render_hecke_algebras_webpage_l_adic(**args):
    data = None
    if 'orbit_label' in args and 'prime' in args:
        lab = clean_input(args.get('orbit_label'))
        if lab != args.get('orbit_label'):
            base_lab=".".join([split(lab)[i] for i in [0,1,2]])
            return redirect(url_for('.render_hecke_algebras_webpage', label=base_lab), 301)
        try:
            ell = int(args.get('prime'))
        except ValueError:
            base_lab=".".join([split(lab)[i] for i in [0,1,2]])
            return redirect(url_for('.render_hecke_algebras_webpage', label=base_lab), 301)
        data = db.hecke_ladic.lucky({'orbit_label': lab , 'ell': ell})
    if data is None:
        t = "Hecke Algebras Search Error"
        bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label for the &#x2113;-adic information for an Hecke Algebra orbit in the database." % (lab)),"error")
        return render_template("hecke_algebras-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(data)

    proj = ['index','orbit_label','ell','idempotent','field','structure','properties','operators']
    res = list(db.hecke_ladic.search({'level': data['level'],'weight': data['weight'],'orbit_label': data['orbit_label'], 'ell': data['ell']}, proj))

    for f in res:
        if f['idempotent'] != "":
            dim = len(sage_eval(f['idempotent']))
            l_max = sage_eval(f['idempotent'])[0][0].ndigits()
            if dim > 4 or l_max > 5:
                f['idempotent_display'] = []
            elif dim == 1:
                f['idempotent_display'] = sage_eval(f['idempotent'])[0][0]
            else:
                f['idempotent_display'] = latex(matrix(sage_eval(f['idempotent'])))
        else:
            f['idempotent_display']=latex(matrix([[1]]))
        del f['idempotent']
        f['download_id'] = [(i, url_for(".render_hecke_algebras_webpage_ell_download", orbit_label=f['orbit_label'], index=f['index'], prime=f['ell'], lang=i, obj='idempotents')) for i in ['magma','sage']]  # for 'gp' the code does not work, since p-adics are not implemented
        field = f.pop('field')
        if field is not None:
            f['deg'] = field[1]
            f['field_poly'] = field[2]
        structure = f.pop('structure')
        if structure is not None:
            f['dim'] = structure[0]
            f['num_gen'] = structure[1]
            s2 = sage_eval(structure[2])
            f['gens'] = [[int(s2.index(i)+1), str(i)] for i in s2]
            f['rel'] = sage_eval(structure[3])
        properties = f.pop('properties')
        if properties is not None:
            f['grading'] = properties[0]
            f['gorenstein_def'] = properties[1]
            f['gorenstein'] = "yes" if properties[1] == 0 else "no"
        operators = f.pop('operators')
        if operators is not None:
            f['operators_mod_l'] = operators
            f['num_hecke_op'] = len(operators)
            f['size_op'] = size = sqrt(len(operators[0]))
            if size > 4:
                f['operators_mod_l_display'] = []
            elif size == 1:
                f['operators_mod_l_display'] = [[i+1, operators[i][0]] for i in range(10)]
            else:
                f['operators_mod_l_display'] = [[i+1, latex(matrix(size,size,operators[i]))] for i in range(5)]
            f['download_op'] = [(lang, url_for(".render_hecke_algebras_webpage_ell_download", orbit_label=f['orbit_label'], index=f['index'], prime=f['ell'], lang=lang, obj='operators')) for lang in ['magma','sage']]  # for 'gp' the code does not work

    info['num_l_adic_orbits'] = len(res)
    info['l_adic_orbits'] = res
    info['level']=int(data['level'])
    info['weight']= int(data['weight'])
    info['base_lab']=".".join([split(data['orbit_label'])[i] for i in [0,1,2]])
    info['orbit_label']= str(data['orbit_label'])
    info['ell']=int(data['ell'])

    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")), ('%s' % info['base_lab'], url_for('.render_hecke_algebras_webpage', label=info['base_lab'])), ('%s' % info['ell'], ' ')]
    credit = hecke_algebras_credit
    info['properties'] = [
        ('Level', '%s' %info['level']),
        ('Weight', '%s' %info['weight']),
        ('Characteristic', '%s' %info['ell']),
        ('Orbit label', '%s' %info['orbit_label'])]
    info['friends'] = [('Modular form ' + info['base_lab'], url_for("cmf.by_url_space_label", level=info['level'], weight=info['weight'], char_orbit_label='a'))]

    t = "%s-adic and mod %s Data for the Hecke Algebra Orbit %s" % (info['ell'], info['ell'], info['orbit_label'])
    return render_template("hecke_algebras_l_adic-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list(), friends=info['friends'])



#data quality pages
@hecke_algebras_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Hecke Algebra Data'
    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),
             ('Completeness', '')]
    credit = hecke_algebras_credit
    return render_template("single.html", kid='dq.hecke_algebras.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@hecke_algebras_page.route("/Source")
def how_computed_page():
    t = 'Source of the Hecke Algebra Data'
    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),
             ('Source', '')]
    credit = hecke_algebras_credit
    return render_template("single.html", kid='dq.hecke_algebras.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@hecke_algebras_page.route("/Labels")
def labels_page():
    t = 'Label of Hecke Algebras'
    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),
             ('Labels', '')]
    credit = hecke_algebras_credit
    return render_template("single.html", kid='hecke_algebras.label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

@hecke_algebras_page.route("/History")
def history_page():
    t = 'A Brief History of Hecke Algebras'
    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),
             ('Histoy', '')]
    credit = hecke_algebras_credit
    return render_template("single.html", kid='hecke_algebras.history',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('History'))

#download
download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\'}
download_assignment_start = {'magma':'data := ','sage':'data = ','gp':'data = '}
download_assignment_end = {'magma':';','sage':'','gp':''}
download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp'}


@hecke_algebras_page.route('/<orbit_label>/download/<lang>/<obj>')
def render_hecke_algebras_webpage_download(**args):
    if args['obj'] == 'operators':
        response = make_response(download_hecke_algebras_full_lists_op(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'gen': 
        response = make_response(download_hecke_algebras_full_lists_gen(**args))
        response.headers['Content-type'] = 'text/plain'
        return response

def download_hecke_algebras_full_lists_op(**args):
    label = str(args['orbit_label'])
    res = db.hecke_orbits.lucky({'orbit_label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No operators available"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + 'Hecke algebra for Gamma0(%s) and weight %s, orbit label %s. List of Hecke operators T_1, ..., T_%s. Downloaded from the LMFDB on %s. \n\n'%(res['level'], res['weight'], res['orbit_label'],res['num_hecke_op'], mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join([entry(r) for r in [sage_eval(res['hecke_op'])[i] for i in range(0,res['num_hecke_op'])]])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr

def download_hecke_algebras_full_lists_gen(**args):
    label = str(args['orbit_label'])
    res = db.hecke_orbits.lucky({'orbit_label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No generators available"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + 'Hecke algebra for Gamma0(%s) and weight %s, orbit label %s. List of generators for the algebra. Downloaded from the LMFDB on %s. \n\n'%(res['level'], res['weight'], res['orbit_label'], mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join([entry([list(k) for k in matrix(sqrt(len(r)), sqrt(len(r)), r).rows()]) for r in [[int(i) for i in j] for j in res['Zbasis']] ])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr


@hecke_algebras_page.route('/<orbit_label>/<index>/<prime>/download/<lang>/<obj>')
def render_hecke_algebras_webpage_ell_download(**args):
    if args['obj'] == 'operators':
        response = make_response(download_hecke_algebras_full_lists_mod_op(**args)) 
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'idempotents': 
        response = make_response(download_hecke_algebras_full_lists_id(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_hecke_algebras_full_lists_mod_op(**args):
    label = str(args['orbit_label'])
    ell=int(args['prime'])
    index=int(args['index'])
    res = db.hecke_ladic.lucky({'orbit_label': label, 'index': index, 'ell': ell})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No mod %s operators available"%ell
    lang = args['lang']
    c = download_comment_prefix[lang]
    field='GF(%s), %s, %s, '%(res['ell'], sqrt(len(res['operators'][0])), sqrt(len(res['operators'][0])))
    mat_start = "Mat("+field if lang == 'gp' else "Matrix("+field 
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + ' List of Hecke operators T_1, ..., T_%s mod %s for orbit %s index %s downloaded from the LMFDB on %s. \n\n'%(len(res['operators']), ell, label, index, mydate)
    outstr += download_assignment_start[lang] +'[\\\n'
    outstr += ",\\\n".join([entry(r) for r in res['operators']])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr


def download_hecke_algebras_full_lists_id(**args):
    label = str(args['orbit_label'])
    ell=int(args['prime'])
    index=int(args['index'])
    idempotent = db.hecke_ladic.lucky({'orbit_label': label, 'index': index, 'ell': ell }, projection='idempotent')
    mydate = time.strftime("%d %B %Y")
    if idempotent is None:
        return "No mod %s operators available"%ell
    lang = args['lang']
    c = download_comment_prefix[lang]

    if lang == 'magma': #no idea for gp
        ladic = 'pAdicRing(%s : Precision :=200),'%ell
    elif lang== 'sage':
        ladic = 'Qp(%s, 200),'%ell
    mat_start = "Mat("+ladic if lang == 'gp' else "Matrix("+ladic
    mat_end = "~)" if lang == 'gp' else ")"

    outstr = c + ' Idempotent for the Hecke orbit %s mod %s and index %s downloaded from the LMFDB on %s. \n\n'%( label, ell , index, mydate)
    outstr += download_assignment_start[lang] +'['
    outstr += " ".join([mat_start, idempotent, mat_end])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr
