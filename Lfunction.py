import re
import logging

from flask import render_template, url_for, make_response, abort, redirect
from sage.all import *
import tempfile, os
import pymongo
from WebLfunction import *
import LfunctionNavigationProcessing
import LfunctionPageProcessing
import LfunctionComp
import LfunctionPlot
from utils import to_dict
#from elliptic_curve import by_cremona_label
# just testing



cremona_label_regex = re.compile(r'(\d+)([a-z])+(\d*)')

def render_webpage(request, arg1, arg2, arg3, arg4, arg5):
    args = request.args
    temp_args = to_dict(args)
    if len(args) == 0: 
        if arg1 == None: # this means we're at the start page
            info = set_info_for_start_page()
            return render_template("LfunctionNavigate.html", info = info, title = 'L-functions', bread=info['bread'])
        elif arg1.startswith("degree"):
            degree = int(arg1[6:])
            info = { "degree" : degree }
            info["key"] = 777
            info["bread"] =  [('L-functions', url_for("render_Lfunction")), ('Degree '+str(degree), '/L/degree'+str(degree))]
            if degree == 1:
                info["contents"] = [LfunctionPlot.getOneGraphHtmlChar(1,35,1,13)]
                info['friends'] = [('Dirichlet Characters', '/Character/Dirichlet/')]
            elif degree == 2:
#                info["contents"] = [processEllipticCurveNavigation(args),"holomorphic here"]
                info["contents"] = [processEllipticCurveNavigation(args), LfunctionPlot.getOneGraphHtmlHolo(1, 22, 2, 14)]
            elif degree == 3 or degree == 4:
                info["contents"] = LfunctionPlot.getAllMaassGraphHtml(degree)
                
            return render_template("DegreeNavigateL.html", info=info, title = 'Degree ' + str(degree)+ ' L-functions', bread = info["bread"])
            
        elif arg1 == 'custom': # need a better name
            return "not yet implemented"
            
    # args may or may not be empty
    # what follows are all things that need homepages

    if arg1 == 'Riemann':
        temp_args['type'] = 'riemann'
    elif arg1 == 'Character' and arg2 == 'Dirichlet' and arg3 == '1' and arg4 == '0':
        temp_args['type'] = 'riemann'
    elif arg1 == 'Character' and arg2 == 'Dirichlet':
        temp_args['type'] = 'dirichlet'
        temp_args['charactermodulus'] = arg3
        temp_args['characternumber'] = arg4 

    elif arg1 == 'EllipticCurve' and arg2 == 'Q':
        temp_args['type'] = 'ellipticcurve'
        temp_args['label'] = str(arg3) 

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 == 'Q' and arg4 == 'holomorphic': # this has args: one for weight and one for level
        temp_args['type'] = 'gl2holomorphic'
        logging.info(temp_args)

    elif arg1 == 'ModularForm' and arg2 == 'GL2'and arg3 == 'Q' and arg4 == 'maass':
        temp_args['type'] = 'gl2maass'
    
    elif arg1 == 'ModularForm' and arg2 == 'GSp4'and arg3 == 'Q' and arg4 == 'maass':
        temp_args['type'] = 'sp4maass'
        temp_args['source'] = args['source']

    elif arg1 == 'ModularForm' and arg2 == 'GL4'and arg3 == 'Q' and arg4 == 'maass':
        temp_args['type'] = 'sl4maass'
        temp_args['source'] = args['source'] 

    elif arg1 == 'ModularForm' and arg2 == 'GL3'and arg3 == 'Q' and arg4 == 'maass':
        temp_args['type'] = 'sl3maass'
        temp_args['source'] = args['source'] 

    elif arg1 == 'NumberField':
        temp_args['type'] = 'dedekind'
        temp_args['label'] = str(arg2)
        temp_args['source'] = ""  # it's a bug to require this to be defined


    else: # this means we're somewhere that requires args: db queries, holomorphic modular forms, custom,  maass forms, and maybe some others, all of which require a homepage.  
        return redirect(url_for("not_yet_implemented"))

    L = WebLfunction(temp_args)
    #return "23423"
   
    try:
        logging.info(temp_args)
        if temp_args['download'] == 'lcalcfile':
            return render_lcalcfile(L)
    except:
        1
        #Do nothing

    info = initLfunction(L, temp_args, request)

    # HSY: when you do "**dictionary" in a function call (at the very end),
    # you 'unpack' it. that saves you all this "title = info['title']" nonsense ;)

    return render_template('Lfunction.html', info=info, **info)
    
                           # above's **info is equivalent to:

                           #title   = info['title'],
                           #bread   = info['bread'], 
                           #properties2 = info['properties2'],
                           #citation = info['citation'], 
                           #credit   = info['credit'],
                           #support  = info['support'])


   # put different types of L-functions into here
#    temp_args = {}
#    info = {}
#    for a in args:
#        temp_args[a] = args[a]
    #if temp_args.has_key('degree'):
         #d = temp_args['degree']  
         #info = { "degree" : int(d)}
         #info["key"] = 777
    #     return render_template("/lfunction_db/templates/list.html", info=info)
#    if arg1 == 'Riemann':
#        temp_args['type'] = 'riemann'
#    elif len(args)==0 and arg1 == None: #this means I'm at the basic navigation page
#        info = set_info_for_start_page()
#        return render_template("LfunctionNavigate.html", info = info, title = 'L-functions')
#    elif arg1 == 'Character' and arg2 == 'Dirichlet' and len(args)==0:
#        info['title'] = 'Table of Dirichlet Characters'
#        info['contents'] = processDirichletNavigation(args)
#        return render_template("LfunctionTable.html",info=info,
#                               title=info['title'])
#    elif arg1 == 'Character' and arg2 == 'Dirichlet' and args['characternumber'] and args['charactermodulus']:
#        temp_args['type'] = 'dirichlet'
#    elif arg1 == 'EllipticCurve' and arg2 == 'Q' and arg3:
#        temp_args['type'] = 'ellipticcurve'
#        temp_args['label'] = str(arg3) 
#    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 == 'Q' and arg4 == 'holomorphic':
#        temp_args['type'] = 'gl2holomorphic'
#
#    elif arg1 and arg1.startswith("degree"):
#        degree = int(arg1[6])
#        info = { "degree" : degree }
#        info["key"] = 777
#        return render_template("DegreeNavigateL.html", info=info,
#                               title = 'Degree ' + str(degree)+ ' L-functions')

#David and Sally added the following case to handle Stefan's L-functions
#    elif args['type'] and args['type'] == 'lcalcurl':
#        temp_args['type'] = args['type']
#        temp_args['url'] = args['url'] 
#
#
#        #info = getNavigationFromDb(temp_args, arg1, arg2, arg3, arg4, arg5)
#        #info = processNavigationContents(info, temp_args, arg1, arg2, arg3, arg4, arg5)
#        
#    #else:
#    #    info = getNavigationFromDb(temp_args, arg1, arg2, arg3, arg4, arg5)
#    #    info = processNavigationContents(info, args, arg1, arg2, arg3, arg4, arg5)
#        



def set_info_for_start_page():
    tl = [{'title':'Riemann','link':'Riemann'},
          {'title':'Dirichlet','link':'degree1#Dirichlet'}, {'title':'','link':''}] #make the degree 1 ones, should be url_fors

    tt = {1: tl}

    tl = [{'title':'Elliptic Curve','link':'degree2#EllipticCurve_Q'},
          {'title':'Holomorphic SL2 Cusp Form', 'link':'degree2#GL2_Q_Holomorphic'},
          {'title':'Maass GL2 Form', 'link':'degree2#GL2_Q_Maass'}]

    tt[2] = tl

    info = {
        'degree_list': range(1,6),
        #'signature_list': sum([[[d-2*r2,r2] for r2 in range(1+(d//2))] for d in range(1,11)],[]), 
        #'class_number_list': range(1,11)+['11-1000000'],
        #'discriminant_list': discriminant_list
        'type_table': tt,
        'l':[1,2] #just for testing
    }
    credit = ''
    t = 'L-functions'
    info['bread'] = [('L-functions', url_for("render_Lfunction"))]
    info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-function')]
#         explain=['Further information']
#         explain.append(('Unique labels for number fields',url_for("render_labels_page")))
#         explain.append(('Unique labels for Galois groups',url_for("render_groups_page")))
#         explain.append(('Discriminant ranges (not yet implemented)','/'))
#         sidebar = set_sidebar([explain])

    return info
#        return number_field_search(**args)


def getNavigationFromDb(args, family, group, field, objectName, level):
    logging.info("%s %s %s" % (family,group,field))
    pageid = 'L'
    if family:
        pageid += '/' + family
        if group:
            pageid += '/' + group
            if field:
                pageid += '/' + field
                if objectName:
                    pageid += '/' + objectName
                    if level:
                        pageid += '/' + level

    import base
    connection = base.getDBConnection()
    db = connection.Lfunction
    collection = db.LNavigation
    return collection.find_one({'id': pageid})


def processNavigationContents(info, args, arg1,arg2,arg3,arg4,arg5):
    #logging.info("%s %s %s" % (family,group,field))
    if arg4:
        None
    else:
        if arg3:
            None
        else:
            if arg2:
                if arg2 == 'dirichlet':
                    info = LfunctionNavigationProcessing.processDirichletNavigation(info, args)
            else:
                if arg1:
                    None
                else:
                    None
                    #This is the top page
    return info

    

def initLfunction(L,args, request):
    info = {'title': L.title}
    info['citation'] = ''
    info['support'] = ''
    info['sv12'] = specialValueString(L.sageLfunction, 0.5, '\\frac12')
    info['sv1'] = specialValueString(L.sageLfunction, 1, '1')
    info['args'] = args

    info['credit'] = L.credit
    info['citation'] = L.citation

    try:
        info['url'] = L.url
    except:
        info['url'] =''

    info['degree'] = int(L.degree)

    info['zeroeslink'] = url_for('zeroesLfunction', **args)
    info['plotlink'] = url_for('plotLfunction', **args)

    #set info['bread'] and to be empty and set info['properties'], but exist (temp. fix by David & Sally)
    info['bread'] = []
    info['properties2'] = L.properties

    if args['type'] == 'gl2maass':
        info['zeroeslink'] = ''
        info['plotlink'] = ''
#        info['bread'] = [('L-function','/L'),('GL(2) Maass','/L/ModularForm/GL2/Q/maass')]

    elif args['type'] == 'riemann':
        info['bread'] = [('L-function','/L'),('Riemann Zeta','/L/Riemann')]

    elif args['type'] == 'dirichlet':
        snum = str(L.characternumber)
        smod = str(L.charactermodulus)
        info['bread'] = [('L-function','/L'),('Dirichlet Character','/L/degree1#Dirichlet'),('Character Number '+snum+' of Modulus '+ smod,'/L/Character/Dirichlet/'+smod+'/'+snum)]
        charname = '\(\\chi_{%s}\\!\\!\\pmod{%s}\)' %(snum,smod)
        info['friends'] = [('Dirichlet Character '+str(charname), '/Character/Dirichlet/'+smod+'/'+snum)]
                

    elif args['type'] == 'ellipticcurve':
        label = L.label
        info['friends'] = [('Elliptic Curve', url_for('by_label',label=label)),('Modular Form', url_for('not_yet_implemented'))]
        info['bread'] = [('L-function','/L'),('Elliptic Curve','/L/degree2#EllipticCurve_Q'),
                         (label,url_for('render_Lfunction',arg1='EllipticCurve',arg2='Q',arg3= label))]

    elif args['type'] == 'gl2holomorphic':
        weight = str(L.weight)
        level = str(L.level)
        character = str(L.character)
        label = str(L.label)
        number = str(L.number)
        info['friends'] = [('Modular Form','/ModularForm/GL2/Q/holomorphic/?weight='+weight+'&level='+level+'&character='+character +'&label='+label+'&number='+number)]

    elif args['source'] == 'db':
        info['bread'] = [('L-function','/L') ,
                         ('Degree ' + str(L.degree),'/L/degree' +
                          str(L.degree)),
                         (L.id, request.url )]

    info['dirichlet'] = L.lfuncDStex("analytic")
    info['eulerproduct'] = L.lfuncEPtex("abstract")
    info['functionalequation'] = L.lfuncFEtex("analytic")
    info['functionalequationAnalytic'] = L.lfuncFEtex("analytic").replace('\\','\\\\').replace('\n','')
    info['functionalequationSelberg'] = L.lfuncFEtex("selberg").replace('\\','\\\\').replace('\n','')

    
#LfunctionPageProcessing.setPageLinks(info, L, args)

    info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
    if len(request.args)==0:
        lcalcUrl = request.url + '?download=lcalcfile'
    else:
        lcalcUrl = request.url + '&download=lcalcfile'
        
    info['downloads'] = [('Lcalcfile', lcalcUrl) ]
    
    info['check'] = [('Riemann hypothesis', '/L/TODO') ,('Functional equation', '/L/TODO') \
                       ,('Euler product', '/L/TODO')]
    return info

def specialValueString(sageL, s, sLatex):
    val = sageL.value(s)
    return '\(L\left(' + sLatex + '\\right)=' + latex(round(val.real(),4)+round(val.imag(),4)*I) + '\)'


def parameterstringfromdict(dic):
    answer = ''
    for k, v in dic.iteritems():
        answer += k
        answer += '='
        answer += v
        answer += '&'
    return answer[0:len(answer)-1]
         

def plotLfunction(args):
    WebL = WebLfunction(args)
    L = WebL.sageLfunction
    # HSY: I got exceptions that "L.hardy_z_function" doesn't exist
    # TODO sort this out, do we need psage?!
    if not hasattr(L, "hardy_z_function"):
      return None
    #FIXME there could be a filename collission
    fn = tempfile.mktemp(suffix=".png")
    F=[(i,L.hardy_z_function(CC(.5,i)).real()) for i in srange(-30,30,.1)]
    p = line(F)
    p.save(filename = fn)
    data = file(fn).read()
    os.remove(fn)
    return data

def render_plotLfunction(args):
    data = plotLfunction(args)
    if not data:
      # see not about missing "hardy_z_function" in plotLfunction()
      return abort(404)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response

def render_browseGraph(args):
    logging.info(args)
    data = LfunctionPlot.paintSvgFile(args['group'], int(args['level']), args['sign'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response

def render_browseGraphHolo(args):
    logging.info(args)
    data = LfunctionPlot.paintSvgHolo(args['Nmin'], args['Nmax'], args['kmin'], args['kmax'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response

def render_browseGraphChar(args):
    data = LfunctionPlot.paintSvgChar(args['min_cond'], args['max_cond'], args['min_order'], arg['max_order'])
    response = make_response(data)
    respone.headers['Content-type'] = 'image/svg+xml'
    return response

def render_zeroesLfunction(args):
    WebL = WebLfunction(args)
    s = str(WebL.sageLfunction.find_zeros(-15,15,0.1))
    return s[1:len(s)-1]

def render_lcalcfile(L):
    try:
        response = make_response(L.lcalcfile)
    except:
        response = make_response(L.createLcalcfile())

    response.headers['Content-type'] = 'text/plain'
    return response


def render_showcollections_demo():
    connection = pymongo.Connection()
    dbNames = connection.database_names()
    dbList = []
    for dbName in dbNames:
        db = pymongo.database.Database(connection, dbName)
        dbMeta = connection.Metadata
        collectionNames = db.collection_names()
        collList = []
        for collName in collectionNames:
            if not collName == 'system.indexes': 
                collMeta = pymongo.collection.Collection(dbMeta,'collection_data')
                infoMeta = collMeta.find_one({'db': dbName, 'collection': collName})
                try:
                    info = infoMeta['description']
                except:
                    info = ''
                collList.append( (collName, info) )
        dbList.append( (str(db.name), collList) )
    info = {'collections' : dbList}
    return render_template("ShowCollectionDemo.html", info = info)

def processDirichletNavigation(args):
    logging.info(str(args))
    try:
        logging.debug(args['start'])
        N = int(args['start'])
        if N < 3:
            N=3
        elif N > 100:
            N=100
    except:
        N = 3
    try:
        length = int(args['length'])
        if length < 1:
            length = 1
        elif length > 20:
            length = 20
    except:
        length = 10
    try:
        numcoeff = int(args['numcoeff'])
    except:
        numcoeff = 50
    chars = LfunctionComp.charactertable(N, N+length,'primitive')
    s = '<table>\n'
    s += '<tr>\n<th scope="col">Conductor</th>\n'
    s += '<th scope="col">Primitive characters</th>\n</tr>\n'
    for i in range(N,N+length):
        s += '<tr>\n<th scope="row">' + str(i) + '</th>\n'
        s += '<td>\n'
        j = i-N
        for k in range(len(chars[j][1])):
            s += '<a style=\'display:inline\' href="Character/Dirichlet/'
            s += str(i)
            s += '/'
            s += str(chars[j][1][k])
            s += '/&numcoeff='
            s += str(numcoeff)
            s += '">'
            s += '\(\chi_{' + str(chars[j][1][k]) + '}\)</a> '
        s += '</td>\n</tr>\n'
    s += '</table>\n'
    return s
    #info['contents'] = s
    #return info

def processEllipticCurveNavigation(args):
    try:
        logging.info(args['start'])
        N = int(args['start'])
        if N < 11:
            N=11
        elif N > 100:
            N=100
    except:
        N = 11
    try:
        length = int(args['length'])
        if length < 1:
            length = 1
        elif length > 20:
            length = 20
    except:
        length = 10
    try:
        numcoeff = int(args['numcoeff'])
    except:
        numcoeff = 50
    iso_dict = LfunctionComp.isogenyclasstable(N, N+length)
    s = '<table>'
    s += '<tr><th scope="col">Conductor</th>\n'
    s += '<th scope="col">Isogeny Classes</th>\n</tr>\n'
    iso_dict.keys()
    logging.info(iso_dict)
    for cond in iso_dict.keys():
        s += '<tr>\n<td scope="row">%s</td>' % cond
        for iso in iso_dict[cond]:
            logging.info("%s %s" % (cond, iso))
            s += '<td><a href="EllipticCurve/Q/%(iso)s">%(iso)s</a></td>' % { 'iso' : iso }
        s += '</tr>\n'
    s += '</table>\n'
    return s
    #info['contents'] = s
     #return info
