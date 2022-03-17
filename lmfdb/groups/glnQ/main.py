# -*- coding: utf-8 -*-

import re #, StringIO, yaml, ast, os

from flask import render_template, request, url_for, redirect #, send_file, abort
#from sage.all import ZZ, latex, Permutation

from lmfdb import db
from lmfdb.utils import (
    flash_error, SearchArray, TextBox, CountBox,
    parse_ints, clean_input, to_dict,
    # parse_gap_id, parse_bracketed_posints,
    search_wrap)
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol
from lmfdb.groups.abstract.web_groups import group_names_pretty
from lmfdb.groups.abstract.main import abstract_group_display_knowl

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
    return abstract_subgroup_label_regex.fullmatch(lab)

def label_is_valid(lab):
    return glnq_label_regex.fullmatch(lab)

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

    return render_template("glnQ-index.html", title=r"Finite subgroups of $\GL(n,\Q)$", bread=bread, info=info, learnmore=learnmore_list(), credit=credit_string)



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

def get_url(label):
    return url_for(".by_label", label=label)

glnQ_columns = SearchColumns([
    LinkCol("label", "group.label", "Label", get_url, default=True),
    MathCol("tex_name", "group.name", "Name", default=True),
    MathCol("order", "group.order", "Order", default=True),
    MathCol("dim", "group.dimension", "Dimension", default=True)],
    db_cols=["label", "group", "order", "dim"])
glnQ_columns.dummy_download=True

def glnQ_postprocess(res, info, query):
    tex_names = {rec["label"]: rec["tex_name"] for rec in db.gps_groups.search({"label": {"$in": [gp["group"] for gp in res]}}, ["label", "tex_name"])}
    for gp in res:
        gp["tex_name"] = tex_names[gp["group"]]
    return res

@search_wrap(table=db.gps_qrep,
             title=r'$\GL(n,\Q)$ subgroup search results',
             err_title=r'$\GL(n,\Q)$ subgroup search input error',
             columns=glnQ_columns,
             shortcuts={'jump':group_jump,
                        'download':group_download},
             postprocess=glnQ_postprocess,
             bread=lambda:get_bread([('Search Results', '')]),
             learnmore=learnmore_list,
             credit=lambda:credit_string,
             url_for_label=url_for_label)
def group_search(info, query):
    info['group_url'] = get_url
    info['getname'] = lambda xx: '$'+group_names_pretty(xx)+'$'
    parse_ints(info, query, 'order', 'order')
    parse_ints(info, query, 'dim', 'dim')

#Writes individual pages
def render_glnQ_group(args):
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        info = db.gps_qrep.lucky({'label': label})
        info['dispmat'] = dispmat
        info['groupname'] = '${}$'.format(group_names_pretty(info['group']))
        info['groupknowl'] = abstract_group_display_knowl(info['group'], info['groupname'])

        title = r'$\GL('+str(info['dim'])+r',\Q)$ subgroup '  + label

        prop = [('Label', '%s' %  label),
                ('Order', r'\(%s\)' % info['order']),
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

@glnQ_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of the $\GL(n,\Q)$ subgroup data'
    bread = get_bread([("Completeness", '')])
    return render_template("single.html", kid='rcs.groups.glnQ.extent',
                            title=t, bread=bread,
                            learnmore=learnmore_list_remove('Complete'),
                            credit=credit_string)


@glnQ_page.route("/Labels")
def labels_page():
    t = r'Labels for finite subgroups of $\GL(n,\Q)$'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='rcs.groups.glnQ.label',
                           learnmore=learnmore_list_remove('label'),
                           title=t, bread=bread, credit=credit_string)


@glnQ_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of the $\GL(n,\Q)$ subgroup data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.groups.glnQ.reliability',
                           title=t, bread=bread,
                           learnmore=learnmore_list_remove('Reliability'),
                           credit=credit_string)


@glnQ_page.route("/Source")
def how_computed_page():
    t = r'Source of the $\GL(n,\Q)$ subgroup data'
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
            [dim],
            [count]]
        self.refine_array = [
            [order, dim]]
