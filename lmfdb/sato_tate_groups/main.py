# -*- coding: utf-8 -*-

import re, itertools
from flask import render_template, url_for, redirect, request, jsonify
from lmfdb.sato_tate_groups import st_page
from lmfdb.utils import to_dict, encode_plot, flash_error
from lmfdb.search_parsing import parse_ints, parse_rational, parse_count, parse_start, parse_ints_to_list_flash, clean_input
from lmfdb.db_backend import db
from lmfdb.base import ctx_proc_userdata
from psycopg2.extensions import QueryCanceledError

from sage.all import ZZ, cos, sin, pi, list_plot, circle

###############################################################################
# Globals
###############################################################################

MU_LABEL_RE = '^0\.1\.[1-9][0-9]*'
MU_LABEL_NAME_RE = r'^0\.1\.mu\([1-9][0-9]*\)$'
ST_LABEL_RE = '^\d+\.\d+\.\d+\.\d+\.\d+[a-z]+$'
ST_LABEL_SHORT_RE = '^\d+\.\d+\.\d+\.\d+\.\d+$'
ST_LABEL_NAME_RE = r'^\d+\.\d+\.[a-zA-z0-9\{\}\(\)\[\]\_\,]+'
INFINITY = -1

credit_string = 'Andrew Sutherland'

# use a list and a dictionary (for pretty printing) so that we can control the display order (switch to ordered dictionary once everyone is on python 3.1)
st0_list = ( 'SO(1)', 'U(1)', 'SU(2)', 'U(1)_2', 'SU(2)_2','U(1)xU(1)', 'U(1)xSU(2)','SU(2)xSU(2)','USp(4)' )
st0_dict = {
    'SO(1)':'\\mathrm{SO}(1)',
    'U(1)':'\\mathrm{U}(1)',
    'SU(2)':'\\mathrm{SU}(2)',
    'U(1)_2':'\\mathrm{U}(1)_2',
    'SU(2)_2':'\\mathrm{SU}(2)_2',
    'U(1)xU(1)':'\\mathrm{U}(1)\\times\\mathrm{U}(1)',
    'U(1)xSU(2)':'\\mathrm{U}(1)\\times\\mathrm{SU}(2)',
    'SU(2)xSU(2)':'\\mathrm{SU}(2)\\times\\mathrm{SU}(2)',
    'USp(4)':'\\mathrm{USp}(4)'
}

###############################################################################
# Utility functions
###############################################################################

def boolean_name(value):
    return '\\mathrm{True}' if value else '\\mathrm{False}'

def comma_separated_list(list):
    return ', '.join(list)

def string_matrix(m):
    if len(m) == 0:
        return ''
    return '\\begin{bmatrix}' + '\\\\'.join(['&'.join(map(str, m[i])) for i in range(len(m))]) + '\\end{bmatrix}'

def st_link(label):
    if re.match(MU_LABEL_RE, label):
        return '''<a href=%s>$%s$</a>'''% (url_for('.by_label', label=label), '\\mu(%s)'%label.split('.')[2])
    data = db.gps_sato_tate.lookup(label)
    if not data:
        return label
    return '''<a href=%s>$%s$</a>'''% (url_for('.by_label', label=label), data['pretty'])

def st_ambient(weight, degree):
    return '\\mathrm{USp}(%d)'%degree if weight%2 == 1 else '\\mathrm{O}(%d)'%degree

def trace_moments(moments):
    for m in moments:
        if m[0] == 'a_1'or m[0] == 's_1':
            return m[1:10]
    return ''

def st0_pretty(st0_name):
    if re.match('SO\(1\)\_\d+', st0_name):
        return '\\mathrm{SO}(1)_{%s}' % st0_name.split('_')[1]
    return st0_dict.get(st0_name,st0_name)

def sg_pretty(sg_label):
    data = db.gps_small.lookup(sg_label)
    if data and 'pretty' in data:
        return data['pretty']
    return sg_label
    
# dictionary for quick and dirty prettification that does not access the database
st_pretty_dict = {
    'USp(4)':'\\mathrm{USp}(4)',
    'SU(2)':'\\mathrm{SU}(2)',
    'U(1)':'\\mathrm{U}(1)',
    'N(U(1))':'N(\\mathrm{U}(1))'
}

def st_pretty(st_name):
    if re.match('mu\([1-9][0-9]*\)', st_name):
        return '\\' + st_name
    return st_pretty_dict.get(st_name,st_name)

def st_link_by_name(weight,degree,name):
    return '<a href="%s">$%s$</a>' % (url_for('st.by_label', label="%s.%s.%s"%(weight,degree,name)), st_pretty(name))

###############################################################################
# Learnmore display functions
###############################################################################

def learnmore_list():
    return [('Completeness of the data', url_for('.completeness_page')),
            ('Source of the data', url_for('.how_computed_page')),
            ('Sato-Tate group labels', url_for('.labels_page'))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

###############################################################################
# Pages
###############################################################################

@st_page.route('/')
def index():
    if len(request.args) != 0:
        return search(**request.args)
    weight_list= [0, 1]
    degree_list=range(1, 5, 1)
    group_list = [ '1.2.1.2.1a','1.2.3.1.1a', '1.4.1.12.4d', '1.4.3.6.2a', '1.4.6.1.1a', '1.4.10.1.1a' ]
    group_dict = { '1.2.1.2.1a':'N(\\mathrm{U}(1))','1.2.3.1.1a':'\\mathrm{SU}(2)', '1.4.1.12.4d':'D_{6,2}','1.4.3.6.2a':'E_6', '1.4.6.1.1a':'G_{3,3}', '1.4.10.1.1a':'\\mathrm{USp}(4)' }
    info = {'weight_list' : weight_list, 'degree_list' : degree_list, 'st0_list' : st0_list, 'st0_dict' : st0_dict, 'group_list': group_list, 'group_dict' : group_dict}
    title = 'Sato-Tate Groups'
    bread = [('Sato-Tate Groups', '.')]
    return render_template('st_browse.html', info=info, credit=credit_string, title=title, learnmore=learnmore_list_remove('Completeness'), bread=bread)

@st_page.route('/random')
def random():
    label = db.gps_sato_tate.random()
    return redirect(url_for('.by_label', label=label), 307)

@st_page.route('/<label>')
def by_label(label):
    clean_label = clean_input(label)
    if clean_label != label:
        return redirect(url_for('.by_label', label=clean_label), 301)
    return search_by_label(label)

###############################################################################
# Searching
###############################################################################

def search_by_label(label):
    """ search for Sato-Tate group by label and render if found """

    if re.match(ST_LABEL_RE, label):
        return render_by_label(label)
    if re.match(ST_LABEL_SHORT_RE, label):
        return redirect(url_for('.by_label',label=label+'a'),301)
    # check for labels of the form 0.1.n corresponding to mu(n)
    if re.match(MU_LABEL_RE, label):
        return render_by_label(label)
    # check for labels of the form 0.1.mu(n) (redirecto to 0.1.n)
    if re.match(MU_LABEL_NAME_RE, label):
        return redirect(url_for('.by_label',label='0.1.'+label.split('(')[1].split(')')[0]), 301)
    # check for general labels of the form w.d.name
    if re.match(ST_LABEL_NAME_RE,label):
        slabel = label.split('.')
        try:
            label = db.gps_sato_tate.lucky({'weight':int(slabel[0]),'degree':int(slabel[1]),'name':slabel[2]}, 0)
        except ValueError:
            label = None
    if label is None:
        flash_error("%s is not the label or name of a Sato-Tate group currently in the database", label)
        return redirect(url_for(".index"))
    else:
        return redirect(url_for('.by_label', label=label), 301)

# This search function doesn't fit the model of search_wrapper very well,
# So we don't use it.
def search(**args):
    """ query processing for Sato-Tate groups -- returns rendered results page """
    info = to_dict(args)
    if 'jump' in info:
        return redirect(url_for('.by_label', label=info['jump']), 301)
    if 'label' in info:
        return redirect(url_for('.by_label', label=info['label']), 301)
    template_kwds = {'bread':[('Sato-Tate Groups', url_for('.index')),('Search Results', '.')],
                     'credit':credit_string,
                     'learnmore':learnmore_list()}
    title = 'Sato-Tate Group Search Results'
    err_title = 'Sato-Tate Groups Search Input Error'
    count = parse_count(info, 25)
    start = parse_start(info)
    # if user clicked refine search always restart at 0
    if 'refine' in info:
        start = 0
    ratonly = True if info.get('rational_only','no').strip().lower() == 'yes' else False
    query = {'rational':True} if ratonly else {}
    try:
        parse_ints(info,query,'weight','weight')
        if 'weight' in query:
            weight_list = parse_ints_to_list_flash(info.get('weight'),'weight')
        parse_ints(info,query,'degree','degree')
        if 'degree' in query:
            degree_list = parse_ints_to_list_flash(info.get('degree'),'degree')
        if info.get('identity_component'):
            query['identity_component'] = info['identity_component']
        parse_ints(info,query,'components','components')
        if 'components' in query:
            components_list = parse_ints_to_list_flash(info.get('components'), 'components')
        parse_rational(info,query,'trace_zero_density','trace zero density')
    except ValueError as err:
        info['err'] = str(err)
        return render_template('st_results.html', info=info, title=err_title, **template_kwds)

    # Check mu(n) groups first (these are not stored in the database)
    results = []
    if (not 'weight' in query or 0 in weight_list) and \
       (not 'degree' in query or 1 in degree_list) and \
       (not 'identity_component' in query or query['identity_component'] == 'SO(1)') and \
       (not 'trace_zero_density' in query or query['trace_zero_density'] == '0'):
        if not 'components' in query:
            components_list = xrange(1,3 if ratonly else start+count+1)
        elif ratonly:
            components_list = [n for n in range(1,3) if n in components_list]
        nres = len(components_list) if 'components' in query or ratonly else INFINITY
        for n in itertools.islice(components_list,start,start+count):
            results.append(mu_info(n))
    else:
        nres = 0

    if 'result_count' in info:
        nres += db.gps_sato_tate.count(query)
        return jsonify({"nres":str(nres)})

    # Now lookup other (rational) ST groups in database
    if nres != INFINITY:
        start2 = start - nres if start > nres else 0
        proj = ['label','weight','degree','real_dimension','identity_component','name','pretty','components','component_group','trace_zero_density','moments']
        try:
            res = db.gps_sato_tate.search(query, proj, limit=max(count - len(results), 0), offset=start2, info=info)
        except QueryCanceledError as err:
            ctx = ctx_proc_userdata()
            flash_error('The search query took longer than expected! Please help us improve by reporting this error  <a href="%s" target=_blank>here</a>.' % ctx['feedbackpage'])
            info['err'] = str(err)
            return render_template('st_results.html', info=info, title=err_title, **template_kwds)
        info['number'] += nres
        if start < info['number'] and len(results) < count:
            for v in res:
                v['identity_component'] = st0_pretty(v['identity_component'])
                v['component_group'] = sg_pretty(v['component_group'])
                v['trace_moments'] = trace_moments(v['moments'])
                results.append(v)
    else:
        info['number'] = 'infinity'
        info['start'] = start
        info['count'] = count

    info['st0_list'] = st0_list
    info['st0_dict'] = st0_dict
    info['results'] = results
    info['stgroup_url'] = lambda dbc: url_for('.by_label', label=dbc['label'])
    return render_template('st_results.html', info=info, title=title, **template_kwds)

###############################################################################
# Rendering
###############################################################################

def mu_info(n):
    """ return data for ST group mu(n); for n > 2 these groups are irrational and not stored in the database """
    n = ZZ(n)
    rec = {}
    rec['label'] = "0.1.%d"%n
    rec['weight'] = 0
    rec['degree'] = 1
    rec['rational'] = boolean_name(True if n <= 2 else False)
    rec['name'] = 'mu(%d)'%n
    rec['pretty'] = '\mu(%d)'%n
    rec['real_dimension'] = 0
    rec['components'] = int(n)
    rec['ambient'] = '\mathrm{O}(1)' if n <= 2 else '\mathrm{U}(1)'
    rec['connected'] = boolean_name(rec['components'] == 1)
    rec['st0_name'] = '\mathrm{SO}(1)'
    rec['identity_component'] = st0_pretty(rec['st0_name'])
    rec['st0_description'] = '\\mathrm{trivial}'
    rec['component_group'] = 'C_{%d}'%n
    rec['trace_zero_density']='0'
    rec['abelian'] = boolean_name(True)
    rec['cyclic'] = boolean_name(True)
    rec['solvable'] = boolean_name(True)
    rec['gens'] = r'\left[\zeta_{%d}\right]'%n
    rec['numgens'] = 1
    rec['subgroups'] = comma_separated_list([st_link("0.1.%d"%(n/p)) for p in n.prime_factors()])
    # only list supgroups with the same ambient (i.e.if mu(n) lies in O(1) don't list supgroups that are not)
    if n == 1:
        rec['supgroups'] = st_link("0.1.2")
    elif n > 2:
        rec['supgroups'] = comma_separated_list([st_link("0.1.%d"%(p*n)) for p in [2,3,5]] + ["$\ldots$"])
    rec['moments'] = [['x'] + [ '\\mathrm{E}[x^{%d}]'%m for m in range(13)]]
    rec['moments'] += [['a_1'] + ['1' if m % n == 0  else '0' for m in range(13)]]
    rec['trace_moments'] = trace_moments(rec['moments'])
    rational_traces = [1] if n%2 else [1,-1]
    rec['counts'] = [['a_1', [[t,1] for t in rational_traces]]]
    rec['probabilities'] = [['\\mathrm{P}[a_1=%d]=\\frac{1}{%d}'%(m,n)] for m in rational_traces]
    return rec

def mu_portrait(n):
    """ returns an encoded scatter plot of the nth roots of unity in the complex plane """
    if n <= 120:
        plot =  list_plot([(cos(2*pi*m/n),sin(2*pi*m/n)) for m in range(n)],pointsize=30+60/n, axes=False)
    else:
        plot = circle((0,0),1,thickness=3)
    plot.xmin(-1); plot.xmax(1); plot.ymin(-1); plot.ymax(1)
    plot.set_aspect_ratio(4.0/3.0)
    return encode_plot(plot)

def render_by_label(label):
    """ render html page for Sato-Tate group sepecified by label """
    if re.match(MU_LABEL_RE, label):
        n = ZZ(label.split('.')[2])
        if n > 10**20:
            flash_error("number of components %s is too large, it should be less than 10^{20}$.", n)
            return redirect(url_for(".index"))
        return render_st_group(mu_info(n), portrait=mu_portrait(n))
    data = db.gps_sato_tate.lookup(label)
    info = {}
    if data is None:
        flash_error ("%s is not the label of a Sato-Tate group currently in the database.", label)
        return redirect(url_for(".index"))
    for attr in ['label','weight','degree','name','pretty','real_dimension','components']:
        info[attr] = data[attr]
    info['ambient'] = st_ambient(info['weight'],info['degree'])
    info['connected']=boolean_name(info['components'] == 1)
    info['rational']=boolean_name(info.get('rational',True))
    st0 = db.gps_sato_tate0.lucky({'name':data['identity_component']})
    if not st0:
        flash_error ("%s is not the label of a Sato-Tate identity component currently in the database.", data['identity_component'])
        return redirect(url_for(".index"))
    info['st0_name']=st0['pretty']
    info['st0_description']=st0['description']
    G = db.gps_small.lookup(data['component_group'])
    if not G:
        flash_error ("%s is not the label of a Sato-Tate component group currently in the database.", data['component_group'])
        return redirect(url_for(".index"))
    info['component_group']=G['pretty']
    info['cyclic']=boolean_name(G['cyclic'])
    info['abelian']=boolean_name(G['abelian'])
    info['solvable']=boolean_name(G['solvable'])
    info['gens']=comma_separated_list([string_matrix(m) for m in data['gens']])
    info['numgens']=len(info['gens'])
    info['subgroups'] = comma_separated_list([st_link(sub) for sub in data['subgroups']])
    info['supgroups'] = comma_separated_list([st_link(sup) for sup in data['supgroups']])
    if data['moments']:
        info['moments'] = [['x'] + [ '\\mathrm{E}[x^{%d}]'%m for m in range(len(data['moments'][0])-1)]]
        info['moments'] += data['moments']
    if data['counts']:
        c=data['counts']
        info['probabilities'] = [['\\mathrm{P}[%s=%d]=\\frac{%d}{%d}'%(c[i][0],c[i][1][j][0],c[i][1][j][1],data['components']) for j in range(len(c[i][1]))] for i in range(len(c))]
    return render_st_group(info, portrait=data.get('trace_histogram'))

def render_st_group(info, portrait=None):
    """ render html page for Sato-Tate group described by info """
    prop2 = [('Label', '%s'%info['label'])]
    if portrait:
        prop2 += [(None, '&nbsp;&nbsp;<img src="%s" width="220" height="124"/>' % portrait)]
    prop2 += [
        ('Name', '\(%s\)'%info['pretty']),
        ('Weight', '%d'%info['weight']),
        ('Degree', '%d'%info['degree']),
        ('Real dimension', '%d'%info['real_dimension']),
        ('Components', '%d'%info['components']),
        ('Contained in','\(%s\)'%info['ambient']),
        ('Identity Component', '\(%s\)'%info['st0_name']),
        ('Component group', '\(%s\)'%info['component_group']),
    ]
    bread = [
        ('Sato-Tate Groups', url_for('.index')),
        ('Weight %d'% info['weight'], url_for('.index')+'?weight='+str(info['weight'])),
        ('Degree %d'% info['degree'], url_for('.index')+'?weight='+str(info['weight'])+'&degree='+str(info['degree'])),
        (info['name'], '')
    ]
    title = 'Sato-Tate Group \(' + info['pretty'] + '\) of Weight %d'% info['weight'] + ' and Degree %d'% info['degree']
    return render_template('st_display.html',
                           properties2=prop2,
                           credit=credit_string,
                           info=info,
                           bread=bread,
                           learnmore=learnmore_list(),
                           title=title)

@st_page.route('/Completeness')
def completeness_page():
    t = 'Completeness of Sato-Tate Group Data'
    bread = [('Sato-Tate Groups', url_for('.index')), ('Completeness','')]
    return render_template('single.html', kid='dq.st.extent',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@st_page.route('/Source')
def how_computed_page():
    t = 'Source of Sato-Tate Group Data'
    bread = [('Sato-Tate Groups', url_for('.index')), ('Source','')]
    return render_template('single.html', kid='dq.st.source',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@st_page.route('/Labels')
def labels_page():
    t = 'Labels for Sato-Tate Groups'
    bread = [('Sato-Tate Groups', url_for('.index')), ('Labels','')]
    return render_template('single.html', kid='st_group.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
