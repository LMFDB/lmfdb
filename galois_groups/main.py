# -*- coding: utf-8 -*-
# This Blueprint is about Galois Groups
# Author: John Jones

import pymongo
ASC = pymongo.ASCENDING
import flask
import base
from base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from utils import ajax_more, image_src, web_latex, to_dict, parse_range, parse_range2, make_logger
import os, re
from galois_groups import galois_groups_page, logger
import sage.all
from sage.all import ZZ, latex, gap

# Test to see if this gap installation knows about transitive groups
logger = make_logger("GG")

try:
  G = gap.TransitiveGroup(9,2)
except:
  logger.fatal("It looks like the SPKGes gap_packages and database_gap are not installed on the server.  Please install them via 'sage -i ...' and try again.")

from transitive_group import group_display_short, group_display_long, group_display_inertia, group_knowl_guts, subfield_display, otherrep_display, resolve_display, conjclasses, generators, chartable

GG_credit = 'GAP and J. Jones'

def get_bread(breads = []):
  bc = [("Galois Groups", url_for(".index"))]
  for b in breads:
    bc.append(b)
  return bc

def galois_group_data(n, t):
  C = base.getDBConnection()
  return group_knowl_guts(n, t, C)

#@app.context_processor
#def ctx_galois_groups():
#  return {'galois_group_data': galois_group_data }

def group_display_shortC(C):
  def gds(nt):
    return group_display_short(nt[0], nt[1], C)
  return gds

@galois_groups_page.route("/")
def index():
  bread = get_bread()
  if len(request.args) != 0:
    return galois_group_search(**request.args)
  info = {}
  info['degree_list'] = range(14)[2:]
  return render_template("gg-index.html", title ="Galois Groups", bread = bread, info = info)

@galois_groups_page.route("/<label>")
def by_label(label):
    return render_group_webpage({'label' : label})

@galois_groups_page.route("/search", methods = ["GET", "POST"])
def search():
  if request.method == "GET":
    val = request.args.get("val", "no value")
    bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
    return render_template("gg-search.html", title="Galois Group Search", bread = bread, val = val)
  elif request.method == "POST":
    return "ERROR: we always do http get to explicitly display the search parameters"
  else:
    return flask.redirect(404)


def galois_group_search(**args):
  info = to_dict(args)
  bread = get_bread()
  C = base.getDBConnection()
  query = {}
  if 'jump_to' in info:
    return render_group_webpage({'label' : info['jump_to']})

  for param in ['n', 't']:
    if info.get(param):
      ran = info[param]
      ran = ran.replace('..','-')
      tmp = parse_range2(ran, param)
      # work around syntax for $or
      # we have to foil out multiple or conditions
      if tmp[0]=='$or' and query.has_key('$or'):
        newors = []
        for y in tmp[1]:
          oldors = [dict.copy(x) for x in query['$or']]
          for x in oldors: x.update(y)
          newors.extend(oldors)
        tmp[1] = newors
      query[tmp[0]] = tmp[1]

  res = C.transitivegroups.groups.find(query).sort([('n',pymongo.ASCENDING),('t',pymongo.ASCENDING)])
  nres = res.count()
#  res = iter_limit(res, count, start)
  info['groups'] = res
  info['group_display'] = group_display_shortC(C)
  info['report'] = "found %s groups"%nres
  info['yesno'] = yesno

  bread = get_bread([("Search results", url_for('.search'))])
  return render_template("gg-search.html", info = info, title="Galois Group Search Result", bread=bread, credit=GG_credit)

def yesno(val):
  if val:
    return 'Yes'
  return 'No'
  
def render_group_webpage(args):
  data = None
  info = {}
  if 'label' in args:
    label = str(args['label'])
    C = base.getDBConnection()
    data = C.transitivegroups.groups.find_one({'label': label})
    if data is None:
        bread = get_bread([("Search error", url_for('.search'))])
        info['msg'] = "Group " + label + " was not found in the database."
        return render_template("gg-error.html", info=info, title="Galois Group Search Error", bread=bread, credit=GG_credit), 404
    title = 'Galois Group:' + label
    n = data['n']
    t = data['t']
    data['yesno'] = yesno
    order = data['order']
    data['orderfac'] = latex(ZZ(order).factor())
    pgroup = len(ZZ(order).prime_factors())<2
    G = gap.TransitiveGroup(n,t)
    ctable = chartable(n,t)
    #CT = G.CharacterTable()
    #chartable = gap.eval("Display(%s)"%CT.name())
    #chartable = re.sub("^.*\n", '', chartable)
    #chartable = re.sub("^.*\n", '', chartable)
    data['gens'] = generators(n,t)
    data['chartable'] = ctable
    data['cclasses'] = conjclasses(G, n)
    data['subinfo'] = subfield_display(C, n, data['subs'])
    data['resolve'] = resolve_display(C, data['resolve'])
#    if len(data['resolve']) == 0: data['resolve'] = 'None'
    data['otherreps'] = otherrep_display(C, data['repns'])
    prop2 = [
             ('Order:', '\(%s\)' % order ),
             ('n:', '\(%s\)' % data['n']),
             ('Cyclic:', yesno(data['cyc'])),
             ('Abelian:', yesno(data['ab'])),
             ('Solvable:', yesno(data['solv'])),
             ('Primitive:', yesno(data['prim'])),
             ('$p$-group:', yesno(pgroup)),
             ('Name:', group_display_short(n, t, C)),
             ]
    info.update(data)
    

    bread = get_bread([(label, ' ')])
    return render_template("gg-show-group.html", credit=GG_credit, title = title, bread = bread, info = info, properties2=prop2 )

