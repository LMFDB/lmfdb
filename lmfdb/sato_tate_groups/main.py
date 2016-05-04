# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
from flask import flash, render_template, url_for, redirect, request
from markupsafe import Markup
from lmfdb.sato_tate_groups import st_page
from lmfdb.utils import to_dict, random_object_from_collection
from lmfdb.base import getDBConnection
from lmfdb.search_parsing import parse_bool, parse_ints, parse_rational, parse_count, parse_start

###############################################################################
# Globals
###############################################################################

credit_string = 'Andrew Sutherland'

# use a list and a dictionary (for pretty printing) so that we can control the display order (switch to ordered dictionary once everyone is on python 3.1)
st0_list = ( 'U(1)', 'SU(2)', 'U(1)_2', 'SU(2)_2','U(1)xU(1)', 'U(1)xSU(2)','SU(2)xSU(2)','USp(4)' )
st0_dict = {
    'U(1)':'\\mathrm{U}(1)',
    'SU(2)':'\\mathrm{SU}(2)',
    'U(1)_2':'\\mathrm{U}(1)_2',
    'SU(2)_2':'\\mathrm{SU}(2)_2',
    'U(1)xU(1)':'\\mathrm{U}(1)x\\mathrm{U}(1)',
    'U(1)xSU(2)':'\\mathrm{U}(1)x\\mathrm{SU}(2)',
    'SU(2)xSU(2)':'\\mathrm{SU}(2)x\\mathrm{SU}(2)',
    'USp(4)':'\\mathrm{USp}(4)'
}

###############################################################################
# Database connection
###############################################################################

the_stdb = None

def stdb():
    global the_stdb
    if the_stdb is None:
        the_stdb = getDBConnection().sato_tate_groups
    return the_stdb

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
    return '\\begin{bmatrix}' + '\\\\'.join(['&'.join(m[i]) for i in range(len(m))]) + '\\end{bmatrix}'

def stgroup_link(weight, degree, name):
    label = '%d.%d.%s'%(weight,degree,name)
    data = stdb().groups.find_one({'label':label})
    if not data:
        return name
    return '''<a href=%s>\(%s\)</a>'''% (url_for('.by_label', label=label), data['pretty'])
    
def stgroup_ambient(weight, degree):
    return '\\mathrm{USp}(%d)'%degree if weight%2 == 1 else '\\mathrm{O}(%d)'%degree
    
def trace_moments(moments):
    for m in moments:
        if m[0] == 'a_1'or m[0] == 's_1':
            return m[1:10]
    return ''
    
def st0_pretty(st0_name):
    data = stdb().groups0.find_one({'name':st0_name})
    if data and 'pretty' in data:
        return data['pretty']
    return st0_name
    
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
    weight_list= [0,1]
    degree_list=range(1, 5, 1)
    group_list = [ '1.2.1.2.1a', '1.2.3.1.1a', '1.4.6.1.1a', '1.4.10.1.1a' ]
    group_dict = { '1.2.1.2.1a':'N(\\mathrm{U}(1))', '1.2.3.1.1a':'\\mathrm{SU}(2)', '1.4.6.1.1a':'G_{3,3}', '1.4.10.1.1a':'\\mathrm{USp}(4)' }
    info = {'weight_list' : weight_list, 'degree_list' : degree_list, 'st0_list' : st0_list, 'st0_dict' : st0_dict, 'group_list': group_list, 'group_dict' : group_dict}
    title = 'Sato-Tate groups'
    bread = [('Sato-Tate groups', '.')]
    return render_template('browse.html', info=info, credit=credit_string, title=title, learnmore=learnmore_list_remove('Completeness'), bread=bread)

@st_page.route('/random')
def random():
    data = random_object_from_collection(stdb().groups)
    return redirect(url_for('.by_label', label=data['label']))

@st_page.route('/<label>')
def by_label(label):
    return search_by_label(label)

###############################################################################
# Searching
###############################################################################

ec_groups = { 'U(1)':'1.2.1.1.1a', 'N(U(1))':'1.2.1.2.1a', 'SU(2)':'1.2.3.1.1a' }

def search_by_label(label):
    label_regex = re.compile(r'\d+.\d+.\d+.\d+.\d+[a-z]+$')
    if label_regex.match(label.strip()):
        return render_by_label(label.strip())
    label_regex = re.compile(r'\d+.\d+.\d+.\d+.\d+$')
    if label_regex.match(label.strip()):
        return render_by_label(label.strip()+'a')
    # backward compatibility for old labels coming from ec or g2c
    name = label.strip().split('.')[-1]
    if name in ec_groups:
        return render_by_label(ec_groups[name])
    else:
        data = stdb().groups.find_one({'weight':int(1),'degree':int(4),'name':name})
        if not data:
            flash(Markup("Error: <span style='color:black'>%s</span> is not the label or name of a Sato-Tate group currently in the database" % label),"error")
            return redirect(url_for(".index"))
        else:
            return render_by_label(data['label'])

def search(**args):
    info = to_dict(args)
    query = {}
    if 'label' in info:
        return search_by_label(info['label'])
    info['st0_list'] = st0_list
    info['st0_dict'] = st0_dict
    bread = [('Sato-Tate groups', url_for('.index')),('Search Results', '.')]
    if not query:
        try:
            parse_ints(info,query,'weight')
            parse_ints(info,query,'degree')
            if info.get('identity_component'):
                query['identity_component'] = info['identity_component']
            parse_ints(info,query,'components')
            parse_rational(info,query,'trace_zero_density')
        except ValueError as err:
            info['err'] = str(err)
            return render_template('results.html', info=info, title='Sato-Tate groups search input rror', bread=bread, credit=credit_string)
        cursor = stdb().groups.find(query)
    info['query'] = dict(query)
    count = parse_count(info, 50)
    start = parse_start(info)
    nres = cursor.count()
    if (start >= nres):
        start -= (1 + (start - nres) / count) * count
    if (start < 0):
        start = 0
    res = cursor.sort([('weight', ASCENDING), ('degree', ASCENDING),  ('identity_component', ASCENDING),  ('name', ASCENDING)]).skip(start).limit(count)
    nres = res.count()

    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    res_clean = []

    for v in res:
        v_clean = {}
        v_clean['label'] = v['label']
        v_clean['weight'] = v['weight']
        v_clean['degree'] = v['degree']
        v_clean['name'] = v['name']
        v_clean['pretty'] = v['pretty']
        v_clean['ambient'] = stgroup_ambient(v['weight'],v['degree'])
        v_clean['real_dimension'] = v['real_dimension']
        v_clean['identity_component'] = st0_pretty(v['identity_component'])
        v_clean['components'] = v['components']
        v_clean['trace_zero_density'] = v['trace_zero_density']
        v_clean['trace_moments'] = trace_moments(v['moments'])
        res_clean.append(v_clean)

    info['stgroups'] = res_clean
    info['stgroup_url'] = lambda dbc: url_for('.by_label', label=dbc['label'])
    info['start'] = start
    info['count'] = count
    info['more'] = int(start+count<nres)
    
    credit = credit_string
    title = 'Sato-Tate group search results'
    return render_template('results.html', info=info, credit=credit,learnmore=learnmore_list(), bread=bread, title=title)

###############################################################################
# Rendering
###############################################################################

def render_by_label(label):
    credit = credit_string
    data = stdb().groups.find_one({'label': label})
    info = {}
    if data is None:
        flash(Markup("Error: <span style='color:black'>%s</span> is not the label of a Sato-Tate group currently in the database." % (label)),'error')
        return redirect(url_for(".index"))
    for attr in ['label','weight','degree','pretty','real_dimension','components']:
        info[attr] = data[attr]
    info['ambient'] = stgroup_ambient(info['weight'],info['degree'])
    info['connected']=boolean_name(info['components'] == 1)
    st0 = stdb().groups0.find_one({'name':data['identity_component']})
    if not st0:
        flash(Markup("Error: <span style='color:black'>%s</span> is not the label of a Sato-Tate identity component currently in the database." % (data['identity_component'])),'error')
        return redirect(url_for(".index"))
    info['st0_name']=st0['pretty']
    info['st0_description']=st0['description']
    G = stdb().small_groups.find_one({'label':data['component_group']})
    if not G:
        flash(Markup("Error: <span style='color:black'>%s</span> is not the label of a Sato-Tate component group currently in the database." % (data['component_group'])),'error')
        return redirect(url_for(".index"))
    info['component_group']=G['pretty']
    info['abelian']=boolean_name(G['abelian'])
    info['cyclic']=boolean_name(G['cyclic'])
    info['gens']=comma_separated_list([string_matrix(m) for m in data['gens']])
    info['numgens']=len(info['gens'])
    info['subgroups'] = comma_separated_list([stgroup_link(data['weight'],data['degree'],name) for name in data['subgroups']])
    info['supgroups'] = comma_separated_list([stgroup_link(data['weight'],data['degree'],name) for name in data['supgroups']])
    info['subsups'] = len(info['subgroups'])+len(info['supgroups'])
    if data['moments']:
        info['moments'] = [['x'] + [ '\\mathrm{E}[x^{%d}]'%n for n in range(len(data['moments'][0])-1)]]
        info['moments'] += data['moments']
    else:
        info['moments'] = []
    if data['counts']:
        c=data['counts']
        info['probabilities'] = [['\\mathrm{P}[%s=%d]=\\frac{%d}{%d}'%(c[i][0],c[i][1][j][0],c[i][1][j][1],data['components']) for j in range(len(c[i][1]))] for i in range(len(c))]
    else:
        info['probabilities'] = []
    prop2 = [('Label', '%s'%info['label'])]
    if 'trace_histogram' in data:
        prop2 += [(None, '&nbsp;&nbsp;<img src="%s" width="200" height="114"/>' % data['trace_histogram'])]
    prop2 += [
        ('Weight', '%d'%info['weight']),
        ('Degree', '%d'%info['degree']),
        ('Name', '\(%s\)'%info['pretty']),
        ('Subgroup of','\(%s\)'%info['ambient']),
        ('Real dimension', '%d'%info['real_dimension']),
        ('Identity Component', '\(%s\)'%info['st0_name']),
        ('Components', '%d'%info['components']),
        ('Component group', '\(%s\)'%info['component_group']),
    ]
    bread = [
        ('Sato-Tate groups', url_for('.index')),
        ('Weight %d'% info['weight'], url_for('.index')+'?weight='+str(info['weight'])),
        ('Degree %d'% info['degree'], url_for('.index')+'?weight='+str(info['weight'])+'&degree='+str(info['degree'])),
        (data['name'], '')
    ]
    title = 'Sato-Tate group \(' + info['pretty'] + '\) of weight %d'% info['weight'] + ' and degree %d'% info['degree']
    return render_template('display.html',
                           properties2=prop2,
                           credit=credit_string,
                           info=info,
                           bread=bread,
                           learnmore=learnmore_list(),
                           title=title)

@st_page.route('/Completeness')
def completeness_page():
    t = 'Completeness of Sato-Tate group data'
    bread = [('Sato-Tate groups', url_for('.index')), ('Completeness','')]
    return render_template('single.html', kid='dq.st.extent',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@st_page.route('/Source')
def how_computed_page():
    t = 'Source of Sato-Tate group data'
    bread = [('Sato-Tate groups', url_for('.index')), ('Source','')]
    return render_template('single.html', kid='dq.st.source',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@st_page.route('/Labels')
def labels_page():
    t = 'Labels for Sato-Tate groups'
    bread = [('Sato-Tate groups', url_for('.index')), ('Labels','')]
    return render_template('single.html', kid='st_group.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
