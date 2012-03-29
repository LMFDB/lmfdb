# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
r"""
Main file for viewing elliptical modular forms.

AUTHOR: Fredrik Strömberg

"""
from flask import render_template, url_for, request, redirect, make_response,send_file,send_from_directory
import tempfile, os,re
from utils import ajax_more,ajax_result,make_logger,to_dict
from sage.all import *
from sage.modular.dirichlet import DirichletGroup
from base import app, db
from modular_forms.elliptic_modular_forms.backend.web_modforms import WebModFormSpace,WebNewForm
from modular_forms.elliptic_modular_forms.backend.emf_classes import ClassicalMFDisplay
from modular_forms import MF_TOP
from modular_forms.backend.mf_utils import my_get
from modular_forms.elliptic_modular_forms import EMF_TOP
from modular_forms.elliptic_modular_forms.backend.emf_core import * 
from modular_forms.elliptic_modular_forms.backend.emf_utils import *
from modular_forms.elliptic_modular_forms.backend.plot_dom import * 
from modular_forms.elliptic_modular_forms import EMF, emf_logger, emf
from emf_render_one_form import render_one_elliptic_modular_form#,get_qexp
from emf_render_elliptic_modular_form_space import render_elliptic_modular_form_space
from emf_render_browsing import *
import StringIO
logger = emf_logger

@emf.context_processor
def body_class():
  return { 'body_class' : EMF }

### Maximum values to be generated on the fly
N_max_comp = 100
k_max_comp = 30
### Maximum values from the database (does this make sense)
N_max_db = 1000000 
k_max_db = 300000

#################
# Top level
#################

###########################################
# Search / Navigate
###########################################

met = ['GET','POST']
@emf.route("/",methods=met)
@emf.route("/<int:level>/",methods=met)
@emf.route("/<int:level>/<int:weight>/",methods=met)
@emf.route("/<int:level>/<int:weight>/<int:character>/",methods=met)
@emf.route("/<int:level>/<int:weight>/<int:character>/<label>",methods=met)
@emf.route("/<int:level>/<int:weight>/<int:character>/<label>/",methods=met)
def render_elliptic_modular_forms(level=0,weight=0,character=None,label='',**kwds):
    r"""
    Default input of same type as required. Note that for holomorphic modular forms: level=0 or weight=0 are non-existent.
    """
    if character == None and level == 0 and weight == 0:
        character = 0
    elif character == None:
        character = -1
    emf_logger.debug("In render: level={0},weight={1},character={2},label={3}".format(level,weight,character,label))
    emf_logger.debug("args={0}".format(request.args))
    emf_logger.debug("args={0}".format(request.form))
    emf_logger.debug("met={0}".format(request.method))
    keys=['download','jump_to']
    info = get_args(request,level,weight,character,label,keys=keys)
    level=info['level']; weight=info['weight']; character=info['character']; label=info['label']
    emf_logger.debug("info={0}".format(info))
    emf_logger.debug("level=%s, %s"%(level,type(level)))
    emf_logger.debug("label=%s, %s"%(label,type(label)))
    emf_logger.debug("wt=%s, %s"% (weight,type(weight)) )
    emf_logger.debug("character=%s, %s"% (character,type(character)) )
    if info.has_key('download'):
        return get_downloads(**info)
    emf_logger.debug("info=%s"%info)
    ## Consistency of arguments>
    #if level<=0:  level=None
    #if weight<=0:  weight=None
    if info.has_key('jump_to'):  # try to find out which form we want to jump
        s = my_get(info,'jump_to','',str)
        emf_logger.info("info.keys1={0}".format(info.keys()) )        
        info.pop('jump_to')
        emf_logger.info("info.keys2={0}".format(info.keys()) )        
        args=extract_data_from_jump_to(s)
        emf_logger.debug("args=%s"%args)
        return redirect(url_for("emf.render_elliptic_modular_forms", **args), code=301)
        #return render_elliptic_modular_forms(**args)
    if level>0 and weight>0 and character>-1 and label<>'':
        return render_one_elliptic_modular_form(**info)
    if level>0 and weight>0 and character>-1:
        return render_elliptic_modular_form_space(**info)
    if level>0 and weight>0:
        return browse_elliptic_modular_forms(**info)
    if (level>0 and weight==0) or (weight>0 and level==0):
        emf_logger.debug("Have level or weight only!")
        return browse_elliptic_modular_forms(**info)
        #return render_elliptic_modular_form_navigation_wp(**info) 
    # Otherwise we go to the main navigation page
    return render_elliptic_modular_form_navigation_wp(**info)

# If we don't match any arglist above we see if we have only a label
@emf.route("/<test>/")
def redirect_false_route(test=None):
    args=extract_data_from_jump_to(s)
    redirect(url_for("render_elliptic_modular_forms", **args), code=301)
    #return render_elliptic_modular_form_navigation_wp(**info)


def get_args(request,level=0,weight=0,character=-1,label='',keys=[]):    
    r"""
    Use default input of the same type as desired output.
    """
    if request.method == 'GET':
        dd = to_dict(request.args)
    else:
        dd = to_dict(request.form)
    info = dict()
    info['level']=my_get(dd,'level',level,int)
    info['weight']=my_get(dd,'weight',weight,int)
    info['character']=my_get(dd,'character',character,int)
    info['label']=my_get(dd,'label',label,str)
    for key in keys:
        if dd.has_key(key):
            info[key]=my_get(dd,key,'',str)
    return info


###
## The routines that renders the various parts
###

                
def render_elliptic_modular_form_navigation_wp(**args):
    r"""
    Renders the webpage for the navigational page.
    
    """
    emf_logger.debug("render_c_m_f_n_wp")
    info = to_dict(args)
    level  = my_get(info,'level', 0,int)
    weight = my_get(info,'weight', 0,int)
    character = my_get(info,'character',0,int)
    label  = info.get('label', '')
    disp = ClassicalMFDisplay('modularforms')
    emf_logger.debug("info={0}".format(info))
    emf_logger.debug("level=%s, %s"%(level,type(level)))
    emf_logger.debug("label=%s, %s"%(label,type(label)))
    emf_logger.debug("wt=%s, %s"% (weight,type(weight)) )
    emf_logger.debug("character=%s, %s"% (character,type(character)) )
    
    if(info.has_key('plot') and level <> None):
        return render_fd_plot(level,info)
    is_set=dict()
    is_set['weight']=False; is_set['level']=False
    if weight<>0:
        is_set['weight']=True
    if level<>0:
        is_set['level']=True
    if(info.has_key('get_table')): # we want a table
        info = set_table(info,is_set)
        page = "emf_table.html"
        title = "Table of spaces of elliptic modular forms"
        return render_template(page, info=info,title=title)
    ## This is the list of weights we initially put on the form
    weight = int (weight)
    title = "Holomorphic Cusp Forms"
    bread =[(MF_TOP,url_for('mf.modular_form_main_page'))]
    #  fun = dimension_new_cusp_forms
    #  title = 'Newforms'
    if is_set['weight']:
        wt_range=(weight,weight)
    else:
        if character == 0:
            wt_range=(2,36)
        else:
            wt_range=(2,20)
    if is_set['level']:
        level_range=(level,level)
    else:
        level_range=(1,20)
    if character==0:
        info['grouptype']=0
        info['groupother']=1
    else:
        info['grouptype']=1
        info['groupother']=0
    info['show_switch']=True
    disp.set_table_browsing(limit=[wt_range,level_range],
                            keys=['Weight','Level'],character=character,
                            dimension_fun=dimension_new_cusp_forms,title='Browse Holomorphic Modular Forms')
    info['browse_table']=disp._table

    return render_template("emf_navigation.html", info=info,title=title,bread=bread)

met = ['GET','POST']
@emf.route("/Download/<int:level>/<int:weight>/<int:character>/<label>",methods=['GET','POST'])

def get_downloads(level=None,weight=None,character=None,label=None,**kwds):
    keys=['download','download_file','tempfile','format','number']
    info = get_args(request,level,weight,character,label,keys=keys)
    #info = to_dict(request.form)
    #info['level']=level; info['weight']=weight; info['character']=character; info['label']=label
    if not info.has_key('download'):
        emf_logger.critical("Download called without specifying what to download!")
        return ""
    emf_logger.debug("in get_downloads: info={0}".format(info))
    if info['download']=='file':
        # there are only a certain number of fixed files that we want people to download
        filename=info['download_file']
        if filename=="web_modforms.py":
            dirname=emf.app.root_static_folder
            try:
                emf_logger.debug("Dirname:{0}, Filename:{1}".format(dirname,filename))
                return send_from_directory(dirname,filename, as_attachment=True,attachment_filename=filename)
            except IOError:
                info['error']="Could not find  file! "
    if info['download']=='coefficients':
        info['tempfile'] = "/tmp/tmp_web_mod_form.txt"
        return get_coefficients(info)
    if info['download']=='object':
        return download_web_modform(info)

        info['error']="Could not find  file! "
        #if label<>'':
        #    # download a function
        #    render_one_elliptic_modular_form_wp(info)
        #else:
        #    render_one_elliptic_modular_form_space_wp(info)
        #    # download a space

def get_coefficients(info):
    emf_logger.debug("IN GET_COEFFICIENTS!!!")
    level  = my_get(info,'level', -1,int)
    weight = my_get(info,'weight',-1,int) 
    character = my_get(info,'character', '',str) #int(info.get('weight',0))
    emf_logger.debug("info={0}".format(info))
    if character=='':
        character=0
    label  = info.get('label', '')
    # we only want one form or one embedding
    s = print_list_of_coefficients(info)
    info['filename']=str(weight)+'-'+str(level)+'-'+str(character)+'-'+label+'coefficients-0to'+info['number']+'.txt'
    #return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=info["filename"],
                     as_attachment=True)



def download_web_modform(info):
    emf_logger.debug("IN GET_WEB_MODFORM!!! info={0}".format(info))
    level  = my_get(info,'level', -1,int)
    weight = my_get(info,'weight',-1,int)
    character = my_get(info,'character', '',str) #int(info.get('weight',0))
    emf_logger.debug("info={0}".format(info))
    if character=='':
        character=0
    label  = info.get('label', '')
    # we only want one form or one embedding
    if label<>'':
        if format=='sage':
            if character<>0:
                D = DirichletGroup(level)
                x = D[character]
                X = Newforms(x,weight,names='a')
            else:
                X = Newforms(level,weight,names='a')
        else: # format=='web_new':
            X = WebNewForm(weight,level,character,label)
    s = X.dumps()
    name = "{0}-{1}-{2}-{3}-web_newform.sobj".format(weight,level,character,label)
    emf_logger.debug("name={0}".format(name))
    info['filename']=name
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    try:
        return send_file(strIO,
                         attachment_filename=info["filename"],
                         as_attachment=True)
    except IOError:
        info['error']="Could not send file!"

        



#return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
        
    # first check database.




######### OBSOLETE


## def make_table_of_characters(level,weight,**kwds):
##     r""" Make a table of spaces S_k(N,\chi) for all compatible characters chi.
##     """
##     if level>0:
##       D=DirichletGroup(level); l=D.list()
##     else:
##       D=list(); l=[]
##     #print "D=",D
##     s = "List of \(S_{%s} (%s, \chi_{n}) \)" %(weight,level)
##     s+="<a name=\"#"+str(level)+"\"></a>"
##     tbl=dict()
##     tbl['headersv']=['order of \(\chi_{n}\):','dimension:']
##     tbl['headersh']=list()
##     tbl['corner_label']="\( n \):"
##     tbl['data']=list()
##     tbl['atts']="class=\"nt_data\" border=\"0\" padding=\"25\""
##     tbl['data_format']='html'
##     row=list()
##     rowlen = 25
##     ii=0
##     dims = dict()
##     for chi in range(0,len(l)):
##         x=D[chi]; d=dimension_new_cusp_forms(x,weight)
##         dims[chi]=d
##     num_non_zero = (map(lambda x:  x>0,dims.values())).count(True)
##     print "Number of non_zer0",num_non_zero
##     if num_non_zero == 1:
##         d = max(dims.values())
##         chi = dims.keys()[dims.values().index(d)]
##         return chi
##     numrows = ceil(map(lambda x: x>0,dims).count(True)/rowlen)
##     tbl['col_width']=dict()
##     ci=0
##     for chi in range(0,len(l)):
##         d = dims[chi]
##         if d==0:
##             continue
##         tbl['headersh'].append(chi)
##         tbl['col_width'][ii]=["100"]
##         x = l[chi]
##         order = x.order()
##         #st = " %s (order %s) " %(chi,order)
##         ii=ii+1
##         row.append(order)
##         if(ii>rowlen and len(row)>0):
##             print "appending row:",row
##             tbl['data'].append(row)
##             s=s+html_table(tbl)
##             tbl['headersh']=list(); tbl['data']=list(); row=list()
##             ii=0
##     if(len(row)>0):
##         tbl['data'].append(row)
##         #if (len(row)>0 or len(tbl['data'])>0): 
##         #    ss=html_table(tbl)
##         #    s=s+ss

##     row = list()
##     ii=0
##     for chi in range(0,len(l)):
##         d = dims[chi]
##         if d==0:
##             continue
##         url = url_for('emf.render_elliptic_modular_forms',level=level,weight=weight,character=chi) 
##         row.append("<a href=\""+url+"\">"+str(d)+"</a>")
##         ii=ii+1
##         if(ii>rowlen and len(row)>0):
##             print "appending row:",row
##             tbl['data'].append(row)
##             s=s+html_table(tbl)
##             tbl['headersh']=list(); tbl['data']=list(); row=list()
##             ii=0

##     if(len(row)>0):
##         tbl['data'].append(row)
##         if (len(row)>0 or len(tbl['data'])>0): 
##             ss=html_table(tbl)
##             s=s+ss
##         else:
##             s="All spaces are zero-dimensional!"
##     return s

def make_table_of_dimensions(level_start=1,level_stop=50,weight_start=1,weight_stop=24,char=0,**kwds):
    r"""
    make an html table with information about spaces of modular forms
    with parameters in the given ranges. using a fixed character.
    Should use database in the future... 
    """
    D=0
    rowlen=15 # split into rows of this length...
    rowlen0 = rowlen
    rowlen1 = rowlen
    characters=dict()
    level = 'N' ; weight = 'k'
    print "char=",char
    if level_start == level_stop:
        level = level_start
        count_min = weight_start; count_max = weight_stop
        if (weight_stop-weight_start+1) < rowlen:
            rowlen0=weight_stop-weight_start+1
    if weight_start==weight_stop:
        weight = weight_start
        count_min = level_start; count_max = level_stop
        if (level_stop-level_start+1) < rowlen:
            rowlen0=level_stop-level_start+1
    #else:
    #    return ""
    tbl=dict()
    if(char==0):
        tbl['header']='' #Dimension of \( S_{'+str(weight)+'}('+str(level)+',\chi_{n})\)'
        charst=""
    else:
        #s = 'Dimension of \( S_{'+str(weight)+'}('+str(level)+')\)'
        #s += ' (trivial character)'
        charst=",\chi_{%s}" % char
        tbl['header']=''
    tbl['headersv']=list()
    tbl['headersh']=list()
    if weight=='k':
        tbl['corner_label']="weight \(k\):"
    else:
        tbl['corner_label']="level \(N\):"
    tbl['data']=list()
    tbl['data_format']='html'
    tbl['class']="dimension_table"
    tbl['atts']="border=\"1\" class=\"nt_data\" padding=\"25\" width=\"100%\""
    num_rows = ceil(QQ(count_max-count_min+1) / QQ(rowlen0))
    print "num_rows=",num_rows
    for i in range(1,rowlen0+1):
        tbl['headersh'].append(i+count_min-1)
    if level_start==level_stop:
        st = "Dimension of \(S_{k}(%s%s) \):" % (level,charst)
        tbl['headersv']=[st]
    else:
        st = "Dimension of \(S_{%s}(N%s) \):" % (weight,charst)
        tbl['headersv']=[st]
    tbl['headersv'].append('Link to space:')
    # make a dummy table first
    #num_rows = (num_rows-1)*2
    for r in range(num_rows*2):
        row=[]
        for k in range(1,rowlen0+1):
            row.append("")
        tbl['data'].append(row)                         
    tbl['data_format']=dict()
    for k in range(0,rowlen0):
        tbl['data_format'][k]='html'

    print "nu_rows=",len(tbl['data'])
    print "num_cols=",rowlen0
    print "num_cols=",[len(r) for r in tbl['data']]
    for r in range(num_rows):
        for k in range(0,rowlen0):
            cnt = count_min+r*rowlen0+k
            if level_start==level_stop:
                weight=cnt
            else:
                level=cnt
            url = url_for('emf.render_elliptic_modular_forms',level=level,weight=weight)
            if(cnt>count_max or cnt < count_min):
                tbl['data'][2*r][k]=""
                continue
            #s="<a name=\"#%s,%s\"></a>" % (level,weight)
            if(char==0):
                d=dimension_cusp_forms(level,weight)
            else:
                x = DirichletGroup(level)[char]
                d=dimension_cusp_forms(x,weight)
            tbl['data'][2*r][k]=str(d)
            if d>0:
                s = "\(S_{%s}(%s)\)" % (weight,level)
                ss = "<a  href=\""+url+"\">"+s+"</a>"
                tbl['data'][2*r+1][k]=ss
            #else:
            #    tbl['data'][2*r+1][k]="\(\emptyset\)"
            #    ss = make_table_of_characters(level,weight)
            #    tbl['data'][2*r+1][k]=ss
            #tbl['data'][r][k]=s
            #print "row=",row
            #tbl['data'][r]=row                 
    #print "tbl=",tbl
    s=html_table(tbl)
    #s=s+"\n <br> \(N="+str(rowlen0)+"\cdot row+col\)"
    #print "SS=",s
    return s
    #ss=re.sub('texttt','',s)
    #info['popup_table']=ss
        #info['sidebar']=set_sidebar([navigation,parents,siblings,friends,lifts])
        #   return info



def set_table(info,is_set,make_link=True): #level_min,level_max,weight=2,chi=0,make_link=True):
        r"""
        make a bunch of html tables with information about spaces of modular forms
        with parameters in the given ranges.
        Should use database in the future... 
        """
        D=0
        rowlen=10 # split into rows of this length...
        rowlen0 = rowlen
        rowlen1 = rowlen
        characters=dict()
        if(info.has_key('level_min')):
                level_min=int(info['level_min'])
        else:
                level_min=1
        if(info.has_key('level_max')):
                level_max=int(info['level_max'])
        else:
                level_max=50
        if (level_max-level_min+1) < rowlen:
                rowlen0=level_max-level_min+1
        if(info['list_chars']<>'0'):
                char1=1
        else:
                char1=0
        if(is_set['weight']):
                weight=int(info['weight'])
        else:
                weight=2
        ## setup the table
        #print "char11=",char1
        tbl=dict()
        if(char1==1):
                tbl['header']='Dimension of \( S_{'+str(weight)+'}(N,\chi_{n})\)'
        else:
                tbl['header']='Dimension of \( S_{'+str(weight)+'}(N)\)'
        tbl['headersv']=list()
        tbl['headersh']=list()
        tbl['corner_label']=""
        tbl['data']=list()
        tbl['data_format']='html'
        tbl['class']="dimension_table"
        tbl['atts']="border=\"0\" class=\"data_table\""
        num_rows = ceil(QQ(level_max-level_min+1) / QQ(rowlen0))
        print "num_rows=",num_rows
        for i in range(1,rowlen0+1):
                tbl['headersh'].append(i+level_min-1)

        for r in range(num_rows):
                tbl['headersv'].append(r*rowlen0)
        print "level_min=",level_min
        print "level_max=",level_max
        print "char=",char1
        for r in range(num_rows):
                row=list()
                for k in range(1,rowlen0+1):
                    row.append("")
                #print "row nr. ",r
                for k in range(1,rowlen0+1):
                        N=level_min-1+r*rowlen0+k
                        s="<a name=\"#"+str(N)+"\"></a>"
                        #print "col ",k,"=",N
                        if(N>level_max or N < 1):
                                continue
                        if(char1==0):
                                d=dimension_cusp_forms(N,weight)
                                print "d=",d
                                if(make_link):
                                        url="?weight="+str(weight)+"&level="+str(N)+"&character=0"
                                        row.append(s+"<a target=\"mainWindow\" href=\""+url+"\">"+str(d)+"</a>")
                                else:
                                        row.append(s+str(d))

                                #print "dim(",N,weight,")=",d
                        else:

                                D=DirichletGroup(N)
                                print "D=",D
                                s="<a name=\"#"+str(N)+"\"></a>"
                                small_tbl=dict()
                                #small_tbl['header']='Dimension of \( S_{'+str(weight)+'}(N)\)'
                                small_tbl['headersv']=['\( d \)']
                                small_tbl['headersh']=list()
                                small_tbl['corner_label']="\( n \)"
                                small_tbl['data']=list()
                                small_tbl['atts']="border=\"1\" padding=\"1\""
                                small_tbl['data_format']='html'
                                row1=list()
                                #num_small_rows = ceil(QQ(level_max) / QQ(rowlen))
                                ii=0
                                for chi in range(0,len(D.list())):
                                        x=D[chi]
                                        S=CuspForms(x,weight)
                                        d=S.dimension()
                                        if(d==0):
                                                continue
                                        small_tbl['headersh'].append(chi)
                                        if(make_link):
                                                url="?weight="+str(weight)+"&level="+str(N)+"&character="+str(chi)
                                                row1.append("<a target=\"mainWindow\" href=\""+url+"\">"+str(d)+"</a>")
                                        else:
                                                row1.append(d)
                                        ii=ii+1
                                        print "d=",d
                                        if(ii>rowlen1 and len(row1)>0):
                                                ## we make a new table since we may not have regularly dstributed labels
                                                #print "Break line! Make new table!"
                                                small_tbl['data'].append(row1)
                                                s=s+html_table(small_tbl)
                                                small_tbl['headersh']=list()
                                                small_tbl['data']=list()
                                                row1=list()
                                                ii=0

                                if(len(row1)>0):
                                        small_tbl['data'].append(row1)
                                if(len(row1)>0 or len(small_tbl['data'])>0): 
                                        #print "small_tbl=",small_tbl                                   
                                        ss=html_table(small_tbl)
                                        #print "ss=",ss
                                        s=s+ss
                                        #s=s+"\( \chi_{"+str(chi)+"}\) :"+str(d)

                                        #print N,k,chi,d
                                #print s
                                else:
                                        s="All spaces are zero-dimensional!"
                                row.append(s)
                print "row=",row
                tbl['data'].append(row)                         
        s=html_table(tbl)
        s=s+"\n <br> \(N="+str(rowlen0)+"\cdot row+col\)"
        print "Whole table=",s
        ## ugly solution. but we have latex in the data fields...
        ss=re.sub('texttt','',s)
        info['popup_table']=ss
        #info['sidebar']=set_sidebar([navigation,parents,siblings,friends,lifts])
        return info


def print_list_of_coefficients(info):
        r"""
        Print a table of Fourier coefficients in the requested format
        """
        level  = my_get(info,'level', -1,int)
        weight = my_get(info,'weight',-1,int) 
        prec= my_get(info,'prec',12,int) # number of digits 
        character = my_get(info,'character', '',str) #int(info.get('weight',0))
        if character=='':
            character=0
        label  = info.get('label', '')
        print "--------------"
        if label=='' or level==-1 or weight==-1:
            return "Need to specify a modular form completely!!"
        
        WMFS = WebModFormSpace(weight,level,character)
        if not WMFS:
            return ""
        if(info.has_key('number')):
                number=int(info['number'])
        else:
                number=max(WMFS.sturm_bound()+1,20)
        if(info.has_key('prec')):
            bprec=int(ceil(prec*3.4))
        else:
                bprec=53
        FS=list()
        if(label <>None):
                FS.append(WMFS.f(label))
        else:
                for a in WMFS.labels():
                        FS.append(WMFS.f(a))
        shead="Cusp forms of weight "+str(weight)+"on \("+latex(WMFS.group())+"\)"
        s=""
        if( (character<>None) and (character>0)):
                s=s+" and character \( \chi_{"+str(character)+"}\)"
                #s="<table><tr><td>"
        coefs=""
        for F in FS:
            if len(FS)>1:
                if info['format']=='html':
                    coefs+=F.label()
                else:
                    coefs+=F.label()
            coefs+=print_coefficients_for_one_form(F,number,info['format'])
        ss=coefs
        return ss


def print_coefficients_for_one_form(F,number,fmt):
    emf_logger.debug("in print coef 1 form: format={0}".format(fmt))
    s=""
    if fmt == "q_expansion_one_line":
        s += F.print_q_expansion(number)
    if fmt == "q_expansion_table":
        qe = F.q_expansion(number).list()
        if F.dimension()>1:
            s+=F.polynomial()
        s+="\n"
        for c in qe:
            s+=str(c)+"\n"
    if fmt == "embeddings":
        embeddings = F.q_expansion_embeddings(number)
        if F.degree() > 1:
            for j in range(F.degree()):
                for n in range(number):
                  s+=str(n)+"\t"+str(embeddings[n][j])+"\n"
        else:
            for n in range(number):
                s+=str(n)+"\t"+str(embeddings[n])+"\n"
    emf_logger.debug("s={0}".format(s))
    return s


    #fn = tempfile.mktemp(suffix=".png")#
    #fd.save(filename = fn)
    #data = file(fn).read()
    #os.remove(fn)
    #response = make_response(data)
    #response.headers['Content-type'] = 'image/png'
    #return response


def set_info_for_navigation(info,is_set,sbar):
        r"""
        Set information for the navigation page.
        """
        (friends,lifts)=sbar
        ## We always print the list of weights
        info['initial_list_of_weights'] = print_list_of_weights()
#ajax_more2(print_list_of_weights,{'kstart':[0,10,25,50],'klen':[15,15,15]},text=['<<','>>'])
        ## And the  list of characters if we know the level.

        if(is_set['level']): 
                s="<option value="+str(0)+">Trivial character</option>"
                D=DirichletGroup(info['level'])
                if(is_set['weight'] and is_even(info['weight'])):
                        if(is_fundamental_discriminant(info['level'])):
                                x=kronecker_character(info['level'])
                                xi=D.list().index(x)
                                s=s+"<option value="+str(xi)+">Kronecker character</option>"
                for x in D:
                        if(is_set['weight'] and is_even(info['weight']) and x.is_odd()):
                                continue
                        if(is_set['weight'] and is_odd(info['weight']) and x.is_even()):
                                continue
                        xi=D.list().index(x)
#                       s=s+"<option value="+str(xi)+">\(\chi_{"+str(xi)+"}\)</option>"
                        s=s+"<option value="+str(xi)+">"+str(xi)+"</option>"
                info['list_of_characters']=s
        friends.append(('L-function','/Lfunction/ModularForm/GL2/Q/holomorphic/'))
        lifts.append(('Half-Integral Weight Forms','/ModularForm/Mp2/Q'))
        lifts.append(('Siegel Modular Forms','/ModularForm/GSp4/Q'))
        return (info,lifts)


def print_list_of_weights_old(kstart=0,klen=20):
    r"""
    prints as list of weights with links to left and right.
    """
    s=""
    for k in range(kstart+1,kstart+klen+1):
        s+="<a href=\""+url_for('emf.render_elliptic_modular_forms',weight=k)+"\">%s </a>\n" % k
    return s

def print_list_of_weights(kstart=0,klen=20):
    r"""
    prints as list of weights with links to left and right.
    """
    print "kstart,klen=",kstart,klen
    nonce = hex(random.randint(0, 1<<128))
    s=""
    for k in range(kstart+1,kstart+klen+1):
        s+="<a href=\""+url_for('emf.render_elliptic_modular_forms',weight=k)+"\">%s </a>\n" % k

    url = ajax_url(print_list_of_weights,print_list_of_weights,kstart,klen,inline=True)
    s0 = """<span id='%(nonce)s'>""" % locals() 
    s1 = """<small><a onclick="$('#%(nonce)s').load('%(url)s', {kstart:10},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#"> &lt;&lt; </a></small>""" %locals()
    s2 = """<small><a onclick="$('#%(nonce)s').load('%(url)s', {kstart:50},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#"> &gt;&gt; </a></small>""" %locals()    
    res = s0 + s1 + s + s2 + "</span>"
    return res





def make_table_of_spaces_fixed_level(level=1,character=0,weight_block=0,**kwds):
    r"""
    """
    wlen=15
    print "make table: ",level,character,weight_block
    w_start = wlen*weight_block
    w_stop  = wlen*(weight_block+1)
    s="<table><thead></thead><tbody>\n"
    s+="<tr><td>Weight \(k\):</td>"
    dims=dict()
    links=dict()
    character = int(character)
    x = trivial_character(level)
    if character > 0 :
        D = DirichletGroup(level).list()
        x = D[int(character)]
    if x.is_even() and is_odd(w_start):
            w_start = w_start+1; w_stop = w_stop+1
    if x.is_odd() and is_even(w_start):
        w_start = w_start+1; w_stop = w_stop+1
    weights = list()
    for weight in range(w_start,w_start+2*wlen,2):
        weights.append(weight)
    for weight in weights:
        s+="<td> %s </td>" % weight
    s+="</tr><tr>"
    if character > 0 :
        s+="<td>Dimension:" # of  \(S^{\\textrm{new}}_{k}(%s),\chi_{%s}\):" % (level,character)
    else:
        s+="<td>Dimension:" # of \(S^{\\textrm{new}}_{k}(%s)\):" % (level)
    for weight in weights:
        if character > 0 :
            dims[weight]=dimension_new_cusp_forms(x,weight)
        else:
            dims[weight]=dimension_new_cusp_forms(level,weight)
        s+="<td> %s </td>" % dims[weight]
    j = 0 # we display ony even weight if the character is even
    print "w_start=",w_start
    print "w_stop=",w_stop
    for weight in weights:
        if not dims.has_key(weight):
            continue
        if dims[weight]>0:
            url = url_for('emf.render_elliptic_modular_forms',level=level,weight=weight)
            if character>0:
                lab = "\(S^{\\textrm{}}_{%s}(%s,\chi_{%s})\)" %(weight,level,character)
            else:
                #lab = " \(S_{%s}(%s)\)" %(weight,level)
                lab = " S<sup><small></small></sup><sub><small>%s</small></sub>(%s)" %(weight,level)
            links[weight]="<a  style=\"display:inline\" href=\"%s\">%s</a>" %(url,lab)
        else:
            links[weight]=""
        j+=1
        if j>=wlen:
            exit
    l=max(map(len_as_printed,map(str,links)))*10.0
    s+="</tr><tr>"
    s+="<td>Link to space:</td>"
    for weight in weights:
        if links.has_key(weight):
            s += "<td width=\"%s\">%s</td>" % (l+50,links[weight])
    s+="</tr></tbody></table>"
    #print s
    return s





def print_list_of_characters(level=1,weight=2):
        r"""
        Prints a list of characters compatible with the weight and level.
        """
        emf_logger.debug("print_list_of_chars")
        D = DirichletGroup(level)
        res=list()
        for j in range(len(D.list())):
                if D.list()[j].is_even() and is_even(weight):
                        res.append(j)
                if D.list()[j].is_odd() and is_odd(weight):
                        res.append(j)
        s = ""
        for j in res:
                s+="\(\chi_{"+str(j)+"}\)"
        return s

