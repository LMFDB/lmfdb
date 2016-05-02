# -*- coding: utf-8 -*-
from flask import flash, render_template, url_for, redirect
from markupsafe import Markup
from lmfdb.sato_tate_groups import st_page
from lmfdb.utils import web_latex, random_object_from_collection
from lmfdb.base import getDBConnection

from sage.all import ZZ, QQ, latex, matrix
credit_string = "Andrew Sutherland"

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
    label = "%d.%d.%s"%(weight,degree,name)
    data = stdb().st_groups.find_one({'label':label})
    if not data:
        return name
    return """<a href=%s>\(%s\)</a>"""% (url_for(".by_label", label=label), data['pretty'])

###############################################################################
# Learnmore display functions
###############################################################################

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Sato-Tate group labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

###############################################################################
# Pages
###############################################################################

@st_page.route("/random")
def random():
    data = random_object_from_collection(stdb().st_groups)
    return redirect(url_for(".by_label", label=data['label']))

@st_page.route("/<label>")
def by_label(label):
    return render_stgroup_by_label(label)

###############################################################################
# Rendering
###############################################################################

def render_stgroup_by_label(label):
    credit = credit_string
    data = stdb().st_groups.find_one({'label': label})
    print data
    info = {}
    if data is None:
        title = "Sato-Tate group lookup error"
        bread = [('Sato-Tate groups', url_for(".index"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not the label of a Sato-Tate group currently in the database." % (label)),"error")
        return render_template("error.html", title=title, properties=[], bread=bread, learnmore=learnmore_list())
    for attr in ['label','weight','degree','pretty','real_dimension','components']:
        info[attr] = data[attr]
    info['ambient'] = '\\mathrm{USp}(%d)'%info['degree'] if info['weight']%2 == 1 else '\\mathrm{O}(%d)'%info['degree']
    info['connected']=boolean_name(info['components'] == 1)
    st0 = stdb().st0_groups.find_one({'label':data['identity_component']})
    if not st0:
        title = "Sato-Tate group lookup error"
        bread = [('Sato-Tate groups', url_for(".index"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not the label of a Sato-Tate identity component currently in the database." % (data['identity_component'])),"error")
        return render_template("error.html", title=title, properties=[], bread=bread, learnmore=learnmore_list())
    info['st0_name']=st0['pretty']
    info['st0_description']=st0['description']
    G = stdb().small_groups.find_one({'label':data['component_group']})
    if not G:
        title = "Sato-Tate group lookup error"
        bread = [('Sato-Tate groups', url_for(".index"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not the label of a Sato-Tate component group currently in the database." % (data['component_group'])),"error")
        return render_template("error.html", title=title, properties=[], bread=bread, learnmore=learnmore_list())
    info['component_group']=G['pretty']
    info['abelian']=boolean_name(G['abelian'])
    info['cyclic']=boolean_name(G['cyclic'])
    info['gens']=comma_separated_list([string_matrix(m) for m in data['gens']])
    info['numgens']=len(info['gens'])
    info['subgroups'] = comma_separated_list([stgroup_link(data['weight'],data['degree'],name) for name in data['subgroups']])
    info['supgroups'] = comma_separated_list([stgroup_link(data['weight'],data['degree'],name) for name in data['supgroups']])
    info['subsups'] = len(info['subgroups'])+len(info['supgroups'])
    if data['moments']:
        info['moments'] = [['x'] + [ '\\mathrm{E}[x^{%d}]'%n for n in range(len(data["moments"][0])-1)]]
        info['moments'] += data['moments']
    else:
        info['moments'] = []
    if data['counts']:
        c=data['counts']
        print c
        info['probabilities'] = [['\\mathrm{P}[%s=%d]=\\frac{%d}{%d}'%(c[i][0],c[i][1][j][0],c[i][1][j][1],data['components']) for j in range(len(c[i][1]))] for i in range(len(c))]
    else:
        info['probabilities'] = []
    prop2 = [
        ('Label', '%s'%info['label']),
        ('Subgroup of','\(%s\)'%info['ambient']),
        ('Name', '\(%s\)'%info['pretty']),
        ('Weight', '%d'%info['weight']),
        ('Degree', '%d'%info['degree']),
        ('Identity Component', '\(%s\)'%info['st0_name']),
        ('Real dimension', '%d'%info['real_dimension']),
        ('Components', '%d'%info['components']),
        ('Component group', '\(%s\)'%info['component_group']),
    ]
    bread = [('Sato-Tate groups', ' '), ('Weight %d'% info['weight'], ' '), ('Degree %d'% info['degree'], ' '), (data['name'], '')]
    title = 'Sato-Tate group \(' + info['pretty'] + '\) of weight %d'% info['weight'] + ' and degree %d'% info['degree']
    return render_template("display.html",
                           properties2=prop2,
                           credit=credit_string,
                           info=info,
                           bread=bread,
                           learnmore=learnmore_list(),
                           title=title)
                           #friends=data.friends)
                           #downloads=data.downloads)

@st_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Sato-Tate group data'
    bread = [('Sato-Tate groups', ' '), ('Completeness','')]
    return render_template("single.html", kid='dq.st.extent',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@st_page.route("/Source")
def how_computed_page():
    t = 'Source of Sato-Tate group data'
    bread = [('Sato-Tate groups', ' '), ('Source','')]
    return render_template("single.html", kid='dq.st.source',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@st_page.route("/Labels")
def labels_page():
    t = 'Labels for Sato-Tate groups'
    bread = [('Sato-Tate groups', ' '), ('Labels','')]
    return render_template("single.html", kid='st.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
