from flask import render_template, url_for, request, redirect, make_response,send_file
import flask
import tempfile, os,re
from utils import ajax_more,ajax_result
#from utils import ajax_result as a sajax_result #,ajax_url
from sage.all import *
from base import app, db
from classical_modular_forms.backend.web_modforms import WebModFormSpace,WebNewForm
from classical_modular_forms.backend.cmf_core import * #html_table
from cmf_utils import *

CMF="cmf"
cmf = flask.Blueprint(CMF, __name__, template_folder="templates")

@cmf.context_processor
def body_class():
  return { 'body_class' : CMF }

#import re
### Maximum values to be generated on the fly
N_max_comp = 100
k_max_comp = 30
### Maximum values from the database (does this make sense)
N_max_db = 1000000 
k_max_db = 300000

_verbose = 0

#from jinja2 import Environment
print "EN_V path:",app.jinja_loader.searchpath
l=app.jinja_env.list_templates()
#for x in l:
#    print x
print "MODULES:",app.blueprints
#################
# Top level
#################

#def render_classical_modular_form():#
#	#return render_webpage(**request.args)
#	return classical_modular_forms(**request.args)
###########################################
# Search / Navigate
###########################################
#@app.route("/ModularForm/GL2/Q/holomorphic/")
@cmf.route("/",methods=['GET','POST']) #'/ModularForm/GL2/Q/holomorphic/')
def render_classical_modular_forms():
    info = get_args()
    if info.has_key('download'):
        return get_downloads(info)
    print "MODULES:",app.modules
    print "EN_V path:",app.modules['cmf'].jinja_loader.searchpath
    print "args=",request.args
    print "method=",request.method
    print "req.form=",request.form
    print "info=",info
    level = info['level']; weight=info['weight']; character=info['character']; label=info['label']
    print "HERE1:::::::::::::::::::",level,weight,character,label
    if level<=0:
        level=None
    if weight<=0:
        weight=None
    if info.has_key('jump_to'):  # try to find out where we want to jump
	s = _my_get(info,'jump_to','',str)
	info.pop('jump_to')
	weight = 2  # this is default for jumping
        character = 0 # this is default for jumping
	if s == 'delta':
	    weight = 12; level = 1; label = "a"
	    exit
	# first see if we have a label or not, i.e. if we have precisely one string of letters at the end
	test = re.findall("[a-z]+",s)
	if len(test)==1: 
	    label = test[0]
	print "label1=",label
        
	# the first string of integers should be the level
	test = re.findall("^\d+",s)
	print "level mat=",test
	if test:
	    level = int(test[0])
	if len(test)>1: ## we also have weight
	    weight = int(test[1])
	if len(test)>1: ## we also have character
	    character = int(test[2])
	    
	print "label=",label
	print "level=",level

	    
    print "HERE:::::::::::::::::::",level,weight,character,label

    # we see if we have submitted parameters
    if level and weight and character<>'' and label:
		#return redirect(url_for("render_one_classical_modular_form", level,weight,character,label))
        info['level']=level; info['weight']=weight; info['label']=label; info['character']=character
        print "WE ARE HERE!"
        return redirect(url_for("cmf.render_one_classical_modular_form", level=level, weight=weight,character=character,label=label))
    if level and weight and character:
        info['level']=level; info['weight']=weight; info['label']=label; info['character']=character
        return redirect(url_for("cmf.render_classical_modular_form_space", **info))
    if level and weight:
        info['level']=level; info['weight']=weight; info['label']=label; info['character']=character
        return redirect(url_for("cmf.render_classical_modular_form_browsing", **info))
    if level:
        info['level']=level
        print "Have level only!"
        return redirect(url_for("cmf.render_classical_modular_form_space2", **info))
    if weight:
        print "Have weight only!"
        return browse_classical_modular_forms(**info)
    if request.method == 'GET':
        return render_classical_modular_form_navigation_wp(**info) #request.args)
    else:
        return render_classical_modular_form_navigation_wp(**info) #request.form)  


#@cmf.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<int:character>/<label>/")
@cmf.route("/<int:level>/<int:weight>/<int:character>/<label>/")
def render_one_classical_modular_form(level,weight,character,label):
    r"""
     Rendering one modular form.
     """
    info = get_args() # in case we have extra args
    info['level']=level; info['weight']=weight; info['character']=character; info['label']=label
    print "info=",info
    return render_one_classical_modular_form_wp(info) #level,weight,character,label,info)

@cmf.route("/<int:level>/<int:weight>/<int:character>/")
def render_classical_modular_form_space(level,weight,character,**kwds):
    print "render_classical_modular_form_space::",level,weight
    info = get_args()
    info['level']=level; info['weight']=weight; info['character']=character
    if info['label']<>'':
        return render_one_classical_modular_form_wp(info) #level,weight,character,label,info)
    return render_classical_modular_form_space_wp(info)


@cmf.route("/<int:level>/<int:weight>/")
def render_classical_modular_form_browsing(level,weight):
    info = get_args()
    info['level']=level; info['weight']=weight
    return browse_classical_modular_forms(**info)


@cmf.route("/<int:level>/")
def render_classical_modular_form_space2(level):
    print "render_classical_modular_form_space2::",level
    info=get_args()
    info['level']=level; info['weight']=None
    return browse_classical_modular_forms(**info)

# see if the argument can be interpreted as a label of some sort
# see if we can jump directly to it
@cmf.route("/<label>/")
def render_classical_modular_form_from_label(label):
    return redirect(url_for("cmf.render_classical_modular_forms", jump_to=label))



###
## The routines that renders the various parts
###

def render_one_classical_modular_form_wp(info):
    r"""
    Renders the webpage for one classical modular form.
    
    """
    #info['level']=level; info['weight']=weight; info['character']=character; info['label']=label
    properties=list(); parents=list(); siblings=list(); friends=list()
    level  = _my_get(info,'level', -1,int)
    weight = _my_get(info,'weight',-1,int) 
    character = _my_get(info,'character', '',str) #int(info.get('weight',0))
    label  = info.get('label', '')
    citation = ['Sage:'+version()]
    lifts=['Lifts / Correspondences'] #list()
    sbar=(properties,parents,friends,siblings,lifts)
    (info,sbar)=set_info_for_one_modular_form(info,sbar)

    print "INFO111=",info


    err = info.get('error','')
    info['parents']=parents
    info['siblings']=siblings
    info['friends']=friends
    print "friends=",friends
    ## Check if we want to download either file of the function or Fourier coefficients
    if info.has_key('download') and not info.has_key('error'):					
	return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])

    #os.remove(fn) ## clears the temporary file					
    info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
    template = "cmf.html"
    title = "Cuspidal newform %s of weight %s for "%(label,weight)
    if level==1:
        title+="\(\mathrm{SL}_{2}(\mathbb{Z})\)"
    else:
	title+="\(\Gamma_0(%s)\)" %(level)
    if character>0:
	title+=" with character \(\chi_{%s}\) mod %s" %(character,level)
	title+=" of order %s and conductor %s" %(info['character_order'],info['character_conductor'])
    else:
        title+=" with trivial character!"
    url1 = url_for("cmf.render_classical_modular_forms")
    url2 = url_for("cmf.render_classical_modular_form_space",level=level,weight=weight,character=character) 
    url3 = url_for("cmf.render_classical_modular_form_space",level=level,weight=weight,character=character) 
    bread = [('Holomorphic Modular Forms',url1)]
    bread.append(("of level %s" % level,url2))
    bread.append(("weight %s" % weight,url3))
    if character == 0 :
        bread.append(("and trivial character",url3))
    else:
	bread.append(("and character \(\chi_{%s}\)" % character,url3))
    return render_template(template, info=info,title=title,bread=bread,properties=properties)	

		
def render_classical_modular_form_navigation_wp(**args):
    r"""
    Renders the webpage for the navigational page.
    
    """
    info = to_dict(args)
    level  = _my_get(info,'level', 0,int)
    weight = _my_get(info,'weight', 0,int)
    label  = info.get('label', '')
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
	page = "cmf_table.html"
	title = "Table of Classical Modular Forms Spaces"
	return render_template(page, info=info,title=title)
    ## This is the list of weights we initially put on the form
        ## List of weights and levels we initially put on the form
	## This is the list of weights we initially put on the form
	## This is the list of weights we initially put on the form
    weight = int (weight)
    #info['initial_list_of_weights'] = print_list_of_weights()
    #info['initial_list_of_levels']=range(1,30+1)
	
    #url1 = ajax_url(ajax_more2, print_list_of_characters, *arg_list1, inline=True, text='List Characters')

    info['list_chars']=ajax_once(print_list_of_characters,text='print list of characters!')
    ## t = """| <a onclick="$('#%(nonce)s').load('%(url2)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text1)s</a>]</span>""" % locals()
	## info['list_of_characters'] = 
    if level>0:
	info['geometric'] = print_geometric_data_Gamma0N(level)
	#if info.has_key('plot'):
        info['fd_plot'] = render_fd_plot(level,info)
    title = "Holomorphic Cusp Forms"
    bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    return render_template("cmf_navigation.html", info=info,title=title,bread=bread)


def get_args():
    r"""
    Get the supplied parameters.
    """
    if request.method == 'GET':
	info   = to_dict(request.args)
        print "req=",request.args
    else:
	info   = to_dict(request.form)
        print "req=",request.form
    # fix formatting of certain standard parameters
    level  = _my_get(info,'level', -1,int)
    weight = _my_get(info,'weight',-1,int) 
    character = _my_get(info,'character', '',str) #int(info.get('weight',0))
    label  = info.get('label', '')
    info['level']=level; info['weight']=weight; info['label']=label; info['character']=character
    return info

def browse_classical_modular_forms(**info):
    r"""
    Renders the webpage for browsing modular forms of given level and/or weight.
    """
    print "BROWSE HERE!!!!!!!!!!!!!!"
    info   = to_dict(info)
    print "info=",info
    level  = _my_get(info,'level', '-1',int)
    weight = _my_get(info,'weight', '-1',int)
    label  = info.get('label', '')
    char  = info.get('character', '0')
    #bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    bread =[('Modular Forms',url_for('.render_classical_modular_forms'))]
    if level <0:
        level=None
    if weight<0:
        weight=None
    if char=='0':
        info['list_chars']='0'
    else:
        info['list_chars']='1'
    print "level=",level
    print "wt=",weight    
    if level:
        info['geometric'] = print_geometric_data_Gamma0N(level)
        #if info.has_key('plot'):
        grp=MyNewGrp(level,info)
        plot=grp.plot
        info['fd_plot']= image_src(grp)
        print "PLOT:",info['fd_plot']
    if level and not weight:
        #print "here1!"
        title = "Holomorphic Cusp Forms of level %s " % level
        level = int(level)
        info['level_min']=level;info['level_max']=level
        info['weight_min']=1;info['weight_max']=36
        largs = [ {'level':level,'character':char,'weight_block':k} for k in range(100)]
        info['list_spaces']=ajax_more(make_table_of_spaces_fixed_level,*largs,text='more')
	title = "Holomorphic Cusp Forms of level %s " % level
	#bread =[('Modular Forms',url_for('modular_form_toplevel'))]
	bread =[('Modular Forms',url_for('.render_classical_modular_forms'))]
	info['browse_type']=" of level %s " % level
        return render_template("cmf_browse.html", info=info,title=title,bread=bread)
    if weight and not level:
        print "here2!"
        info['level_min']=1;info['level_max']=50
        info['weight_min']=weight;info['weight_max']=weight
        info['list_spaces']=make_table_of_dimensions(weight_start=weight,weight_stop=weight,**info) #make_table_of_spaces(level=[10,20,30])
	title = "Holomorphic Cusp Forms of weight %s" %weight
	#bread =[('Modular Forms',url_for('modular_form_toplevel'))]
	bread =[('Modular Forms',url_for('.render_classical_modular_forms'))]
        info['browse_type']=" of weight %s " % weight
        return render_template(CMF+"/cmf_browse.html", info=info,title=title,bread=bread)
    print "here2!"
    info['level_min']=level;info['level_max']=level
    info['weight_min']=weight;info['weight_max']=weight
    return render_classical_modular_form_space_list_chars(level,weight) 
    
def render_classical_modular_form_space_wp(info):
    r"""
    Render the webpage for a classical modular forms space.
    """
    level  = _my_get(info,'level', -1,int)
    weight = _my_get(info,'weight',-1,int) 
    character = _my_get(info,'character', '',str) #int(info.get('weight',0))
    label = _my_get(info,'label', 'a',str)
    if character=='':
        character=0
    properties=list(); parents=list(); friends=list(); lifts=list(); siblings=list() 
    sbar=(properties,parents,friends,siblings,lifts)
    if info.has_key('character') and info['character']=='*':
        return render_classical_modular_form_space_list_chars(level,weight)
    ### This might take forever....
    ### want to display 
    (info,sbar)=set_info_for_modular_form_space(info,sbar)
    print "HERE!!!!!!!!"
    print "keys=",info.keys()
    print "dim=",info['dimension']
    if info.has_key('download') and not info.has_key('error'):					
	return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    if info.has_key('dimension') and info['dimension']==1: # if there is only one orbit we list it
	print "Dimension is one!"
        info =dict()
        info['level']=level; info['weight']=weight; info['label']='a'; info['character']=character
        # print "INFO=",info
        return redirect(url_for('cmf.render_one_classical_modular_form', **info))
    #properties=[
    s = """
    Dimension: %s <br>
    Sturm bound: %s <br>
    """ %(info['dimension'],info['sturm_bound'])
    (properties,parents,friends,siblings,lifts)=sbar
    properties=[s]
    title = "Holomorphic Cusp Forms of weight %s on \(\Gamma_{0}(%s)\)" %(weight,level)
    bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    bread.append(("Level %s" %level,url_for('cmf.render_classical_modular_form_space2',level=level)))
    bread.append(("Weight %s" %weight,url_for('cmf.render_classical_modular_form_browsing',level=level,weight=weight)))
    print "friends=",friends
    info['friends']=friends
    #info['test']=ajax_later(_test)

    return render_template(CMF+"/cmf_space.html", info=info,title=title,bread=bread,parents=parents,friends=friends,siblings=siblings,properties=properties)



def _test(do_now=0):
    print "do_now=",do_now
    if do_now==0:
        return ""
    s="Testing!!"
    print "in test!"
    return s

        #l.append(('Friend '+str(i),'/'))
    ## print "keys=",info.keys()
    ## print "dim=",info['dimension']
    ## if info.has_key('download') and not info.has_key('error'):					
    ##     return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
    ## if info.has_key('dimension') and info['dimension']==1: # if there is only one orbit we list it
    ##     print "Dimension is one!"
    ##     info =dict()
    ##     info['level']=level; info['weight']=weight; info['label']='a'; info['character']=character
    ##     # print "INFO=",info
    ##     return redirect(url_for('cmf.render_one_classical_modular_form', **info))
    ## (properties,parents,friends,siblings,lifts)=sbar
    ## title = "Holomorphic Cusp Forms of weight %s on \(\Gamma_{0}(%s)\)" %(weight,level)
    ## bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    ## return render_template(CMF+"/cmf_space.html", info=info,title=title,bread=bread)



def render_classical_modular_form_space_list_chars(level,weight):
    r"""
    Renders a page with list of spaces of classical forms of given 
    level and weight (list all characters) 
    """
    info = dict()
    D = DirichletGroup(level)
    #s = make_table_of_dimensions(level_start=level,level_stop=level,weight_start=weight,weight_stop=weight,char=1)
    s = make_table_of_characters(level,weight)
    info['level']=level; info['weight']=weight
    if not isinstance(s,str):
	info['character'] = s
	#info['extra_info']="This is the only space of level %s and weight %s." %(level,weight)
	return redirect(url_for("cmf.render_classical_modular_form_space", **info))
    info['list_spaces']=s
    title = "Holomorphic Modular Cuspforms of level %s and weight %s " %(level,weight)
    bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    bread.append(("Level %s" %level,url_for('cmf.render_classical_modular_form_space2',level=level)))
    info['browse_type']=" of level %s and weight %s " % (level,weight)
    return render_template("cmf_browse.html", info=info,title=title,bread=bread)




def set_sidebar(l):
	res=list()
	#print "l=",l
	for ll in l:
		if(len(ll)>1):
			content=list()
			for n in range(1,len(ll)):
				content.append(ll[n])
			res.append([ll[0],content])
	return res

def make_table_of_characters(level,weight,**kwds):
    r""" Make a table of spaces S_k(N,\chi) for all compatible characters chi.
    """
    D=DirichletGroup(level)
    print "D=",D
    s = "List of \(S_{%s} (%s, \chi_{n}) \)" %(weight,level)
    s+="<a name=\"#"+str(level)+"\"></a>"
    tbl=dict()
    tbl['headersv']=['order of \(\chi_{n}\):','dimension:']
    tbl['headersh']=list()
    tbl['corner_label']="\( n \):"
    tbl['data']=list()
    tbl['atts']="class=\"nt_data\" border=\"0\" padding=\"25\""
    tbl['data_format']='html'
    row=list()
    rowlen = 25
    ii=0
    dims = dict()
    for chi in range(0,len(D.list())):
        x=D[chi]; S=CuspForms(x,weight); d=S.dimension()
        dims[chi]=d
    num_non_zero = (map(lambda x:  x>0,dims.values())).count(True)
    print "Number of non_zer0",num_non_zero
    if num_non_zero == 1:
	d = max(dims.values())
	chi = dims.keys()[dims.values().index(d)]
	return chi
    numrows = ceil(map(lambda x: x>0,dims).count(True)/rowlen)
    tbl['col_width']=dict()
    ci=0
    for chi in range(0,len(D.list())):
        d = dims[chi]
        if d==0:
            continue
        tbl['headersh'].append(chi)
        tbl['col_width'][ii]=["100"]
        x = D.list()[chi]
        order = x.order()
        #st = " %s (order %s) " %(chi,order)
        ii=ii+1
        row.append(order)
        if(ii>rowlen and len(row)>0):
            print "appending row:",row
            tbl['data'].append(row)
            s=s+html_table(tbl)
            tbl['headersh']=list(); tbl['data']=list(); row=list()
            ii=0
    if(len(row)>0):
        tbl['data'].append(row)
        #if (len(row)>0 or len(tbl['data'])>0): 
        #    ss=html_table(tbl)
        #    s=s+ss

    row = list()
    ii=0
    for chi in range(0,len(D.list())):
        d = dims[chi]
        if d==0:
            continue
        url = url_for('cmf.render_classical_modular_form_space',level=level,weight=weight,character=chi) 
        row.append("<a href=\""+url+"\">"+str(d)+"</a>")
        ii=ii+1
        if(ii>rowlen and len(row)>0):
            print "appending row:",row
            tbl['data'].append(row)
            s=s+html_table(tbl)
            tbl['headersh']=list(); tbl['data']=list(); row=list()
            ii=0

    if(len(row)>0):
        tbl['data'].append(row)
        if (len(row)>0 or len(tbl['data'])>0): 
            ss=html_table(tbl)
            s=s+ss
        else:
            s="All spaces are zero-dimensional!"
    return s

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
            url = url_for('cmf.render_classical_modular_form_browsing',level=level,weight=weight)
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

def get_downloads(info):
    if info['download']=='file':
        # there are only a certain number of fixed files that we want people to download
        filename=info['download_file']
        if(filename=="web_modforms.py"):
            full_filename=os.curdir+"/classical_modular_forms/backend/web_modforms.py"
            try: 
                return send_file(full_filename, as_attachment=True, attachment_filename=filename)
            except IOError:
                info['error']="Could not find  file! "
    if info['download']=='coefficients':
  	info['tempfile'] = "/tmp/tmp_web_mod_form.txt"
        return get_coefficients(info)
    if info['download']=='object':
        info['tempfile'] = "/tmp/tmp_web_mod_form.sobj"
        if label<>'':
            # download a function
            render_one_classical_modular_form_wp(info)
        else:
            render_one_classical_modular_form_space_wp(info)
            # download a space

def get_coefficients(info):
    print "IN GET_COEFFICIENTS!!!"
    level  = _my_get(info,'level', -1,int)
    weight = _my_get(info,'weight',-1,int) 
    character = _my_get(info,'character', '',str) #int(info.get('weight',0))
    if character=='':
        character=0
    label  = info.get('label', '')
    # we only want one form or one embedding
    s = print_list_of_coefficients(info)
    fp=open(info['tempfile'],"w")
    fp.write(s)
    fp.close()
    info['filename']=str(weight)+'-'+str(level)+'-'+str(character)+'-'+label+'coefficients-1to'+info['number']+'.txt'
    return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
        
    # first check database.


def print_list_of_coefficients(info):
	r"""
	Print a table of Fourier coefficients in the requested format
	"""
        level  = _my_get(info,'level', -1,int)
        weight = _my_get(info,'weight',-1,int) 
        prec= _my_get(info,'prec',12,int) # number of digits 
        character = _my_get(info,'character', '',str) #int(info.get('weight',0))
        if character=='':
            character=0
        label  = info.get('label', '')
	print "--------------"
        if label=='' or level==-1 or weight==-1:
            return "Need to specify a modular form completely!!"
        
	WMFS = WebModFormSpace(weight,level,character)
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
	## 	shead="Functions: <ul>"
	## 	for F in FS:
	## 		shead=shead+"<li><a href=\"#"+F.label()+"\">"+F.label()+"</a>"
	## 		if(F.dimension()==1):
	## 			shead=shead+"</li> \n"
	## 		else:
	## 			shead=shead+"Embeddings: <ul>"
	## 			for j in range(1,F.dimension()):
	## 				shead=shead+"<li><a href=\"#"+F.label()+"\">"+F.label()+"</a>"

	## 	for F in FS:
	## 		c=F.print_q_expansion_embeddings(number,bprec)
	## 		s=s+"<a name=\""+F.label()+"\"></a>\n"
	## 		for j in range(F.dimension()):
	## 			s=s+"<a name=\""+str(j)+"\"></a>\n"
	## 			for n in range(len(c)): 
	## 				s=s+str(j)+" "+str(c[n][j])

	## ss= shead+"\n"+s 
	## #info['popup_table']=ss
	return ss


def print_coefficients_for_one_form(F,number,format):
    s=""
    if format == "q_expansion_one_line":
        s += F.print_q_expansion(number)
    if format == "q_expansion_table":
        qe = F.q_expansion(number).list()
        if F.dimension()>1:
            s+=F.polynomial()
        s+="\n"
        for c in qe:
            s+=c+"\n"
    if format == "embeddings":
        embeddings = F.q_expansion_embeddings(number)
        #print "F=",F
        #print "EMBEDDINGS=",embeddings
        #print "number = ",number
        if F.degree() > 1:
            for j in range(F.degree()):
                for n in range(number):
                    s+=str(n)+"\t"+str(embeddings[n][j])+"\n"
        else:
            for n in range(number):
                s+=str(n)+"\t"+str(embeddings[n])+"\n"
    print s
    return s

class MyNewGrp (SageObject):
    def __init__(self,level,info):
        self._level=level
        self._info=info
    def plot(self,**kwds):
        return render_fd_plot(self._level,self._info,**kwds)
            
def render_fd_plot(level,info,**kwds):
    group = None
    if(info.has_key('group')):
        group = info['group']
	# we only allow standard groups
    if (group  not in ['Gamma0','Gamma','Gamma1']):
        group = 'Gamma0'
    return draw_fundamental_domain(level,group,**kwds) 
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
#			s=s+"<option value="+str(xi)+">\(\chi_{"+str(xi)+"}\)</option>"
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
        s+="<a href=\""+url_for('cmf.render_classical_modular_forms',weight=k)+"\">%s </a>\n" % k
    return s

def print_list_of_weights(kstart=0,klen=20):
    r"""
    prints as list of weights with links to left and right.
    """
    print "kstart,klen=",kstart,klen
    nonce = hex(random.randint(0, 1<<128))
    s=""
    for k in range(kstart+1,kstart+klen+1):
        s+="<a href=\""+url_for('cmf.render_classical_modular_forms',weight=k)+"\">%s </a>\n" % k

    url = ajax_url(print_list_of_weights,print_list_of_weights,kstart,klen,inline=True)
    s0 = """<span id='%(nonce)s'>""" % locals() 
    s1 = """<small><a onclick="$('#%(nonce)s').load('%(url)s', {kstart:10},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#"> &lt;&lt; </a></small>""" %locals()
    s2 = """<small><a onclick="$('#%(nonce)s').load('%(url)s', {kstart:50},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#"> &gt;&gt; </a></small>""" %locals()    
    res = s0 + s1 + s + s2 + "</span>"
    return res



#import __main__.web_modforms #WebNewForm 
#from web_modforms import
#import __main__
#__main__.WebModFormSpace=WebModFormSpace
#__main__.WebNewForm=WebNewForm

def set_info_for_one_modular_form(info,sbar): #level,weight,character,label,info,sbar):
    r"""
    Set the info for on modular form.
    
    """
    level  = _my_get(info,'level', -1,int)
    weight = _my_get(info,'weight',-1,int) 
    character = _my_get(info,'character', '',str) #int(info.get('weight',0))
    if character=='':
        character=0
    label  = info.get('label', '')
    try:
        #M = WebModFormSpace(weight,level,character)
        #if label
        print weight,level,character,label
        print type(weight),type(level),type(character),type(label)
        WNF = WebNewForm(weight,level,character,label)
        if info.has_key('download') and info.has_key('tempfile'):
            WNF._save_to_file(info['tempfile'])
            info['filename']=str(weight)+'-'+str(level)+'-'+str(character)+'-'+label+'.sobj'
            return (info,sbar)
    except IndexError:
        WNF = None
        print "Could not compute the desired function!"
        print level,weight,character,label
        info['error']="Could not compute the desired function!"
    (properties,parents,friends,siblings,lifts)=sbar

    #print info.keys()
    #print "--------------------------------------------------------------------------------"
    #print WNF
    if WNF==None or  WNF._f == None:
        print "level=",level
        print WNF
        info['error']="This space is empty!"
		
    D = DirichletGroup(level)
    if len(D.list())> character:
        x = D.list()[character]
        info['character_order']=x.order()
        info['character_conductor']=x.conductor()
    else:
        info['character_order']='0'
        info['character_conductor']=level
    if info.has_key('error'):
        return (info,sbar)		
    info['name']=WNF._name
    #info['embeddings'] =  ajax_more2(WNF.print_q_expansion_embeddings,{'prec':[5,10,25,50],'bprec':[26,53,106]},text=['more coeffs.','more precision'])
    info['satake'] = ajax_more2(WNF.print_satake_parameters,{'prec':[5,10,25,50],'bprec':[26,53,106]},text=['more parameters','more precision'])
    info['polynomial'] = WNF.polynomial()
    #info['q_exp'] = "\["+WNF.print_q_expansion()+"\]"
    #old_break = WNF._break_line_at
    #WNF._break_line_at=50
    #info['q_exp'] = ajax_more(WNF.print_q_expansion,5,10,20,50,100)
    br = 500
    info['q_exp'] = ajax_more(WNF.print_q_expansion,{'prec':5,'br':br},{'prec':10,'br':br},{'prec':20,'br':br},{'prec':100,'br':br},{'prec':200,'br':br})
    #WNF._break_line_at=old_break
    ## check the varable...
    #m = re.search('zeta_{\d+}',info['q_exp'])
    #if(m):
    #	ss = re.sub('x','\\'+m.group(),info['polynomial'])
    #	info['polynomial'] = ss
    if(WNF.dimension()>1 or WNF.base_ring()<>QQ):
        info['polynomial_st'] = 'where ' +'\('+	info['polynomial'] +'=0\)'
    else:
        info['polynomial_st'] = ''
        
    #info['satake_angle'] = WNF.print_satake_parameters(type='thetas')
    K = WNF.base_ring()
    if(K<>QQ and K.is_relative()):
        info['degree'] = int(WNF.base_ring().relative_degree())
    else:
        info['degree'] = int(WNF.base_ring().degree())
    #info['q_exp_embeddings'] = WNF.print_q_expansion_embeddings()
    if(int(info['degree'])>1 and WNF.dimension()>1):
        s = 'One can embed it into \( \mathbb{C} \) as:' 
        bprec = 26
        print s
        #args = 
        #info['embeddings'] =  ajax_more2(WNF.print_q_expansion_embeddings,{'prec':5,'bprec':bprec},{'prec':10,'bprec':bprec},{'prec':25,'bprec':bprec},{'prec':50,'bprec':bprec},text='More coefficients')
        info['embeddings'] =  ajax_more2(WNF.print_q_expansion_embeddings,{'prec':[5,10,25,50],'bprec':[26,53,106]},text=['more coeffs.','more precision'])
    elif(int(info['degree'])>1):
        s = 'There are '+str(info['degree'])+' embeddings into \( \mathbb{C} \):'
        bprec = 26
        print s
        info['embeddings'] =  ajax_more2(WNF.print_q_expansion_embeddings,{'prec':[5,10,25,50],'bprec':[26,53,106]},text=['more coeffs.','more precision'])
        #info['embeddings'] = ajax_more2(WNF.print_q_expansion_embeddings,{'prec':5,'bprec':bprec},{'prec':10,'bprec':bprec},{'prec':25,'bprec':bprec},{'prec':50,'bprec':bprec})

    else:
        info['embeddings'] = ''			
    #info['atkin_lehner'] = WNF.print_atkin_lehner_eigenvalues()
    #info['atkin_lehner_cusps'] = WNF.print_atkin_lehner_eigenvalues_for_all_cusps()
    info['twist_info'] = WNF.print_twist_info()
    info['CM'] = WNF.print_is_CM()
    info['CM_values'] = WNF.print_values_at_cm_points()
    # properties for the sidebar
    if(info['twist_info'][0]):				
        s='- Is minimal<br>'
    else:
        s='- Is a twist of lower level<br>'
    properties.append(s)
    if(WNF.is_CM()[0]):				
        s='- Is a CM-form'
    else:
        s='- Is not a CM-form'
    properties.append(s)
    
    #info['atkin_lehner'] = WNF.print_atkin_lehner_eigenvalues()
    #info['atkin_lehner_cusps'] =
    if len(WNF.atkin_lehner_eigenvalues().keys())>0:
        s = "<h5> Atkin-Lehner eigenvalues</h5>"
        s = s+WNF.print_atkin_lehner_eigenvalues_for_all_cusps()
        s+="<br><small>* ) The Fricke involution</small>"
        properties.append(s)
    if(level==1):
        info['explicit_formula'] = WNF.print_as_polynomial_in_E4_and_E6()
    cur_url='?&level='+str(level)+'&weight='+str(weight)+'&character='+str(character)+'&label='+str(label)
    if(len(WNF.parent().galois_decomposition())>1):
        for label_other in WNF.parent()._galois_orbits_labels:
            if(label_other<>label):
                s='Modular Form '
            else:
                s='Modular Form '
            s=s+str(level)+str(label_other)
            url = url_for('cmf.render_one_classical_modular_form',level=level,weight=weight,character=character,label=label_other)                 
            friends.append((s,url))

    #    label = str(label)+str(j+1)
    s = 'L-Function '+str(level)+label
    url = "/L/ModularForm/GL2/Q/holomorphic?level=%s&weight=%s&character=%s&label=%s&number=%s" %(level,weight,character,label,0)
    # url = '/L'+url_for('cmf.render_one_classical_modular_form',level=level,weight=weight,character=character,label=label) 
    friends.append((s,url))
    # if there is an elliptic curve over Q associated to self we also list that
    if WNF.weight()==2 and WNF.degree()==1:
        llabel=str(level)+label
        s = 'Elliptic Curve '+llabel
        url = '/EllipticCurve/Q/'+llabel 
        friends.append((s,url))
    #friends.append((s,'/Lfunction/ModularForm/GL2/Q/holomorphic/?weight='+str(weight)+'&level='+str(level)+'&character='+str(character)+"&label="+label+"&number="+str(j)))

    space_url='?&level='+str(level)+'&weight='+str(weight)+'&character='+str(character)
    parents.append(('\( S_{k} (\Gamma_0(' + str(level) + '),\chi )\)',space_url))
    info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
    return (info,sbar)



def make_table_of_spaces_fixed_level(level=1,character=0,weight_block=0,**kwds):
    r"""
    """
    wlen=15
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
        s+="<td>Dimension of  \(S_{k}(%s),\chi_{%s}\):" % (level,character)
    else:
        s+="<td>Dimension of \(S_{k}(%s)\):" % (level)
    for weight in weights:
        if character > 0 :
            dims[weight]=dimension_cusp_forms(x,weight)
        else:
            dims[weight]=dimension_cusp_forms(level,weight)
        s+="<td> %s </td>" % dims[weight]
    j = 0 # we display ony even weight if the character is even
    print "w_start=",w_start
    print "w_stop=",w_stop
    for weight in weights:
	if not dims.has_key(weight):
	    continue
        if dims[weight]>0:
            url = url_for('cmf.render_classical_modular_form_browsing',level=level,weight=weight)
            if character>0:
                lab = "\(S_{%s}(%s,\chi_{%s})\)" %(weight,level,character)
            else:
                #lab = " \(S_{%s}(%s)\)" %(weight,level)
                lab = " S<sub><small>%s</small></sub>(%s)" %(weight,level)
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



def set_info_for_modular_form_space(info,sbar):
	r"""
	Set information about a space of modular forms.
	"""
        print "info=",info
        level  = _my_get(info,'level', -1,int)
        weight = _my_get(info,'weight',-1,int) 
        character = _my_get(info,'character', '',str) #int(info.get('weight',0))
        if character=='':
            character=0
	(properties,parents,friends,siblings,lifts)=sbar
	if(level > N_max_comp or weight > k_max_comp):
            info['error']="Will take too long to compute!"
        if level > 0:
            try:
		#print  "PARAM_S:",weight,level,character
                #if level > 10 or weight > 30:
                if True:
                    WMFS = WebModFormSpace(weight,level,character,use_db=True)
                else:
                    WMFS = WebModFormSpace(weight,level,character)
                if info.has_key('download') and info.has_key('tempfile'):
                    WNF._save_to_file(info['tempfile'])
                    info['filename']=str(weight)+'-'+str(level)+'-'+str(character)+'-'+label+'.sobj'
                    return (info,sbar)
            except RuntimeError:
                info['error']="Sage error: Could not construct the desired space!"
        else:
            info['error']="Got wrong level: %s " %level
	if(info.has_key('error')):
		return (info,sbar)
	info['dimension'] = WMFS.dimension()
	info['sturm_bound'] = WMFS.sturm_bound()
	info['new_decomposition'] = WMFS.print_galois_orbits()
	print "new_decomp=",info['new_decomposition']
	info['nontrivial_new'] = len(info['new_decomposition'])
	## we try to catch well-known bugs...
	try:
		O = WMFS.print_oldspace_decomposition()
		info['old_decomposition'] = O
	except:
		O =[]
		info['old_decomposition'] = "n/a"
		(A,B,C)=sys.exc_info()
		# build an error message...
		errtype=A.__name__
		errmsg=B
		s="%s: %s  at:" %(errtype,errmsg)
		next=C.tb_next
		while(next):
			ln=next.tb_lineno
			filen=next.tb_frame.f_code.co_filename 			
			s+="\n line no. %s in file %s" %(ln,filen)
			next=next.tb_next
		#print s
		## make 97an error popup with detailed error message

		info['error_note'] = "Could not construct oldspace!\n"+s
	# properties for the sidebar
	s='Dimension = '+str(info['dimension'])
	properties.append(s)
	s='Newspace dimension = '+str(WMFS.dimension_newspace())
	properties.append(s)
	s='Sturm bound = '+str(WMFS.sturm_bound())
	properties.append(s)		

	## Make parent spaces of S_k(N,chi) for the sidebar
	par_lbl='\( S_{*} (\Gamma_0(' + str(level) + '),\cdot )\)'
	par_url='?level='+str(level)
	parents.append([par_lbl,par_url])
	par_lbl='\( S_{k} (\Gamma_0(' + str(level) + '),\cdot )\)'
	par_url='?level='+str(level)+'&weight='+str(weight)
	parents.append((par_lbl,par_url))
	##
	if info.has_key('character'):
		info['character_order']=WMFS.character_order()
		info['character_conductor']=WMFS.character_conductor()
	if(not info.has_key('label')):
		O=WMFS.oldspace_decomposition()
		#print "O=",O
		try:
			for (old_level,chi,mult,d) in O:
				if chi<>0:
					s="\(S_{%s}(\Gamma_0(%s),\chi_{%s}) \) " % (weight,old_level,chi)
					friends.append((s,'?weight='+str(weight)+'&level='+str(old_level)+'&character='+str(chi)))
				else:
					s="\(S_{%s}(\Gamma_0(%s)) \) " % (weight,old_level)
					friends.append((s,'?weight='+str(weight)+'&level='+str(old_level)+'&character='+str(0)))
		except:
			pass
	#friends.append(('Lfunctions','/Lfunction'))
	lifts.append(('Half-Integral Weight Forms','/ModularForm/Mp2/Q'))
	lifts.append(('Siegel Modular Forms','/ModularForm/GSp4/Q'))
	sbar=(properties,parents,friends,siblings,lifts)
	return (info,sbar)


def print_list_of_characters(level=1,weight=2):
	r"""
	Prints a list of characters compatible with the weight and level.
	"""
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

def _my_get(dict,key,default,f=None):
	r"""
	Improved version of dict.get where an empty string also gives default.
	and before returning we apply f on the result.
	"""
	x = dict.get(key,default)
	if x=='':
		x=default
	if f<>None:
		try:
			x = f(x)
		except:
			pass
	return x
	
