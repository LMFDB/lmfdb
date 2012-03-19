from utils import to_dict,image_src
from sage.all import dimension_new_cusp_forms,dimension_cusp_forms,dimension_eis,dimension_modular_forms
from modular_forms.elliptic_modular_forms import EMF, emf_logger, emf,EMF_TOP
from modular_forms.elliptic_modular_forms.backend.emf_core import get_geometric_data_Gamma0N
from modular_forms.elliptic_modular_forms.backend.emf_utils import MyNewGrp,my_get
from modular_forms.backend.mf_utils import my_get
from modular_forms import MF_TOP
from flask import render_template, url_for, request, redirect, make_response,send_file
from modular_forms.elliptic_modular_forms.backend.emf_classes import ClassicalMFDisplay
list_of_implemented_dims=['new','cusp','modular','eisenstein']
from sage.all import DirichletGroup
met = ['POST','GET']
@emf.route("/TablesMF/",methods=met)
@emf.route("/TablesMF/<int:nrows>/<int:ncols>/",methods=met)
def draw_table(nrows=None,ncols=None,**kwds):
    if request.method == 'GET':
        info = to_dict(request.args)
    else:
        info = to_dict(request.form)
    ncols = my_get(info,'ncols',ncols,int)
    nrows = my_get(info,'nrows',nrows,int)
    if nrows==None or ncols==None:
        return emf_error("Please supply level weight (and optional character)!")
    ttype = my_get(info,'ttype','new',str)
    ttype = my_get(kwds,'ttype',info.get('ttype'),str)
    info = to_dict(kwds)
    ttype = my_get(kwds,'ttype','new',str)
    info['title']='Title of table'
    info['ttype']=ttype
    info['nrows']=nrows
    info['ncols']=ncols
    return render_template("emf_table2.html",**info)


@emf.route("/DimensionMF/",methods=met)
@emf.route("/DimensionMF/<int:level>/<int:weight>/<int:chi>",methods=met)
def return_dimension(level=None,weight=None,chi=None,**kwds):
    if request.method == 'GET':
        info = to_dict(request.args)
    else:
        info = to_dict(request.form)
    level = my_get(info,'level',level,int)
    weight = my_get(info,'weight',weight,int)
    chi = my_get(info,'chi',chi,int)
    if level==None or weight==None:
        return emf_error("Please supply level weight (and optional character)!")
    ttype = my_get(kwds,'ttype',info.get('ttype','new'),str)
    emf_logger.debug("level,weight,chi: {0},{1},{2}, type={3}".format(level,weight,chi,ttype))
    if chi==0 or chi==None:
        x = level
    else:
        x = DirichletGroup(level).list()[chi]
    if ttype=='new':
        return str(dimension_new_cusp_forms(x,weight))
    if ttype=='cusp':
        return str(dimension_cusp_forms(x,weight))
    if ttype=='modular':
        return str(dimension_modular_forms(x,weight))
    if ttype=='eisenstein':
        return str(dimension_eis(x,weight))
    s = "Please use one of the available table types: 'new', 'cusp','modular', 'eisenstein' Got:{0}".format(ttype)
    return emf_error(s)


def emf_error(s):
    s="ERROR: "+s
    s="<span style='color:red;'>{0}</span>".format(s)
    emf_logger.critical(s)
    return s


@emf.route("/Tables/<int:level>/")
def render_table(level,**kwds):
    r"""
    Return a html table with appropriate dimensions.
    """
    nrows = my_get(kwds,'nrows',10,int)
    ncols = my_get(kwds,'ncols',10,int)
    ttype = my_get(kwds,'ttype','newforms',str)
    
    


def browse_elliptic_modular_forms(level=0,weight=0,character=-1,label='',**kwds):
    r"""
    Renders the webpage for browsing modular forms of given level and/or weight.
    """
    emf_logger.debug("In browse_elliptic_modular_forms kwds: {0}".format(kwds))
    emf_logger.debug("Input: level={0},weight={1},character={2},label={3}".format(level,weight,character,label))
    bread = [(MF_TOP,url_for('mf.modular_form_main_page'))]
    bread.append((EMF_TOP,url_for('emf.render_elliptic_modular_forms')))
    #if level <0:
    #    level=None
    #if weight<0:
    #    weight=None
    info=dict()
    if character=='0':
        info['list_chars']='0'
    else:
        info['list_chars']='1'
    emf_logger.info("level=%s, %s"%(level,type(level)))
    emf_logger.info("wt=%s, %s"% (weight,type(weight)) )
    if level>0:
        info['geometric'] = get_geometric_data_Gamma0N(level)
        #if info.has_key('plot'):
        grp=MyNewGrp(level,info)
        plot=grp.plot
        info['fd_plot']= image_src(grp)
        emf_logger.info("PLOT: %s" % info['fd_plot'])
    if level>0 and weight==0:
        #print "here1!"
        title = "Holomorphic Cusp Forms of level %s " % level
        level = int(level)
        info['level_min']=level;info['level_max']=level
        info['weight_min']=1;info['weight_max']=36
        largs = [ {'level':level,'character':character,'weight_block':k} for k in range(100)]
        disp = ClassicalMFDisplay('modularforms')
        disp.set_table_browsing(limit=[(1,36),(level,level)],keys=['Weight','Level'],character='all',dimension_fun=dimension_new_cusp_forms,title='Dimension of newforms')
        info['show_all_characters']=1
        info['browse_table']=disp._table
        
        #info['list_spaces']=ajax_more(make_table_of_spaces_fixed_level,*largs,text='more')
        title = "Holomorphic Cusp Forms of level %s " % level
        bread =[(MF_TOP,url_for('mf.modular_form_main_page'))]
        bread.append((EMF_TOP,url_for('emf.render_elliptic_modular_forms')))
        info['browse_type']=" of level %s " % level
        info['title']=title;  info['bread']=bread
        info['level']=level
        return render_template("emf_browse_fixed_level.html", **info)
    if weight>0 and level==0:
        #disp = ClassicalMFDisplay('modularforms')
        #disp.set_table_browsing(limit=[(weight,weight),(1,50)],keys=['Weight','Level'],character='all',dimension_fun=dimension_new_cusp_forms,title='Dimension of newforms')
        info['show_all_characters']=1
        #info['browse_table']=disp._table
        emf_logger.debug("here2!")
        info['level_min']=1;info['level_max']=50
        info['weight_min']=weight;info['weight_max']=weight
        #info['list_spaces']=make_table_of_dimensions(weight_start=weight,weight_stop=weight,**info) #make_table_of_spaces(level=[10,20,30])
        title = "Holomorphic Cusp Forms of weight %s" %weight
        bread =[(MF_TOP,url_for('mf.modular_form_main_page'))]
        info['browse_type']=" of weight %s " % weight
        table=dict()
        row_heads=list()
        col_heads=list()
        i  = 0 
        for N in range(info['level_min'],info['level_max']+1):
            row_heads.append(N)
            D = DirichletGroup(N).list()
            table[i]=dict()
            j = 0
            for x in range(len(D)):
                if x not in col_heads:
                    col_heads.append(x)
                url = url_for('emf.render_elliptic_modular_forms',level=N,weight=weight,character=x)
                d = dimension_cusp_forms(D[x],weight)
                table[i][j]={"dim":d,"url":url}
                j = j+1
            i = i + 1
        info['browse_table']=table
        info['nrows']=len(row_heads)
        info['ncols']=len(col_heads)
        info['title']=title;  info['bread']=bread
        info['row_heads']=row_heads
        info['col_heads']=col_heads
        return render_template("emf_browse_fixed_level.html", **info)
    emf_logger.debug("here2!")
    info['level_min']=level;info['level_max']=level
    info['weight_min']=weight;info['weight_max']=weight
    return render_elliptic_modular_form_space_list_chars(level,weight) 
    


def render_elliptic_modular_form_space_list_chars(level,weight):
    r"""
    Renders a page with list of spaces of elliptic forms of given 
    level and weight (list all characters) 
    """
    info = dict()
    #s = make_table_of_characters(level,weight)
    info['level']=level; info['weight']=weight
    #if not isinstance(s,str):
    #    info['character'] = s
    #    return redirect(url_for("emf.render_elliptic_modular_forms", **info))
    #info['list_spaces']=s
    title = "Holomorphic Cuspforms of level %s and weight %s " %(level,weight)
    bread =[(MF_TOP,url_for('mf.modular_form_main_page'))]
    bread.append((EMF_TOP,url_for('emf.render_elliptic_modular_forms')))
    bread.append(("Level %s" %level,url_for("emf.render_elliptic_modular_forms",level=level)))
    
    info['browse_type']=" of level %s and weight %s " % (level,weight)
    disp = ClassicalMFDisplay('modularforms')
    disp.set_table_browsing(limit=[(weight,weight),(level,level)],keys=['Weight','Level'],character='all',dimension_fun=dimension_new_cusp_forms,title='Dimension of newforms')
    info['show_all_characters']=1
    info['browse_table']=disp._table    
    info['bread']=bread
    info['title']=title
    return render_template("emf_browse_fixed_level.html", **info)
#                           =info,title=title,bread=bread)




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
    s=html_table(tbl)
    #s=s+"\n <br> \(N="+str(rowlen0)+"\cdot row+col\)"
    #print "SS=",s
    return s
    #ss=re.sub('texttt','',s)
    #info['popup_table']=ss
        #info['sidebar']=set_sidebar([navigation,parents,siblings,friends,lifts])
        #   return info
