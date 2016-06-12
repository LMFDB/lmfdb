# -*- coding: utf-8 -*-
# This Blueprint is about Higher Genus Curves
# Author: Jen Paulhus (copied from John Jones Local Fields)

import re
import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb import base
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, coeff_to_poly, pol_to_html, make_logger
from lmfdb.search_parsing import parse_ints, parse_count, parse_bool, parse_start, parse_list, clean_input

from sage.all import Permutation

from lmfdb.higher_genus_w_automorphisms import higher_genus_w_automorphisms_page, logger

from lmfdb.genus2_curves.data import group_dict




# Determining what kind of label
family_label_regex = re.compile(r'(\d+)\.(\d+-\d+)\.(\d+)\.(\d+-)')
passport_label_regex = re.compile(r'((\d+)\.(\d+-\d+)\.(\d+)\.(\d+.*))\.(\d+)')
cc_label_regex = re.compile(r'((\d+)\.(\d+-\d+)\.(\d+)\.(\d+.*))\.(\d+)')

def label_is_one_family(lab):
    return family_label_regex.match(lab)

def label_is_one_passport(lab):
    return passport_label_regex.match(lab)



def get_bread(breads=[]):
    bc = [("Higher Genus/C/aut", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc


#pretty printing functions 
def groupid_to_meaningful(groupid):
    if groupid[0] < 120:
        return group_dict[str(groupid).replace(" ", "")]
    elif groupid[0]==168 and groupid[1]==42:
        return 'PSL(2,7)'
    elif groupid[0]==120 and groupid[1]==34:
        return 'S_5'
    else:    
        return str(groupid)

def tfTOyn(bool):
    if bool:
        return "Yes"
    else:
        return "No"
    
def group_display_shortC(C):
    def gds(nt):
        return group_display_short(nt[0], nt[1], C)
    return gds

        
def sign_display(L):
    sizeL = len(L)                
    signL = "[ " + str(L[0]) + "; "
    for i in range(1,sizeL-1):
        signL= signL + str(L[i]) + ", "                    
     
    signL=signL + str(L[sizeL-1]) + " ]"                  
    return signL                

def cc_display(L):
    sizeL = len(L)
    stg = str(L[0])+ ", "
    for i in range(1,sizeL-1):
        stg =stg + str(L[i])+", "
    stg=stg+ str(L[sizeL-1])
    return stg

    
@higher_genus_w_automorphisms_page.route("/")
def index():
    bread = get_bread()
    if request.args:
        return higher_genus_w_automorphisms_search(**request.args)
    genus_list = range(2,6)
    info = {'count': 20,'genus_list': genus_list}
    

    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]
    
    return render_template("hgcwa-index.html", title="Higher Genus Curves with Automorphisms", bread=bread, info=info, learnmore=learnmore)




@higher_genus_w_automorphisms_page.route("/<label>")
def by_label(label):

    if label_is_one_passport(label):
        return render_passport({'passport_label': label})
    elif label_is_one_family(label):
        return render_family({'label': label})    
    else:
        info = {}
        bread = get_bread([("Search error", url_for('.search'))])
        info['err'] = "Higher Genus Curve with Automorphism " + label + " was not found in the database."
        info['label'] = label
        return search_input_error(info, bread)
    

@higher_genus_w_automorphisms_page.route("/<passport_label>")
def by_passport_label(label):
    return render_passport({'passport_label': label})


@higher_genus_w_automorphisms_page.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        val = request.args.get("val", "no value")
        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
        return render_template("hgcwa-search.html", title="Automorphisms of Higher Genus Curves Search", bread=bread, val=val)
    elif request.method == "POST":
        return "ERROR: we always do http get to explicitly display the search parameters"
    else:
        return flask.redirect(404)


def higher_genus_w_automorphisms_search(**args):
    info = to_dict(args)
    bread = get_bread([("Search results", url_for('.search'))])
    C = base.getDBConnection()
    query = {}
    if 'jump_to' in info:
        return render_family({'label': info['jump_to']})

    try:
        parse_list(info,query,'group', name='Group')
        parse_ints(info,query,'genus',name='Genus')
        parse_list(info,query,'signature',name='Signature')
        parse_ints(info,query,'dim',name='Dimension of the family')
        if 'inc_hyper' in info:
            if info['inc_hyper'] == 'exclude':
                query['hyperelliptic'] = False
            elif info['inc_hyper'] == 'only':
                query['hyperelliptic'] = True
    except ValueError:
        return search_input_error(info, bread)
    count = parse_count(info)
    start = parse_start(info)
    
    res = C.curve_automorphisms.passports.find(query).sort([(
         'g', pymongo.ASCENDING), ('dim', pymongo.ASCENDING)])
    nres = res.count()
    res = res.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    info['fields'] = res
    info['number'] = nres
    info['group_display'] = group_display_shortC(C)
    info['sign_display'] = sign_display
    info['start'] = start
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(
                               nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    return render_template("hgcwa-search.html", info=info, title="Higher Genus Curves with Automorphisms Search Result", bread=bread)





def render_family(args):
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        C = base.getDBConnection()
        dataz = C.curve_automorphisms.passports.find({'label': label})
        if dataz.count() is 0:
            bread = get_bread([("Search error", url_for('.search'))])
            info['err'] = "Higher Genus Curve with Automorphism " + label + " was not found in the database."
            info['label'] = label
            return search_input_error(info, bread)
        data=dataz[0]
        g = data['genus']
        GG = data['group']
        gn = GG[0]
        gt = GG[1]
    

        group = groupid_to_meaningful(data['group'])
        if group == str(GG) or group == "[" + str(gn)+","+str(gt)+"]":
            spname=False
        else:
            spname=True
        title = 'Family of genus ' + str(g) + ' curves with automorphism group $' + group +'$'
        smallgroup="(" + str(gn) + "," +str(gt) +")"   

        prop2 = [
            ('Genus', '\(%d\)' % g),
            ('Small Group', '\(%s\)' %  smallgroup),
            ('Signature', '\(%s\)' % sign_display(data['signature']))
        ]
        info.update({'genus': data['genus'],
                    'sign': sign_display(data['signature']),   
                    'group': groupid_to_meaningful(data['group']),
                    'g0':data['g0'],
                    'dim':data['dim'],
                    'r':data['r'],
                    'gpid': smallgroup
                   })

        if spname:
            info.update({'specialname': True})

        Lcc=[]
        Lall=[]
        i=1
        for dat in dataz:
            if dat['con'] not in Lcc:
                urlstrng=dat['passport_label']
                Lcc.append(dat['con'])
                Lall.append([cc_display(dat['con']),dat['passport_label'],
                             urlstrng])
                i=i+1
            
        info.update({'passport': Lall})

            
        friends = [ ]
        
        
        bread = get_bread([(label, ' ')])
        learnmore =[('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]

        downloads = [('Download this example', '.')]
            
        return render_template("hgcwa-show-family.html", 
                               title=title, bread=bread, info=info,
                               properties2=prop2, friends=friends,
                               learnmore=learnmore, downloads=downloads)



def render_passport(args):
    info = {}
    if 'passport_label' in args:
        label =clean_input(args['passport_label'])
        
        C = base.getDBConnection()
        
        dataz = C.curve_automorphisms.passports.find({'passport_label': label})
        if dataz.count() is 0:
            bread = get_bread([("Search error", url_for('.search'))])
            info['err'] = "Higher Genus Curve with Automorphism " + label + " was not found in the database."
            info['label'] = label
            return search_input_error(info, bread)
        data=dataz[0]
        g = data['genus']
        GG = data['group']
        gn = GG[0]
        gt = GG[1]
        numb = dataz.count()


        group = groupid_to_meaningful(data['group'])
        if group == str(GG) or group == "[" + str(gn)+","+str(gt)+"]":
            spname=False
        else:
            spname=True
        title = 'One passport of genus ' + str(g) + ' curves with automorphism group $' + group +'$'
        smallgroup="(" + str(gn) + "," +str(gt) +")"   

        prop2 = [
            ('Genus', '\(%d\)' % g),
            ('Small Group', '\(%s\)' %  smallgroup),
            ('Signature', '\(%s\)' % sign_display(data['signature'])),
            ('Generating Vectors','\(%d\)' % numb)
        ]
        info.update({'genus': data['genus'],
                    'cc': cc_display(data['con']), 
                    'sign': sign_display(data['signature']),   
                    'group': groupid_to_meaningful(data['group']),
                     'gpid': smallgroup
                   })

        if spname:
            info.update({'specialname': True})

        Ldata=[]
        HypColumn = False
        Lfriends=[]
        for dat in dataz:
            x1=dat['total_label']
            if 'full_auto' in dat:
                x2='No'
                if dat['full_label'] not in Lfriends:
                    Lfriends.append(dat['full_label'])
            else:
                x2='Yes'
                
            if 'hyperelliptic' in dat:
                x3=tfTOyn(dat['hyperelliptic'])
                HypColumn= True
            else:
                x3=' '

            x4=[]    
            for perm in dat['gen_vectors']:
                cycperm=Permutation(perm).cycle_string()

                x4.append(cycperm)
                    
            Ldata.append([x1,x2,x3,x4])

            
                
        info.update({'genvects': Ldata, 'HypColumn' : HypColumn})


        if 'hyperelliptic' in data:
            info.update({'ishyp':  tfTOyn(data['hyperelliptic'])})
            
        if 'hyp_involution' in data:
            info.update({'hypinv': data['hyp_involution']})
            

        if 'full_auto' in data:
            info.update({'fullauto': groupid_to_meaningful(data['full_auto']),
                         'signH':sign_display(data['signH']),
                         'higgenlabel' : data['full_label'] })


        if Lfriends:
           for Lf in Lfriends:
              friends = [("Full Automorphism " + Lf, Lf) ]
  
        else:    
            friends = [ ]
        

        
        bread = get_bread([(data['label'], ' '),(data['cc'][0], ' ')])
        learnmore =[('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]

        downloads = [('Download this example', '.')]
            
        return render_template("hgcwa-show-passport.html", 
                               title=title, bread=bread, info=info,
                               properties2=prop2, friends=friends,
                               learnmore=learnmore, downloads=downloads)


    


def search_input_error(info, bread):
    return render_template("hgcwa-search.html", info=info, title='Higher Genus Curve Search Input Error', bread=bread)


 
@higher_genus_w_automorphisms_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the automorphisms of curves data'
    bread = get_bread([("Completeness", )])
    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.extent',
                            title=t, bread=bread,learnmore=learnmore)


@higher_genus_w_automorphisms_page.route("/Labels")
def labels_page():
    t = 'Label scheme for the data'
    bread = get_bread([("Labels", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.label',
                           learnmore=learnmore, title=t, bread=bread)

@higher_genus_w_automorphisms_page.route("/Source")
def how_computed_page():
    t = 'Source of the automorphisms of curve data'
    bread = get_bread([("Source", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.source',
                           title=t, bread=bread, learnmore=learnmore)
