# -*- coding: utf-8 -*-
r"""
Routines for rendering the navigation.
"""
from flask import url_for,render_template,request,redirect
from lmfdb.utils import to_dict
from lmfdb.base import getDBConnection
from lmfdb.modular_forms import MF_TOP
from lmfdb.modular_forms.backend.mf_utils import my_get
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger, EMF_TOP
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import extract_limits_as_tuple, render_fd_plot

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
    # character = my_get(info, 'character', 1, int) # not used
    # label = info.get('label', '') # not used
    if('plot' in info and isinstance(level,int) and level > 0):
        return render_fd_plot(level, info)
    is_set = dict()
    is_set['weight'] = False
    is_set['level'] = False
    limits_weight = extract_limits_as_tuple(info, 'weight')
    limits_level = extract_limits_as_tuple(info, 'level')
    title = "Holomorphic Cusp Forms"
    bread = [(MF_TOP, url_for('mf.modular_form_main_page')), (EMF_TOP, url_for('.render_elliptic_modular_forms'))]
    if isinstance(level,int) and level > 0:
        is_set['level'] = True
        level = int(level)
        bread.append(('Level %d'%level, url_for('emf.render_elliptic_modular_forms', level=level)))
        title += " of level %d"%level 
    else:
        level = None
        info.pop('level',None)
    if isinstance(weight,int) and weight > 0:
        is_set['weight'] = True
        weight = int(weight)
        bread.append(('Weight %d'%weight, url_for('emf.render_elliptic_modular_forms', level=level, weight=weight)))
        title += " of weight %d"%weight
    else:
       weight = None
       info.pop('weight',None)
    ## This is the list of weights we initially put on the form
    if is_set['weight']:
        limits_weight = (weight, weight)
    elif limits_weight is None:
        limits_weight = (2, 12) # default values
    # we don't have weight 1 in database, reset range here to exclude it
    if limits_weight[0]==1:
        limits_weight=(2,limits_weight[1])
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
    # Special case: if the range reduces to a singleton for both level
    # and weight then we return a single page rather than a table:
    if limits_weight[0] == limits_weight[1] and limits_level[0] == limits_level[1]:
        return redirect(url_for("emf.render_elliptic_modular_forms",
          level=limits_level[0],weight=limits_weight[0],group=group), code=301)
    info['show_switch'] = True
    db_dim = getDBConnection()['modularforms2'][dimension_table_name]
    s = {'level':{"$lt":int(limits_level[1]+1),"$gt":int(limits_level[0]-1)},
         'weight' : {"$lt":int(limits_weight[1]+1),"$gt":int(limits_weight[0]-1)}}
    if group == 0:
        s['cchi']=int(1)
    else:
        s['gamma1_label']={"$exists":True}
    info['table'] = {}
    level_range = range(limits_level[0],limits_level[1]+1)
    weight_range = range(limits_weight[0],limits_weight[1]+1)
    if group == 0:
        weight_range = filter(is_even,weight_range)
    if len(weight_range)>1:
        info['weight_range']="{0}-{1}".format(limits_weight[0],limits_weight[1])
    elif len(weight_range)==1:
        info['weight_range']="{0}".format(limits_weight[0])
    if len(level_range)>1:
        info['level_range']="{0}-{1}".format(limits_level[0],limits_level[1])
    if len(level_range)==1:
        info['level_range']="{0}".format(limits_level[0])        
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
    lm = [('History of modular forms', url_for(".holomorphic_mf_history"))]
    return render_template("emf_browse_spaces.html", info=info, title=title, bread=bread, learnmore=lm)
