# -*- coding: utf-8 -*-
# This Blueprint is about Local Fields
# Author: John Jones

import pymongo
ASC = pymongo.ASCENDING
import flask
import base
from base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from utils import ajax_more, image_src, web_latex, to_dict, parse_range, coeff_to_poly, pol_to_html
from sage.all import ZZ
from local_fields import local_fields_page, logger, logger

from transitive_group import group_display_short, group_display_long, group_display_inertia

LF_credit = 'J. Jones and D. Roberts'

def get_bread(breads = []):
  bc = [("Local Field", url_for(".index"))]
  for b in breads:
    bc.append(b)
  return bc

def display_poly(coeffs):
  return web_latex(coeff_to_poly(coeffs))

def format_coeffs(coeffs):
    return pol_to_html(str(coeff_to_poly(coeffs)))

def group_display_shortC(C):
  def gds(nt):
    return group_display_short(nt[0], nt[1], C)
  return gds


@local_fields_page.route("/")
def index():
  bread = get_bread()
  if len(request.args) != 0:
    return local_field_search(**request.args)
  #info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
  return render_template("lf-index.html", title ="Local Fields", bread = bread)

@local_fields_page.route("/<label>")
def by_label(label):
    return render_field_webpage({'label' : label})

@local_fields_page.route("/search", methods = ["GET", "POST"])
def search():
  if request.method == "GET":
    val = request.args.get("val", "no value")
    bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
    return render_template("lf-search.html", title="Local Field Search", bread = bread, val = val)
  elif request.method == "POST":
    return "ERROR: we always do http get to explicitly display the search parameters"
  else:
    return flask.redirect(404)


def local_field_search(**args):
  info = to_dict(args)
  bread = get_bread()
  C = base.getDBConnection()
  query = {}
  if 'jump_to' in info:
    return render_field_webpage({'label' : info['jump_to']})

  for param in ['p', 'n', 'c', 'e']:
    if info.get(param):
      ran = info[param]
      ran = ran.replace('..','-')
      query[param] = parse_range(ran)

  res = C.localfields.fields.find(query).sort([('p',pymongo.ASCENDING),('n',pymongo.ASCENDING),('c',pymongo.ASCENDING)])
  nres = res.count()
  info['fields'] = res
  info['group_display'] = group_display_shortC(C)
  info['display_poly'] = format_coeffs
  info['report'] = "found %s fields"%nres

  bread = get_bread([("Search results", url_for('.search'))])
  return render_template("lf-search.html", info = info, title="Local Field Search Result", bread=bread, credit=LF_credit)
  
def render_field_webpage(args):
  data = None
  info = {}
  if 'label' in args:
    label = str(args['label'])
    C = base.getDBConnection()
    data = C.localfields.fields.find_one({'label': label})
    if data is None:
        bread = get_bread([("Search error", url_for('.search'))])
        info['msg'] = "Field " + label + " was not found in the database."
        return render_template("lf-error.html", info=info, title="Local Field Search Error", bread=bread, credit=LF_credit) 
    title = 'Local field:' + label
    polynomial = coeff_to_poly(data['coeffs'])
    p = data['p']
    e = data['e']
    f = data['f']
    cc = data['c']
    GG = data['gal']
    gn = GG[2][0]
    gt = GG[2][1]
    prop2 = [
             ('Base', '\(\mathbb{Q}_{%s}\)' % p ),
             ('Degree', '\(%s\)' % data['n']),
             ('e', '\(%s\)' % e),
             ('f', '\(%s\)' % f),
             ('c', '\(%s\)' % cc),
             ('Galois group', group_display_short(gn, gt, C)),
             ]
    info.update({
      'polynomial': web_latex(polynomial),
      'n': data['n'],
      'p': data['p'],
      'c': data['c'],
      'e': data['e'],
      'f': data['f'],
      't': data['t'],
      'u': data['u'],
      'rf': printquad(data['rf'], p),
      'hw': data['hw'],
      'slopes': show_slopes(data['slopes']),
      'gal': group_display_long(gn, gt, C),
      'inertia': group_display_inertia(data['inertia'], C),
      'unram': web_latex(data['unram']),
      'eisen': web_latex(data['eisen']),
      'gms': data['gms'],
      'aut': data['aut'],
      })
    

    bread = get_bread([(label, ' ')])
    return render_template("lf-show-field.html", credit=LF_credit, title = title, bread = bread, info = info, properties2=prop2 )

def show_slopes(sl):
  if len(sl)==0:
    return "None"
  return(sl)

def printquad(code, p):
  if code == [1,0] :
    return('$\mathbb{Q}_{%s}$' % p)
  if code == [1,1] :
    return('$\mathbb{Q}_{%s}(\sqrt{*})$' % p)
  if code == [-1,1] :
    return('$\mathbb{Q}_{%s}(\sqrt{-*})$' % p)
  s = code[0]
  if code[1] == 1 :
    s = str(s)+'*';
  return('$\mathbb{Q}_{'+str(p)+'}(\sqrt{'+ str(s)+'})$')
