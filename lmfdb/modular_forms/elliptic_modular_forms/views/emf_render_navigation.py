r"""

Routines for rendering the navigation.


"""
import json
from flask import url_for,render_template,request
from lmfdb.utils import to_dict
from lmfdb.base import getDBConnection
from lmfdb.modular_forms import MF_TOP
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import extract_limits_as_tuple


def _browse_web_modform_spaces_in_ranges(**kwds):
    return render_elliptic_modular_form_navigation_wp(**kwds)

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



def render_elliptic_modular_form_navigation_wp(**args):
    r"""
    Renders the webpage for the navigational page.

    """
    from sage.all import is_even
    info = to_dict(args)
    args = to_dict(request.args)
    info.update(args)
    form = to_dict(request.form)
    info.update(form)
    emf_logger.debug("render_c_m_f_n_wp info={0}".format(info))
    level = my_get(info, 'level', 0, int)
    weight = my_get(info, 'weight', 0, int)
    character = my_get(info, 'character', 1, int)
    label = info.get('label', '')
    #disp = ClassicalMFDisplay('modularforms2')
    emf_logger.debug("info={0}".format(info))
    emf_logger.debug("level=%s, %s" % (level, type(level)))
    emf_logger.debug("label=%s, %s" % (label, type(label)))
    emf_logger.debug("wt=%s, %s" % (weight, type(weight)))
    emf_logger.debug("character=%s, %s" % (character, type(character)))
    if('plot' in info and level is not None):
        return render_fd_plot(level, info)
    is_set = dict()
    is_set['weight'] = False
    is_set['level'] = False
    if weight != 0:
        is_set['weight'] = True
    if level != 0:
        is_set['level'] = True
    ## This is the list of weights we initially put on the form
    weight = int(weight)
    title = "Holomorphic Cusp Forms"
    bread = [(MF_TOP, url_for('mf.modular_form_main_page'))]
    limits_weight = extract_limits_as_tuple(info, 'weight')
    limits_level = extract_limits_as_tuple(info, 'level')
    if limits_weight[0] == limits_weight[1] and limits_level[0] == limits_level[1]:
        return render_elliptic_modular_form_space_list_chars(limits_level[0], limits_weight[0])
    if is_set['weight']:
        limits_weight = (weight, weight)
    else:
        if character == 1:
            limits_weight = (2, 12)
        else:
            limits_weight = (2, 12)
    if is_set['level']:
        limits_level = (level, level)
    else:
        limits_level = (1, 24)
    if character == 1:
        info['grouptype'] = 0; info['groupother'] = 1
    else:
        info['grouptype'] = 1; info['groupother'] = 0
    info['show_switch'] = True
    db = getDBConnection()['modularforms2']['webmodformspace_dimension']
    table = {}
    if character == 1:
        q = db.find_one({'group':'gamma0'})
        if q:
            table = q.get('data',{})
    else:
        q = db.find_one({'group':'gamma1'})
        if q:
            table = q.get('data',{})
    if table <> {}:
        table = json.loads(table)
    info['table'] = {}
    
    level_range = range(limits_level[0],limits_level[1]+1)
    weight_range = range(limits_weight[0],limits_weight[1]+1)
    #print "levels=",level_range
    #print "weights=",weight_range
    if character == 1:
        weight_range = filter(is_even,weight_range)
        for n in level_range:
            info['table'][n]={}
            sn = unicode(n)
            for k in weight_range:
                info['table'][n][k]={}
                sk = unicode(k)
                if table.has_key(sn):
                    if table[sn].has_key(sk):
                        info['table'][n][k] = table[sn][sk] #.get(str(n),{}).get(str(k),"n/a")
    else:
        for n in level_range:
            info['table'][n]={}
            for k in weight_range:
                info['table'][n][k] = table.get(str(n),{}).get(str(k),"{}").get(str(character),"n/a")
    #print "table=\n",table
    #print "info=\n",info
    #info['table']=table
    info['col_heads'] = level_range
    info['row_heads'] = weight_range
    return render_template("emf_browse_spaces.html", info=info, title=title, bread=bread)

    
