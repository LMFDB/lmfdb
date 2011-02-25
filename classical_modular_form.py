from flask import Flask, session, g, render_template, url_for, request, redirect, make_response
from web_modforms import *
import tempfile, os,re
from utilities import ajax_more
from base import app, db, C
#import re
### Maximum values to be generated on the fly
N_max_comp = 100
k_max_comp = 30
### Maximum values from the database (does this make sense)
N_max_db = 1000000 
k_max_db = 300000

_verbose = 0


#################
# Top level
#################

#def render_classical_modular_form():#
#	#return render_webpage(**request.args)
#	return classical_modular_forms(**request.args)



###########################################
# Search / Navigate
###########################################
@app.route('/ModularForm/GL2/Q/holomorphic/')
def render_classical_modular_forms():
	info   = to_dict(request.args)
	level  = _my_get(info,'level', -1,int)
	weight = _my_get(info,'weight',-1,int) 
	character = _my_get(info,'character', '0',str) #int(info.get('weight',0))
	label  = info.get('label', '')
        print "HERE:::::::::::::::::::",level,weight
        if level<0:
            level=None
        if weight<0:
            weight=None
        print "HERE:::::::::::::::::::",level,weight

	# we see if we have submitted parameters
	if level and weight and character and label:
		#return redirect(url_for("render_one_classical_modular_form", level,weight,character,label))
            return redirect(url_for("render_one_classical_modular_form", **info))
	if level and weight and character:
            return redirect(url_for("render_classical_modular_form_space", **info))
	if level and weight:
            return redirect(url_for("render_classical_modular_form_browsing", **info))
	if level:
            info['level']=level
            return redirect(url_for("render_classical_modular_form_space2", **info))
        if weight:
            return browse_classical_modular_forms(**info)
        #return redirect(url_for("render_classical_modular_form_browsing", **info))
        return render_classical_modular_form_navigation_wp(**request.args)
#return redirect(url_for("render_classical_modular_form_space", **info))


@app.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<int:character>/<label>/")
def render_one_classical_modular_form(level,weight,character,label):
	## see if we want to display it or if we want to do domething else
	print level,weight,character,label
	return render_one_classical_modular_form_wp(level,weight,character,label)

@app.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<int:character>/")
def render_classical_modular_form_space(level,weight,character):
    print "render_classical_modular_form_space::",level,weight
    info=to_dict(request.args)
    info['level']=level; info['weight']=weight; info['character']=character
    return render_classical_modular_form_space_wp(**info)

@app.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/")
def render_classical_modular_form_browsing(level,weight):
    print "Get level and ewight"
    info=to_dict(request.args)
    info['level']=level; info['weight']=weight
    print "render_classical_modular_form_browsing::",level,weight
    return browse_classical_modular_forms(**info)
#return render_classical_modular_form_space_wp(**info)
#return redirect(url_for("render_classical_modular_form_space", **info))


@app.route("/ModularForm/GL2/Q/holomorphic/<int:level>/")
def render_classical_modular_form_space2(level):
    print "render_classical_modular_form_space2::",level
    info=to_dict(request.args);
    info['level']=level; info['weight']=None
    return browse_classical_modular_forms(**info)


###
## The routines that renders the various parts
###

def render_one_classical_modular_form_wp(level,weight,character,label):
	info = to_dict(request.args) # get any extra info wee might have submitted
	if info.has_key('download'):
		print "saving self!"
		info['tempfile'] = "/tmp/tmp_web_mod_form.sobj"
	properties=list(); parents=list(); siblings=list(); friends=list()
	citation = ['Sage:'+version()]
	lifts=['Lifts / Correspondences'] #list()
	sbar=(properties,parents,friends,siblings,lifts)
	(info,sbar)=set_info_for_one_modular_form(level,weight,character,label,info,sbar)
	err = info.get('error','')
	info['parents']=parents
	info['siblings']=siblings
	info['friends']=friends
	print "friends=",friends
	if info.has_key('download') and not info.has_key('error'):					
		return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
	#os.remove(fn) ## clears the temporary file					
	info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
	template = "classical_modular_forms/classical_modular_form.html"
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
	url1 = url_for('render_classical_modular_forms')
	url2 = url_for('render_classical_modular_form_space',level=level,weight=weight,character=character) 
	url3 = url_for('render_classical_modular_form_space',level=level,weight=weight,character=character) 
	bread = [('Holomorphic Modular Forms',url1)]
	bread.append(("of level %s" % level,url2))
	bread.append(("weight %s" % weight,url3))
	if character == 0 :
		bread.append(("and trivial character",url3))
	else:
		bread.append(("and character \(\chi_{%s}\)" % character,url3))
	#info['name']=str(level)+str(label)
	return render_template(template, info=info,title=title,bread=bread,properties=properties)	

		
def render_classical_modular_form_navigation_wp(**args):
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
		page = "classical_modular_forms/classical_modular_form_table.html"
		title = "Table of Classical Modular Forms Spaces"
		return render_template(page, info=info,title=title)
		## This is the list of weights we initially put on the form
        ## List of weights and levels we initially put on the form
	## This is the list of weights we initially put on the form
	## This is the list of weights we initially put on the form
	weight = int (weight)
        info['initial_list_of_weights'] = print_list_of_weights()
	info['initial_list_of_levels']=range(1,30+1)
	
	#url1 = ajax_url(ajax_more2, print_list_of_characters, *arg_list1, inline=True, text='List Characters')

	info['list_chars']=ajax_once(print_list_of_characters,text='print list of characters!')
	## t = """| <a onclick="$('#%(nonce)s').load('%(url2)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text1)s</a>]</span>""" % locals()
	## info['list_of_characters'] = 
	if level:
		info['geometric'] = print_geometric_data_Gamma0N(level)
		if info.has_key('plot'):
			return render_fd_plot(level,info)
	title = "Holomorphic Modular Cuspforms"
	bread =[('Modular Forms',url_for('modular_form_toplevel'))]
	return render_template("classical_modular_forms/classical_modular_form_navigation.html", info=info,title=title,bread=bread)



def browse_classical_modular_forms(**info):
    r"""
    Browse modular forms of given level or weight.
    """
    print "BROWSE HERE!!!!!!!!!!!!!!"
    info   = to_dict(info)
    print "info=",info
    level  = _my_get(info,'level', '-1',int)
    weight = _my_get(info,'weight', '-1',int)
    label  = info.get('label', '')
    char  = info.get('character', '0')
    bread =[('Modular Forms',url_for('modular_form_toplevel'))]
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
    if level and not weight:
        print "here1!"
        title = "Holomorphic Modular Cuspforms of level %s " % level
        level = int(level)
        info['level_min']=level;info['level_max']=level
        info['weight_min']=1;info['weight_max']=36
        s = make_table_of_dimensions(level_start=level,level_stop=level,**info)
        print "s=",s
        info['list_spaces']=s
        #info['list_spaces']=ajax_more(make_table_of_dimensions,{'weight':10},{'weight':20},{'weight':30},text='more')
	title = "Holomorphic Modular Cuspforms of level %s " % level
	bread =[('Modular Forms',url_for('modular_form_toplevel'))]
        return render_template("classical_modular_forms/classical_modular_form_browse.html", info=info,title=title,bread=bread)
    if weight and not level:
        print "here2!"
        info['level_min']=1;info['level_max']=50
        info['weight_min']=weight;info['weight_max']=weight
        info['list_spaces']=make_table_of_dimensions(weight_start=weight,weight_stop=weight,**info) #make_table_of_spaces(level=[10,20,30])
	title = "Holomorphic Modular Cuspforms of weight %s" %weight
	bread =[('Modular Forms',url_for('modular_form_toplevel'))]
        return render_template("classical_modular_forms/classical_modular_form_browse.html", info=info,title=title,bread=bread)
    print "here2!"
    info['level_min']=level;info['level_max']=level
    info['weight_min']=weight;info['weight_max']=weight
    return render_classical_modular_form_space_list_chars(level,weight) #
    #make_table_of_dimensions(weight_start=weight,weight_stop=weight,**info) #make_table_of_spaces(level=[10,20,30])
    #title = "Holomorphic Modular Cuspforms of level %s and weight %s" %(level,weight)
    #bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    #return render_template("classical_modular_forms/classical_modular_form_browse.html", info=info,title=title,bread=bread)
    
def render_classical_modular_form_space_wp(**args):
    info = to_dict(args)
    level  = _my_get(info,'level', 0,int)
    weight = _my_get(info,'weight', 0,int)
    character = _my_get(info,'character', 0,int)
    properties=list(); parents=list(); friends=list(); lifts=list(); siblings=list() 
    sbar=(properties,parents,friends,siblings,lifts)
    if character=='*':
        return render_classical_modular_form_space_list_chars(level,weight)
    (info,sbar)=set_info_for_modular_form_space(level,weight,character,info,sbar)
    (properties,parents,friends,siblings,lifts)=sbar
    title = "Holomorphic Modular Cuspforms of weight %s on \(\Gamma_{0}(%s)\)" %(weight,level)
    bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    return render_template("classical_modular_forms/classical_modular_form_space.html", info=info,title=title,bread=bread)



def render_classical_modular_form_space_list_chars(level,weight):
    r"""

    """
    info = dict()
    D = DirichletGroup(level)
    #s = make_table_of_dimensions(level_start=level,level_stop=level,weight_start=weight,weight_stop=weight,char=1)
    s = make_table_of_characters(level,weight)
    info['level']=level; info['weight']=weight
    info['list_spaces']=s
    title = "Holomorphic Modular Cuspforms of level %s and weight %s " %(level,weight)
    bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    return render_template("classical_modular_forms/classical_modular_form_browse.html", info=info,title=title,bread=bread)

def render_webpage(**args):
	info   = to_dict(args)
	level  = info.get('level', '')
	weight = info.get('weight', '')
	label  = info.get('label', '')
	info['credit'] = 'Sage'	
	info['sage_version']=version()
	# the topics for the sidebar

	properties=['Properties']
	parents=['Parents'] #list()
	friends=['Friends'] #list()
	siblings=['Siblings'] #list()
	lifts=['Lifts / Correspondences'] #list()

	## This is the list of weights we initially put on the form
        info['initial_list_of_weights'] = print_list_of_weights()
	## This is the list of levels we initially put on the form
	info['initial_list_of_levels']=range(1,50)
	cur_url='?'
	## try to get basic parameters. If this generates an error someone supplied wrong type of parameters.
	#print "info1=",info
	(info,is_set)=set_basic_parameters(info)
	#print "info2=",info
	if(info.has_key('error')): 
		page = "classical_modular_forms/classical_modular_form_navigation.html"
		title = "Classical Modular Forms Navigation Page"
		return render_template(page, info=info,title=title)
	cur_url=""
	if(is_set['level']):
		level = info['level']
		cur_url=cur_url+'&level='+str(level)
		info['geometric'] = print_geometric_data_Gamma0N(level)
	if(is_set['weight']):
		weight = info['weight']
		cur_url=cur_url+'&weight='+str(weight)
	if(is_set['character']):
		character = info['character']
		cur_url=cur_url+'&character='+str(character)
	if(is_set['label']):
		label = info['label']
		cur_url=cur_url+'&label='+str(label)
	#
	# we now have all parameters set and can go to choose which action we perform
	#
	if(info.has_key('get_coeffs')):
		if(is_set['level'] and is_set['weight']):
			# we want to print more Fourier coefficients
			# either as q_expansions (in non-parsed latex)  or simply as a table
			info=print_list_of_coefficients(info)
			info['sidebar']=set_sidebar([parents,siblings,friends,lifts])
			#print "Printing table of coefficients!"
			#print "info=",info
			page = "classical_modular_forms/classical_modular_form_table.html"
			title = "Table of Classical Modular Forms Spaces"
			return render_template(page, info=info,title=title)

		else:
			info['error']="Need weight and level!"
			page = "classical_modular_forms/classical_modular_form_navigation.html"
			title = "Classical Modular Forms Navigation Page"
			return render_template(page, info=info,title=title)

	## if we have a level, weight and character we want to show the homepage of a space.
	if(is_set['level'] and is_set['weight'] and is_set['character']):
		sbar=(properties,parents,friends,siblings,lifts)
		(info,sbar)=set_info_for_modular_form_space(level,weight,character,info,sbar)
		(properties,parents,friends,siblings,lifts)=sbar

		## if all parameters are specified we display the homepage of a single (galois orbit of a) form
		if(is_set['label']): 
			if info.has_key('download'):
				print "saving self!"
				info['tempfile'] = "/tmp/tmp_web_mod_form.sobj"
			(info,sbar)=set_info_for_one_modular_form(level,weight,character,label,info,sbar,args)
			if info.has_key('download') and not info.has_key('error'):					
				return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
				#os.remove(fn) ## clears the temporary file					
			info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
			#print info
			page = "classical_modular_forms/classical_modular_form.html"
			title = "Cuspidal newform %s of weight %s for "%(info['label'],info['weight'])
			if info['level']==1:
				title+="\(\mathrm{SL}_{2}(\mathbb{Z})\)"
			else:
				title+="\(\Gamma_0(%s)\)" %(info['level'])
			if info['character']>0:
				title+=" with character \(\chi_{%s}\) mod %s" %(info['character'],info['level'])
				title+=" of order %s and conductor %s" %(info['character_order'],info['character_conductor'])
			url1 = url_for('render_classical_modular_forms',level=level,weight=weight) 
			bread = [('Space',url1)]
			return render_template("classical_modular_forms/classical_modular_form.html", info=info,title=title,bread=bread)
		else:
			info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
			return render_template("classical_modular_forms/classical_modular_form_space.html", info=info)
	##
	## If we did not specify a space completely we want the navigation page
	## 
	#return render_template("classical_modular_form_navigation.html", info=info)
	## if we only specify a level and a weight but no character we give a list of possible characters
	#if(level<>None and not (chi<>None and  weight<>None)):
	#	#print "Here!!!!"
	#
	# if we have a weight we only list the even/odd characters

	sbar=(friends,lifts)
	(info,lifts)=set_info_for_navigation(info,is_set,sbar)
	(friends,lifts)=sbar
	info['sidebar']=set_sidebar([friends,lifts])
	#print "sidebar=",info['sidebar']
	return render_template("classical_modular_forms/classical_modular_form_navigation.html", info=info)




def set_sidebar(l):
	res=list()
	#print "l=",l
	for ll in l:
		if(len(ll)>1):
			content=list()
			for n in range(1,len(ll)):
				content.append(ll[n])
			res.append([ll[0],content])
	#print "res=",res
	return res
#	info['sidebar']=set_sidebar(navigation,parents,siblings,friends)



#def make_table_of_spaces(weight=None,level=None):
#    r"""
#    """
#    set_table(info,is_set,make_link=True)

def make_table_of_characters(level,weight,**kwds):
    r""" Make a table of spaces S_k(N,\chi) for all compatible characters chi.
    """
    D=DirichletGroup(level)
    print "D=",D
    s = "List of \(S_{%s} (%s, \chi_{n}) \)" %(weight,level)
    s+="<a name=\"#"+str(level)+"\"></a>"
    tbl=dict()
    tbl['headersv']=['\( d \)']
    tbl['headersh']=list()
    tbl['corner_label']="\( n \)"
    tbl['data']=list()
    tbl['atts']="class=\"nt_data\" border=\"0\" padding=\"1\""
    tbl['data_format']='html'
    row=list()
    rowlen = 25
    ii=0
    dims = dict()
    for chi in range(0,len(D.list())):
        x=D[chi]; S=CuspForms(x,weight); d=S.dimension()
        dims[chi]=d
    numrows = ceil(map(lambda x: x>0,dims).count(True)/rowlen)

    for chi in range(0,len(D.list())):
        d = dims[chi]
        if d==0:
            continue
        tbl['headersh'].append(chi)
        url = url_for('render_classical_modular_form_space',level=level,weight=weight,character=chi) 
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
    with parameters in the given ranges.
    Should use database in the future... 
    """
    D=0
    rowlen=30 # split into rows of this length...
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
    if(char==1):
        tbl['header']='Dimension of \( S_{'+str(weight)+'}('+str(level)+',\chi_{n})\)'
    else:
        s = 'Dimension of \( S_{'+str(weight)+'}('+str(level)+')\)'
        s += ' (trivial character)'
        tbl['header']=s
    tbl['headersv']=list()
    tbl['headersh']=list()
    if weight=='k':
        tbl['corner_label']="k"
    else:
        tbl['corner_label']="N"
    tbl['data']=list()
    tbl['data_format']='html'
    tbl['class']="dimension_table"
    tbl['atts']="border=\"0\" class=\"data_table\""
    num_rows = ceil(QQ(count_max-count_min+1) / QQ(rowlen0))
    print "num_rows=",num_rows
    for i in range(1,rowlen0+1):
        tbl['headersh'].append(i+count_min-1)
    if level_start==level_stop:
        tbl['headersv']=['d:']
    else:
        tbl['headersv']=['d:']
    # make a dummy table first
    for r in range(num_rows):
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
            url = url_for('render_classical_modular_form_browsing',level=level,weight=weight)
            if(cnt>count_max or cnt < count_min):
                tbl['data'][r][k]=""
                continue
            s="<a name=\"#%s,%s\"></a>" % (level,weight)
            if(char==0):
                d=dimension_cusp_forms(level,weight)
                #print "d=",d
                #url="?weight="+str(weight)+"&level="+str(N)+"&character=0"
                print "cnt=",cnt
                print "r,k=",r,k
                ss = s + "<a  href=\""+url+"\">"+str(d)+"</a>"
                tbl['data'][r][k]=ss
            else:
                ss = make_table_of_characters(level,weight)
                tbl['data'][r][k]=ss
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

	print "info.keys=",info.keys()
	print "info[level]=",info['level']
	l = set_basic_parameters(info)
	print "l=",l
	print "--------------"
	try:
		(level,weight,chi,label)=l
	except:
		info['error'] = "The type of parameters were incorrect!"
		return  info
	WMFS = WebModFormSpace(weight,level,chi)
	if(info.has_key('number')):
		number=int(info['number'][0])
	else:
		number=max(WMFS.sturm_bound()+1,20)
	if(info.has_key('prec')):
		bprec=int(ceil(info['prec'][0]*3.4))
	else:
		bprec=53
	FS=list()
	if(label <>None):
		FS[0] = WMFS.f(label)
	else:
		for a in WMFS.labels():
			FS.append(WMFS.f(a))
	shead="Cuspidal modular forms of weight "+str(weight)+"on \("+latex(WMFS.group())+"\)"
	s=""
	if( (chi<>None) and (chi>0)):
		s=s+" and character \( \chi_{"+str(chi)+"}\)"
		#s="<table><tr><td>"
	if(info.has_key('format') and info['format']=='q_exp'):
		for F in FS:
			s=s+"<tr><td>"+F.print_q_expansion(prec)+"</td></tr>\n"
	else:
		# header
		shead="Functions: <ul>"
		for F in FS:
			shead=shead+"<li><a href=\"#"+F.label()+"\">"+F.label()+"</a>"
			if(F.dimension()==1):
				shead=shead+"</li> \n"
			else:
				shead=shead+"Embeddings: <ul>"
				for j in range(1,F.dimension()):
					shead=shead+"<li><a href=\"#"+F.label()+"\">"+F.label()+"</a>"

		for F in FS:
			c=F.print_q_expansion_embeddings(number,bprec)
			s=s+"<a name=\""+F.label()+"\"></a>\n"
			for j in range(F.dimension()):
				s=s+"<a name=\""+str(j)+"\"></a>\n"
				for n in range(len(c)): 
					s=s+str(j)+" "+str(c[n][j])

	ss= shead+"\n"+s 
	info['popup_table']=ss
	return info


def set_basic_parameters(info):
	r"""
	Set the basic parameters based on the info dict. With some error handling.
	"""
	level=None; character=None; weight=None;label=None
	is_set = dict()
	# we need this dictionary since "0" is "False" i python
	is_set['level']=False;	is_set['weight']=False;	is_set['character']=False;	is_set['label']=False;
	llevel=None; wweigh=None; llabel=None; ccharacter=None
	try:
		level=_extract_info(info,is_set,'level')
		weight=_extract_info(info,is_set,'weight')
		character=_extract_info(info,is_set,'character')
		label=_extract_info(info,is_set,'label')
		#print info
		if _verbose>0:
			print "is_set=",is_set
			print "weight=",weight
			print "level=",level
			print "char=",character
			print "label=",label
	except ArithmeticError: ## An error here means that someone supplied wrong type of parameters
		s='Incorrect parameters were supplied! Please try again'
		print s
		info['error'] = s
		#return render_template("classical_modular_form_navigation.html", info=info)
	return (info,is_set) # (level,weight,character,label)


def _extract_info(info,is_set,label):
	r"""
	"""
	if(not info.has_key(label) or str(info[label][0])==''):
		is_set[label]=False
		return None
	is_set[label]=True
	if(str(info[label][0])==''):
		print label+"is not set!"
	else:
		print label+"is set to:"+str(info[label])+":"
	if(isinstance(info[label],list)):
		val=info[label][0]
	elif(isinstance(info[label],dict)):
		val=info[label][info[label].keys()[0]]
	else:
		val=info[label]
	if(val<>'' and label=='weight' or label=='level'):
		info[label]=int(val)
	elif(label=='character'):
		if(val=='Trivial character'):
			info[label]=int(0)
		else:
			try:
				info[label]=int(val)
			except ValueError:
				info[label]=int(0)
	elif(label=='label'):
		info[label]=str(val)
	return val

def render_fd_plot(level,info):
	group = None
	if(info.has_key('group')):
		group = info['group'][0]
	# we only allow standard groups
	if (group  not in ['Gamma0','Gamma','Gamma1']):
		group = 'Gamma0'
	fd = draw_fundamental_domain(level,group) 
	fn = tempfile.mktemp(suffix=".png")
	fd.save(filename = fn)
	data = file(fn).read()
	os.remove(fn)
	response = make_response(data)
	response.headers['Content-type'] = 'image/png'
	return response


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
        s+="<a href=\""+url_for('render_classical_modular_forms',weight=k)+"\">%s </a>\n" % k
    return s

def print_list_of_weights(kstart=0,klen=20):
    r"""
    prints as list of weights with links to left and right.
    """
    print "kstart,klen=",kstart,klen
    nonce = hex(random.randint(0, 1<<128))
    s=""
    for k in range(kstart+1,kstart+klen+1):
        s+="<a href=\""+url_for('render_classical_modular_forms',weight=k)+"\">%s </a>\n" % k

    url = ajax_url(print_list_of_weights,print_list_of_weights,kstart,klen,inline=True)
    s0 = """<span id='%(nonce)s'>""" % locals() 
    s1 = """<small><a onclick="$('#%(nonce)s').load('%(url)s', {kstart:10},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#"> &lt;&lt; </a></small>""" %locals()
    s2 = """<small><a onclick="$('#%(nonce)s').load('%(url)s', {kstart:50},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#"> &gt;&gt; </a></small>""" %locals()    
    res = s0 + s1 + s + s2 + "</span>"
    return res



#import __main__.web_modforms #WebNewForm 
#from web_modforms import
import __main__
__main__.WebModFormSpace=WebModFormSpace
__main__.WebNewForm=WebNewForm

def set_info_for_one_modular_form(level,weight,character,label,info,sbar):
	r"""
	Set the info for on modular form.

	"""
	try:
		#M = WebModFormSpace(weight,level,character)
		#if label
		WNF = WebNewForm(weight,level,character,label)
		if info.has_key('download') and info.has_key('tempfile'):
			WNF._save_to_file(info['tempfile'])
			info['filename']=str(weight)+'-'+str(level)+'-'+str(character)+'-'+label+'.sobj'
			return (info,sbar)
	except:
		WNF = None
		print "Could not compute the desired function!"
		info['error']="Could not compute the desired function!"
	(properties,parents,friends,siblings,lifts)=sbar
	#print info.keys()
	#print "--------------------------------------------------------------------------------"
	#print WNF
	if WNF==None or  WNF.f == None:
		print "level=",level
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
	br = 45
	info['q_exp'] = ajax_more(WNF.print_q_expansion,{'prec':5,'br':br},{'prec':10,'br':br},{'prec':20,'br':br},{'prec':100,'br':br},{'prec':200,'br':br})
	#WNF._break_line_at=old_break
	## check the varable...
	#m = re.search('zeta_{\d+}',info['q_exp'])
	#if(m):
	#	ss = re.sub('x','\\'+m.group(),info['polynomial'])
	#	info['polynomial'] = ss
	if(WNF.dimension()>1):
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
		s = 'There are '+info['degree']+' embeddings into \( \mathbb{C} \):'
		bprec = 26
		print s
		info['embeddings'] = ajax_more2(WNF.print_q_expansion_embeddings,{'prec':5,'bprec':bprec},{'prec':10,'bprec':bprec},{'prec':25,'bprec':bprec},{'prec':50,'bprec':bprec})

	else:
		info['embeddings'] = ''			



	info['atkin_lehner'] = WNF.print_atkin_lehner_eigenvalues()
	info['atkin_lehner_cusps'] = WNF.print_atkin_lehner_eigenvalues_for_all_cusps()
	info['twist_info'] = WNF.print_twist_info()
	info['CM'] = WNF.print_is_CM()
	info['CM_values'] = WNF.print_values_at_cm_points()
	# properties for the sidebar
	if(info['twist_info'][0]):				
		s='Is minimal'
	else:
		s='Is a twist of lower level'
	properties.append(s)
	if(WNF.is_CM()[0]):				
		s='Is a CM-form'
	else:
		s='Is not a CM-form'
	properties.append(s)
	if(level==1):
		info['explicit_formula'] = WNF.print_as_polynomial_in_E4_and_E6()
	cur_url='?&level='+str(level)+'&weight='+str(weight)+'&character='+str(character)+'&label='+str(label)
	if(len(WNF.parent().galois_decomposition())>1):
		for label_other in WNF.parent()._galois_orbits_labels:
			if(label_other<>label):
				s=re.sub('label='+label,'label='+str(label_other),cur_url)
				l=(str(label_other),s)
			else:
				l=('-- '+str(label),cur_url)
			siblings.append(l)

	for j in range(WNF.degree()):
		label = str(label)+str(j+1)
		s = 'L-function '+str(level)+label
		url = '/L'+url_for('render_one_classical_modular_form',level=level,weight=weight,character=character,label=label) 
		friends.append((s,url))
		#friends.append((s,'/Lfunction/ModularForm/GL2/Q/holomorphic/?weight='+str(weight)+'&level='+str(level)+'&character='+str(character)+"&label="+label+"&number="+str(j)))

	space_url='?&level='+str(level)+'&weight='+str(weight)+'&character='+str(character)
	parents.append(('\( S_{k} (\Gamma_0(' + str(level) + '),\chi )\)',space_url))
	info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
	return (info,sbar)





def set_info_for_modular_form_space(level,weight,character,info,sbar):
	r"""
	Set information about a space of modular forms.
	"""
        print "character=",character
	(properties,parents,friends,siblings,lifts)=sbar
	if(level > N_max_comp or weight > k_max_comp):
            info['error']="Will take too long to compute!"
	try:
		#print  "PARAM_S:",weight,level,character
            WMFS = WebModFormSpace(weight,level,character)
	except RuntimeError:
		info['error']="Sage error: Could not construct the desired space!"
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
		## make an error popup with detailed error message

		info['error_note'] = "Could not construct oldspace!\n"+s
	# properties for the sidebar
	s='Dimension = '+str(info['dimension'])
	properties.append((s,''))
	s='Newspace dimension = '+str(WMFS.dimension_newspace())
	properties.append((s,''))
	s='Sturm bound = '+str(WMFS.sturm_bound())
	properties.append((s,''))		

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

import random
from utilities import *


def ajax_more2(callback, *arg_list, **kwds):
	r"""
	Like ajax_more but accepts increase in two directions.
	Call with
	ajax_more2(function,{'arg1':[x1,x2,...,],'arg2':[y1,y2,...]},'text1','text2')
	where function takes two named argument 'arg1' and 'arg2'
	"""
	inline = kwds.get('inline', True)
	text = kwds.get('text', 'more')
	print "inline=",inline

	print "text=",text
	text0 = text[0]
	text1 = text[1]
	print "arglist=",arg_list
	nonce = hex(random.randint(0, 1<<128))
	if inline:
		args = arg_list[0]
		print "args=",args
		key1,key2=args.keys()
		l1=args[key1]
		l2=args[key2]
		print "key1=",key1
		print "key2=",key2
		print "l1=",l1
		print "l2=",l2
		args={key1:l1[0],key2:l2[0]}
		l11=l1[1:]; l21=l2[1:]
		#arg_list = arg_list[1:]
		arg_list1 = {key1:l1,key2:l21}
		arg_list2 = {key1:l11,key2:l2}
		#print "arglist1=",arg_list
		if isinstance(args, tuple):
			res = callback(*arg_list)
		elif isinstance(args, dict):
			res = callback(**args)
		else:
			res = callback(args)
		res = web_latex(res)
	else:
		res = ''
	print "arg_list1=",arg_list1
	print "arg_list2=",arg_list2
	arg_list1=(arg_list1,)
	arg_list2=(arg_list2,)
	if arg_list1 or arg_list2:
		url1 = ajax_url(ajax_more2, callback, *arg_list1, inline=True, text=text)
		url2 = ajax_url(ajax_more2, callback, *arg_list2, inline=True, text=text)
		print "arg_list1=",url1
		print "arg_list2=",url2
		s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
		s1 = """[<a onclick="$('#%(nonce)s').load('%(url1)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text0)s</a>""" % locals()
		t = """| <a onclick="$('#%(nonce)s').load('%(url2)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text1)s</a>]</span>""" % locals()
		return (s0+s1+t)
	else:
		return res

def ajax_once(callback,*arglist,**kwds):
	r"""
	"""

	text = kwds.get('text', 'more')
	print "text=",text
	print "arglist=",arglist
	print "kwds=",kwds
	print "req=",request.args
	nonce = hex(random.randint(0, 1<<128))
	res = callback()
	url = ajax_url(ajax_once,print_list_of_characters,arglist,kwds,inline=True)
	s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
	#	s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {'level':22,'weight':4},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
	s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {a:1},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
	return s0+s1

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
	
