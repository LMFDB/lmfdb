# -*- coding: utf-8 -*-
# This Blueprint is about Higher Genus Curves
# Authors: Jen Paulhus, Lex Martin, David Neill Asanza
# (initial code copied from John Jones Local Fields)

import StringIO
import re
import ast
import yaml
import os
from lmfdb.db_backend import db
from flask import render_template, request, url_for, redirect, send_file, abort
from lmfdb.utils import flash_error
from lmfdb.search_parsing import parse_ints, clean_input, parse_bracketed_posints, parse_gap_id
from lmfdb.search_wrapper import search_wrap

from sage.all import Permutation
from lmfdb.higher_genus_w_automorphisms import higher_genus_w_automorphisms_page
from lmfdb.sato_tate_groups.main import sg_pretty
from lmfdb.higher_genus_w_automorphisms.hgcwa_stats import HGCWAstats


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
        return higher_genus_w_automorphisms_search(request.args)
    genus_max = db.hgcwa_passports.max('genus')
    genus_list = range(2,genus_max+1)
    info = {'count': 20,
            'genus_list': genus_list,
            'stats': HGCWAstats().stats(),}

    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page")),
                ('Completeness of the data', url_for(".completeness_page"))]

    return render_template("hgcwa-index.html", title="Families of Higher Genus Curves with Automorphisms", bread=bread, credit=credit, info=info, learnmore=learnmore)


@higher_genus_w_automorphisms_page.route("/random")
def random_passport():
    label = db.hgcwa_passports.random(projection='passport_label')
    return redirect(url_for(".by_passport_label", passport_label=label))

@higher_genus_w_automorphisms_page.route("/stats")
def statistics():
    info = {
        'stats': HGCWAstats().stats(),
    }
    title = 'Families of Higher Genus Curves with Automorphisms: Statistics'
    bread = get_bread([('Statistics', ' ')])
    return render_template("hgcwa-stats.html", info=info, credit=credit, title=title, bread=bread)

@higher_genus_w_automorphisms_page.route("/stats/groups_per_genus/<genus>")
def groups_per_genus(genus):
    group_stats = db.hgcwa_passports.stats.get_oldstat('bygenus/' + genus + '/group')

    # Redirect to 404 if statistic is not found
    if not group_stats:
        return abort(404, 'Group statistics for curves of genus %s not found in database.' % genus)

    # Groups are stored in sorted order
    groups = group_stats['counts']

    # Create isomorphism classes
    hgcwa_group = re.compile(r'\[(\d+),(\d+)\]')
    iso_classes = []

    for group in groups:
        iso_classes.append(sg_pretty(re.sub(hgcwa_group, r'\1.\2', group[0])))

    info = {
        'genus' : genus,
        'groups': groups,
        'iso_classes' : iso_classes
    }

    title = 'Families of Higher Genus Curves with Automorphisms: Genus ' + genus + ' Group Statistics'
    bread = get_bread([('Statistics', url_for('.statistics')), ('Groups per Genus', url_for('.statistics')), (str(genus), ' ')])
    return render_template("hgcwa-stats-groups-per-genus.html", info=info, credit=credit, title=title, bread=bread)

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

cur_expr = None
cur_index = 0

def is_letter(char):
    return (ord(char) >= ord('a') and ord(char) <= ord('z')) or (ord(char) >= ord('A') and ord(char) <= ord('Z'))

def expr_error(err):
    expr_getc()
    err_msg = ('-' * max(cur_index - 1, 0))
    err_msg_lst = list(err_msg)
    err_msg = "".join(err_msg_lst)
    err_msg += "^ " + err
    return err_msg

def expr_getc():
    global cur_expr, cur_index
    while cur_index < len(cur_expr):
        result = cur_expr[cur_index]
        cur_index += 1
        if result != ' ':
            return result
    else:
        return None

def expr_peekc():
    global cur_index
    result = expr_getc()
    if result != None: cur_index -= 1
    return result

def expr_expect_char(char):
    actual_char = expr_getc()

    if actual_char != char:
        return expr_error("expected '" + char +"' here")
    else:
        return None

def read_num():
    num = ""
    c = expr_peekc()
    while c != None and c.isdigit():
        num += c
        expr_getc()
        c = expr_peekc()
    return int(num)

def expect_var(vars):
    c = expr_peekc()
    is_valid_var = False
    for var in vars.keys():
        if var == c:
            is_valid_var = True
            break

    if is_valid_var:
        var = expr_getc()
        return (None, vars[var])
    else:
        return (expr_error("'" + c + "' is not a recognized variable"), None)

def expect_factor(vars):
    c = expr_peekc()
    if c == None:
        return (expr_error("expected factor here"), None)
    elif c.isdigit():
        return (None, read_num())
    elif is_letter(c):
        err, result = expect_var(vars)
        return err, result
    elif c == '(':
        expr_getc()
        err, result = expect_expr(vars)
        if err != None: return (err, None)
        err = expr_expect_char(')')
        if err != None: return (err, None)
        else: return (None, result)
    else:
        return (expr_error("'" + c + "' unexpected symbol"), None)

def expect_term(vars):
    err, result = expect_factor(vars)
    if err != None: return (err, None)

    c = expr_peekc()
    while c != None and (c.isdigit() or is_letter(c) or c == '('):
        err, factor_result = expect_factor(vars)
        if err != None: return (err, None)
        result *= factor_result
        c = expr_peekc()

    return (None, result)

def expect_expr(vars):
    err, result = expect_term(vars)
    if err != None: return (err, None)

    c = expr_peekc()
    while c == "+" or c == "-":
        expr_getc()
        err, term_result = expect_term(vars)
        if err != None: return (err, None)
        if c == "+":
            result += term_result
        elif c == "-":
            result -= term_result
        c = expr_peekc()

    return (None, result)

def evaluate_expr(expr, vars):
    global cur_expr, cur_index
    cur_expr = expr
    cur_index = 0
    err, result = expect_expr(vars)

    if err == None:
        if expr_peekc() != None:
            return (expr_error("unexpected symbol"), None)

    return (err, result)

def add_group_order_range(query, expr):
    # Support -- and .. as range
    query_range = expr.replace("--", "..")
    raw_parts = expr.split('..')
    raw_parts = filter(lambda x: x != '', raw_parts)
    min_genus = 1
    max_genus = db.hgcwa_passports.max('genus')

    # when given A-B and A,B are integers treat A-B as a range not subtraction.
    special_case_parts = expr.split('-')
    #is_special_case_range = special_case_parts[0].isdigit() and special_case_parts[1].isdigit()
    is_special_case_range = len(special_case_parts) == 2 and special_case_parts[0].isdigit() and special_case_parts[1].isdigit()

    if is_special_case_range:
        query["group_order"] = {"$gte": int(special_case_parts[0]), "$lte": int(special_case_parts[1])}
        return (None, None)

    elif len(raw_parts) == 2:
        options = []

        for cur_genus in range(min_genus, max_genus + 1):
            left_err, left_value   = evaluate_expr(raw_parts[0], {'g': cur_genus})
            right_err, right_value = evaluate_expr(raw_parts[1], {'g': cur_genus})
            if left_err == None and right_err == None:
                options.append({"group_order": {"$gte": left_value, "$lte" : right_value}, "genus": cur_genus})
            elif left_err != None:
                query["$or"] = [{"genus": {"$lte": 0}}]
                return (raw_parts[0], left_err)
            else:
                query["$or"] = [{"genus": {"$lte": 0}}]
                return (raw_parts[1], right_err)

        query["$or"] = options
        return (None, None)
    elif len(raw_parts) == 1:
        condition = ""

        if query_range.find('..') != -1:
            if query_range.index("..") == 0:
                condition = "$lte"
            else:
                condition = "$gte"
        else:
            condition = "$eq"

        options = []
        for cur_genus in range(min_genus, max_genus + 1):
            err, value = evaluate_expr(raw_parts[0], {'g': cur_genus})
            if err == None:
                options.append({"group_order": {condition: value}, "genus": {"$eq": cur_genus}})
            else:
                query["$or"] = [{"genus": {"$lte": 0}}]
                return (raw_parts[0], err)

        query["$or"] = options
        return (None, None)
    else:
        return ("", "You must either specify a group size or range in the format Min..Max")

def higher_genus_w_automorphisms_jump(info):
    labs = info['jump_to']
    if label_is_one_passport(labs):
        return render_passport({'passport_label': labs})
    elif label_is_one_family(labs):
        return render_family({'label': labs})
    else:
        flash_error ("The label %s is not a legitimate label for this data.",labs)
        return redirect(url_for(".index"))

def higher_genus_w_automorphisms_postprocess(res, info, query):
    info['show_downloads'] = len(res) > 0
    return res

@search_wrap(template="hgcwa-search.html",
             table=db.hgcwa_passports,
             title='Families of Higher Genus Curves with Automorphisms Search Results',
             err_title='Families of Higher Genus Curve Search Input Error',
             per_page=20,
             shortcuts={'jump_to':higher_genus_w_automorphisms_jump},
             longcuts={'download_magma':(lambda res, info, query: hgcwa_code_download_search(res,'magma')),
                       'download_gap':(lambda res, info, query: hgcwa_code_download_search(res,'gap'))},
             cleaners={'signature': lambda field:ast.literal_eval(field['signature'])},
             postprocess=higher_genus_w_automorphisms_postprocess,
             bread=lambda:get_bread([("Search Results",'')]),
             credit=lambda:credit)
def higher_genus_w_automorphisms_search(info, query):
    if info.get('signature'):
        #allow for ; in signature
        info['signature'] = info['signature'].replace(';',',')
        parse_bracketed_posints(info,query,'signature',split=False,name='Signature',keepbrackets=True)
        if query.get('signature'):
            query['signature'] = info['signature'] = str(sort_sign(ast.literal_eval(query['signature']))).replace(' ','')
    parse_gap_id(info,query,'group',name='Group',qfield='group')
    parse_ints(info,query,'genus',name='Genus')
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
    if info.get('groupsize'):
        err, result = add_group_order_range(query, info['groupsize'])
        if err is not None:
            flash_error('Parse error on group order field. <font face="Courier New"><br />Given: ' + err + '<br />-------' + result + '</font>')

    info['group_display'] = sg_pretty
    info['sign_display'] = sign_display

def render_family(args):
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        dataz = list(db.hgcwa_passports.search({'label':label}))
        if len(dataz) == 0:
            flash_error( "No family with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        data=dataz[0]
        g = data['genus']
        GG = ast.literal_eval(data['group'])
        gn = GG[0]
        gt = GG[1]

        gp_string = str(gn) + '.' + str(gt)
        pretty_group = sg_pretty(gp_string)

        if gp_string == pretty_group:
            spname = False
        else:
            spname = True
        title = 'Family of Genus ' + str(g) + ' Curves with Automorphism Group $' + pretty_group +'$'
        smallgroup="[" + str(gn) + "," +str(gt) + "]"

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
        label = clean_input(args['passport_label'])
        dataz = list(db.hgcwa_passports.search({'passport_label': label}))
        if len(dataz) == 0:
            bread = get_bread([("Search Error", url_for('.index'))])
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

        numb = len(dataz)

        try:
            numgenvecs = request.args['numgenvecs']
            numgenvecs = int(numgenvecs)
        except:
            numgenvecs = 20
        info['numgenvecs']=numgenvecs

        title = 'One Refined Passport of Genus ' + str(g) + ' with Automorphism Group $' + pretty_group +'$'
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
    t = 'Completeness of the Automorphisms of Curves Data'
    bread = get_bread([("Completeness", )])
    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.extent',
                            title=t, bread=bread,learnmore=learnmore, credit=credit)


@higher_genus_w_automorphisms_page.route("/Labels")
def labels_page():
    t = 'Label Scheme for the Data'
    bread = get_bread([("Labels", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.label',
                           learnmore=learnmore, title=t, bread=bread,credit=credit)

@higher_genus_w_automorphisms_page.route("/Source")
def how_computed_page():
    t = 'Source of the Automorphisms of Curve Data'
    bread = get_bread([("Source", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.curve.highergenus.aut.source',
                           title=t, bread=bread, learnmore=learnmore, credit=credit)




_curdir = os.path.dirname(os.path.abspath(__file__))
code_list =  yaml.load(open(os.path.join(_curdir, "code.yaml")))


same_for_all =  ['signature', 'genus']
other_same_for_all = [ 'r', 'g0', 'dim','sym']
depends_on_action = ['gen_vectors']


Fullname = {'magma': 'Magma', 'gap': 'GAP'}
Comment = {'magma': '//', 'gap': '#'}
FileSuffix= {'magma': '.m', 'gap': '.g'} 

@higher_genus_w_automorphisms_page.route("/<label>/download/<download_type>")
def hgcwa_code_download(**args):
    import time
    label = args['label']
    lang = args['download_type']
    s = Comment[lang]
    filename= 'HigherGenusData' + str(label) + FileSuffix[lang] 
    code = s + " " + Fullname[lang]+  " code for the lmfdb family of higher genus curves " + str(label) + '\n'  
    code += s + " The results are stored in a list of records called 'data'\n\n" 
    code +=code_list['top_matter'][lang] + '\n' +'\n'
    code +="data:=[];" + '\n' +'\n'


    if label_is_one_passport(label):
        data = list(db.hgcwa_passports.search({"passport_label" : label}))

    elif label_is_one_family(label):
        data = list(db.hgcwa_passports.search({"label" : label}))
    
    code += s + code_list['gp_comment'][lang] +'\n'
    code += code_list['group'][lang] + str(data[0]['group'])+ ';\n'

    if lang == 'magma':
        code += code_list['group_construct'][lang] + '\n'

    for k in same_for_all:
        code += code_list[k][lang] + str(data[0][k])+ ';\n'

    for k in other_same_for_all:
        code += code_list[k][lang] + '\n'

    code += '\n'

    # create formatting templates to be filled in with each record in data
    startstr = s + ' Here we add an action to data.\n'
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
    lines = [(startstr + (signHfmt if dataz.get('signH') is not None else stdfmt).format(**dataz) + ((hypfmt.format(**dataz) if dataz['hyperelliptic'] else cyctrigfmt.format(**dataz) if dataz['cyclic_trigonal'] else nhypcycstr) if dataz.get('hyperelliptic') else '')) for dataz in data]
    code += '\n'.join(lines)
    print "%s seconds for %d bytes" %(time.time() - start,len(code))
    strIO = StringIO.StringIO()
    strIO.write(code)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)




#JEN TEST FUNCTION
@higher_genus_w_automorphisms_page.route("/download/<download_type>")
#def hgcwa_code_download_search(**args):
def hgcwa_code_download_search(res,download_type):
    import time
    lang = download_type
    s = Comment[lang]
    filename= 'HigherGenusSearch' + FileSuffix[lang] 
    code = s + " " + Fullname[lang]+  " CODE FOR SEACH RESULTS" + '\n' + '\n'
    code += s + " The results are stored in a list of records called 'data'\n\n" 
    code +=code_list['top_matter'][lang] + '\n' +'\n'
    code +="data:=[];" + '\n' +'\n'

    label_list=[]
    for field in res:
        label=field['label']
        if  label not in label_list:
            label_list.append(label)
            
            data = list(db.hgcwa_passports.search({"label" : label}))
            code += s + code_list['search_result_gp_comment'][lang] +'\n'
            code += code_list['group'][lang] + str(data[0]['group'])+ ';\n'

            if lang == 'magma':
                code += code_list['group_construct'][lang] + '\n'


            for k in same_for_all:
                code += code_list[k][lang] + str(data[0][k])+ ';\n'
        
            for k in other_same_for_all:
                code += code_list[k][lang] + '\n'

            code += '\n'

            # create formatting templates to be filled in with each record in data
            startstr = s + ' Here we add an action to data.\n'
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


            code +='\n'

    print "%s seconds for %d bytes" %(time.time() - start,len(code))
    strIO = StringIO.StringIO()
    strIO.write(code)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

