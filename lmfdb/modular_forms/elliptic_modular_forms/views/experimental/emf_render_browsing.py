# -*- coding: utf8 -*-
from lmfdb.utils import to_dict, image_src
from sage.all import dimension_new_cusp_forms, dimension_cusp_forms, dimension_eis, dimension_modular_forms, Zmod, DirichletGroup, latex
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf, EMF_TOP, N_max_Gamma0_fdraw, N_max_Gamma1_fdraw
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_core import get_geometric_data
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import my_get, parse_range, extract_limits_as_tuple
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.modular_forms import MF_TOP
from lmfdb.modular_forms.elliptic_modular_forms import N_max_comp, k_max_comp, N_max_db, k_max_db
from flask import render_template, url_for, request, redirect, make_response, send_file
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_classes import ClassicalMFDisplay, DimensionTable
list_of_implemented_dims = ['new', 'cusp', 'modular', 'eisenstein']

try:
    from dirichlet_conrey import *
except:
    emf_logger.critical("Could not import dirichlet_conrey!")

met = ['POST', 'GET']


@emf.route("/TablesMF/", methods=met)
@emf.route("/TablesMF/<int:nrows>/<int:ncols>/", methods=met)
def draw_table(nrows=None, ncols=None, **kwds):
    if request.method == 'GET':
        info = to_dict(request.args)
    else:
        info = to_dict(request.form)
    ncols = my_get(info, 'ncols', ncols, int)
    nrows = my_get(info, 'nrows', nrows, int)
    if nrows is None or ncols is None:
        return emf_error("Please supply level weight (and optional character)!"), 500
    ttype = my_get(info, 'ttype', 'new', str)
    ttype = my_get(kwds, 'ttype', info.get('ttype'), str)
    info = to_dict(kwds)
    ttype = my_get(kwds, 'ttype', 'new', str)
    info['title'] = 'Title of table'
    info['ttype'] = ttype
    info['nrows'] = nrows
    info['ncols'] = ncols
    return render_template("emf_table2.html", **info)


@emf.route("/DimensionMF/", methods=met)
@emf.route("/DimensionMF/<int:level>/<int:weight>/<int:chi>", methods=met)
def return_dimension(level=None, weight=None, chi=None, **kwds):
    if request.method == 'GET':
        info = to_dict(request.args)
    else:
        info = to_dict(request.form)
    level = my_get(info, 'level', level, int)
    weight = my_get(info, 'weight', weight, int)
    chi = my_get(info, 'chi', chi, int)
    if level is None or weight is None:
        return emf_error("Please supply level weight (and optional character)!"), 500
    ttype = my_get(kwds, 'ttype', info.get('ttype', 'new'), str)
    emf_logger.debug("level,weight,chi: {0},{1},{2}, type={3}".format(level, weight, chi, ttype))
    if chi == 0 or chi is None:
        x = level
    else:
        x = DirichletGroup(level).list()[chi]
    if ttype == 'new':
        return str(dimension_new_cusp_forms(x, weight))
    if ttype == 'cusp':
        return str(dimension_cusp_forms(x, weight))
    if ttype == 'modular':
        return str(dimension_modular_forms(x, weight))
    if ttype == 'eisenstein':
        return str(dimension_eis(x, weight))
    s = "Please use one of the available table types: 'new', 'cusp','modular', 'eisenstein' Got:{0}".format(
        ttype)
    return emf_error(s), 500


def emf_error(s):
    s = "ERROR: " + s
    s = "<span style='color:red;'>{0}</span>".format(s)
    emf_logger.critical(s)
    return s


@emf.route("/Tables/<int:level>/")
def render_table(level, **kwds):
    r"""
    Return a html table with appropriate dimensions.
    """
    nrows = my_get(kwds, 'nrows', 10, int)
    ncols = my_get(kwds, 'ncols', 10, int)
    ttype = my_get(kwds, 'ttype', 'newforms', str)


@emf.route("/ranges", methods=["GET"])
def browse_elliptic_modular_forms_ranges(**kwds):
    r"""
    Renders the webpage for browsing modular forms of given level and/or weight ranges.
    """
    emf_logger.debug("In browse_elliptic_modular_forms_ranges kwds: {0}".format(kwds))
    emf_logger.debug("args={0}".format(request.args))
    default = {}
    default['level'] = '1-12'
    default['weight'] = '2-36'
    default['character'] = 1
    info = dict()
    args = to_dict(request.args)
    emf_logger.debug("args={0}".format(args))
    for field in ['level', 'weight', 'character']:
        if args.get(field):
            info[field] = parse_range(args[field])
        else:
            info[field] = parse_range(default[field])
    if info['weight'] == 1:
        return render_template("not_available.html")
    elif (type(info['weight']) == dict) and info['weight'].get('min') == 1:
        info['weight']['min'] = 2
    emf_logger.debug("Input: info={0}".format(info))
    bread = [(MF_TOP, url_for('mf.modular_form_main_page'))]
    bread.append((EMF_TOP, url_for('emf.render_elliptic_modular_forms')))
    limits_weight = extract_limits_as_tuple(info, 'weight')
    limits_level = extract_limits_as_tuple(info, 'level')
    if limits_weight[0] == limits_weight[1] and limits_level[0] == limits_level[1]:
        return render_elliptic_modular_form_space_list_chars(limits_level[0], limits_weight[0])
    if limits_level[0] > N_max_db:
        emf_logger.debug("limits_level={0} > N_max_db={1}".format(limits_level, N_max_db))
        return render_template("not_available.html")
    if limits_weight[0] > k_max_db:
        emf_logger.debug("limits_weight={0} > k_max_db={1}".format(limits_weight, k_max_db))
        return render_template("not_available.html")
    if info['character'] == 0:
        info['grouptype'] = 0
        info['groupother'] = 1
        dimtbl = DimensionTable(0)
    else:
        info['grouptype'] = 1
        info['groupother'] = 0
        dimtbl = DimensionTable(1)
        if info['character'] == -1:
            info['show_all_characters'] = 1
    disp = ClassicalMFDisplay('modularforms')
    disp.set_table_browsing(limit=[limits_weight, limits_level],
                            keys=['Weight', 'Level'], character=info['character'], dimension_table=dimtbl, title='Dimension of newforms')
    tbl = disp._table
    if tbl is None:
        return render_template("not_available.html")
    else:
        info['browse_table'] = tbl
    if limits_level[0] == limits_level[1]:
        drawdomain = False
        level = limits_level[0]
        if info['grouptype'] == 0 and level <= N_max_Gamma0_fdraw:
            drawdomain = True
        elif level <= N_max_Gamma1_fdraw:
            drawdomain = True
        info['geometric'] = get_geometric_data(level, info['grouptype'])
        if drawdomain:
            info['fd_plot_url'] = url_for('emf.render_plot', level=level, grouptype=info['grouptype'])
        title = "Newforms for \(\Gamma_{0}({1})\)".format(info['grouptype'], level)
        level = int(level)
        # info['list_spaces']=ajax_more(make_table_of_spaces_fixed_level,*largs,text='more')
        bread.append(("Level %s" % level, url_for("emf.render_elliptic_modular_forms", level=level)))
        info['browse_type'] = " of level %s " % level
        info['title'] = title
        info['bread'] = bread
        info['level'] = level
        return render_template("emf_browse_fixed_level.html", **info)
    title = "Newforms for \(\Gamma_{0}(N)\)".format(info['grouptype'])
    info['browse_type'] = ""
    info['title'] = title
    info['bread'] = bread
    # info['level']=level
    return render_template("emf_navigation.html", info=info, title=title, bread=bread)


def browse_elliptic_modular_forms(level=0, weight=0, character=-1, label='', limits=None, **kwds):
    r"""
    Renders the webpage for browsing modular forms of given level and/or weight.
    """
    emf_logger.debug("In browse_elliptic_modular_forms kwds: {0}".format(kwds))
    emf_logger.debug(
        "Input: level={0},weight={1},character={2},label={3}".format(level, weight, character, label))
    bread = [(EMF_TOP, url_for('emf.render_elliptic_modular_forms'))]
    # if level <0:
    #    level=None
    # if weight<0:
    #    weight=None
    info = dict()
    drawdomain = False
    if character == 0:
        info['grouptype'] = 0
        info['groupother'] = 1
        dimtbl = DimensionTable(0)
        if level <= N_max_Gamma0_fdraw:
            drawdomain = True
    else:
        info['grouptype'] = 1
        info['groupother'] = 0
        if level <= N_max_Gamma1_fdraw:
            drawdomain = True
        dimtbl = DimensionTable(1)
        emf_logger.info("level=%s, %s" % (level, type(level)))
    emf_logger.info("wt=%s, %s" % (weight, type(weight)))
    if level > 0:
        info['geometric'] = get_geometric_data(level, info['grouptype'])
        # if info.has_key('plot'):
        if drawdomain:
            info['fd_plot_url'] = url_for('emf.render_plot', level=level, grouptype=info['grouptype'])
            emf_logger.info("PLOT: %s" % info['fd_plot_url'])
    if level > 0 and weight == 0:
        # print "here1!"
        title = "Newforms for \(\Gamma_{0}({1})\)".format(info['grouptype'], level)
        level = int(level)
        info['level_min'] = level
        info['level_max'] = level
        info['weight_min'] = 1
        info['weight_max'] = 20
        # largs = [ {'level':level,'character':character,'weight_block':k} for k in range(100)]
        disp = ClassicalMFDisplay('modularforms')
        disp.set_table_browsing(limit=[(2, 12), (level, level)], keys=['Weight', 'Level'],
                                character=character, dimension_table=dimtbl, title='Dimension of cusp forms')
        tbl = disp._table
        if tbl is not None:
            info['browse_table'] = tbl
        # info['list_spaces']=ajax_more(make_table_of_spaces_fixed_level,*largs,text='more')
        bread.append(("Level %s" % level, url_for("emf.render_elliptic_modular_forms", level=level)))
        info['browse_type'] = " of level %s " % level
        info['title'] = title
        info['bread'] = bread
        info['level'] = level
        return render_template("emf_browse_fixed_level.html", **info)
    elif level == 0 and weight > 0:
        title = "Newforms of weight %s " % weight
        bread.append(("Weight %s" % level, url_for("emf.render_elliptic_modular_forms", weight=weight)))
        level = int(weight)
        info['level_min'] = 1
        info['level_max'] = 20
        info['weight_min'] = weight
        info['weight_max'] = weight
        # largs = [ {'level':level,'character':character,'weight_block':k} for k in range(100)]
        # info['show_all_characters']=1
        disp = ClassicalMFDisplay('modularforms')
        disp.set_table_browsing(
            limit=[(weight, weight), (info['level_min'], info['level_max'])], keys=['Weight', 'Level'],
            character=character, dimension_table=dimtbl, title='Dimension of cusp forms')
        tbl = disp._table
        if tbl is not None:
            info['browse_table'] = tbl
        # info['list_spaces']=ajax_more(make_table_of_spaces_fixed_level,*largs,text='more')
        info['title'] = title
        info['bread'] = bread
        info['level'] = level
        return render_template("emf_navigation.html", info=info, title=title, bread=bread)
    emf_logger.debug("here2!")
    info['level_min'] = level
    info['level_max'] = level
    info['weight_min'] = weight
    info['weight_max'] = weight
    return render_elliptic_modular_form_space_list_chars(level, weight)


def render_elliptic_modular_form_space_list_chars(level, weight):
    r"""
    Renders a page with list of spaces of elliptic forms of given
    level and weight (list all characters)
    """
    emf_logger.debug(
        "In render_elliptic_modular_form_space_list_chars(level={0},weight={1})".format(level, weight))
    info = dict()
    # s = make_table_of_characters(level,weight)
    info['level'] = level
    info['weight'] = weight
    # if not isinstance(s,str):
    #    info['character'] = s
    #    return redirect(url_for("emf.render_elliptic_modular_forms", **info))
    # info['list_spaces']=s
    title = "Newforms of weight {0} for \(\Gamma_1({1})\)".format(weight, level)
    # bread =[(MF_TOP,url_for('mf.modular_form_main_page'))]
    bread = [(EMF_TOP, url_for('emf.render_elliptic_modular_forms'))]
    bread.append(("Level %s" % level, url_for("emf.render_elliptic_modular_forms", level=level)))
    bread.append(
        ("Weight %s" % weight, url_for("emf.render_elliptic_modular_forms", level=level, weight=weight)))
    # info['browse_type']=" of level %s and weight %s " % (level,weight)
    dimtbl = DimensionTable(1)
    info['grouptype'] = 1
    disp = ClassicalMFDisplay('modularforms')
    disp.set_table_browsing(limit=[(weight, weight), (level, level)], keys=['Weight', 'Level'],
                            character='all', dimension_table=dimtbl, title='Dimension of newforms')
    info['show_all_characters'] = 1
    info['browse_table'] = disp._table
    info['bread'] = bread
    info['title'] = title
    return render_template("emf_browse_fixed_level.html", **info)
#                           =info,title=title,bread=bread)


def make_table_of_dimensions(level_start=1, level_stop=50, weight_start=1, weight_stop=24, char=0, **kwds):
    r"""
    make an html table with information about spaces of modular forms
    with parameters in the given ranges. using a fixed character.
    Should use database in the future...
    """
    D = 0
    rowlen = 15  # split into rows of this length...
    rowlen0 = rowlen
    rowlen1 = rowlen
    characters = dict()
    level = 'N'
    weight = 'k'
    print "char=", char
    if level_start == level_stop:
        level = level_start
        count_min = weight_start
        count_max = weight_stop
        if (weight_stop - weight_start + 1) < rowlen:
            rowlen0 = weight_stop - weight_start + 1
    if weight_start == weight_stop:
        weight = weight_start
        count_min = level_start
        count_max = level_stop
        if (level_stop - level_start + 1) < rowlen:
            rowlen0 = level_stop - level_start + 1
    # else:
    #    return ""
    tbl = dict()
    if(char == 0):
        tbl['header'] = ''  # Dimension of \( S_{'+str(weight)+'}('+str(level)+',\chi_{n})\)'
        charst = ""
    else:
        # s = 'Dimension of \( S_{'+str(weight)+'}('+str(level)+')\)'
        # s += ' (trivial character)'
        charst = ",\chi_{%s}" % char
        tbl['header'] = ''
    tbl['headersv'] = list()
    tbl['headersh'] = list()
    if weight == 'k':
        tbl['corner_label'] = "weight \(k\):"
    else:
        tbl['corner_label'] = "level \(N\):"
    tbl['data'] = list()
    tbl['data_format'] = 'html'
    tbl['class'] = "dimension_table"
    tbl['atts'] = "border=\"1\" class=\"nt_data\" padding=\"25\" width=\"100%\""
    num_rows = ceil(QQ(count_max - count_min + 1) / QQ(rowlen0))
    print "num_rows=", num_rows
    for i in range(1, rowlen0 + 1):
        tbl['headersh'].append(i + count_min - 1)
    if level_start == level_stop:
        st = "Dimension of \(S_{k}(%s%s) \):" % (level, charst)
        tbl['headersv'] = [st]
    else:
        st = "Dimension of \(S_{%s}(N%s) \):" % (weight, charst)
        tbl['headersv'] = [st]
    tbl['headersv'].append('Link to space:')
    # make a dummy table first
    # num_rows = (num_rows-1)*2
    for r in range(num_rows * 2):
        row = []
        for k in range(1, rowlen0 + 1):
            row.append("")
        tbl['data'].append(row)
    tbl['data_format'] = dict()
    for k in range(0, rowlen0):
        tbl['data_format'][k] = 'html'

    print "nu_rows=", len(tbl['data'])
    print "num_cols=", rowlen0
    print "num_cols=", [len(r) for r in tbl['data']]
    for r in range(num_rows):
        for k in range(0, rowlen0):
            cnt = count_min + r * rowlen0 + k
            if level_start == level_stop:
                weight = cnt
            else:
                level = cnt
            url = url_for('emf.render_elliptic_modular_forms', level=level, weight=weight)
            if(cnt > count_max or cnt < count_min):
                tbl['data'][2 * r][k] = ""
                continue
            # s="<a name=\"#%s,%s\"></a>" % (level,weight)
            if(char == 0):
                d = dimension_cusp_forms(level, weight)
            else:
                x = DirichletGroup(level)[char]
                d = dimension_cusp_forms(x, weight)
            tbl['data'][2 * r][k] = str(d)
            if d > 0:
                s = "\(S_{%s}(%s)\)" % (weight, level)
                ss = "<a  href=\"" + url + "\">" + s + "</a>"
                tbl['data'][2 * r + 1][k] = ss
    s = html_table(tbl)
    # s=s+"\n <br> \(N="+str(rowlen0)+"\cdot row+col\)"
    # print "SS=",s
    return s
    # ss=re.sub('texttt','',s)
    # info['popup_table']=ss
        # info['sidebar']=set_sidebar([navigation,parents,siblings,friends,lifts])
        #   return info
