import flask
import bson
import pymongo
from flask import render_template, url_for, request, redirect, make_response,send_file
from utils import *
from modular_forms.elliptic_modular_forms.backend.plot_dom import *
from modular_forms.maass_forms.maass_waveforms import MWF,mwf_logger, mwf
from knowledge.knowl import Knowl
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
    return base.getDBConnection()[mwf_dbname]

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



def get_distinct_keys(key):
    res = []
    db = connect_db()
    for c in db.collection_names():
        res.extend(db[c].distinct(key))
    res = set(res)
    res = list(res)
    return res

def get_all_levels():
    return get_distinct_keys('Level')

def get_all_weights(Level):
    return get_distinct_keys('Weight')


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
    #ret['level_lower']=my_get(info,'level_lower',-1,int)
    #ret['level_upper']=my_get(info,'level_upper',-1,int)
    level_range = my_get(info,'level_range','').split('..')
    if len(level_range)==0:
        ret['level_lower']=0
        ret['level_upper']=0
    elif len(level_range)==1:
        ret['level_lower']=level_range[0]
        ret['level_upper']=level_range[0]
    else:
        ret['level_lower']=level_range[0] #my_get(info,'ev_lower',None)
        ret['level_upper']=level_range[1] #my_get(info,'ev_upper',None)
    if ret['level_lower']>0 and ret['level_upper']>0:
        level_range={"$gte" : ret['level_lower'],"$lte":ret['level_upper']}
    elif ret['level_upper']>0:
        level_range={"$lte":ret['level_upper']}
    elif ret['level_lower']>0:
        level_range={"$gte":ret['level_lower']}        

    ret['rec_start']=my_get(info,'rec_start',1,int)
    ret['limit']=my_get(info,'limit',20,int)
    ret['weight']=my_get(info,'weight',0,int)
    ev_range = my_get(info,'ev_range','').split('..')
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

from knowledge import logger
from base import getDBConnection

class MWFTable(object):
    def __init__(self,db_name,collection='all',skip=[0,0],limit=[6,10],keys=['Level','Eigenvalue'],weight=0):
        r"""
        Skip tells you how many chunks of data you want to skip (from the geginning) and limit tells you how large each chunk is.
        """
        self.collection=collection
        self.keys=keys
        self.skip=skip
        self.limit=limit
        self.db = connect_db()
        self.metadata=[]
        self.title=''
        self.cols=[]
        self.get_collections()
        self.table=[]
        self.wt=weight

    def set_collection(self,collection):
        r"""
        Change collection.
        """
        self.collection=collection
        self.get_collections()
        
    def shift(self,i=1,key='Level'):
        if not key in self._keys:
            logger.warning("{0} not a valid key in {1}".format(key,self._keys))
        else:
            ix = self._keys.index[key]
            self.skip[ix]+=i

    def get_collections(self):
        cols = get_collection(self.collection)        
        if not cols:
            cols=list()
            for c in self.db.collection_names():
                if c<>'system.indexes' and c<>'metadata':
                    print "cc=",c
                cols.append(self.db[c])        
        self.cols=cols

    def get_metadata(self):
        if not self.cols:
            self.get_collections()
        metadata=list()
        for c in self.cols:
            f=self.db.metadata.find({'c_name':c.name})
            for x in f:
                print "x=",x
                metadata.append(x)
        self.metadata=metadata
        

    def set_table(self):
        logger.debug("skip= {0}".format(self.skip))
        logger.debug("limit= {0}".format(self.limit))
        self.table=[]
        level_ll=(self.skip[self.keys.index('Level')])*self.limit[self.keys.index('Level')]
        level_ul=(self.skip[self.keys.index('Level')]+1)*self.limit[self.keys.index('Level')]
        ev_limit=self.limit[self.keys.index('Eigenvalue')]
        ev_skip=self.skip[self.keys.index('Eigenvalue')]*ev_limit
        for N in get_all_levels():
            N=int(N)
            if N<level_ll:
                continue
            if N>level_ul:
                break
            evs=[]
            for c in self.cols:
                finds=c.find({'Level':N,'Weight':self.wt}).sort('Eigenvalue',1).skip(ev_skip).limit(ev_limit);
                for f in finds:
                    _id = f['_id']
                    R = f['Eigenvalue']
                    url = url_for('mwf.render_one_maass_waveform',objectid=str(_id),db=c.name)
                    evs.append([R,url,c.name])
            evs.sort()
            # If we have too many we delete the 
            while len(evs)>ev_limit:
                t=evs.pop()
                logger.debug("removes {0}".format(t))
            #logger.debug("found eigenvalues in {0} is {1}".format(c.name,evs))
            self.table.append({'N':N,'evs':evs})
        

    ## def print_table(self):
    ##     r"""
    ##     Prints the table with current limits set.
    ##     """
    ##     # def print_table_of_maass_waveforms(collection,lrange=[],erange=[],wt=0):


    ##     logger.debug("names={0}".format(db.collection_names()))

    ##     tbl="<table class=\"ntdata\"><thead><tr><td></td></tr></thead>"
    ##     tbl+="<tbody><tr>" 
    ##     levels = get_all_levels(); levels.sort()
    ##     mwf_logger.debug("levels= {0}".format(levels))
    ##     col_info=dict()
    ##     for c in db.collection_names():
    ##         k=Knowl("mwf.collections.{0}".format(c))
    ##         col_info[c]=k
    ##     print "col info=",col_info

    ##     evs=list()
    ##     print "N=",N

    ##     if len(evs)>0:
    ##         tbl_one_level="<td valign=\"top\">"
    ##         tbl_one_level+="<table class=\"ntdata\">\n<thead><tr><td>Level {0}</td></tr></thead>\n<tbody>".format(N)
    ##         cl="odd"
    ##     for R,_id,name in evs:
    ##         if cl=="odd":
    ##             cl="even"
    ##         else:
    ##             cl="odd"
    ##         url = url_for('mwf.render_one_maass_waveform',objectid=str(_id),db=name)
    ##         s="<tr class=\"{0}\"><td><a href=\"{1}\">{2}</a> ".format(cl,url,R)
    ##         #s+="{{{{Knowl('mwf.collections.{0}')}}}}</td></tr>\n".format(name)
    ##         s+=str(col_info[name])+"</td></tr>\n"
    ##         tbl_one_level+=s
    ##     if len(evs)>0:
    ##         tbl_one_level+="</tbody></table></td>"
    ##         mwf_logger.debug("Tbl for {0} is {1}".format(N,tbl_one_level))
    ##         tbl+=tbl_one_level
    ## tbl+="</tr></tbody></table>"
    ## return tbl
          
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
    level_l=float(search['level_lower'])
    level_u=float(search['level_upper'])
    if level_l>0 and level_u>0:
        level_range={"$gte" : level_l,"$lte":level_u}
    elif level_u>0:
        level_range={"$lte":level_u}
    elif level_l>0:
        level_range={"$gte":level_l}        
    if ev_l>0 and ev_u>0:
        ev_range={"$gte" : ev_l,"$lte":ev_u}
    elif ev_u>0:
        ev_range={"$lte":ev_u}
    elif ev_l>0:
        ev_range={"$gte":ev_l}        
    weight=float(search['weight'])
    rec_start=search['rec_start']
    limit=search['limit']
    res = dict()
    res['weights']=[]
    #SearchLimit = limit_u
    db = connect_db()
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
    browse = my_get(info,"browse", '',str)
    eskip= my_get(info,"ev_skip", '',str)
    erange= my_get(info,"ev_range", '',str)
    lskip= my_get(info,"level_skip", '',str)
    lrange= my_get(info,"level_range", '',str)
#int(info.get('weight',0))
    #label  = info.get('label', '')
    info['level']=level; info['weight']=weight; info['character']=character
    info['MaassID']=MaassID
    info['DBname']=DBname
    info['search']=search
    info['collection']=collection
    info['SearchAll']=SearchAll
    info['eigenvalue']=eigenvalue
    info['browse']=browse
    info['ev_skip']=eskip
    info['level_skip']=lskip
    info['level_range']=lrange
    info['ev_range']=erange
    
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



