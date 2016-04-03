r"""

Routines for rendering the navigation.


"""
import json
from flask import url_for,render_template,request,redirect
from lmfdb.utils import to_dict
from lmfdb.search_parsing import parse_range
from lmfdb.base import getDBConnection
from lmfdb.modular_forms import MF_TOP
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf,EMF_TOP,emf_version
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import extract_limits_as_tuple

def _browse_web_modform_spaces_in_ranges(**kwds):
    r"""
    Renders the webpage for browsing modular forms of given level and/or weight ranges.
    """
    return render_elliptic_modular_form_navigation_wp(**kwds)
    emf_logger.debug("In browse_elliptic_modular_forms_ranges kwds: {0}".format(kwds))
    emf_logger.debug("args={0}".format(request.args))
    level = kwds.get('level',int(1))
    if level is None or isinstance(level,int):
        pass
    default = {}
    default['level'] = '1-12'
    default['weight'] = '2-36'
    default['character'] = 1
    info = dict()
    args = to_dict(request.args)
    emf_logger.debug("args={0}".format(args))
    for field in ['level', 'weight', 'character']:
        if args.get(field):
            info[field] = parse_range(args[field],use_dollar_vars=True)
        else:
            info[field] = parse_range(default[field],use_dollar_vars=True)
    if info['weight'] == 1:
        return render_template("not_available.html")
    elif (type(info['weight']) == dict) and info['weight'].get('min') == 1:
        info['weight']['min'] = 2
    emf_logger.debug("Input: info={0}".format(info))
    bread = [(MF_TOP, url_for('mf.modular_form_main_page'))]
    bread.append((EMF_TOP, url_for('emf.render_elliptic_modular_forms')))
    limits_weight = extract_limits_as_tuple(info, 'weight')
    limits_level = extract_limits_as_tuple(info, 'level')
    # Special case: if the range reduces to a singleton for both level
    # and weight then we return a single page rather than a table:
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



def render_elliptic_modular_form_navigation_wp1(**args):
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
    group = my_get(info, 'group', 1, int)
    if group == int(0):
      pass
    character = my_get(info, 'character', 1, int)
    label = info.get('label', '')
    #disp = ClassicalMFDisplay('modularforms2')
    emf_logger.debug("info={0}".format(info))
    emf_logger.debug("level=%s, %s" % (level, type(level)))
    emf_logger.debug("label=%s, %s" % (label, type(label)))
    emf_logger.debug("wt=%s, %s" % (weight, type(weight)))
    emf_logger.debug("character=%s, %s" % (character, type(character)))
    emf_logger.debug("group=%s, %s" % (group, type(group)))
    if('plot' in info and level is not None):
        return render_fd_plot(level, info)
    is_set = dict()
    is_set['weight'] = False
    is_set['level'] = False
    limits_weight = extract_limits_as_tuple(info, 'weight')
    limits_level = extract_limits_as_tuple(info, 'level')
    if isinstance(weight,int) and weight > 0:
        is_set['weight'] = True
        weight = int(weight)
    else:
       weight = None
       info.pop('weight',None)
    if isinstance(level,int) and level > 0:
        is_set['level'] = True
        level = int(level)
    else:
        level = None
        info.pop('level',None)
    ## This is the list of weights we initially put on the form
    title = "Holomorphic Cusp Forms"
    bread = [(MF_TOP, url_for('mf.modular_form_main_page')),
             (title, url_for('.render_elliptic_modular_forms'))]

    limits_weight = extract_limits_as_tuple(info, 'weight')
    limits_level = extract_limits_as_tuple(info, 'level')
    # Special case: if the range reduces to a singleton for both level
    # and weight then we return a single page rather than a table:
    if limits_weight[0] == limits_weight[1] and limits_level[0] == limits_level[1]:
        return render_elliptic_modular_form_space_list_chars(limits_level[0], limits_weight[0])
    if is_set['weight']:
        limits_weight = (weight, weight)
    elif limits_weight is None:
        limits_weight = (2, 12) # default values
    if is_set['level']:
        limits_level = (level, level) 
    elif limits_level is None:
        limits_level = (1, 24) # default values
    try:
        group = info.get('group',0) # default group is gamma_0
        group = int(group)
    except ValueError: 
        group = 0
    if group not in [0,1]:
        group = 0
    if group == 0:
        info['grouptype'] = 0; info['groupother'] = 1
    else:
        info['grouptype'] = 1; info['groupother'] = 0
    emf_logger.debug("level:{0},level_range={1}".format(level,limits_level))
    emf_logger.debug("weight:{0},weight_range={1}".format(weight,limits_weight))

    if limits_weight[0] == limits_weight[1] and limits_level[0] == limits_level[1]:
        return redirect(url_for("emf.render_elliptic_modular_forms",
          level=limits_level[0],weight=limits_weight[0],group=group), code=301)
    info['show_switch'] = True
    db = getDBConnection()['modularforms2']['webmodformspace_dimension']
    table = {}
    q = db.find_one({'group':'gamma{0}'.format(group)})
    if q:
        table = q.get('data',{})
    if table != {}:
        table = json.loads(table)
    info['table'] = {}
    level_range = range(limits_level[0],limits_level[1]+1)
    # we don't have weight 1 in database
    if limits_weight[0]==1:
        limits_weight=(2,limits_weight[1])
    weight_range = range(limits_weight[0],limits_weight[1]+1)
    #print "levels=",level_range
    #print "weights=",weight_range
    if len(weight_range)>1:
        info['weight_range']="{0}-{1}".format(limits_weight[0],limits_weight[1])
    if len(level_range)>1:
        info['level_range']="{0}-{1}".format(limits_level[0],limits_level[1])
    if group == 0:
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
        emf_logger.debug("Set table for Gamma1")
        for n in level_range:
            info['table'][n]={}
            for k in weight_range:
                info['table'][n][k] = table.get(str(n),{}).get(str(k),{}).get(str(-1),"n/a")
    #print "table=\n",table
    #print "info=\n",info
    #info['table']=table
    info['col_heads'] = level_range
    info['row_heads'] = weight_range
    return render_template("emf_browse_spaces.html", info=info, title=title, bread=bread)

    


def render_elliptic_modular_form_navigation_wp(**args):
    r"""
    Renders the webpage for the navigational page.

    """
    from sage.all import is_even
    from lmfdb.modular_forms.elliptic_modular_forms import WebModFormSpace
    dimension_table_name = WebModFormSpace._dimension_table_name
  
    info = to_dict(args)
    args = to_dict(request.args)
    info.update(args)
    form = to_dict(request.form)
    info.update(form)
    emf_logger.debug("render_c_m_f_n_wp info={0}".format(info))
    level = my_get(info, 'level', None, int)
    weight = my_get(info, 'weight', None, int)
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
    limits_weight = extract_limits_as_tuple(info, 'weight')
    limits_level = extract_limits_as_tuple(info, 'level')
    if isinstance(weight,int) and weight > 0:
        is_set['weight'] = True
        weight = int(weight)
    else:
       weight = None
       info.pop('weight',None)
    if isinstance(level,int) and level > 0:
        is_set['level'] = True
        level = int(level)
    else:
        level = None
        info.pop('level',None)
    ## This is the list of weights we initially put on the form
    title = "Holomorphic Cusp Forms"
    bread = [(MF_TOP, url_for('mf.modular_form_main_page'))]
    bread.append((EMF_TOP, url_for('.render_elliptic_modular_forms')))
    if is_set['weight']:
        limits_weight = (weight, weight)
    elif limits_weight is None:
        limits_weight = (2, 12) # default values
    if is_set['level']:
        limits_level = (level, level) 
    elif limits_level is None:
        limits_level = (1, 24) # default values
    try:
        group = info.get('group',0) # default group is gamma_0
        group = int(group)
    except ValueError: 
        group = 0
    if group not in [0,1]:
        group = 0
    if group == 0:
        info['grouptype'] = 0; info['groupother'] = 1
    else:
        info['grouptype'] = 1; info['groupother'] = 0
    emf_logger.debug("group=%s, %s" % (group, type(group)))
    emf_logger.debug("level:{0},level_range={1}".format(level,limits_level))
    emf_logger.debug("weight:{0},weight_range={1}".format(weight,limits_weight))    
    # Special case: if the range reduces to a singleton for both level
    # and weight then we return a single page rather than a table:
    if limits_weight[0] == limits_weight[1] and limits_level[0] == limits_level[1]:
        return redirect(url_for("emf.render_elliptic_modular_forms",
          level=limits_level[0],weight=limits_weight[0],group=group), code=301)
    info['show_switch'] = True
    emf_logger.debug("dimension table name={0}".format(dimension_table_name))
    db_dim = getDBConnection()['modularforms2'][dimension_table_name]
    s = {'level':{"$lt":int(limits_level[1]+1),"$gt":int(limits_level[0]-1)},
         'weight' : {"$lt":int(limits_weight[1]+1),"$gt":int(limits_weight[0]-1)}}
    if group == 0:
        s['cchi']=int(1)        
    else:
        s['gamma1_label']={"$exists":True}
    g = db_dim.find(s).sort([('level',int(1)),('weight',int(1))])
    table = {}
    info['table'] = {}
    level_range = range(limits_level[0],limits_level[1]+1)
    # we don't have weight 1 in database
    if limits_weight[0]==1:
        limits_weight=(2,limits_weight[1])
    weight_range = range(limits_weight[0],limits_weight[1]+1)
    if group == 0:
        weight_range = filter(is_even,weight_range)
    if len(weight_range)>1:
        info['weight_range']="{0}-{1}".format(limits_weight[0],limits_weight[1])
    if len(level_range)>1:
        info['level_range']="{0}-{1}".format(limits_level[0],limits_level[1])
    for n in level_range:
        info['table'][n]={}
        for k in weight_range:
            info['table'][n][k]={'dim_new':int(0), 'in_db':-1}
    for r in db_dim.find(s):
        N = r['level']
        k = r['weight']
        if group != 0 or k%2==0:
            #emf_logger.debug("Found:k={0},N={1}".format(k,N))
            dim = r['d_newf'] # dimension of newforms
            info['table'][N][k]['dim_new'] = dim
            if group == 0:
                indb = r['in_wdb'] # 1 if it is in the webmodforms db else 0
            else:
                indb = r.get('one_in_wdb',0) # 1 if it is in the webmodforms db else 0
                if dim == 0:
                    indb = 1
            info['table'][N][k]['in_db'] = indb
    info['col_heads'] = level_range
    info['row_heads'] = weight_range
    return render_template("emf_browse_spaces.html", info=info, title=title, bread=bread)

    
