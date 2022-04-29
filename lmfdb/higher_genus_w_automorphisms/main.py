# -*- coding: utf-8 -*-
# This Blueprint is about higher genus curves
# Authors: Jen Paulhus, Lex Martin, David Neill Asanza, Nhi Ngo, Albert Ford
# (initial code copied from John Jones Local Fields)

import ast
import os
import re
from io import BytesIO
import yaml

from lmfdb.logger import make_logger
from flask import render_template, request, url_for, redirect, send_file, abort
from sage.all import Permutation

from lmfdb import db
from lmfdb.utils import (
    flash_error, to_dict,
    SearchArray, TextBox, ExcludeOnlyBox, CountBox,
    parse_ints, clean_input, parse_bracketed_posints, parse_gap_id,
    search_wrap, redirect_no_cache)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_parsing import (search_parser, collapse_ors)
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, ProcessedCol
from lmfdb.api import datapage
from lmfdb.sato_tate_groups.main import sg_pretty
from lmfdb.higher_genus_w_automorphisms import higher_genus_w_automorphisms_page
from lmfdb.higher_genus_w_automorphisms.hgcwa_stats import HGCWAstats
from collections import defaultdict

logger = make_logger("hgcwa")

#Parsing group order
LIST_RE = re.compile(r'^(\d+|(\d*-(\d+)?)|((\d*)\**(g((\+|\-)(\d*))*|\(g(\+|\-)(\d+)\))))(,(\d+|(\d*-(\d+)?)|((\d*)\**(g((\+|\-)(\d*))*|\(g(\+|\-)(\d+)\)))))*$')
GENUS_RE = re.compile(r'^(\d*)\**(g((\+|\-)(\d*))*|\(g(\+|\-)(\d+)\))$')

# Determining what kind of label
family_label_regex = re.compile(r'(\d+)\.(\d+-\d+)\.(\d+\.\d+-?[^\.]*$)')
passport_label_regex = re.compile(r'((\d+)\.(\d+-\d+)\.(\d+\.\d+.*))\.(\d+)')
vector_label_regex = re.compile(r'(\d+\.\d+-\d+\.\d+\.\d+.*)\.(\d+)\.(\d+)')
cc_label_regex = re.compile(r'((\d+)\.(\d+-\d+)\.(\d+)\.(\d+.*))\.(\d+)')
hgcwa_group = re.compile(r'\[(\d+),(\d+)\]')

def label_is_one_family(lab):
    return family_label_regex.match(lab)


def label_is_one_passport(lab):
    return passport_label_regex.match(lab)

def label_is_one_vector(lab):
    return vector_label_regex.match(lab)


def split_family_label(lab):
    return family_label_regex.match(lab).groups()

def split_passport_label(lab):
    return passport_label_regex.match(lab).groups()

def split_vector_label(lab):
    return vector_label_regex.match(lab).groups()

def get_bread(tail=[]):
    base = [("Higher genus", url_for(".index")),
            ("C", url_for(".index")),
            ("Aut", url_for(".index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Labeling convention', url_for(".labels_page"))]


# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def tfTOyn(b: bool):
    return "yes" if b else "no"


# Convert [4,1] to 4.1, then  apply sg_pretty
def group_display(strg):
    return sg_pretty(re.sub(hgcwa_group, r'\1.\2', strg))


def sign_display(L):
    sizeL = len(L)
    if sizeL == 1:
        signL = "[ " + str(L[0]) + "; -]"
    else:
        signL = "[ " + str(L[0]) + "; "
        for i in range(1, sizeL-1):
            signL = signL + str(L[i]) + ", "
        signL = signL + str(L[sizeL-1]) + " ]"
    return signL

def cc_display(L):
    sizeL = len(L)
    if sizeL == 0:
        return
    if sizeL == 1:
        return str(L[0])
    stg = str(L[0]) + ", "
    for i in range(1, sizeL-1):
        stg = stg + str(L[i])+", "
    stg = stg + str(L[sizeL-1])
    return stg


# for splitting permutations cycles
sep = ' '

def split_perm(strg):
    startpoint = 0
    for i in range(0, len(strg)):
        if strg[i] == ")":
            yield strg[startpoint:i+1]
            startpoint = i+1

def sort_sign(L):
    L1 = L[1:]
    L1.sort()
    return [L[0]] + L1

def label_to_breadcrumbs(L):
    newsig = '['+L[0]
    for i in range(1, len(L)):
        if (L[i] == '-'):
            newsig += ","
        elif (L[i] == '.'):
            newsig += ';'
        elif (L[i] == '0' and L[i-1] == '.'):  # The case where there is no ramification gives a 0 in signature
            newsig += '-'
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

# Turn 'i.j' in the total label in to cc displayed in mongo
def cc_to_list(cc):
    l = cc.split('.')
    return [int(l[1]), int(l[-1])]

@higher_genus_w_automorphisms_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=HGCWASearchArray())
    if request.args:
        return higher_genus_w_automorphisms_search(info)
    genus_max = db.hgcwa_passports.max('genus')
    genus_list = list(range(2, genus_max + 1))
    info['count'] = 50
    info['genus_list'] = genus_list
    info['short_summary'] = HGCWAstats().short_summary

    return render_template("hgcwa-index.html",
                           title="Families of higher genus curves with automorphisms",
                           bread=bread,
                           info=info,
                           learnmore=learnmore_list())


@higher_genus_w_automorphisms_page.route("/random")
@redirect_no_cache
def random_passport():
    label = db.hgcwa_passports.random(projection='passport_label')
    return url_for(".by_passport_label", passport_label=label)

@higher_genus_w_automorphisms_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "curve.highergenus.aut",
        db.hgcwa_passports,
        url_for_label,
        label_col="label",
        title=r"Some interesting higher genus families",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )

@higher_genus_w_automorphisms_page.route("/stats")
def statistics():
    title = 'Families of higher genus curves with automorphisms: Statistics'
    bread = get_bread('Statistics')
    return render_template("hgcwa-stats.html", info=HGCWAstats(), title=title, learnmore=learnmore_list(), bread=bread)


@higher_genus_w_automorphisms_page.route("/stats/groups_per_genus/<int:genus>")
def groups_per_genus(genus):
    un_grps = db.hgcwa_unique_groups
    # Redirect to 404 if statistic is not found
    if not un_grps.count({'genus':genus}):
        return abort(404, 'Group statistics for curves of genus %s not found in database.' % genus)

    info = {}
    gp_data = un_grps.search({'genus':genus},projection=['group','g0_is_gt0','g0_gt0_list','gen_vectors','topological','braid'],info=info)

    # Make list groups_0 where each entry is a list [ group, gen_vectors, tops, braids
    groups_0 = []
    # Make list groups_gt0 where each entry is a list [group, gen_vectors]
    groups_gt0 = []

    complete_info = db.hgcwa_complete.lucky({'genus':genus})
    show_top_braid = complete_info['top_braid_compute']
    show_g0_gt0 = complete_info['g0_gt0_compute']

    for dataz in gp_data:
        group = dataz['group']
        group_str = str(dataz['group'])
        iso_class = sg_pretty("%s.%s" % tuple(group))
        if dataz['g0_is_gt0']:
            groups_gt0.append((iso_class, group_str, dataz['gen_vectors'], cc_display(dataz['g0_gt0_list'])))
        elif not show_top_braid:
            groups_0.append((iso_class, group_str, dataz['gen_vectors']))
        else:
            groups_0.append((iso_class, group_str, dataz['gen_vectors'], dataz['topological'], dataz['braid']))

    info = {
        'genus': genus,
        'groups_0': groups_0,
        'groups_gt0': groups_gt0,
        'show_top_braid': show_top_braid,
        'show_g0_gt0': show_g0_gt0,
        'group_display': group_display
    }

    title = 'Families of higher genus curves with automorphisms: Genus %s group statistics' % genus
    bread = get_bread([('Statistics', url_for('.statistics')),
                       ('Groups per genus', url_for('.statistics')),
                       (str(genus), ' ')])

    return render_template("hgcwa-stats-groups-per-genus.html",
                           info=info,
                           title=title,
                           learnmore=learnmore_list(),
                           bread=bread)

def url_for_label(label):
    if label == "random":
        return url_for(".random_passport")
    return url_for(".by_label", label=label)

@higher_genus_w_automorphisms_page.route("/<label>")
def by_label(label):
    if label_is_one_passport(label):
        return render_passport({'passport_label': label})
    elif label_is_one_family(label):
        return render_family({'label': label})
    flash_error("No family with label %s was found in the database.", label)
    return redirect(url_for(".index"))


@higher_genus_w_automorphisms_page.route("/<passport_label>")
def by_passport_label(label):
    return render_passport({'passport_label': label})

cur_expr = None
cur_index = 0
#FIXME all these err is None should be done through raising exceptions

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
    if result is not None:
        cur_index -= 1
    return result

def expr_expect_char(char):
    actual_char = expr_getc()

    if actual_char != char:
        return expr_error("expected '" + char + "' here")
    else:
        return None

def read_num():
    num = ""
    c = expr_peekc()
    while c is not None and c.isdigit():
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
    if c is None:
        return (expr_error("expected factor here"), None)
    elif c.isdigit():
        return (None, read_num())
    elif is_letter(c):
        err, result = expect_var(vars)
        return err, result
    elif c == '(':
        expr_getc()
        err, result = expect_expr(vars)
        if err is not None:
            return (err, None)
        err = expr_expect_char(')')
        if err is not None:
            return (err, None)
        else:
            return (None, result)
    else:
        return (expr_error("'" + c + "' unexpected symbol"), None)

def expect_term(vars):
    err, result = expect_factor(vars)
    if err is not None:
        return (err, None)

    c = expr_peekc()
    while c is not None and (c.isdigit() or is_letter(c) or c == '('):
        err, factor_result = expect_factor(vars)
        if err is not None:
            return (err, None)
        result *= factor_result
        c = expr_peekc()

    return (None, result)

def expect_expr(vars):
    err, result = expect_term(vars)
    if err is not None:
        return (err, None)

    c = expr_peekc()
    while c == "+" or c == "-":
        expr_getc()
        err, term_result = expect_term(vars)
        if err is not None:
            return (err, None)
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

    if err is None:
        if expr_peekc() is not None:
            return (expr_error("unexpected symbol"), None)

    return (err, result)


def higher_genus_w_automorphisms_jump(info):
    labs = info['jump']
    if label_is_one_passport(labs):
        return render_passport({'passport_label': labs})
    elif label_is_one_family(labs):
        return render_family({'label': labs})
    flash_error("The label %s is not a legitimate label for this data.", labs)
    return redirect(url_for(".index"))


def hgcwa_code_download_search(info):
    import time
    lang = info.get('Submit')
    s = Comment[lang]
    filename = 'HigherGenusSearch' + FileSuffix[lang]
    code = s + " " + Fullname[lang] + " CODE FOR SEARCH RESULTS" + '\n' + '\n'
    code += s + " The results are stored in a list of records called 'data'"
    code += "\n\n"
    code += code_list['top_matter'][lang] + '\n' + '\n'
    code += "data:=[];" + '\n\n'

    res = list(db.hgcwa_passports.search(ast.literal_eval(info["query"])))
    # group results by label
    res_label = defaultdict(list)
    for row in res:
        res_label[row['label']].append(row)

    for label, data in res_label.items():
        code += s + " label = {}".format(label) + '\n'
        code += s + code_list['search_result_gp_comment'][lang] + '\n'
        code += code_list['group'][lang] + str(data[0]['group']) + ';\n'

        if lang == 'magma':
            code += code_list['group_construct'][lang] + '\n'

        for k in same_for_all:
            code += code_list[k][lang] + str(data[0][k]) + ';\n'

        for k in other_same_for_all:
            code += code_list[k][lang] + '\n'

        code += '\n'

        # create formatting templates to be filled in with each record in data
        startstr = s + ' Here we add an action to data.\n'
        stdfmt = ''
        for k in depends_on_action:
            stdfmt += code_list[k][lang] + '{' + k + '}' + ';\n'

        if lang == 'magma':
            stdfmt += code_list['con'][lang] + '{con}' + ';\n'

        stdfmt += code_list['gen_gp'][lang] + '\n'
        stdfmt += code_list['passport_label'][lang] + '{cc[0]}' + ';\n'
        stdfmt += code_list['gen_vect_label'][lang] + '{cc[1]}' + ';\n'

        # extended formatting template for when signH is present
        signHfmt = stdfmt
        signHfmt += code_list['full_auto'][lang] + '{full_auto}' + ';\n'
        signHfmt += code_list['full_sign'][lang] + '{signH}' + ';\n'
        signHfmt += code_list['add_to_total_full'][lang] + '\n'

        # additional info for hyperelliptic cases
        hypfmt = code_list['hyp'][lang] + code_list['tr'][lang] + ';\n'
        hypfmt += code_list['hyp_inv'][lang]
        hypfmt += '{hyp_involution}' + code_list['hyp_inv_last'][lang]
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
        code += '\n'

    logger.info("%s seconds for %d chars" % (time.time() - start, len(code)))
    strIO = BytesIO()
    strIO.write(code.encode('utf-8'))
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=filename,
                     as_attachment=True,
                     add_etags=False)


#Similar to parse_ints in lmfdb/utils
#Add searching with genus variable for group orders
def parse_range2_extend(arg, key, parse_singleton=int, parse_endpoint=None, instance=1):
    if parse_endpoint is None:
        parse_endpoint = parse_singleton
    if type(arg) == str:
        arg = arg.replace(' ', '')
    if type(arg) == parse_singleton:
        return [key, arg]
    if ',' in arg:
        instance = len(arg.split(','))
        tmp = [parse_range2_extend(a, key, parse_singleton, parse_endpoint, instance) for a in arg.split(',')]
        ret = []
        for a in tmp:
            if a[0] == key:
                if len(a) == 3:
                    ret.append({a[0]:a[1], 'genus': a[2]})
                else:
                    ret.append({a[0]:a[1]})
            else:
                for i in range(0, len(a)):
                    ret.append({a[i][0]: a[i][1], 'genus': a[i][2]})
        return ['$or', ret]
    elif 'g' in arg: # linear function of variable g (ax+b)
        if GENUS_RE.match(arg):
            a = GENUS_RE.match(arg).groups()[0]
            genus_list = db.hgcwa_passports.distinct('genus')
            genus_list.sort()
            min_genus = genus_list[0]
            max_genus = genus_list[-1]
            queries = []

            for g in range(min_genus,max_genus+1):
                if '(' in arg:
                    b = int(GENUS_RE.match(arg).groups()[6])
                    if '+' in arg: #a(g+b)
                        group_order = int(a)*(g+b)
                    elif '-' in arg: #a(g-b)
                        group_order = int(a)*(g-b)
                else:
                    if '+' in arg:
                        b = int(GENUS_RE.match(arg).groups()[4])
                        if a == '': #g+b
                            group_order = g+b
                        else: #ag+b
                            group_order = int(a)*g+b
                    elif '-' in arg:
                        b = int(GENUS_RE.match(arg).groups()[4])
                        if a == '': #g-b
                            group_order = g-b
                        else: #ag-b
                            group_order = int(a)*g-b
                    elif a== '':
                        group_order = g
                    else: #ag
                        group_order = int(a)*g

                queries.append((group_order, g))

            if instance == 1: #If there is only one linear function
                return ['$or', [{key: gp_ord, 'genus': g} for (gp_ord,g) in queries]]
            else:
                return [[key, gp_ord, g] for (gp_ord,g) in queries] #Nested list

        else:
            raise ValueError("It needs to be an integer (such as 25), \
                    a range of integers (such as 2-10 or 2..10), \
                    a linear function of variable g for genus \
                    (such as 84(g-1), 84g-84, 84g, or g-1), \
                    or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")

    elif '-' in arg and 'g' not in arg:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        q = {}
        if start:
            q['$gte'] = parse_endpoint(start)
        if end:
            q['$lte'] = parse_endpoint(end)
        return [key, q]
    else:
        return [key, parse_singleton(arg)]


@search_parser(clean_info=True, prep_ranges=True)
def parse_group_order(inp, query, qfield, parse_singleton=int):
    if LIST_RE.match(inp):
        collapse_ors(parse_range2_extend(inp, qfield, parse_singleton), query)
    else:
        raise ValueError("It needs to be an integer (such as 25), \
                    a range of integers (such as 2-10 or 2..10), \
                    a linear function of variable g for genus (such as 84(g-1), 84g-84, 84g, or g-1), \
                    or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")

hgcwa_columns = SearchColumns([
    LinkCol("passport_label", "dq.curve.highergenus.aut.label", "Refined passport label",
            lambda label: f"/HigherGenus/C/Aut/{label}",
            default=True),
    MathCol("genus", "ag.curve.genus", "Genus", default=True),
    MathCol("g0", "curve.highergenus.aut.quotientgenus", "Quotient genus"),
    ProcessedCol("group", "group.small_group_label", "Group", group_display, mathmode=True, align="center", default=True),
    MathCol("group_order", "group.order", "Group order", default=True),
    MathCol("dim", "curve.highergenus.aut.dimension", "Dimension", default=True),
    ProcessedCol("signature", "curve.highergenus.aut.signature", "Signature", lambda sig: sign_display(ast.literal_eval(sig)), default=True, mathmode=True)])
hgcwa_columns.languages = ['gap', 'magma']

@search_wrap(
    table=db.hgcwa_passports,
    title='Family of higher genus curves with automorphisms search results',
    err_title='Family of higher genus curves with automorphisms search input error',
    columns=hgcwa_columns,
    per_page=50,
    url_for_label=url_for_label,
    random_projection="passport_label",
    shortcuts={'jump': higher_genus_w_automorphisms_jump,
               'download': hgcwa_code_download_search },
    bread=lambda: get_bread("Search results"),
    learnmore=learnmore_list)
def higher_genus_w_automorphisms_search(info, query):
    if info.get('signature'):
        # allow for ; in signature
        info['signature'] = info['signature'].replace(';',',')
        parse_bracketed_posints(info,query,'signature',split=False,name='Signature',keepbrackets=True, allow0=True)
        if query.get('signature'):
            query['signature'] = info['signature'] = str(sort_sign(ast.literal_eval(query['signature']))).replace(' ','')
    parse_gap_id(info,query,'group',qfield='group')
    parse_ints(info,query,'g0')
    parse_ints(info,query,'genus')
    parse_ints(info,query,'dim')
    parse_group_order(info,query,'group_order')


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

    info['group_display'] = group_display
    info['sign_display'] = sign_display


def render_family(args):
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        dataz = list(db.hgcwa_passports.search({'label':label}))
        if not dataz:
            flash_error("No family with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        data = dataz[0]
        g = data['genus']
        g0 = data['g0']
        GG = ast.literal_eval(data['group'])
        gn = GG[0]
        gt = GG[1]

        gp_string = str(gn) + '.' + str(gt)
        pretty_group = sg_pretty(gp_string)

        if gp_string == pretty_group:
            spname = False
        else:
            spname = True
        title = 'Family of genus ' + str(g) + ' curves with automorphism group $' + pretty_group +'$'
        smallgroup="[" + str(gn) + "," +str(gt) + "]"

        prop2 = [
            ('Label', label),
            ('Genus', r'\(%d\)' % g),
            ('Quotient genus', r'\(%d\)' % g0),
            ('Group', r'\(%s\)' % pretty_group),
            ('Signature', r'\(%s\)' % sign_display(ast.literal_eval(data['signature'])))
        ]
        info.update({'genus': data['genus'],
                    'sign': sign_display(ast.literal_eval(data['signature'])),
                     'group': pretty_group,
                    'g0': data['g0'],
                    'dim': data['dim'],
                    'r': data['r'],
                    'gpid': smallgroup,
                    'numb': len(dataz)
                   })

        if spname:
            info.update({'specialname': True})

        Lcc=[]
        Lall=[]
        Ltopo_rep=[] #List of topological representatives
        for dat in dataz:
            if ast.literal_eval(dat['con']) not in Lcc:
                urlstrng = dat['passport_label']
                Lcc.append(ast.literal_eval(dat['con']))
                Lall.append([cc_display(ast.literal_eval(dat['con'])),dat['passport_label'],
                             urlstrng,dat['cc']])

            #Topological equivalence
            if 'topological' in dat:
                if dat['topological'] == dat['cc']:
                    x1 = [] #A list of permutations of generating vectors of topo_rep
                    for perm in dat['gen_vectors']:
                        x1.append(sep.join(split_perm(Permutation(perm).cycle_string())))
                    Ltopo_rep.append([dat['total_label'],
                                      x1,
                                      dat['label'],
                                      'T.' + '.'.join(str(x) for x in dat['cc']),
                                      dat['cc']]) #2nd to last element is used for webpage tag

        #Add topological equivalence to info
        info.update({'topological_rep': Ltopo_rep})
        info.update({'topological_num': len(Ltopo_rep)})

        info.update({'passport': Lall})
        info.update({'passport_num': len(Lall)})


        g2List = ['[2,1]', '[4,2]', '[8,3]', '[10,2]', '[12,4]', '[24,8]', '[48,29]']
        if g == 2 and data['group'] in g2List:
            g2url = "/Genus2Curve/Q/?geom_aut_grp_label=" + ".".join(data['group'][1:-1].split(','))
            friends = [(r"Genus 2 curves over $\Q$", g2url)]
        else:
            friends = []


        br_g, br_gp, br_sign = split_family_label(label)

        bread_sign = label_to_breadcrumbs(br_sign)
        bread_gp = label_to_breadcrumbs(br_gp)

        bread = get_bread([(br_g, './?genus='+br_g),
                           ('$'+pretty_group+'$',
                            './?genus='+br_g + '&group='+bread_gp),
                           (bread_sign,' ')])

        if len(Ltopo_rep) == 0 or len(dataz) == 1:
            downloads = [('Code to Magma', url_for(".hgcwa_code_download", label=label, download_type='magma')),
                         ('Code to Gap', url_for(".hgcwa_code_download", label=label, download_type='gap'))]
        else:
            downloads = [('Code to Magma', None),
                         (u'\u2003 All vectors', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
                         (u'\u2003 Up to topological equivalence', url_for(".hgcwa_code_download", label=label, download_type='topo_magma')),
                         ('Code to Gap', None),
                         (u'\u2003 All vectors', url_for(".hgcwa_code_download",  label=label, download_type='gap')),
                         (u'\u2003 Up to topological equivalence', url_for(".hgcwa_code_download", label=label, download_type='topo_gap'))]
        downloads.append(('Underlying data', url_for(".hgcwa_data", label=label)))
        return render_template("hgcwa-show-family.html",
                               title=title, bread=bread, info=info,
                               properties=prop2, friends=friends,
                               KNOWL_ID="curve.highergenus.aut.%s" % label,
                               learnmore=learnmore_list(), downloads=downloads)

@higher_genus_w_automorphisms_page.route("/data/<label>")
def hgcwa_data(label):
    if label_is_one_family(label):
        label_col = "label"
        title = f"Higher genus family - {label}"
    elif label_is_one_passport(label):
        label_col = "passport_label"
        title = f"Higher genus passport - {label}"
    else:
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    return datapage(label, "hgcwa_passports", title=title, bread=bread, label_cols=[label_col])

def render_passport(args):
    info = {}
    if 'passport_label' in args:
        label = clean_input(args['passport_label'])
        dataz = list(db.hgcwa_passports.search({'passport_label': label}))
        if not dataz:
            bread = get_bread([("Search Error", url_for('.index'))])
            flash_error("No refined passport with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        data=dataz[0]
        g = data['genus']
        g0=data['g0']
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
            numgenvecs = int(request.args['numgenvecs'])
            numbraidreps = int(request.args['numbraidreps'])
        except Exception:
            numgenvecs = 20
            numbraidreps = 20

        info['numgenvecs']=numgenvecs
        info['numbraidreps']=numbraidreps

        title = 'One refined passport of genus ' + str(g) + ' with automorphism group $' + pretty_group +'$'
        smallgroup="[" + str(gn) + "," +str(gt) +"]"

        prop2 = [
            ('Label', label),
            ('Genus', r'\(%d\)' % g),
            ('Quotient genus', r'\(%d\)' % g0),
            ('Group', r'\(%s\)' % pretty_group),
            ('Signature', r'\(%s\)' % sign_display(ast.literal_eval(data['signature']))),
            ('Generating Vectors', r'\(%d\)' % numb)
        ]
        info.update({'genus': data['genus'],
                    'cc': cc_display(data['con']),
                    'sign': sign_display(ast.literal_eval(data['signature'])),
                     'group': pretty_group,
                     'gpid': smallgroup,
                     'numb': numb,
                     'disp_numb': min(numb, numgenvecs),
                     'g0': data['g0']
                   })

        if spname:
            info.update({'specialname': True})

        Ldata = []
        HypColumn = False
        Lfriends = []
        Lbraid = []
        for i in range(0, min(numgenvecs,numb)):
            dat = dataz[i]
            x1 = dat['total_label']
            if 'full_auto' in dat:
                x2 = 'no'
                if dat['full_label'] not in Lfriends:
                    Lfriends.append(dat['full_label'])
            else:
                x2 = 'yes'

            if 'hyperelliptic' in dat:
                x3 = tfTOyn(dat['hyperelliptic'])
                HypColumn = True
            else:
                x3 = ' '

            x4 = []
            if dat['g0'] == 0:
                for perm in dat['gen_vectors']:
                    cycperm = Permutation(perm).cycle_string()
                    x4.append(sep.join(split_perm(cycperm)))

            elif dat['g0'] > 0:
                for perm in dat['gen_vectors']:
                    cycperm = Permutation(perm).cycle_string()
                    #if display_perm == '()':
                    if cycperm == '()':
                        x4.append('Id(G)')
                    else:
                        x4.append(sep.join(split_perm(cycperm)))
            Ldata.append([x1, x2, x3, x4])

        info.update({'genvects': Ldata, 'HypColumn': HypColumn})
        info.update({'passport_cc': cc_display(ast.literal_eval(data['con']))})

        #Generate braid representatives
        if 'braid' in dataz[0]:
            braid_data = [entry for entry in dataz if entry['braid'] == entry['cc']]
            for dat in braid_data:
                x5 = []
                for perm in dat['gen_vectors']:
                    x5.append(sep.join(split_perm(Permutation(perm).cycle_string())))
                Lbraid.append([dat['total_label'], x5])

        braid_length = len(Lbraid)

        #Add braid equivalence into info
        info.update({'braid': Lbraid,
                    'braid_numb': braid_length,
                    'braid_disp_numb': min(braid_length, numbraidreps)})

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
            full_G = ast.literal_eval(data['full_auto'])
            full_gn = full_G[0]
            full_gt = full_G[1]

            full_gp_string = str(full_gn) + '.' + str(full_gt)
            full_pretty_group = sg_pretty(full_gp_string)
            info.update({'fullauto': full_pretty_group,
                         'signH': sign_display(ast.literal_eval(data['signH'])),
                         'higgenlabel': data['full_label']})


        urlstrng, br_g, br_gp, br_sign, _ = split_passport_label(label)


        if Lfriends:
            friends = [("Full automorphism " + Lf, Lf) for Lf in Lfriends]
            friends += [("Family containing this refined passport ",  urlstrng)]
        else:
            friends = [("Family containing this refined passport",  urlstrng)]


        bread_sign = label_to_breadcrumbs(br_sign)
        bread_gp = label_to_breadcrumbs(br_gp)

        bread = get_bread([
            (br_g, './?genus='+br_g),
            ('$'+pretty_group+'$', './?genus='+br_g + '&group='+bread_gp),
            (bread_sign, urlstrng),
            (data['cc'][0], ' ')])

        if numb == 1 or braid_length == 0:
            downloads = [('Code to Magma', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
                     ('Code to Gap', url_for(".hgcwa_code_download", label=label, download_type='gap'))]

        else:
            downloads = [('Code to Magma', None),
                             (u'\u2003 All vectors', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
                             (u'\u2003 Up to braid equivalence', url_for(".hgcwa_code_download", label=label, download_type='braid_magma')),
                             ('Code to Gap', None),
                             (u'\u2003 All vectors', url_for(".hgcwa_code_download", label=label, download_type='gap')),
                             (u'\u2003 Up to braid equivalence', url_for(".hgcwa_code_download", label=label, download_type='braid_gap'))]
        downloads.append(('Underlying data', url_for(".hgcwa_data", label=label)))


        return render_template("hgcwa-show-passport.html",
                               title=title, bread=bread, info=info,
                               properties=prop2, friends=friends,
                               learnmore=learnmore_list(), downloads=downloads,
                               KNOWL_ID="curve.highergenus.aut.%s" % label)


# Generate topological webpage
@higher_genus_w_automorphisms_page.route("/<fam>/<cc>")
def topological_action(fam, cc):

    try:
        br_g, br_gp, br_sign = split_family_label(fam)
    except AttributeError:
        flash_error("Invalid family label: %s", fam)
        return redirect(url_for(".index"))

    try:
        cc_list = cc_to_list(cc)
    except IndexError:
        flash_error("Invalid topological action label: %s", cc)
        return redirect(url_for(".index"))

    representative = fam + '.' + cc[2:]

    # Get the equivalence class
    topo_class = list(db.hgcwa_passports.search({'label': fam, 'topological': cc_list}))
    if not topo_class:
        flash_error("No orbit in family with label %s and topological action %s was found in the database.", fam, cc)
        return redirect(url_for(".index"))

    GG = ast.literal_eval(topo_class[0]['group'])
    gn = GG[0]
    gt = GG[1]

    gp_string = str(gn) + '.' + str(gt)
    pretty_group = sg_pretty(gp_string)

    bread_sign = label_to_breadcrumbs(br_sign)
    bread_gp = label_to_breadcrumbs(br_gp)

    bread = get_bread(
        [(br_g, '../?genus=' + br_g),
         ('$%s$' % pretty_group, '../?genus=%s&group=%s' % (br_g, bread_gp)),
         (bread_sign, '../' + fam),
         ('Topological Orbit for %s, %s' % (cc_list[0], cc_list[1]), ' ')
        ]
    )

    title = 'One Orbit Under Topological Action'

    downloads = [('Download Magma code', url_for(".hgcwa_code_download",  label=representative, download_type='rep_magma')),
                      ('Download Gap code', url_for(".hgcwa_code_download", label=representative, download_type='rep_gap'))]

    Lbraid = {}

    for element in topo_class:
        if str(element['braid']) in Lbraid:
            Lbraid[str(element['braid'])].append(
                (element['passport_label'],
                 element['total_label'],
                 ' '))
            # We include the space so that we don't have duplicate conjugacy
            # classes displayed
        else:
            Lbraid[str(element['braid'])] = [
                (element['passport_label'],
                 element['total_label'],
                 cc_display(ast.literal_eval(element['con'])))]

    # Sort braid ascending
    key_for_sorted = sorted(ast.literal_eval(key) for key in Lbraid)
    sorted_braid = [Lbraid[str(key)] for key in key_for_sorted]

    info = {'topological_class': sorted_braid, 'representative': representative, 'braid_num': len(Lbraid)}

    return render_template("hgcwa-topological-action.html", info=info, title=title, bread=bread, downloads=downloads)


@higher_genus_w_automorphisms_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of higher genus curve with automorphisms data'
    bread = get_bread("Completeness")
    return render_template("single.html", kid='rcs.cande.curve.highergenus.aut',
                           title=t,
                           bread=bread,
                           learnmore=learnmore_list_remove('Completeness'))


@higher_genus_w_automorphisms_page.route("/Labels")
def labels_page():
    t = 'Labels for higher genus curves with automorphisms'
    bread = get_bread("Labels")
    return render_template("single.html", kid='dq.curve.highergenus.aut.label',
                           learnmore=learnmore_list_remove('Label'),
                           title=t,
                           bread=bread)


@higher_genus_w_automorphisms_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of higher genus curve with automorphisms data'
    bread = get_bread("Reliability")
    return render_template("single.html",
                           kid='rcs.rigor.curve.highergenus.aut',
                           title=t,
                           bread=bread,
                           learnmore=learnmore_list_remove('Reliability'))


@higher_genus_w_automorphisms_page.route("/Source")
def how_computed_page():
    t = 'Source of higher genus curve with automorphisms data'
    bread = get_bread("Source")
    return render_template("multi.html",
                           kids=['rcs.source.curve.highergenus.aut',
                                 'rcs.ack.curve.highergenus.aut',
                                 'rcs.cite.curve.highergenus.aut'],
                           title=t,
                           bread=bread,
                           learnmore=learnmore_list_remove('Source'))




_curdir = os.path.dirname(os.path.abspath(__file__))
code_list = yaml.load(open(os.path.join(_curdir, "code.yaml")), Loader=yaml.FullLoader)


same_for_all = ['signature', 'genus']
other_same_for_all = ['r', 'g0', 'dim', 'sym']
depends_on_action = ['gen_vectors']


Fullname = {'magma': 'Magma', 'gap': 'GAP'}
Comment = {'magma': '//', 'gap': '#'}
FileSuffix = {'magma': '.m', 'gap': '.g'}

@higher_genus_w_automorphisms_page.route("/<label>/download/<download_type>")
def hgcwa_code_download(**args):
    import time
    label = args['label']

    #Choose language
    if args['download_type'] == 'topo_magma' or args['download_type'] == 'braid_magma' or args['download_type']=='rep_magma':
        lang = 'magma'
    elif args['download_type'] == 'topo_gap' or args['download_type'] == 'braid_gap' or args['download_type']=='rep_gap':
        lang = 'gap'
    else:
        lang = args['download_type']

    s = Comment[lang]

    #Choose filename
    if lang == args['download_type']:
        filename= 'HigherGenusData_' + str(label) + FileSuffix[lang]
    elif args['download_type']=='topo_magma' or args['download_type']=='topo_gap':
        filename= 'HigherGenusDataTopolRep_' + str(label) + FileSuffix[lang]
    elif args['download_type']=='braid_magma' or args['download_type']=='braid_gap':
        filename= 'HigherGenusDataBraidRep_' + str(label) + FileSuffix[lang]
    elif args['download_type']=='rep_magma' or args['download_type']=='rep_gap':
        filename= 'HigherGenusDataTopolClass_' + str(label) + FileSuffix[lang]

    code = s + " " + Fullname[lang] + " code for the lmfdb family of higher genus curves " + str(label) + '\n'
    code += s + " The results are stored in a list of records called 'data'\n\n"
    code += code_list['top_matter'][lang] + '\n\n'
    code += "data:=[];" + '\n\n'


    if label_is_one_vector(label):
        fam, cc_1, cc_2 = split_vector_label(label)
        cc_list = [int(cc_1), int(cc_2)]
        search_data = list(db.hgcwa_passports.search({"label": fam}))
        data = [entry for entry in search_data if entry['topological'] == cc_list]

    elif label_is_one_passport(label):
        search_data = list(db.hgcwa_passports.search({"passport_label": label}))
        if lang == args['download_type']:
            data = search_data
        else:
            data = [entry for entry in search_data if entry['braid'] == entry['cc']]

    elif label_is_one_family(label):
        search_data = list(db.hgcwa_passports.search({"label": label}))
        if lang == args['download_type']:
            data = search_data
        else:
            data = [entry for entry in search_data if entry['topological'] == entry['cc']]

    code += s + code_list['gp_comment'][lang] + '\n'
    code += code_list['group'][lang] + str(data[0]['group']) + ';\n'

    if lang == 'magma':
        code += code_list['group_construct'][lang] + '\n'

    for k in same_for_all:
        code += code_list[k][lang] + str(data[0][k]) + ';\n'

    for k in other_same_for_all:
        code += code_list[k][lang] + '\n'

    code += '\n'

    # create formatting templates to be filled in with each record in data
    startstr = s + ' Here we add an action to data.\n'
    stdfmt = ''
    for k in depends_on_action:
        stdfmt += code_list[k][lang] + '{' + k + '}' + ';\n'

    if lang == 'magma':
        stdfmt += code_list['con'][lang] + '{con}' + ';\n'

    stdfmt += code_list['gen_gp'][lang] + '\n'
    stdfmt += code_list['passport_label'][lang] + '{cc[0]}' + ';\n'
    stdfmt += code_list['gen_vect_label'][lang] + '{cc[1]}' + ';\n'

    # Add braid and topological tag for each entry
    if lang == args['download_type'] and 'braid' in data[0]:
        stdfmt += code_list['braid_class'][lang] + '{braid[1]}' + ';\n'
        stdfmt += code_list['topological_class'][lang] + '{topological}' + ';\n'

    if args['download_type'] == 'rep_magma' or args['download_type'] == 'rep_gap':
        stdfmt += code_list['braid_class'][lang] + '{braid}' + ';\n'

    # extended formatting template for when signH is present
    signHfmt = stdfmt
    signHfmt += code_list['full_auto'][lang] + '{full_auto}' + ';\n'
    signHfmt += code_list['full_sign'][lang] + '{signH}' + ';\n'

    # additional info for hyperelliptic cases
    hypfmt = code_list['hyp'][lang] + code_list['tr'][lang] + ';\n'
    hypfmt += code_list['hyp_inv'][lang] + '{hyp_involution}' + code_list['hyp_inv_last'][lang]
    hypfmt += code_list['cyc'][lang] + code_list['fal'][lang] + ';\n'

    cyctrigfmt = code_list['hyp'][lang] + code_list['fal'][lang] + ';\n'
    cyctrigfmt += code_list['cyc'][lang] + code_list['tr'][lang] + ';\n'
    cyctrigfmt += code_list['cyc_auto'][lang] + '{cinv}' + code_list['hyp_inv_last'][lang]

    nhypcycstr = code_list['hyp'][lang] + code_list['fal'][lang] + ';\n'
    nhypcycstr += code_list['cyc'][lang] + code_list['fal'][lang] + ';\n'

    #Action for all vectors and action for just representatives
    if lang == args['download_type'] or \
        args['download_type'] == 'rep_magma' or \
        args['download_type'] == 'rep_gap':
        signHfmt += code_list['add_to_total_full_rep'][lang] + '\n'
        hypfmt += code_list['add_to_total_hyp_rep'][lang] + '\n'
        cyctrigfmt += code_list['add_to_total_cyc_trig_rep'][lang] + '\n'
        nhypcycstr += code_list['add_to_total_basic_rep'][lang] + '\n'
    else:
        signHfmt += code_list['add_to_total_full'][lang] + '\n'
        hypfmt += code_list['add_to_total_hyp'][lang] + '\n'
        cyctrigfmt += code_list['add_to_total_cyc_trig'][lang] + '\n'
        nhypcycstr += code_list['add_to_total_basic'][lang] + '\n'

    start = time.time()
    lines = [(startstr + (signHfmt if 'signH' in dataz else (stdfmt + (hypfmt if (dataz.get('hyperelliptic') and dataz['hyperelliptic']) else cyctrigfmt if (dataz.get('cyclic_trigonal') and dataz['cyclic_trigonal']) else nhypcycstr)))).format(**dataz) for dataz in data]
    code += '\n'.join(lines)
    logger.info("%s seconds for %d chars" % (time.time() - start, len(code)))
    strIO = BytesIO()
    strIO.write(code.encode('utf-8'))
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=filename,
                     as_attachment=True,
                     add_etags=False)

class HGCWASearchArray(SearchArray):
    noun = "passport"
    plural_noun = "passports"
    jump_example = "2.12-4.0.2-2-2-3"
    jump_egspan = "e.g. 2.12-4.0.2-2-2-3 or 3.168-42.0.2-3-7.2"
    jump_knowl = "curve.highergenus.aut.search_input"
    jump_prompt = "Label"
    def __init__(self):
        genus = TextBox(
            name="genus",
            label="Genus",
            knowl="ag.curve.genus",
            example="3",
            example_span="4, or a range like 3..5")
        g0 = TextBox(
            name="g0",
            label="Quotient genus",
            knowl="curve.highergenus.aut.quotientgenus",
            example="0",
            example_span="4, or a range like 3..5")
        signature = TextBox(
            name="signature",
            label="Signature",
            knowl="curve.highergenus.aut.signature",
            example="[0,2,3,3,6]",
            example_span="[0,2,3,3,6] or [0;2,3,8]")
        group_order = TextBox(
            name="group_order",
            label="Group order",
            knowl="group.order",
            example="2..5",
            example_span="12, or a range like 10..20, or you may include the variable g for genus like 84(g-1)")
        group = TextBox(
            name="group",
            label="Group identifier",
            knowl="group.small_group_label",
            example="[4,2]")
        dim = TextBox(
            name="dim",
            label="Dimension of the family",
            knowl="curve.highergenus.aut.dimension",
            example="1",
            example_span="1, or a range like 0..2")
        inc_hyper = ExcludeOnlyBox(
            name="inc_hyper",
            label="Hyperelliptic curves",
            knowl="ag.hyperelliptic_curve")
        inc_cyc_trig = ExcludeOnlyBox(
            name="inc_cyc_trig",
            label="Cyclic trigonal curves",
            knowl="ag.cyclic_trigonal")
        inc_full = ExcludeOnlyBox(
            name="inc_full",
            label="Full automorphism group",
            knowl="curve.highergenus.aut.full")
        count = CountBox()

        self.browse_array = [
            [genus],
            [g0],
            [signature],
            [group_order],
            [group],
            [dim],
            [inc_hyper],
            [inc_cyc_trig],
            [inc_full],
            [count]]

        self.refine_array = [
            [genus, dim, group_order, inc_hyper, inc_full],
            [g0, signature, group, inc_cyc_trig]]

    sort_knowl = "curve.highergenus.aut.sort_order"
    sorts = [("", "genus", ['genus', 'group_order',  'g0', 'dim']),
             ("g0", "quotient genus", ['g0', 'genus', 'group_order', 'dim']),
             ("group_order", "group order", ['group_order', 'group', 'genus', 'g0', 'dim']),
             ("dim", "dimension", ['dim', 'genus', 'group_order', 'g0'])]
