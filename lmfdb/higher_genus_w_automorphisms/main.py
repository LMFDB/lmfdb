# -*- coding: utf-8 -*-
# This Blueprint is about Higher Genus Curves
# Author: Jen Paulhus (copied from John Jones Local Fields)

import re
import pymongo
import ast
ASC = pymongo.ASCENDING
import yaml
import os
from lmfdb import base
from flask import render_template, request, url_for, make_response, redirect, abort
from lmfdb.utils import to_dict, random_value_from_collection, flash_error
from lmfdb.search_parsing import parse_ints, parse_count, parse_start, clean_input, parse_bracketed_posints, parse_gap_id

from sage.all import Permutation
from lmfdb.higher_genus_w_automorphisms import higher_genus_w_automorphisms_page
from lmfdb.sato_tate_groups.main import sg_pretty


# Determining what kind of label
family_label_regex = re.compile(r'(\d+)\.(\d+-\d+)\.(\d+\.\d+-[^\.]*$)')
passport_label_regex = re.compile(r'((\d+)\.(\d+-\d+)\.(\d+\.\d+.*))\.(\d+)')
cc_label_regex = re.compile(r'((\d+)\.(\d+-\d+)\.(\d+)\.(\d+.*))\.(\d+)')

def label_is_one_family(lab):
    return family_label_regex.match(lab)

def label_is_one_passport(lab):
    return passport_label_regex.match(lab)


def split_family_label(lab):
    return family_label_regex.match(lab).groups()


def split_passport_label(lab):
    return passport_label_regex.match(lab).groups()


credit ='Jen Paulhus, using group and signature data originally computed by Thomas Breuer'


def get_bread(breads=[]):
    bc = [("Higher Genus", url_for(".index")),("C", url_for(".index")),("Aut", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def tfTOyn(bool):
    if bool:
        return "Yes"
    else:
        return "No"


def sign_display(L):
    sizeL = len(L)
    signL = "[ " + str(L[0]) + "; "
    for i in range(1,sizeL-1):
        signL= signL + str(L[i]) + ", "

    signL=signL + str(L[sizeL-1]) + " ]"
    return signL

def cc_display(L):
    sizeL = len(L)
    if sizeL == 1:
        return str(L[0])
    stg = str(L[0])+ ", "
    for i in range(1,sizeL-1):
        stg =stg + str(L[i])+", "
    stg=stg+ str(L[sizeL-1])
    return stg


#for splitting permutations cycles
sep=' '

def split_perm(strg):
    startpoint = 0
    for i in range(0,len(strg)):
        if strg[i] == ")":
            yield strg[startpoint:i+1]
            startpoint = i+1

def sort_sign(L):
    L1 = L[1:]
    L1.sort()
    return [L[0]] +L1

def label_to_breadcrumbs(L):
    newsig = '['
    for i in range(0,len(L)):
        if (L[i] == '-'):
            newsig += ","
        elif (L[i] == '.'):
            newsig += ';'
        else:
            newsig += L[i]

    newsig += ']'
    return newsig

def decjac_format(decjac_list):
    entries = []
    for ints in decjac_list:
        entry = ""
        if ints[0] == 1:
            entry = entry + "E"
        else:
            entry = entry + "A_{" + str(ints[0]) + "}"
        if ints[1] != 1:
            entry = entry + "^{" + str(ints[1]) + "}"
        entries.append(entry)
    latex = "\\times ".join(entries)
    ccClasses = cc_display ([ints[2] for ints in decjac_list])
    return latex, ccClasses

@higher_genus_w_automorphisms_page.route("/")
def index():
    bread = get_bread()
    if request.args:
        return higher_genus_w_automorphisms_search(**request.args)

    C = base.getDBConnection()
    genus_max = C.curve_automorphisms.passports.find().sort('genus', pymongo.DESCENDING).limit(1)[0]['genus']  + 1
    genus_list = range(2,genus_max)
    info = {'count': 20,'genus_list': genus_list}


    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]

    return render_template("hgcwa-index.html", title="Families of Higher Genus Curves with Automorphisms", bread=bread, credit=credit, info=info, learnmore=learnmore)


@higher_genus_w_automorphisms_page.route("/random")
def random_passport():
    C = base.getDBConnection()
    label = random_value_from_collection(C.curve_automorphisms.passports,'passport_label')
    return redirect(url_for(".by_passport_label", passport_label=label))



#############################################
#  Stats page functions                     #
#############################################

# TODO Add number of distinct families per genus to stats page

def max_group_order(counts):
    orders = []
    for count in counts:
        group = count[0]
        order = int(re.search(r'\[(\d+)', group).group(1))
        orders.append(order)
    return max(orders)

# TODO Move to proper location
def get_hgcwa_stats():
    # TODO REPLACE WITH SINGLE INSTANCE
    C = base.getDBConnection()
    hgcwa_stats = C.curve_automorphisms.passports.stats
    stats = {}

    # Populate simple data
    stats['genus_summary'] = hgcwa_stats.find_one({'_id':'genus'})
    stats['dim_summary'] = hgcwa_stats.find_one({'_id':'dim'})

    # An iterable list of distinct curve genera
    genus_list = [ count[0] for count in stats['genus_summary']['counts'] ]
    genus_list.sort()

    # Get unique joint genus stats
    stats['genus'] = []

    for genus in genus_list:
        genus_stats = {}
        genus_stats['genus_num'] = genus
        genus_str = str(genus)

        # Get group data
        groups = hgcwa_stats.find_one({'_id':'bygenus/' + genus_str + '/group'})
        group_count = len(groups['counts'])
        group_max_order = max_group_order(groups['counts'])
        genus_stats['groups'] = [group_count, group_max_order]

        # Get family data
        families = hgcwa_stats.find_one({'_id':'bygenus/' + genus_str + '/label'})
        family_count = len(families['counts'])
        genus_stats['families'] = family_count

        # Get refined passport data
        rps = hgcwa_stats.find_one({'_id':'bygenus/' + genus_str + '/passport_label'})
        rp_count = len(rps['counts'])
        genus_stats['refined_passports'] = rp_count

        # TODO May be redundant, see genus data
        # Get generating vector data
        gvs = hgcwa_stats.find_one({'_id':'bygenus/' + genus_str + '/total_label'})
        gv_count = len(gvs['counts'])
        genus_stats['gen_vectors'] = gv_count

        # Keep genus data sorted
        stats['genus'].append(genus_stats)

    return stats

@higher_genus_w_automorphisms_page.route("/stats")
def statistics():
    info = {
        'stats': get_hgcwa_stats(),
    }
    title = 'Higher Genus Curves with Automorphisms: statistics'
    bread = get_bread([('stats', ' ')])
    return render_template("hgcwa-stats.html", info=info, credit=credit, title=title, bread=bread)

@higher_genus_w_automorphisms_page.route("/stats/groups_per_genus/<genus>")
def groups_per_genus(genus):
    # TODO REPLACE WITH SINGLE INSTANCE
    C = base.getDBConnection()
    hgcwa_stats = C.curve_automorphisms.passports.stats

    group_stats = hgcwa_stats.find_one({'_id':'bygenus/' + genus + '/group'})

    # Redirect to 404 if statistic is not found
    if not group_stats:
        return abort(404, 'Group statistics for curves of genus %s not found in database.' % genus)

    info = {
        'genus' : genus,
        'groups': group_stats['counts'],
    }

    title = 'Higher Genus Curves with Automorphisms: groups per genus'
    bread = get_bread([('stats', url_for('.statistics')), ('Groups per genus', ' '), (str(genus), ' ')])
    return render_template("hgcwa-stats-groups-per-genus.html", info=info, credit=credit, title=title, bread=bread)

#############################################
#  End Stats page functions                 #
#############################################

@higher_genus_w_automorphisms_page.route("/<label>")
def by_label(label):

    if label_is_one_passport(label):
        return render_passport({'passport_label': label})
    elif label_is_one_family(label):
        return render_family({'label': label})
    else:
        flash_error( "No family with label %s was found in the database.", label)
        return redirect(url_for(".index"))


@higher_genus_w_automorphisms_page.route("/<passport_label>")
def by_passport_label(label):
    return render_passport({'passport_label': label})


def higher_genus_w_automorphisms_search(**args):
    info = to_dict(args)
    bread = get_bread([("Search results",'')])
    C = base.getDBConnection()
    query = {}
    if 'jump_to' in info:
        labs = info['jump_to']
        if label_is_one_passport(labs):
            return render_passport({'passport_label': labs})
        elif label_is_one_family(labs):
            return render_family({'label': labs})
        else:
            flash_error ("The label %s is not a legitimate label for this data.",labs)
            return redirect(url_for(".index"))

    #allow for ; in signature
    if info.get('signature'):
        info['signature'] = info['signature'].replace(';',',')

    try:
        parse_gap_id(info,query,'group','Group')
        parse_ints(info,query,'genus',name='Genus')
        parse_bracketed_posints(info,query,'signature',split=False,name='Signature',keepbrackets=True)
        if query.get('signature'):
            query['signature'] = info['signature'] = str(sort_sign(ast.literal_eval(query['signature']))).replace(' ','')
        parse_ints(info,query,'dim',name='Dimension of the family')
        if 'inc_hyper' in info:
            if info['inc_hyper'] == 'exclude':
                query['hyperelliptic'] = False
            elif info['inc_hyper'] == 'only':
                query['hyperelliptic'] = True
        if 'inc_cyc_trig' in info:
            if info['inc_cyc_trig'] == 'exclude':
                query['cyclic_trigonal'] = False
            elif info['inc_cyc_trig'] == 'only':
                query['cyclic_trigonal'] = True
        if 'inc_full' in info:
            if info['inc_full'] == 'exclude':
                query['full_auto'] = {'$exists': True}
            elif info['inc_full'] == 'only':
                query['full_auto'] = {'$exists': False}

        query['cc.1'] = 1

    except ValueError:
        return search_input_error(info, bread)
    count = parse_count(info)
    start = parse_start(info)

    res = C.curve_automorphisms.passports.find(query).sort([(
         'genus', pymongo.ASCENDING), ('dim', pymongo.ASCENDING),
        ('cc'[0],pymongo.ASCENDING)])
    nres = res.count()
    res = res.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0


    L = [ ]
    for field in res:
        field['signature'] = ast.literal_eval(field['signature'])
        L.append(field)

    info['fields'] = L
    info['number'] = nres
    info['group_display'] = sg_pretty

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

    return render_template("hgcwa-search.html", info=info, title="Families of Higher Genus Curves with Automorphisms Search Result", credit=credit, bread=bread)



def render_family(args):
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        C = base.getDBConnection()
        dataz = C.curve_automorphisms.passports.find({'label': label})
        if dataz.count() is 0:
            flash_error( "No family with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        data=dataz[0]
        g = data['genus']
        GG = ast.literal_eval(data['group'])
        gn = GG[0]
        gt = GG[1]

        gp_string=str(gn) + '.' + str(gt)
        pretty_group=sg_pretty(gp_string)

        if gp_string == pretty_group:
            spname=False
        else:
            spname=True
        title = 'Family of genus ' + str(g) + ' curves with automorphism group $' + pretty_group +'$'
        smallgroup="[" + str(gn) + "," +str(gt) +"]"

        prop2 = [
            ('Genus', '\(%d\)' % g),
            ('Group', '\(%s\)' %  pretty_group),
            ('Signature', '\(%s\)' % sign_display(ast.literal_eval(data['signature'])))
        ]
        info.update({'genus': data['genus'],
                    'sign': sign_display(ast.literal_eval(data['signature'])),
                     'group': pretty_group,
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
            if ast.literal_eval(dat['con']) not in Lcc:
                urlstrng=dat['passport_label']
                Lcc.append(ast.literal_eval(dat['con']))
                Lall.append([cc_display(ast.literal_eval(dat['con'])),dat['passport_label'],
                             urlstrng])
                i=i+1

        info.update({'passport': Lall})


        g2List = ['[2,1]','[4,2]','[8,3]','[10,2]','[12,4]','[24,8]','[48,29]']
        if g  == 2 and data['group'] in g2List:
            g2url = "/Genus2Curve/Q/?geom_aut_grp_id=" + data['group']
            friends = [("Genus 2 curves over $\Q$", g2url ) ]
        else:
            friends = [ ]


        br_g, br_gp, br_sign = split_family_label(label)

        bread_sign = label_to_breadcrumbs(br_sign)
        bread_gp = label_to_breadcrumbs(br_gp)

        bread = get_bread([(br_g, './?genus='+br_g),('$'+pretty_group+'$','./?genus='+br_g + '&group='+bread_gp), (bread_sign,' ')])
        learnmore =[('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]

        downloads = [('Download Magma code', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
                     ('Download Gap code', url_for(".hgcwa_code_download", label=label, download_type='gap'))]

        return render_template("hgcwa-show-family.html",
                               title=title, bread=bread, info=info,
                               properties2=prop2, friends=friends,
                               learnmore=learnmore, downloads=downloads, credit=credit)


def render_passport(args):
    info = {}
    if 'passport_label' in args:
        label =clean_input(args['passport_label'])

        C = base.getDBConnection()

        dataz = C.curve_automorphisms.passports.find({'passport_label': label})
        if dataz.count() is 0:
            bread = get_bread([("Search error", url_for('.search'))])
            flash_error( "No refined passport with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        data=dataz[0]
        g = data['genus']
        GG = ast.literal_eval(data['group'])
        gn = GG[0]
        gt = GG[1]

        gp_string=str(gn) + '.' + str(gt)
        pretty_group=sg_pretty(gp_string)

        if gp_string == pretty_group:
            spname=False
        else:
            spname=True

        numb = dataz.count()

        try:
            numgenvecs = request.args['numgenvecs']
            numgenvecs = int(numgenvecs)
        except:
            numgenvecs = 20
        info['numgenvecs']=numgenvecs

        title = 'One refined passport of genus ' + str(g) + ' with automorphism group $' + pretty_group +'$'
        smallgroup="[" + str(gn) + "," +str(gt) +"]"

        prop2 = [
            ('Genus', '\(%d\)' % g),
            ('Small Group', '\(%s\)' %  pretty_group),
            ('Signature', '\(%s\)' % sign_display(ast.literal_eval(data['signature']))),
            ('Generating Vectors','\(%d\)' % numb)
        ]
        info.update({'genus': data['genus'],
                    'cc': cc_display(data['con']),
                    'sign': sign_display(ast.literal_eval(data['signature'])),
                     'group': pretty_group,
                     'gpid': smallgroup,
                     'numb':numb,
                     'disp_numb':min(numb,numgenvecs)
                   })

        if spname:
            info.update({'specialname': True})

        Ldata=[]
        HypColumn = False
        Lfriends=[]
        for i in range (0, min(numgenvecs,numb)):
            dat= dataz[i]
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

                x4.append(sep.join(split_perm(cycperm)))

            Ldata.append([x1,x2,x3,x4])



        info.update({'genvects': Ldata, 'HypColumn' : HypColumn})

        info.update({'passport_cc': cc_display(ast.literal_eval(data['con']))})

        if 'eqn' in data:
            info.update({'eqns': data['eqn']})

        if 'ndim' in data:
            info.update({'Ndim': data['ndim']})

        other_data = False

        if 'hyperelliptic' in data:
            info.update({'ishyp':  tfTOyn(data['hyperelliptic'])})
            other_data = True

        if 'hyp_involution' in data:
            inv=Permutation(data['hyp_involution']).cycle_string()
            info.update({'hypinv': sep.join(split_perm(inv))})


        if 'cyclic_trigonal' in data:
            info.update({'iscyctrig':  tfTOyn(data['cyclic_trigonal'])})
            other_data = True

        if 'jacobian_decomp' in data:
            jcLatex, corrChar = decjac_format(data['jacobian_decomp'])
            info.update({'corrChar': corrChar, 'jacobian_decomp': jcLatex})


        if 'cinv' in data:
            cinv=Permutation(data['cinv']).cycle_string()
            info.update({'cinv': sep.join(split_perm(cinv))})

        info.update({'other_data': other_data})


        if 'full_auto' in data:
            full_G=ast.literal_eval(data['full_auto'])
            full_gn = full_G[0]
            full_gt = full_G[1]

            full_gp_string=str(full_gn) + '.' + str(full_gt)
            full_pretty_group=sg_pretty(full_gp_string)
            info.update({'fullauto': full_pretty_group,
                         'signH':sign_display(ast.literal_eval(data['signH'])),
                         'higgenlabel' : data['full_label'] })


        urlstrng,br_g, br_gp, br_sign, refined_p = split_passport_label(label)


        if Lfriends:
           for Lf in Lfriends:
              friends = [("Full automorphism " + Lf, Lf),("Family containing this refined passport ",  urlstrng) ]

        else:
            friends = [("Family containing this refined passport",  urlstrng) ]


        bread_sign = label_to_breadcrumbs(br_sign)
        bread_gp = label_to_breadcrumbs(br_gp)

        bread = get_bread([(br_g, './?genus='+br_g),('$'+pretty_group+'$','./?genus='+br_g + '&group='+bread_gp), (bread_sign, urlstrng),(data['cc'][0],' ')])

        learnmore =[('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]

        downloads = [('Download Magma code', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
                     ('Download Gap code', url_for(".hgcwa_code_download", label=label, download_type='gap'))]

        return render_template("hgcwa-show-passport.html",
                               title=title, bread=bread, info=info,
                               properties2=prop2, friends=friends,
                               learnmore=learnmore, downloads=downloads, credit=credit)



def search_input_error(info, bread):
    return render_template("hgcwa-search.html", info=info, title='Families of Higher Genus Curve Search Input Error', bread=bread, credit=credit)



@higher_genus_w_automorphisms_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the automorphisms of curves data'
    bread = get_bread([("Completeness", )])
    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.extent',
                            title=t, bread=bread,learnmore=learnmore, credit=credit)


@higher_genus_w_automorphisms_page.route("/Labels")
def labels_page():
    t = 'Label scheme for the data'
    bread = get_bread([("Labels", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.label',
                           learnmore=learnmore, title=t, bread=bread,credit=credit)

@higher_genus_w_automorphisms_page.route("/Source")
def how_computed_page():
    t = 'Source of the automorphisms of curve data'
    bread = get_bread([("Source", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.source',
                           title=t, bread=bread, learnmore=learnmore, credit=credit)




_curdir = os.path.dirname(os.path.abspath(__file__))
code_list =  yaml.load(open(os.path.join(_curdir, "code.yaml")))

@higher_genus_w_automorphisms_page.route("/<label>/download/<download_type>")
def hgcwa_code_download(**args):
    response = make_response(hgcwa_code(**args))
    response.headers['Content-type'] = 'text/plain'
    return response


same_for_all =  ['signature', 'genus']
other_same_for_all = [ 'r', 'g0', 'dim','sym']
depends_on_action = ['gen_vectors']


Fullname = {'magma': 'Magma', 'gap': 'GAP'}
Comment = {'magma': '//', 'gap': '#'}

def hgcwa_code(**args):
    import time
    label = args['label']
    C = base.getDBConnection()
    lang = args['download_type']
    code = "%s %s code for the lmfdb family of higher genus curves %s\n" % (Comment[lang],Fullname[lang],label)
    code +="%s The results are stored in a list of records called 'result_record'\n\n" % (Comment[lang])
    code +=code_list['top_matter'][lang] + '\n' +'\n'
    code +="result_record:=[];" + '\n' +'\n'


    if label_is_one_passport(label):
        data = C.curve_automorphisms.passports.find({"passport_label" : label})

    elif label_is_one_family(label):
        data = C.curve_automorphisms.passports.find({"label" : label})

    code += Comment[lang] + code_list['gp_comment'][lang] +'\n'
    code += code_list['group'][lang] + str(data[0]['group'])+ ';\n'

    if lang == 'magma':
        code += code_list['group_construct'][lang] + '\n'

    for k in same_for_all:
        code += code_list[k][lang] + str(data[0][k])+ ';\n'

    for k in other_same_for_all:
        code += code_list[k][lang] + '\n'

    code += '\n'

    # create formatting templates to be filled in with each record in data
    startstr = Comment[lang] + ' Here we add an action to result_record.\n'
    stdfmt = ''
    for k in depends_on_action:
        stdfmt += code_list[k][lang] + '{' + k + '}'+ ';\n'

    if lang == 'magma':
        stdfmt += code_list['con'][lang] + '{con}' + ';\n'

    stdfmt += code_list['gen_gp'][lang]+ '\n'
    stdfmt += code_list['passport_label'][lang] + '{cc[0]}' + ';\n'
    stdfmt += code_list['gen_vect_label'][lang] + '{cc[1]}' + ';\n'

    # extended formatting template for when signH is present
    signHfmt = stdfmt
    signHfmt += code_list['full_auto'][lang] + '{full_auto}' + ';\n'
    signHfmt += code_list['full_sign'][lang] + '{signH}' + ';\n'
    signHfmt += code_list['add_to_total_full'][lang] + '\n'

    # additional info for hyperelliptic cases
    hypfmt = code_list['hyp'][lang] + code_list['tr'][lang] + ';\n'
    hypfmt += code_list['hyp_inv'][lang] + '{hyp_involution}' + code_list['hyp_inv_last'][lang]
    hypfmt += code_list['cyc'][lang] + code_list['fal'][lang] + ';\n'
    hypfmt += code_list['add_to_total_hyp'][lang] + '\n'
    cyctrigfmt = code_list['hyp'][lang] + code_list['fal'][lang] + ';\n'
    cyctrigfmt += code_list['cyc'][lang] + code_list['tr'][lang] + ';\n'
    cyctrigfmt += code_list['cyc_auto'][lang] + '{cinv}' + code_list['hyp_inv_last'][lang]
    cyctrigfmt += code_list['add_to_total_cyc_trig'][lang] + '\n'
    nhypcycstr = code_list['hyp'][lang] + code_list['fal'][lang] + ';\n'
    nhypcycstr += code_list['cyc'][lang] + code_list['fal'][lang] + ';\n'
    nhypcycstr += code_list['add_to_total_basic'][lang] + '\n'

    start = time.time()
    lines = [(startstr + (signHfmt if 'signH' in dataz else stdfmt).format(**dataz) + ((hypfmt.format(**dataz) if dataz['hyperelliptic'] else cyctrigfmt.format(**dataz) if dataz['cyclic_trigonal'] else nhypcycstr) if 'hyperelliptic' in dataz else '')) for dataz in data]
    code += '\n'.join(lines)
    print "%s seconds for %d bytes" %(time.time() - start,len(code))
    return code
