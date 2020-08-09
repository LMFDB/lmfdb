# -*- coding: utf-8 -*-

import re #, StringIO, yaml, ast, os

from flask import render_template, request, url_for, redirect #, send_file, abort
from sage.all import ZZ, latex #, Permutation

from lmfdb import db
from lmfdb.utils import (
    flash_error, display_knowl, SearchArray, TextBox, CountBox,
    parse_ints, parse_bool, clean_input, to_dict,
    # parse_gap_id, parse_bracketed_posints, 
    search_wrap, web_latex)
from lmfdb.groups.abstract.web_groups import WebAbstractGroup

from lmfdb.groups.glnQ import glnQ_page

credit_string = "Michael Bush, Lewis Combes, Tim Dokchitser, John Jones, Kiran Kedlaya, Jen Paulhus, David Roberts,  David Roe, Manami Roy, Sam Schiavone, and Andrew Sutherland"

glnq_label_regex = re.compile(r'^(\d+)\.(\d+).*$')
abstract_subgroup_label_regex = re.compile(r'^(\d+)\.(([a-z]+)|(\d+))\.\d+$')

def learnmore_list():
    return [ ('Completeness of the data', url_for(".completeness_page")),
             ('Source of the data', url_for(".how_computed_page")),
             ('Reliability of the data', url_for(".reliability_page")),
             ('Labeling convention', url_for(".labels_page")) ]

def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

def sub_label_is_valid(lab):
    return abstract_subgroup_label_regex.match(lab)

def label_is_valid(lab):
    return glnq_label_regex.match(lab)

def get_bread(breads=[]):
    bc = [("Groups", url_for(".index")),("GLnQ", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

@glnQ_page.route("/")
def index():
    info = to_dict(request.args, search_array=GLnQSearchArray())
    bread = get_bread()
    if request.args:
        return group_search(info)
    info['order_list']= ['1-10', '20-100', '101-200']

    return render_template("glnQ-index.html", title="Finite subgroups of $\GL(n,\Q)$", bread=bread, info=info, learnmore=learnmore_list(), credit=credit_string)



@glnQ_page.route("/random")
def random_glnQ_group():
    label = db.gps_qrep.random(projection='label')
    return redirect(url_for(".by_label", label=label))


@glnQ_page.route("/<label>")
def by_label(label):
    if label_is_valid(label):
        return render_glnQ_group({'label': label})
    else:
        flash_error( "No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
#Should this be "Bad label instead?"

# Take a list of list of integers and make a latex matrix
def dispmat(mat):
    s = r'\begin{pmatrix}'
    for row in mat:
      rw = '& '.join([str(z) for z in row])
      s += rw + '\\\\'
    s += r'\end{pmatrix}'
    return s

#### Searching
def group_jump(info):
    return redirect(url_for('.by_label', label=info['jump']))

def group_download(info):
    t = 'Stub'
    bread = get_bread([("Jump", '')])
    return render_template("single.html", kid='rcs.groups.glnQ.source',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Source'),
                           credit=credit_string)

def url_for_label(label):
    if label == "random":
        return url_for(".random_abstract_group")
    return url_for(".by_label", label=label)

@search_wrap(template="glnQ-search.html",
             table=db.gps_qrep,
             title='$\GL(n,\Q)$ subgroup search results',
             err_title='$\GL(n,\Q)$ subgroup search input error',
             shortcuts={'jump':group_jump,
                        'download':group_download},
             projection=['label','order','dim','group'],
             #cleaners={"class": lambda v: class_from_curve_label(v["label"]),
             #          "equation_formatted": lambda v: list_to_min_eqn(literal_eval(v.pop("eqn"))),
             #          "st_group_link": lambda v: st_link_by_name(1,4,v.pop('st_group'))},
             bread=lambda:get_bread([('Search Results', '')]),
             learnmore=learnmore_list,
             credit=lambda:credit_string,
             url_for_label=url_for_label)
def group_search(info, query):
    info['group_url'] = get_url
    info['getname'] = lambda label: '$'+WebAbstractGroup(label).tex_name+'$'
    parse_ints(info, query, 'order', 'order')
    parse_ints(info, query, 'dim', 'dim')

def get_url(label):
    return url_for(".by_label", label=label)

#Writes individual pages
def render_glnQ_group(args):
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        info = db.gps_qrep.lucky({'label': label})
        info['dispmat'] = dispmat

        title = '$\GL('+str(info['dim'])+',\Q)$ subgroup '  + label

        prop = [('Label', '%s' %  label), 
                ('Order', '\(%s\)' % info['order']),
                ('Dimension', '%s' % info['dim']) ]

        bread = get_bread([(label, )])

#        downloads = [('Code to Magma', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
#                     ('Code to Gap', url_for(".hgcwa_code_download", label=label, download_type='gap'))]

        return render_template("glnQ-show-group.html",
                               title=title, bread=bread, info=info,
                               properties=prop,
                               #friends=friends,
                               learnmore=learnmore_list(),
                               #downloads=downloads, 
                               credit=credit_string)

def make_knowl(title, knowlid):
    return '<a title="%s" knowl="%s">%s</a>'%(title, knowlid, title)

@glnQ_page.route("/subinfo/<label>")
def shortsubinfo(label):
    if not sub_label_is_valid(label):
        # Should only come from code, so return nothing if label is bad
        return ''
    wsg = WebAbstractSubgroup(label)
    ambientlabel = str(wsg.ambient)
    # helper function
    def subinfo_getsub(title, knowlid, count):
        h = WebAbstractSubgroup("%s.%s"%(ambientlabel,str(count)))
        prop = make_knowl(title, knowlid)
        return '<tr><td>%s<td><span class="%s" data-sgid="%d">$%s$</span>\n' % (
            prop, h.spanclass(), h.counter, h.subgroup_tex)

    ans = 'Information on subgroup <span class="%s" data-sgid="%d">$%s$</span><br>\n' % (wsg.spanclass(), wsg.counter, wsg.subgroup_tex)
    ans += '<table>'
    ans += '<tr><td>%s <td> %s\n' % (
        make_knowl('Cyclic', 'group.cyclic'),wsg.cyclic)
    ans += '<tr><td>%s<td>' % make_knowl('Normal', 'group.subgroup.normal')
    if wsg.normal:
        ans += 'True with quotient group '
        ans +=  '$'+group_names_pretty(wsg.quotient)+'$\n'
    else:
        ans += 'False, and it has %d subgroups in its conjugacy class\n'% wsg.count
    ans += '<tr><td>%s <td>%s\n' % (make_knowl('Characteristic', 'group.characteristic_subgroup'), wsg.characteristic)

    h = WebAbstractSubgroup("%s.%s"%(ambientlabel,str(wsg.normalizer)))
    ans += subinfo_getsub('Normalizer', 'group.subgroup.normalizer',wsg.normalizer)
    ans += subinfo_getsub('Normal closure', 'group.subgroup.normal_closure', wsg.normal_closure)
    ans += subinfo_getsub('Centralizer', 'group.subgroup.centralizer', wsg.centralizer)
    ans += subinfo_getsub('Core', 'group.core', wsg.core)
    ans += '<tr><td>%s <td>%s\n' % (make_knowl('Central', 'group.central'), wsg.central)
    ans += '<tr><td>%s <td>%s\n' % (make_knowl('Hall', 'group.subgroup.hall'), wsg.hall>0)
    #ans += '<tr><td>Coset action <td>%s\n' % wsg.coset_action_label
    p = wsg.sylow
    nt = 'Yes for $p$ = %d' % p if p>0 else 'No'
    ans += '<tr><td>%s<td> %s'% (make_knowl('Sylow subgroup', 'group.sylow_subgroup'), nt)
    #print ""
    #print ans
    ans += '</table>'
    return ans


@glnQ_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the $\GL(n,\Q)$ subgroup data'
    bread = get_bread([("Completeness", '')])
    return render_template("single.html", kid='rcs.groups.glnQ.extent',
                            title=t, bread=bread,
                            learnmore=learnmore_list_remove('Complete'), 
                            credit=credit_string)


@glnQ_page.route("/Labels")
def labels_page():
    t = 'Labels for finite subgroups of $\GL(n,\Q)$'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='rcs.groups.glnQ.label',
                           learnmore=learnmore_list_remove('label'), 
                           title=t, bread=bread, credit=credit_string)


@glnQ_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of the $\GL(n,\Q)$ subgroup data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.groups.glnQ.reliability',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Reliability'), 
                           credit=credit_string)


@glnQ_page.route("/Source")
def how_computed_page():
    t = 'Source of the $\GL(n,\Q)$ subgroup data'
    bread = get_bread([("Source", '')])
    return render_template("single.html", kid='rcs.groups.glnQ.source',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Source'),
                           credit=credit_string)


class GLnQSearchArray(SearchArray):
    noun = "group"
    plural_noun = "groups"
    jump_example = "??"
    jump_egspan = "e.g. ??"
    def __init__(self):
        order = TextBox(
            name="order",
            label="Order",
            knowl="group.order",
            example="3",
            example_span="4, or a range like 3..5")
        dim = TextBox(
            name="dim",
            label="Dimension",
            example="2",
            example_span="4, or a range like 3..5")
        count = CountBox()

        self.browse_array = [
             [order],
             [dim]]
        self.refine_array = [
             [order, dim]]

