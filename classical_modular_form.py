from flask import render_template,send_file, make_response
from web_modforms import *
import tempfile, os,re
from utilities import ajax_more

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
def render_webpage(args):
	if len(args)==0:
		info = dict()
	else:
	        info = dict(args)
	info['credit'] = 'Sage'	
	info['sage_version']=version()
	# the topics for the sidebar
	#navigation=list() #['Browse'] #list()
	properties=['Properties']
	parents=['Parents'] #list()
	friends=['Friends'] #list()
	siblings=['Siblings'] #list()
	lifts=['Lifts / Correspondences'] #list()
	
	## This is the list of weights we initially put on the form
	info['initial_list_of_weights']=list()
	## This is the list of levels we initially put on the form
	info['initial_list_of_levels']=range(1,50)
	cur_url='?'
	## try to get basic parameters. If this generates an error someone supplied wrong type of parameters.
	print "info1=",info
	(info,is_set)=set_basic_parameters(info)
	print "info2=",info
	if(info.has_key('error')): 
		return render_template("classical_modular_form_navigation.html", info=info)
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
	if(info.has_key('plot') and level <> None):
		return render_fd_plot(level,info)
	if(info.has_key('get_table')):
		# we want a table
		info = set_table(info,is_set)
		return render_template("classical_modular_form_table.html", info=info)
	if(info.has_key('get_coeffs')):
		if(is_set['level'] and is_set['weight']):
			# we want to print more Fourier coefficients
			# either as q_expansions (in non-parsed latex)  or simply as a table
			info=print_list_of_coefficients(info)
			info['sidebar']=set_sidebar([parents,siblings,friends,lifts])
			#print "Printing table of coefficients!"
			#print "info=",info
			return  render_template("classical_modular_form_table.html", info=info)
		
		else:
			info['error']="Need weight and level!"
			return render_template("classical_modular_form_navigation.html", info=info)

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
			(info,sbar)=set_info_for_one_modular_form(level,weight,character,label,info,sbar)
			if info.has_key('download') and not info.has_key('error'):					
				return send_file(info['tempfile'], as_attachment=True, attachment_filename=info['filename'])
				#os.remove(fn) ## clears the temporary file					
			info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
			print info
			return render_template("classical_modular_form.html", info=info)
		else:
			info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
			return render_template("classical_modular_form_space.html", info=info)
	##
	## If we did not specify a space completely we want the navigation page
	## 
	#return render_template("classical_modular_form_navigation.html", info=info)
	## if we only specify a level and a weight but no character we give a list of possible characters
	#if(level<>None and not (chi<>None and  weight<>None)):
	#	#print "Here!!!!"
	#
	# if we have a weight we only list the even/odd characters
	#print level,weight,chi
	#print "info=",info
	#space_url=cur_url
	#print "HERE!"
	sbar=(friends,lifts)
	(info,lifts)=set_info_for_navigation(info,is_set,sbar)
	(friends,lifts)=sbar
	info['sidebar']=set_sidebar([friends,lifts])
	print "sidebar=",info['sidebar']
	return render_template("classical_modular_form_navigation.html", info=info)




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
		level_min=int(info['level_min'][0])
	else:
		level_min=1
	if(info.has_key('level_max')):
		level_max=int(info['level_max'][0])
	else:
		level_max=50
	if (level_max-level_min+1) < rowlen:
		rowlen0=level_max-level_min+1
	if(info['list_chars'][0]<>'0'):
		char1=1
	else:
		char1=0
	if(is_set['weight']):
		weight=info['weight']
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
	for r in range(num_rows):
		row=list()
		#print "row nr. ",r
		for k in range(1,rowlen0+1):
			N=level_min-1+r*rowlen0+k
			s="<a name=\"#"+str(N)+"\"></a>"
			#print "col ",k,"=",N
			if(N>level_max or N < 1):
				continue
			if(char1==0):
				d=dimension_cusp_forms(N,weight)
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
		tbl['data'].append(row)				
	s=html_table(tbl)
	s=s+"\n <br> \(N="+str(rowlen0)+"\cdot row+col\)"
	#print "Whole table=",s
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
	if(not is_set['weight']):
		info['weight'] = 2  ## the default value
	for n in range(2,13):
		if(n==info['weight']):
			info['initial_list_of_weights'].append((n,"checked"))
		else:
			info['initial_list_of_weights'].append((n,""))
		
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
		WNF = WebNewForm(weight,level,character,label)
		if info.has_key('download') and info.has_key('tempfile'):
			WNF._save_to_file(info['tempfile'])
			info['filename']=str(weight)+'-'+str(level)+'-'+str(character)+'-'+label+'.sobj'
			return (info,sbar)
	except:
		info['error']="Could not compute the desired function!"
	(properties,parents,friends,siblings,lifts)=sbar
	#print info.keys()
	#print WNF
	if(info.has_key('error')):
		return (info,sbar)		
	info['satake'] = WNF.print_satake_parameters()
	info['polynomial'] = WNF.polynomial()
	#info['q_exp'] = "\["+WNF.print_q_expansion()+"\]"
	info['q_exp'] = ajax_more(WNF.print_q_expansion,5,10,20,50,100)
	
	## check the varable...
	#m = re.search('zeta_{\d+}',info['q_exp'])
	#if(m):
	#	ss = re.sub('x','\\'+m.group(),info['polynomial'])
	#	info['polynomial'] = ss
	if(WNF.dimension()>1):
		info['polynomial_st'] = 'where ' +'\('+	info['polynomial'] +'=0\)'
	else:
		info['polynomial_st'] = ''
		
	info['satake_angle'] = WNF.print_satake_parameters(type='thetas')
	K = WNF.base_ring()
	if(K<>QQ and K.is_relative()):
		info['degree'] = int(WNF.base_ring().relative_degree())
	else:
		info['degree'] = int(WNF.base_ring().degree())
	info['q_exp_embeddings'] = WNF.print_q_expansion_embeddings()
	if(int(info['degree'])>1 and WNF.dimension()>1):
		info['embeddings'] = 'One can embed it into \( \mathbb{C} \) as ' + info['q_exp_embeddings']

	elif(int(info['degree'])>1):
		info['embeddings'] = 'One can embed it into \( \mathbb{C} \) as ' + info['q_exp_embeddings']
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
	properties.append((s,''))
	if(WNF.is_CM()[0]):				
		s='Is a CM-form'
	else:
		s='Is not a CM-form'
	properties.append((s,''))
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
	friends.append(('L-function','/Lfunction/ModularForm/GL2/Q/holomorphic/?weight='+str(weight)+'&level='+str(level)+'&character='+str(character)+"&label="+label))
	
	space_url='?&level='+str(level)+'&weight='+str(weight)+'&character='+str(character)
	parents.append(('\( S_{k} (\Gamma_0(' + str(level) + '),\chi )\)',space_url))
	info['sidebar']=set_sidebar([properties,parents,siblings,friends,lifts])
	return (info,sbar)





def set_info_for_modular_form_space(level,weight,character,info,sbar):
	r"""
	Set information about a space of modular forms.
	"""
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
	friends.append(('Lfunctions','/Lfunction'))
	lifts.append(('Half-Integral Weight Forms','/ModularForm/Mp2/Q'))
	lifts.append(('Siegel Modular Forms','/ModularForm/GSp4/Q'))
	sbar=(properties,parents,friends,siblings,lifts)
	return (info,sbar)
