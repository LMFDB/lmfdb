import flask
import bson
import pymongo
from flask import render_template, url_for, request, redirect, make_response,send_file
from utils import *
from modular_forms.elliptic_modular_forms.backend.plot_dom import *
from modular_forms.maass_forms.maass_waveforms import MWF,mwf_logger, mwf
#from psage.modform.maass.lpkbessel import *
# build extensions

try:
  #  from modular_forms.maass_forms.backend.lpkbessel import *
  from lpkbessel import *
except Exception as ex:
  mwf_logger.critical("maass_waveforms/views/mwf_utils.py: couldn't load backend. Exception: '%s' To enable full Maass waveform functionality: compile the cython file lpkbessel.pyx with sage -c create_local_so('lpkbessel.pyx')" % ex)
  #try:
  #  # Builds the kbessel extension build_ext --inplace $*
  #  execfile("setup.py") 
  #except Exception as ex1:

mwf_dbname = 'MaassWaveForm'

def connect_db():
    import base
    return base.getDBConnection().mwf_dbname

def get_collection(collection=''):
    db = connect_db()
    if collection in db.collection_names():
        return db.collection
    else:
        return None #raise ValueError,"Need Collection in :",db.collection_names()

def get_collections_info():
    db = connect_db()
    for c in db.collection_names():
        metadata=db.metadata[c]
        mwf_logger.debug("METADATA: {0}".format(metadata))

#def GetNameOfPerson(DBname):
#    if DBname == "FS":
#        return "Fredrik Str&ouml;mberg"
#    elif DBname == "HT":
#        return "Holger Then"
#    return None

def get_maassform_by_id(maass_id,fields=None):
    r"""
    """
    ret = []
    db = connect_db() #Col = ConnectByName(DBname)
    try: 
        obj = bson.ObjectId(str(maass_id))
    except bson.errors.InvalidId:
        data['error']="Invalid id for object in database!"
        #return render_template("mwf_browse.html", info=info)
    else:
        data = None
        try:
            for collection_name in db.collection_names():
                c = pymongo.collection.Collection(db,collection_name)
                data = c.find_one({"_id": obj})
                if data <> None:
                    data['dbname']=collection_name
                    data['num_coeffs']=len(data['Coefficient'])
                    raise StopIteration()
        except StopIteration:
            pass
        if data == None:
            data=dict()
            data['error']="Invalid id for object in database!"
        #return render_template("mwf_browse.html", info=info)
    return data

def set_info_for_maass_form(data):
    ret = []
    ret.append(["Eigenvalue","\(\\lambda=r^2 + \\frac{1}{4} \\ , \\quad r= \\ \)"+str(data['Eigenvalue'])])
    if data['Symmetry'] <> "none":
        ret.append(["Symmetry",data['Symmetry']])
    if data['dbname'] == "HT":
        title = MakeTitle("1","0","0") 
    else:
        title = MakeTitle(str(data['Level']),str(data['Weight']),str(data['Character']))
    if data['Coefficient']:
        idx = 0
        ANs = []
        for a in data['Coefficient']:
            if idx >100:
                break
            ANs.append([idx,a])
            idx = idx +1
        ret.append(["Coefficients",ANs])
    return [title,ret]

def make_table_of_coefficients(maass_id,number=100):
    c = get_maassform_by_id(maass_id,fields=['Coefficient'])['Coefficient']
    logger.info("ID=%s" % maass_id)
    logger.info("number=%s" % number)
    s="<table border=\"1\">\n<thead><tr><td>\(n\)</td>"
    s+="<td>&nbsp;</td>"
    s+="<td>\(a(n)\)</td></tr></thead>\n"
    s+="<tbody>\n"
    number = min(number,len(c))
    for n in xrange(number):
        s+="<tr><td> %s </td><td></td><td>%s </td> \n" % (n+1,c[n])
    s+="</tbody></table>\n"
    return s



def get_all_levels():
    ret = []
    db = connect_db()
    for c in db.collection_names():
        Col = db[c]
        for N in Col.find({},{'Level':1},sort=[('Level',1)]):
            print "N=",N
            ret.append(int(N['Level']))
    #s = set(ret)
    #ret = list(s)
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

def get_search_parameters(info):
    ret=dict()
    if not info.has_key('search') or not info['search']:
        return ret
    
    ret['level_lower']=my_get(info,'level_lower',-1,int)
    ret['level_upper']=my_get(info,'level_upper',-1,int)
    ret['rec_start']=my_get(info,'rec_start',1,int)
    ret['limit']=my_get(info,'limit',20,int)
    ret['weight']=my_get(info,'weight',0,int)
    ev_range = my_get(info,'ev_range','').split('-')
    if len(ev_range)==0:
        ret['ev_lower']=0
        ret['ev_upper']=0
    elif len(ev_range)==1:
        ret['ev_lower']=ev_range[0]
        ret['ev_upper']=ev_range[0]
    else:
        ret['ev_lower']=ev_range[0] #my_get(info,'ev_lower',None)
        ret['ev_upper']=ev_range[1] #my_get(info,'ev_upper',None)
    return ret


def print_table_of_maass_waveforms(collection,lrange=[],erange=[]):
    r"""
    Print table of Maass waveforms
    """
    tbl="<table><tr>"
    skip = erange[0]
    limit= erange[1]-erange[0]
    cols = get_collection(collection)
    if not cols:
        cols=list()
        for c in connect_db().collection_names():
            cols.append[connect_db()[c]]
    print "Collections:",cols
    tbl+="<td valign=\"top\"><table>"
    for N in range(lrange[0],lrange[1]):
        #tbl+="<tr><td>"
        
        evs=list()
        for c in cols:
            finds=c.find({'Level':1}).skip(skip).limit(limit)
            for f in finds:
                maass_id = f['_id']
                R = f['Eigenvalue']
                #k = f['Weight']
                url = url_for('mwf.render_one_maass_waveform',objectid=str(maass_id),db=c.name)
                s="<tr class=\"%s\"><td><a href=\"%s\">%s</a></td></tr>\n" %(c.name,url,R)
                evs.append([R,s])
        evs.sort()
        tbl_one_level=""
        for R,s in evs:
            tbl_one_level+=s
        mwf_logger.debug("Tbl for {0} is {1}".format(N,tbl_one_level))
        tbl+=tbl_one_level
    return tbl
          
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


def search_for_eigenvalues(search):
    ev_l=float(search['ev_lower'])
    ev_u=float(search['ev_upper'])
    if ev_l and ev_u:
        ev_range={"$gte" : ev_l,"$lte":ev_u}
    elif ev_u:
        ev_range={"$lte":ev_u}
    elif ev_l:
        ev_range={"$gte":ev_l}
    level_l=int(search['level_lower'])
    level_u=int(search['level_upper'])
    level_range=None
    if level_l>0 and level_u>0:
        level_range={"$gte" : level_l,"$lte":level_u}
    elif level_u>0:
        level_range={"$lte":level_u}
    elif level_l>0:
        level_range={"$gte":level_l}        
    weight=float(search['weight'])
    rec_start=search['rec_start']
    limit=search['limit']
    res = dict()
    res['weights']=[]
    #SearchLimit = limit_u
    db = ConnectDB()
    index = 0
    data = None
    searchp={'fields':['Eigenvalue','Symmetry','Level','Character','Weight','_id'],
             'sort':[('Eigenvalue',pymongo.ASCENDING),('Level',pymongo.ASCENDING)],
             'spec':{"Eigenvalue" : ev_range}}
    if level_range:
        searchp['spec']["Level"]= level_range
    if limit>0:
        searchp['limit']=rec_start+limit


    # the limit of number of records is 'global', for all collections.
    # is this good? 
    print "searchp=",searchp
    index=0
    search['more']=0
    search['rec_start']=rec_start
    search['rec_stop']=-1
    for collection_name in db.collection_names():
        if collection_name in ['system.indexes','contributors']:
            continue
        c = pymongo.collection.Collection(db,collection_name)
        res[collection_name]=list()
        print "c=",c
        f = c.find(**searchp)
        search['num_recs']=f.count()
        for rec in f:
            print  "rec=",rec
            wt = my_get(rec,'Weight',0,float)
            #print "index=",index
            if index >= rec_start and index < limit+rec_start:
                res[collection_name].append(rec)
                if res['weights'].count(wt)==0:
                    res['weights'].append(wt)
            index=index+1
            if index > limit+rec_start:
                search['rec_stop']=index-1
                search['more']=1
                #if len(res[collection_name])<f.count():
                print "There are more to be displayed!"
                exit
    if search['rec_stop']<0:
        search['rec_stop']=limit+rec_start
    return res

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
        print "req:get=",request.args
    else:
	info   = to_dict(request.form)
        print "req:post=",request.form
    # fix formatting of certain standard parameters
    level  = my_get(info,'level', None,int)
    weight = my_get(info,'weight',0,int) 
    character = my_get(info,'character', '',str)
    MaassID = my_get(info,"id", '',int)	
    DBname = my_get(info,"db",'',str)
    search = my_get(info,"search", '',str)
    SearchAll = my_get(info,"search_all", '',str)
    eigenvalue = my_get(info,"eigenvalue", '',str)
    collection = my_get(info,"collection", 'all',str)
#int(info.get('weight',0))
    #label  = info.get('label', '')
    info['level']=level; info['weight']=weight; info['character']=character
    info['MaassID']=MaassID
    info['DBname']=DBname
    info['search']=search
    info['collection']=collection
    info['SearchAll']=SearchAll
    info['eigenvalue']=eigenvalue
    return info


def my_get(dict,key,default,f=None):
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
        url = url_for(".render_maass_waveformspace",level=N)
        print "<a href=\"%s\">%s</a>" (url,N)
    s+="</td></tr></table>"
    return s




def ajax_once(callback,*arglist,**kwds):
    r"""
    """
    
    text = kwds.get('text', 'more')
    print "text=",text
    print "arglist=",arglist
    print "kwds=",kwds
    #print "req=",request.args
    nonce = hex(random.randint(0, 1<<128))
    res = callback()
    url = ajax_url(ajax_once,arglist,kwds,inline=True)
    s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
    #	s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {'level':22,'weight':4},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
    s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {a:1},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
    return s0+s1

def my_get(dict,key,default,f=None):
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

   
def eval_maass_form(R,C,M,x,y):
    s=0
    twopi=RR(2*Pi)
    twopii=CC(I*2*Pi)
    sqrty=y.sqrt()
    for n in range(1,M):
        tmp=sqrty*besselk_dp(R,twopi*n*y)*exp(twopii*n*x)
        s = s+tmp*C[n]
    return s

def plot_maass_form(R,N,C,**kwds):
    r"""
    Plot a Maass waveform with eigenvalue R on Gamma_0(N), using coefficients from the vector C.
    
    """



