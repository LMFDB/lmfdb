r"""

AUTHORS:

 Markus Fraczek <marekf@gmx.net> (2010)
 Fredrik Stroemberg (2011-)



 TODO: 
 + show only 50 eigenvalues/coefficient pro page 
 + improve search 
    - show additional information in search results (group,weght,character)
    - restrict search when items are selected
 + extend database to include more informations (Artkin-Lenhe Eigenvalues)
 + implement checks on homepage of maass wave form
 + provide API (class) for users (like L-functions guys) of database 


"""
import base
from base import app
from flask import render_template, url_for, request, redirect, make_response,send_file
import bson
import pymongo
from sage.all import is_odd,is_even
#mwf = flask.Blueprint('mwf', __name__, template_folder="templates",static_folder="static")
import utils
from  modular_forms.maass_forms.maass_waveforms import MWF,mwf_logger, mwf
from modular_forms.maass_forms.maass_waveforms.backend.mwf_utils import *
from modular_forms.maass_forms.maass_waveforms.backend.mwf_classes import MaassFormTable,WebMaassForm
from modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db import MaassDB
from mwf_upload_data import *
logger = mwf_logger


# this is a blueprint specific default for the tempate system.
# it identifies the body tag of the html website with class="wmf"
@mwf.context_processor
def body_class():
  return { 'body_class' : MWF }

met = ['GET','POST']
@mwf.route("/",methods=met)
@mwf.route("/<int:level>/",methods=met)
@mwf.route("/<int:level>/<int:weight>/",methods=met)
@mwf.route("/<int:level>/<int:weight>/<int:character>/",methods=met)
@mwf.route("/<int:level>/<int:weight>/<int:character>/<float:r1>/",methods=met)
@mwf.route("/<int:level>/<int:weight>/<int:character>/<float:r1>/<float:r2>/",methods=met)
def render_maass_waveforms(level=0,weight=-1,character=-1,r1=0,r2=0,**kwds):
    info = get_args_mwf(level=level,weight=weight,character=character,r1=r1,r2=r2,**kwds)
    print "INFO=",info
    info["credit"] = ""
    info["learnmore"]= []
    info["learnmore"].append(["Wiki","http://wiki.l-functions.org/ModularForms/MaassForms"])
    # if we submit a search we search the database:
    mwf_logger.debug("args=%s"%request.args)
    mwf_logger.debug("method=%s"%request.method)
    mwf_logger.debug("req.form=%s"%request.form)
    mwf_logger.debug("info=%s"%info)
    if info.get('maass_id',None) and info.get('db',None):
        return render_one_maass_waveform_wp(**info)
    if info['search'] or info['browse']:
        search = get_search_parameters(info)
        return render_search_results_wp(info,search)

 
    if not info['collection'] or info['collection']=='all':
        md = get_collections_info()
    info['cur_character'] = character
    #info["info1"] = MakeTitle(level,weight,character)  
    if level:
        info['maass_weight'] = getallweights(int(level))
        info['cur_level'] = level
        
    if level and weight:
        info['cur_weight'] = weight
        info['maass_character'] = getallcharacters(int(level),float(weight))
        
    if level and weight and character:
        info['cur_character'] = character       
    title='Maass forms'
    info['list_of_levels']=get_all_levels()
    if info['list_of_levels']:
        info['max_level']=max(info['list_of_levels'])
    else:
        info['max_level']=0
    mwf_logger.debug("info3=%s"%info)
    return render_template("mwf_navigate.html", info=info,title=title)
    #return render_browse_maass_waveforms(info=info,title=title)
    #return render_template("mwf_browse.html", info=info,title=title)

    
def render_maass_waveform_space(level,weight,character,**kwds):
    mwf_logger.debug("in_render_maass_form_space {0},{1},{2},{3}".format(level,weight,character,kwds))
    title="Space of Maass forms"
    skip=int(kwds.get('skip',0))
    limit=int(kwds.get('limit',10))
    table=MWFTable(skip=skip,limit=limit)
    table.set_table({'level':level,'weight':weight,'character':character})
    info={'table':table}
    return render_template("mwf_browse.html", info=info,title=title)


def render_maass_waveforms_for_one_group(level,**kwds):
    DB = connect_db()
    res  = dict()
    info=dict()
    mwf_logger.debug("collections {0}".format(DB.collection_names()))
    for collection_name in DB.collection_names():
        res[collection_name] = list()
        C = pymongo.collection.Collection(DB,collection_name)
        mwf_logger.debug("Collection {0}".format(C))
        L = C.find({'Level':level,'Weight':0.0})
        for F in L:
            mwf_logger.debug("F: {0}".format(F))
            try:
                id = F['_id']
                R  =  F['Eigenvalue']
                k =   F['Weight']
                res[collection_name].append((R,k,id))
            except:
                pass
        res[collection_name].sort()
    # now we have all maass waveforms for this group
    s="<table><tr>"
    for name in res.keys():
        if(len(res[name])==0):
            continue
        s+="<td valign='top'>"
        s+="<table><thead>"
        s+=" <tr><td valign='top'>Collection:"+name
        s+="     </td></tr></thead>"
        s+="<tbody>"
        for (R,k,id) in res[name]:
            url = url_for('mwf.render_one_maass_waveform',maass_id=str(id),db=name)
            s+="<tr><td><a href=\"%s\">%s</a></td></tr>" %(url,R)
        s+="</tbody>"
        s+="</table>"
        s+="</td>"
    s+="</tr></table>"
    #print "S=",s
    info['table_of_eigenvalues']=s
    title="Maass forms for \(\Gamma_{0}("+str(level)+")\)"
    bread=[('Maass forms',url_for('.render_maass_waveforms'))]
    return render_template("mwf_one_group.html", info=info,title=title)


@mwf.route("/<maass_id>",methods=['GET','POST'])
def render_one_maass_waveform(maass_id,**kwds):
    mwf_logger.debug("in_render_one_maass_form")
    if kwds.get('download','')=='coefficients':
        C,fname = DB.get_coefficients({"_id":self._maassid},filename='True')
        filename=fname+'.txt'
        strIO = StringIO.StringIO()
        strIO.write(s)
        strIO.seek(0)
        try:
            return send_file(strIO,
                             attachment_filename=filename,
                             as_attachment=True)
        except IOError:
            info['error']="Could not send file!"
            
    else:
        info = get_args_mwf()
        info['maass_id']=maass_id
        #mwf_logger.debug("id1={0}".format(id))
        return render_one_maass_waveform_wp(info)


    
def render_one_maass_waveform_wp(info):
    r"""
    Render the webpage of one Maass waveform.
    """
    info["check"]=[]
    DB=connect_db()
    maass_id = info['maass_id']
    mwf_logger.debug("id1={0}".format(maass_id))
    # Create the link to the L-function (put in '/L' at the beginning and '/' before '?'
    Llink = "/L"+url_for('mwf.render_one_maass_waveform',maass_id=maass_id) #+ '/?db=' + info['db']
    
    info["friends"]= [("L-function",Llink)]
    info['bread']=[('Maass waveforms',url_for('.render_maass_waveforms'))]
    info["downloads"]= []
    lenc = 20
    mwf_logger.debug("count={0}".format(DB.count()))
    info['MF'] = WebMaassForm(DB,maass_id)
    mwf_logger.debug("tabl={0}".format(info['MF'].table))
    properties =  [('Level',[info['MF'].level]),
                   ('Symmetry',[info['MF'].even_odd()]),
                   ('Weight',[info['MF'].the_weight()]),
                   ('Character',[info['MF'].the_character()]),
                   ('Fricke Eigenvalue',[info['MF'].fricke()])]
    info['title']="Maass forms on \(\Gamma_{0}( %s )\)" % (info['MF'].level)
    info['properties2']=properties
    return render_template("mwf_one_form.html",**info)


def render_one_maass_waveform_wp_old(info):
    r"""
    Render the webpage of one Maass waveform.
    """
    info["check"]=[]
    #info["check"].append(["Hecke relation",url_for('not_yet_implemented')])
    #info["check"].append(["Ramanujan-Petersson conjecture",url_for('not_yet_implemented')])
    maass_id = info['maass_id']
    #dbname=info['db']
    info["friends"]= []
    info["friends"].append(["L-function","L/"+url_for('.render_one_maass_waveform',maass_id=maass_id)])
    info["downloads"]= []
    #info["downloads"].append(["Maass form data",url_for('not_yet_implemented')])
    bread=[('Maass forms',url_for('.render_maass_waveforms'))]
    properties=[]
    data = get_maassform_by_id(maass_id)
    lenc = 20
    if not data.has_key('error'):
        [title,maass_info] =  set_info_for_maass_form(data)
        info["maass_data"] = maass_info
        #rint "data=",info["maass_data"]
        numc=data['num_coeffs']
        mwf_logger.debug("numc={0}".format(numc))
        if(numc>0):
            #if numc > 10:
                #largs = [{'maass_id':maass_id,'number':k} for k in range(10,numc,50)]
                #mwf_logger.debug("largs={0}".format(largs))
            info['coefficients']=make_table_of_coefficients(maass_id,len,offest) #,largs,text='more')
            #else:
            #    info['coefficients']=make_table_of_coefficients(maass_id)
        else:
            info["maass_data"].append(['Coefficients',''])
            
            s='No coefficients in the database for this form!'
            info['coefficients']=s
        #info['list_spaces']=ajax_once(make_table_of_spaces_fixed_level,*largs,text='more',maass_id=maass_id)
        #info["coefficients"]=table_of_coefficients(
        info["credit"] = GetNameOfPerson(data['dbname'])
        level = data['Level']
        R = data['Eigenvalue']
        title="Maass forms on \(\Gamma_{0}(%s)\) with R=%s" %(level,R)
        ## We see if there is a plot file associated to this waveform
        if data.has_key('plot'):
            mwf_logger.error("file={0}".format(data['plot']))
    else:
        print "data=",data
        title="Could not find this Maass form in the database!"
        info['error']=data['error']


    bread=[('Maass forms',url_for('.render_maass_waveforms'))]
    return render_template("mwf_one_maass_form.html", info=info,title=title,bread=bread,properties=properties)

    

    


def render_search_results_wp(info,search):
    # res contains a lst of Maass waveforms
    mwf_logger.debug("in render_search_results. info=".format(info))
    mwf_logger.debug("Search:".format(search))
    evs={'table':{}}
    table=[]
    nrows=0
    DB=connect_db()
    if not isinstance(search,dict):
        search={}
    if not search.has_key('limit'):
        search['limit']=2000
    if not search.has_key('skip'):
        search['skip']=0        
    finds  = DB.get_Maass_forms(search)
    for f in finds:
            row={}
            R = f.get('Eigenvalue',None)
            N = f.get('Level',None)
            k = f.get('Weight',None)
            if R==None or N==None or k==None:
                continue
            row['R']=R; row['N']=N;
            if k==0 or k==1:
                row['k']=int(k)
            else:
                row['k']=k
            row['ch']=f.get('Character',0)
            st = f.get('Symmetry')
            if st==1:
                st = "odd"
            elif st==0:
                st = "even"
            else:
                st = "undefined"
            row['symmetry']=st
            er = f.get('Error',0)
            if er>0:
                er = "{0:2.1e}".format(er)
            else:
                er="undefined"
            row['err']=er
            dim = f.get('Dim',None)
            if dim==None:
                dim="undefined"
            row['dim']=dim
            cev=f.get('Cusp_evs',[])
            if isinstance(cev,list):
                if len(cev)>1:
                    fricke=cev[1]
                    row['fricke']=fricke
                row['cuspevs']=cev
                url = url_for('mwf.render_one_maass_waveform',maass_id=f.get('_id',None))
            row['url']=url
            nrows+=1
            table.append(row) 
    evs['table']['data']=table
    evs['table']['nrows']=nrows
    evs['table']['ncols']=9
    evs['table']['colheads']=['Level','Weight','Char','Eigenvalue',
                              'Symmetry','Error',
                              'Dimension','Fricke involution','Atkin-Lehner eigenvalues']
    bread=[('Modular forms',url_for('mf.modular_form_main_page')),
           ('Maass forms',url_for('.render_maass_waveforms'))]
    info['bread']=bread
    info['evs']=evs
    if info.get('browse',None)<>None:
        info['title']='Browse Maassforms'
    else:
        info['title']='Search Results'
    return render_template("mwf_display_search_result.html", **info)


def render_browse_maass_waveforms(info,title):
    r"""
    Render a page for browsing Maass forms.
    """
    ## Paging parameters
    level_range=6
    ev_range = 20
    if info['level_skip']:
        level_skip=info['level_skip']*level_range
    else:
        level_skip=0
    if info['ev_skip']:
        ev_skip=info['ev_skip']*ev_range
    else:
        ev_skip=0        
    lrange=[level_skip+1,level_skip+level_range]
    erange=[ev_skip+1,ev_skip+ev_range]
    weight=info.get('weight',0)
    TT=MWFTable(mwf_dbname,collection='all',skip=[0,0],limit=[6,10],keys=['Level','Eigenvalue'],weight=weight)
    TT.set_table()
    TT.get_metadata()
    info['table']=TT
    #s = print_table_of_maass_waveforms(info['collection'],lrange=lrange,erange=erange)
    #info['table']=s
    bread=[('Modular forms',url_for('mf.modular_form_main_page')),('Maass forms',url_for('.render_maass_waveforms'))]
    return render_template("mwf_browse.html", info=info,title=title,bread=bread)



def render_browse_all_eigenvalues(info,**kwds):
    evs={'table':{}}
    table=[]
    nrows=0
    DB=connect_db()
    for coll in DB._show_collection:
        #coll=DB._show_collection[i]
        mwf_logger.debug("coll:{0}".format(coll))
        mwf_logger.debug("f.name={0}".format(coll.name))
        finds = coll.find()
        mwf_logger.debug("f.num={0}".format(finds.count()))
        for f in finds:
            row={}
            R = f.get('Eigenvalue',None)
            N = f.get('Level',None)
            k = f.get('Weight',None)
            if R==None or N==None or k==None:
                continue
            row['R']=R; row['N']=N;
            if k==0 or k==1:
                row['k']=int(k)
            else:
                row['k']=k
            row['ch']=f.get('Character',0)
            st = f.get('Symmetry')
            if st==1:
                st = "odd"
            elif st==0:
                st = "even"
            else:
                st = "undefined"
            row['symmetry']=st
            er = f.get('Error',0)
            if er>0:
                er = "{0:2.1e}".format(er)
            else:
                er="undefined"
            row['err']=er
            dim = f.get('Dim',None)
            if dim==None:
                dim="undefined"
            row['dim']=dim
            cev=f.get('Cusp_evs',[])
            if isinstance(cev,list):
                if len(cev)>1:
                    fricke=cev[1]
                    row['fricke']=fricke
                row['cuspevs']=cev
                url = url_for('mwf.render_one_maass_waveform',maass_id=f.get('_id',None))
            row['url']=url
            nrows+=1
            table.append(row) 
    evs['table']['data']=table
    evs['table']['nrows']=nrows
    evs['table']['ncols']=9
    evs['table']['colheads']=['Level','Weight','Char','Eigenvalue',
                              'Symmetry','Error',
                              'Dimension','Fricke involution','Atkin-Lehner eigenvalues']
    bread=[('Modular forms',url_for('mf.modular_form_main_page')),
           ('Maass forms',url_for('.render_maass_waveforms'))]
    info['bread']=bread
    info['evs']=evs

    return render_template("mwf_browse_all_eigenvalues.html", **info)
    
"""
def write_eigenvalues(search,EVs,index):
        for i in search:
                link=url_for('.render_maass_form',id=str(i['_id']))
                EVs.append([i['Eigenvalue'],index,i['Symmetry'], link])
                index=index+1
        return index

def render_webpage(args):
        info = dict(args)
        maassID = args.get("id", None)#[0]
        eigenvalue = args.get("eigenvalue", None)
#       multicheck = args.get("multicheck", None)
        
        import base
        C = base.getDBConnection()
        DB = C.MaassWaveForm
        Collection = DB.HT
        Collection.ensure_index("Eigenvalue")
#       if show == 'all':
#               return render_template("maass_form.html", info=info)
#       else:
        EVs=[]
        index = 0
        info["credit"] = "Holger Then"
        info["info1"] = "Maass cusp forms for \(PSL(2,Z)\)"
        info["info2"] = "list of  \(r\)"
#, Eigenvalue \(\\lambda= \\frac{1}{4}+ r^2\)"

        info["info3"] = "Maass form"
        info["info4"] = "\(\\quad f(z)=const\\sum_{ n \\not= 0}a_n\\sqrt{y}K_{ir}(2\\pi|n|y)e^{2\\pi inx}\)"
        info["info5"] = "Eigenvalue"
#       info["info6"] = "\( \\quad \\lambda=r^2 + \\frac{1}{4} \\ , \\quad r= \\ \) {{ info.eigenvalue  }}  "
#       info["info7"] = "Coefficients"
#       info["info8"] = "\\quad normalization \(a_1=1\)"
#       info["info9"] = "\\quad symmetry \(a_{-1}=\\%c1\)"
#       info["info10"]= "\\quad multiplicity \(a_{mp}=a_{m}a_{p}-a_{m/p}\)\\quad where \(a_{m/p}=0\) if \(p\\not|m\)"
#       info["info11"]= "\\quad prime coefficients \(a_2= \\%.5f \\quad a_3= \\%.5f \\quad a_5= \\%.5f \\quad a_7= \\%.5f \\quad \\ldots\)"

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
                info["link"] = url_for('.render_maass_form')
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
                info["check"].append(["Hecke relation",url_for('.render_maass_form', multicheck=maassID)])
                info["check"].append(["Ramanujan-Petersson conjecture",url_for('.render_maass_form', RPconj=maassID)])
                info["friends"]= []
                info["friends"].append(["L-function",url_for('.render_maass_form', Lfunction=maassID)])
#               info["learnmore"]= []
#               info["learnmore"].append(["Wiki","http://wiki.l-functions.org/ModularForms/MaassForms"])
#               info["learnmore"].append(["Literature","http://arxiv.org/abs/math-ph/0305047"])
                info["downloads"]= []
                info["downloads"].append(["Maass form data",url_for('.render_maass_form', download=maassID)])
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
