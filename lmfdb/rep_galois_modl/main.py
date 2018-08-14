import re
LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

#from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, Flask, session, g, redirect, make_response, flash,  send_file
from flask import flash, make_response, send_file, request, render_template, redirect, url_for

from lmfdb.db_backend import db

from sage.all import ZZ, conway_polynomial

from lmfdb.rep_galois_modl import rep_galois_modl_page #, rep_galois_modl_logger
from lmfdb.rep_galois_modl.rep_galois_modl_stats import get_stats
from lmfdb.search_parsing import parse_ints, parse_list
from lmfdb.search_wrapper import search_wrap

#should these functions be defined in lattices or somewhere else?
from lmfdb.lattice.main import vect_to_sym, vect_to_matrix

from markupsafe import Markup

import time
import ast
import StringIO

rep_galois_modl_credit = 'Samuele Anni, Anna Medvedovsky, Bartosz Naskrecki, David Roberts'



# utilitary functions for displays 

def my_latex(s):
    ss = ""
    ss += re.sub('x\d', 'x', s)
    ss = re.sub("\^(\d+)", "^{\\1}", ss)
    ss = re.sub('\*', '', ss)
    ss = re.sub('zeta(\d+)', 'zeta_{\\1}', ss)
    ss = re.sub('zeta', '\zeta', ss)
    ss += ""
    return ss

#breadcrumbs and links for data quality entries

def get_bread(breads=[]):
    bc = [('Representations', "/Representation"),("mod &#x2113;", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())


# webpages: main, random and search results

@rep_galois_modl_page.route("/")
def rep_galois_modl_render_webpage():
    args = request.args
    if len(args) == 0:
        # FIXME THIS VARIABLE IS NEVER USED
        #counts = get_stats().counts()
        dim_list= range(1, 11, 1)
        max_class_number=20
        class_number_list=range(1, max_class_number+1, 1)
        det_list_endpoints = [1, 5000, 10000, 20000, 25000, 30000]
#        if counts['max_det']>3000:
#            det_list_endpoints=det_list_endpoints+range(3000, max(int(round(counts['max_det']/1000)+2)*1000, 10000), 1000)
        det_list = ["%s-%s" % (start, end - 1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
        name_list = ["A2","Z2", "D3", "D3*", "3.1942.3884.56.1", "A5", "E8", "A14", "Leech"]
        info = {'dim_list': dim_list,'class_number_list': class_number_list,'det_list': det_list, 'name_list': name_list}
        credit = rep_galois_modl_credit
        t = 'Mod &#x2113; Galois representations'
        bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage"))]
        info['counts'] = get_stats().counts()
        return render_template("rep_galois_modl-index.html", info=info, credit=credit, title=t, learnmore=learnmore_list_remove('Completeness'), bread=bread)
    else:
        return rep_galois_modl_search(args)

# Random rep_galois_modl
@rep_galois_modl_page.route("/random")
def random_rep_galois_modl():
    label = db.modlgal_reps.random()
    return redirect(url_for(".render_rep_galois_modl_webpage", label=label))


rep_galois_modl_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_rep_galois_modl_label(lab):
    return rep_galois_modl_label_regex.match(lab).groups()

def rep_galois_modl_by_label_or_name(lab):
    if db.modlgal_reps.exists({'$or':[{'label': lab}, {'name': lab}]}):
        return render_rep_galois_modl_webpage(label=lab)
    if rep_galois_modl_label_regex.match(lab):
        flash(Markup("The integral rep_galois_modl <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No integral rep_galois_modl in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".rep_galois_modl_render_webpage"))

#download
download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\'}
download_assignment_start = {'magma':'data := ','sage':'data = ','gp':'data = '}
download_assignment_end = {'magma':';','sage':'','gp':''}
download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp'}

def download_search(info):
    lang = info["submit"]
    filename = 'integral_rep_galois_modls' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here

    res = list(db.modlgal_reps.search(ast.literal_eval(info["query"]), "gram"))

    c = download_comment_prefix[lang]
    s =  '\n'
    s += c + ' Integral rep_galois_modls downloaded from the LMFDB on %s. Found %s rep_galois_modls.\n\n'%(mydate, len(res))
    # The list entries are matrices of different sizes.  Sage and gp
    # do not mind this but Magma requires a different sort of list.
    list_start = '[*' if lang=='magma' else '['
    list_end = '*]' if lang=='magma' else ']'
    s += download_assignment_start[lang] + list_start + '\\\n'
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])
    # loop through all search results and grab the gram matrix
    s += ",\\\n".join([entry(gram) for gram in res])
    s += list_end
    s += download_assignment_end[lang]
    s += '\n'
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

@search_wrap(template="rep_galois_modl-search.html",
             table=db.modlgal_reps,
             title='Mod &#x2113; Galois representations Search Results',
             err_title='Mod &#x2113; Galois representations Search Results Error',
             per_page=20,
             shortcuts={'download':download_search,
                        'label':lambda info:rep_galois_modl_by_label_or_name(info.get('label'))},
             projection=['label','dim','det','level','gram'],
             cleaners={'gram':lambda v:vect_to_matrix(v['gram'])},
             bread=lambda:[('Representations', "/Representation"),("mod &#x2113;", url_for(".index")), ('Search Results', ' ')],
             properties=lambda:[],
             learnmore=learnmore_list)
def rep_galois_modl_search(info, query):
    for field, name in (('dim','Dimension'), ('det','Determinant'),
                        ('level',None), ('minimum','Minimal vector length'),
                        ('class_number',None), ('aut','Group order')):
        parse_ints(info, query, field, name)
    # Check if length of gram is triangular
    gram = info.get('gram')
    if gram and not (9 + 8*ZZ(gram.count(','))).is_square():
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input for Gram matrix.  It must be a list of integer vectors of triangular length, such as [1,2,3]." % (gram)),"error")
        raise ValueError
    parse_list(info, query, 'gram', process=vect_to_sym)

@rep_galois_modl_page.route('/<label>')
def render_rep_galois_modl_webpage(**args):
    data = None
    if 'label' in args:
        lab = args.get('label')
        data = db.modlgal_reps.lookup(lab)
    if data is None:
        t = "Mod &#x2113; Galois representations Search Error"
        bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label for a mod &#x2113; Galois representation in the database." % (lab)),"error")
        return render_template("rep_galois_modl-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(data)

    info['friends'] = []


    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage")), ('%s' % data['label'], ' ')]
    credit = rep_galois_modl_credit

    for m in ['base_field','image_type','image_label','image_at','projective_type','projective_label','related_objects', 'label']:
        info[m]=str(data[m])
    for m in ['dim','field_char','field_deg','conductor','weight','abs_irr','image_order','degree_proj_field']:
        info[m]=int(data[m])
    info['primes_conductor']=[int(i) for i in data['primes_conductor']]

    for m in ['poly_ker','poly_proj_ker']:
        info[m]=str(data[m]).replace("*", "").strip('(').strip(')')

    if data['rep_type'] =="symp":
        info['rep_type']="Symplectic"
    elif data['rep_type'] =="orth":
        info['rep_type']="Orthogonal"
    else:
        info['rep_type']="Linear"


    if info['field_deg'] > int(1):
        try:
            pol=str(conway_polynomial(data['characteristic'], data['deg'])).replace("*", "")
            info['field_str']=str('$\mathbb{F}_%s \cong \mathbb{F}_%s[a]$ where $a$ satisfies: $%s=0$' %(str(data['field_char']), str(data['field_char']), pol))
        except:
            info['field_str']=""


    info['bad_prime_list']=[]
    info['good_prime_list']=[]
    for n in data['bad_prime_list']:
        try:
            n1=[int(n[0]), str(n[1]), str(n[2]), int(n[3]), int(n[4])]
        except:
            n1=[int(n[0]), str(n[1]), str(n[2]), str(n[3]), str(n[4])]
        info['bad_prime_list'].append(n1)
    info['len_good']=[int(i+1) for i in range(len(data['good_prime_list'][0][1]))]
    for n in data['good_prime_list']:
        try:
            n1=[int(n[0]), [str(m) for m in n[1]], str(n[2]), int(n[3]), int(n[4])]
        except:
            n1=[int(n[0]), [str(m) for m in n[1]], str(n[2]), str(n[3]), str(n[4])]
        info['good_prime_list'].append(n1)

        info['download_list'] = [
            (i, url_for(".render_rep_galois_modl_webpage_download", label=info['label'], lang=i)) for i in ['gp', 'magma','sage']]

    t = "Mod &#x2113; Galois representation "+info['label']
    info['properties'] = [
        ('Label', '%s' %info['label']),
        ('Dimension', '%s' %info['dim']),
        ('Field characteristic', '%s' %info['field_char']),
        ('Conductor', '%s' %info['conductor']),]
    return render_template("rep_galois_modl-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list())
#friends=friends


#data quality pages
@rep_galois_modl_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the integral rep_galois_modl data'
    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage")),
             ('Completeness', '')]
    credit = rep_galois_modl_credit
    return render_template("single.html", kid='dq.rep_galois_modl.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@rep_galois_modl_page.route("/Source")
def how_computed_page():
    t = 'Source of the integral rep_galois_modl data'
    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage")),
             ('Source', '')]
    credit = rep_galois_modl_credit
    return render_template("single.html", kid='dq.rep_galois_modl.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@rep_galois_modl_page.route("/Labels")
def labels_page():
    t = 'Label of an integral rep_galois_modl'
    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage")),
             ('Labels', '')]
    credit = rep_galois_modl_credit
    return render_template("single.html", kid='rep_galois_modl.label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

@rep_galois_modl_page.route('/<label>/download/<lang>/')
def render_rep_galois_modl_webpage_download(**args):
    if args['obj'] == 'shortest_vectors':
        response = make_response(download_rep_galois_modl_full_lists_v(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'genus_reps':
        response = make_response(download_rep_galois_modl_full_lists_g(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_rep_galois_modl_full_lists_v(**args):
    label = str(args['label'])
    res = db.modlgal_reps.lookup(label, projection=['name','shortest'])
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such rep_galois_modl"
    lang = args['lang']
    c = download_comment_prefix[lang]
    outstr = c + ' Full list of normalized minimal vectors downloaded from the LMFDB on %s. \n\n'%(mydate)
    outstr += download_assignment_start[lang] + '\\\n'
    if res['name']==['Leech']:
        outstr += str(res['shortest']).replace("'", "").replace("u", "")
    else:
        outstr += str(res['shortest'])
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr


def download_rep_galois_modl_full_lists_g(**args):
    label = str(args['label'])
    reps = db.modlgal_reps.lookup(label, projection='genus_reps')
    mydate = time.strftime("%d %B %Y")
    if reps is None:
        return "No such rep_galois_modl"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + ' Full list of genus representatives downloaded from the LMFDB on %s. \n\n'%(mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join([entry(r) for r in reps])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr

