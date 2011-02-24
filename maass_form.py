#
# Markus Fraczek <marekf@gmx.net>
#
# TODO: 
# + show only 50 eigenvalues/coefficient pro page 
# + improve search 
#    - show additional information in search results (group,weight,character)
#    - restrict search when items are selected
# + extend database to include more informations (Artkin-Lenher Eigenvalues)
# + implement checks on homepage of maass wave form
# + provide API (class) for users (like L-functions guys) of database 
#
#

from flask import render_template,url_for
import bson
from sets import Set



def ConnectDB():
    import base
    return base.getDBConnection()

def ConnectToFS():
	return ConnectDB().FS

def ConnectToHT():	
	return ConnectDB().HT

def ConnectByName(name):
	if name == "FS":
		return ConnectToFS()
	elif name == "HT":
		return ConnectToHT()
	return None

def GetNameOfPerson(DBname):
	if DBname == "FS":
		return "Fredrik Str&ouml;mberg"
	elif DBname == "HT":
		return "Holger Then"
	return None

def getMaassfromById(DBname,MaassID):
	ret = []
	Col = ConnectByName(DBname)
	try: 
		OBJ = bson.objectid.ObjectId(MaassID)
        except bson.errors.InvalidId:
        	return render_template("maass_form_nav.html", info=info)
	data = Col.find_one({'_id':OBJ})
	ret.append(["Eigenvalue","\(\\lambda=r^2 + \\frac{1}{4} \\ , \\quad r= \\ \)"+str(data['Eigenvalue'])])
	if data['Symmetry'] <> "none":
		ret.append(["Symmetry",data['Symmetry']])
	if DBname == "HT":
		Title = MakeTitle("1","0","0") 
	else:
		Title = MakeTitle(str(data['Level']),str(data['Weight']),str(data['Character']))
	if data['Coefficient']:
		idx = 0
		ANs = []
		for a in data['Coefficient']:
 			ANs.append([idx,a])
			idx = idx +1
		ret.append(["Coefficients",ANs])
	return [Title,ret]
	

def getallgroupsLevel():
	ret = []
	ret.append(str(1))	
	Col = ConnectToFS()
	for N in Col.find({},{'Level':1},sort=[('Level',1)]):
		ret.append(str(N['Level']))
	return set(ret)

def getallweights(Level):
	ret = []
	Col = ConnectToFS()
	for w in (Col.find({'Level':Level},{'Weight':1},sort=[('Weight',1)])):
		ret.append(str(w['Weight']))
	return set(ret)

def getallcharacters(Level,Weight):
	ret = []
	Col = ConnectToFS()
	for c in (Col.find({'Level':Level,'Weight':Weight},{'Character':1},sort=[('Weight',1)])):
                ret.append(str(c['Character']))
	return set(ret)


def searchinDB(search,coll,filds):
	return coll.find(search,filds,sort=[('Eigenvalue',1)])

def WriteEVtoTable(SearchResult,EV_Result,index):
	for ev in SearchResult:
		EV_Result.append([ev['Eigenvalue'],index,ev['Symmetry'],str(ev['_id'])])
		index=index+1
	return index

def getEivenvalues(search,coll,index):
	ret = []
	sr = searchinDB(search,coll,{'Eigenvalue':1,'Symmetry':1})
	WriteEVtoTable(sr,ret,index)
#	for ev in sr:
#                       ret.append([ev['Eigenvalue'],index,ev['Symmetry'],str(ev['_id'])])
#                        index=index+1	
	return [sr.distinct('Symmetry'),ret]

def getEigenvaluesFS(Level,Weight,Character,index):
	return getEivenvalues({'Level':Level,'Weight':Weight,'Character':Character},ConnectToFS(),index)
	
def getEigenvaluesHT(Level,Weight,Character,index):
	if Level != 1 or Weight != 0.0 or Character != 0:
		return [0,[]]
	return getEivenvalues({},ConnectToHT(),index)

def getData(search,coll,index):
	ret = []
        sr = searchinDB(search,coll,{})
        for ev in sr:
		ret.append([ev['Eigenvalue'],index,ev['Symmetry'],str(ev['_id'])])
		index=index+1
        return [sr.distinct('Symmetry'),ret]

#def SearchEigenvaluesFS(Level,Weight,Character,index,eigenvalue):
	


def MakeTitle(level,weight,character):
	ret = "Maass cusp forms for "
	if level:
		if level == "1":
			ret += "\(PSL(2,Z)\)"
		else:
			ret += "\(\Gamma_0("+str(level)+")\)"
	else:
		ret += "\(\Gamma_0(n)\)"
	
	if weight:
		if float(weight) <> 0:
			ret += ",k="+weight

	if character:
		if character <> "0":
			ret += ",\(\chi_"+character+"\) (according to SAGE)"
	
	return ret


def searchforEV(eigenvalue,DBname):
	ret = []
	SearchLimit = 5
	Col = ConnectByName(DBname)
	ev = float(eigenvalue)
#	return getEivenvalues({'Level':Level,'Weight':Weight,'Character':Character},ConnectToFS(),index)
	index = 0
	search1 = Col.find({"Eigenvalue" : {"$gte" : ev}},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',1)],limit=SearchLimit)
	index = WriteEVtoTable(search1,ret,index)	
	
	search2 = Col.find({"Eigenvalue" : {"$lte" : ev}},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',-1)],limit=SearchLimit)
	index = WriteEVtoTable(search2,ret,index)	
	
	return [set(search1.distinct('Symmetry')+search2.distinct('Symmetry')),ret];

"""
search1 = Collection.find({"Eigenvalue" : {"$gte" : ev}},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',1)],limit=2)
                        search2 = Collection.find({"Eigenvalue" : {"$lte" : ev}},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',-1)],limit=2)
                        index=write_eigenvalues(reversed(list(search2)),EVs,index)
                        write_eigenvalues(search1,EVs,index)
"""

def render_webpage(args):
	info = dict(args)
	level = args.get("level", None)
	weight = args.get("weight", None)
	character = args.get("character", None)
	MaassID = args.get("id", None)	
	DBname = args.get("db", None)
	Search = args.get("search", None)
	SearchAll = args.get("search_all", None)
	eigenvalue = args.get("eigenvalue", None)

	info["credit"] = ""
	

	info["learnmore"]= []
        info["learnmore"].append(["Wiki","http://wiki.l-functions.org/ModularForms/MaassForms"])
	

	if MaassID and DBname:
		info["check"]=[]
                info["check"].append(["Hecke relation",url_for('not_yet_implemented')])
		info["check"].append(["Ramanujan-Petersson conjecture",url_for('not_yet_implemented')])
                info["friends"]= []
                info["friends"].append(["L-function",url_for('not_yet_implemented')])
                info["downloads"]= []
                info["downloads"].append(["Maass form data",url_for('not_yet_implemented')])
		
		info["back"] = url_for('render_maass_form')
		[Title,Maassfrom] = getMaassfromById(DBname,MaassID)
		info["info1"] = Title
		info["maass_data"] = Maassfrom
		info["credit"] += GetNameOfPerson(DBname)
		return render_template("maass_form_show.html", info=info)

	info["info1"] = MakeTitle(level,weight,character)	

	if level:
		info['maass_weight'] = getallweights(int(level))
		info['cur_level'] = level

	if level and weight:
		info['cur_weight'] = weight
		info['maass_character'] = getallcharacters(int(level),float(weight))
	
	if level and weight and character:
		info['cur_character'] = character
		
	if eigenvalue:
		index  = 0
		info["maass_eigenvalue"] = []			
		info["search_for_ev"] = eigenvalue
		
		[Sym,EVFS] = searchforEV(eigenvalue,"FS")

		if EVFS:
			info["maass_eigenvalue"].append([GetNameOfPerson("FS"),"FS",Sym,EVFS])	
			info["credit"] += GetNameOfPerson("FS")
		
		[Sym,EVHT] = searchforEV(eigenvalue,"HT")
		if EVHT:
			info["maass_eigenvalue"].append([GetNameOfPerson("HT"),"HT",Sym,EVHT])
                        info["credit"] += " "+GetNameOfPerson("HT")
		
#		if level and weight and character:
#			Res = searchonLWC(eigenvalue,level,weight,character)
#		elif level and weight:
#			Res = searchonLW(eigenvalue,level,weight)
#		elif level:
#			Res = searchonL(eigenvalue,level)
#		else:
#			Res = searchon(eigenvalue)
#               ("Name",DBname,Symetries,Eigenvalues)
#		info["maass_eigenvalue"] 

				

	elif level and weight and character:
		index = 0
		info["maass_eigenvalue"] = []
		[Sym,EVFS] = getEigenvaluesFS(int(level),float(weight),int(character),index)
		if EVFS:
			info["maass_eigenvalue"].append([GetNameOfPerson("FS"),"FS",Sym,EVFS])	
			info["credit"] += GetNameOfPerson("FS")
		[Sym2,EVHT] = getEigenvaluesHT(int(level),float(weight),int(character),index)
		if EVHT:
			info["maass_eigenvalue"].append([GetNameOfPerson("HT"),"HT",Sym2,EVHT])
			info["credit"] += " and "+ GetNameOfPerson("HT")
	
	info['maass_group'] = getallgroupsLevel()
	return render_template("maass_form_nav.html", info=info)	


"""
def write_eigenvalues(search,EVs,index):
	for i in search:
		link=url_for('render_maass_form',id=str(i['_id']))
		EVs.append([i['Eigenvalue'],index,i['Symmetry'], link])
		index=index+1
	return index

def render_webpage(args):
	info = dict(args)
	maassID = args.get("id", None)#[0]
	eigenvalue = args.get("eigenvalue", None)
#	multicheck = args.get("multicheck", None)
	
	import base
	C = base.getDBConnection()
	DB = C.MaassWaveForm
	Collection = DB.HT
	Collection.ensure_index("Eigenvalue")
#	if show == 'all':
#		return render_template("maass_form.html", info=info)
#	else:
	EVs=[]
	index = 0
	info["credit"] = "Holger Then"
        info["info1"] = "Maass cusp forms for \(PSL(2,Z)\)"
        info["info2"] = "list of  \(r\)"
#, Eigenvalue \(\\lambda= \\frac{1}{4}+ r^2\)"

	info["info3"] = "Maass form"
	info["info4"] = "\(\\quad f(z)=const\\sum_{ n \\not= 0}a_n\\sqrt{y}K_{ir}(2\\pi|n|y)e^{2\\pi inx}\)"
	info["info5"] = "Eigenvalue"
#	info["info6"] = "\( \\quad \\lambda=r^2 + \\frac{1}{4} \\ , \\quad r= \\ \) {{ info.eigenvalue  }}  "
#	info["info7"] = "Coefficients"
#	info["info8"] = "\\quad normalization \(a_1=1\)"
#	info["info9"] = "\\quad symmetry \(a_{-1}=\\%c1\)"
#	info["info10"]= "\\quad multiplicity \(a_{mp}=a_{m}a_{p}-a_{m/p}\)\\quad where \(a_{m/p}=0\) if \(p\\not|m\)"
#	info["info11"]= "\\quad prime coefficients \(a_2= \\%.5f \\quad a_3= \\%.5f \\quad a_5= \\%.5f \\quad a_7= \\%.5f \\quad \\ldots\)"

	info["learnmore"]= []
	info["learnmore"].append(["Wiki","http://wiki.l-functions.org/ModularForms/MaassForms"])
	info["learnmore"].append(["Literature","http://arxiv.org/abs/math-ph/0305047"])

	if maassID:
		try: 
			OBJ = bson.objectid.ObjectId(maassID)
		except bson.errors.InvalidId:
			return render_template("maass_form.html", info=info)
		data=Collection.find_one({'_id':bson.objectid.ObjectId(maassID)})
		info["info1"] += ", r="+str(data['Eigenvalue'])
		info["info2"] = str(data['Symmetry'])+' r='+str(data['Eigenvalue'])
		info["link"] = url_for('render_maass_form')
		info["info6"] = "\( \\quad \\lambda= \\frac{1}{4} + r^2 \\ , \\quad r= "+str(data['Eigenvalue'])+"\)"
		info["info7"] = "Symmetry"
		info["info8"] = str(data['Symmetry'])
		ANs = []
		id = 0
		for a in data['Coefficient']:
			ANs.append([id,a])
			id = id +1
		info["an"]= ANs
		info["check"]=[]
		info["check"].append(["Hecke relation",url_for('render_maass_form', multicheck=maassID)])
		info["check"].append(["Ramanujan-Petersson conjecture",url_for('render_maass_form', RPconj=maassID)])
		info["friends"]= []
		info["friends"].append(["L-function",url_for('render_maass_form', Lfunction=maassID)])
#		info["learnmore"]= []
#		info["learnmore"].append(["Wiki","http://wiki.l-functions.org/ModularForms/MaassForms"])
#		info["learnmore"].append(["Literature","http://arxiv.org/abs/math-ph/0305047"])
		info["downloads"]= []
		info["downloads"].append(["Maass form data",url_for('render_maass_form', download=maassID)])
		return render_template("maass_form2.html", info=info)
	else:	
		offset = maassID = args.get("id", 0)
		EVs = []
		index = 0
		if eigenvalue:
			try:
				ev = float(eigenvalue)
			except ValueError:
				return render_template("maass_form.html", info=info)
			search1 = Collection.find({"Eigenvalue" : {"$gte" : ev}},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',1)],limit=2)
			search2 = Collection.find({"Eigenvalue" : {"$lte" : ev}},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',-1)],limit=2)
			index=write_eigenvalues(reversed(list(search2)),EVs,index)
			write_eigenvalues(search1,EVs,index)
			info["info2"] += " search for: "+eigenvalue
		else:
			searchres=Collection.find({},{'Eigenvalue':1,'Symmetry':1},sort=[('Eigenvalue',1)])
			write_eigenvalues(searchres,EVs,index)
		info["ev"] = EVs
		
		return render_template("maass_form.html", info=info)

#find_one({'_id':bson.objectid.ObjectId('fsdfds')})
"""
