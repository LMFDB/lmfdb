import flask
from flask import  request
from utilities import *

def ConnectDB():
    import base
    return base.getDBConnection().MaassWaveForm

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

def get_all_levels():
	ret = []
	ret.append(1)	
	Col = ConnectToFS()
	for N in Col.find({},{'Level':1},sort=[('Level',1)]):
		ret.append(int(N['Level']))
        s = set(ret)
        ret = list(s)
        ret.sort()
	return ret
    

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


def get_args_mwf():
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
    level  = _my_get(info,'level', None,int)
    weight = _my_get(info,'weight',None,int) 
    character = _my_get(info,'character', '',str)
    MaassID = _my_get(info,"id", '',int)	
    DBname = _my_get(info,"db",'',str)
    Search = _my_get(info,"search", '',str)
    SearchAll = _my_get(info,"search_all", '',str)
    eigenvalue = _my_get(info,"eigenvalue", '',str)
#int(info.get('weight',0))
    #label  = info.get('label', '')
    info['level']=level; info['weight']=weight; info['character']=character
    info['MaassID']=MaassID
    info['DBname']=DBname
    info['Search']=Search
    info['SearchAll']=SearchAll
    info['eigenvalue']=eigenvalue
    return info


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

def print_table_of_levels(start,stop):
    l = getallgroupsLevel()
    print l
    s="<table><tr><td>"
    for N in l:
        if N < start:
            continue
        if N > stop:
            exit
        url = url_for("render_maass_waveformspace",level=N)
        print "<a href=\"%s\">%s</a>" (url,N)
    s+="</td></tr></table>"
    return s
