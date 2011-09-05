import re
import logging

from flask import render_template, url_for, make_response, abort, redirect
from sage.all import *
import tempfile, os
import pymongo
from Lfunction import *
import LfunctionComp
import LfunctionPlot
from utils import to_dict
from Lfunctionutilities import lfuncDStex, lfuncEPtex, lfuncFEtex

##import upload2Db.py


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
                info["contents"] = [processEllipticCurveNavigation(args), LfunctionPlot.getOneGraphHtmlHolo(1, 22, 2, 14)]
            elif degree == 3 or degree == 4:
                info["contents"] = LfunctionPlot.getAllMaassGraphHtml(degree)
                
            return render_template("DegreeNavigateL.html", info=info, title = 'Degree ' + str(degree)+ ' L-functions', bread = info["bread"])
            
        elif arg1 == 'custom': # need a better name
            return "not yet implemented"
            
    # args may or may not be empty
    # what follows are all things that need homepages

    try:
        L = generateLfunctionFromUrl(arg1, arg2, arg3, arg4, temp_args)
        
    except Exception as inst:   # There was an exception when creating the page
        error_message = ('There was an error loading this page. Please report the ' +
                         'address of this page and the following error message: ' +
                         inst.args[0])
        
        info = { 'content': error_message, 'title': 'Error' }
        return render_template('LfunctionSimple.html', info=info, **info)


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


def generateLfunctionFromUrl(arg1, arg2, arg3, arg4, temp_args):
    if arg1 == 'Riemann' or (arg1 == 'Character' and arg2 == 'Dirichlet' and arg3 == '1' and arg4 == '0'):
        return RiemannZeta()

    elif arg1 == 'Character' and arg2 == 'Dirichlet':
        return Lfunction_Dirichlet( charactermodulus = arg3, characternumber = arg4)

    elif arg1 == 'EllipticCurve' and arg2 == 'Q':
        print "Starting to generate EC", arg3
        return Lfunction_EC( label = arg3)

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 == 'Q' and arg4 == 'holomorphic': # this has args: one for weight and one for level
        return Lfunction_EMF( **temp_args)

    elif arg1 == 'ModularForm' and arg2 == 'GL2'and arg3 == 'Q' and arg4 == 'maass':
        return Lfunction_Maass( **temp_args)
    
    elif arg1 == 'ModularForm' and (arg2 == 'GSp4' or arg2 == 'GL4' or  arg2 == 'GL3') and arg3 == 'Q' and arg4 == 'maass':
        return Lfunction_Maass( dbid = temp_args['id'], dbName = 'Lfunction', dbColl = 'LemurellMaassHighDegree')

    elif arg1 == 'NumberField':
        return DedekindZeta( label = str(arg2))

    elif arg1 == 'Lcalcurl':
        return Lfunction( Ltype = arg1, url = arg2)



def set_info_for_start_page():
    tt = [[{'title':'Riemann','link':'Riemann'},
           {'title':'Dirichlet','link':'degree1#Dirichlet'}],

          [{'title':'Elliptic Curve','link':'degree2#EllipticCurve_Q'},
           {'title':'GL2 Cusp Form', 'link':'degree2#GL2_Q_Holomorphic'},
           {'title':'GL2 Maass Form','link':'degree2#GL2_Q_Maass'}],

          [{'title':'GL3 Maass Form', 'link':'degree3#GL3_Q_Maass'},
           {'title':'GL4 Maass Form', 'link':'degree4#GL4_Q_Maass'}]]

    info = {
        'degree_list': range(1,5),
        'type_table': tt,
        'l':[0,1,2] #just for testing
    }
    credit = ''
    t = 'L-functions'
    info['bread'] = [('L-functions', url_for("render_Lfunction"))]
    info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-function')]

    return info
    

def initLfunction(L,args, request):
    info = {'title': L.title}
    info['citation'] = ''
    info['support'] = ''
    info['sv12'] = specialValueString(L.sageLfunction, 0.5, '1/2')
    info['sv1'] = specialValueString(L.sageLfunction, 1, '1')
    info['args'] = args

    info['credit'] = L.credit
    #info['citation'] = L.citation

    try:
        info['url'] = L.url
    except:
        info['url'] =''

    info['degree'] = int(L.degree)

    info['zeroeslink'] = (request.url.replace('/L/', '/zeroesLfunction/').
                          replace('/Lfunction/', '/zeroesLfunction/').
                          replace('/L-function/', '/zeroesLfunction/') ) #url_for('zeroesLfunction',  **args)
    info['plotlink'] = (request.url.replace('/L/', '/plotLfunction/').
                          replace('/Lfunction/', '/plotLfunction/').
                          replace('/L-function/', '/plotLfunction/') ) #info['plotlink'] = url_for('plotLfunction',  **args)

    # set info['bread'] and to be empty and set info['properties'],
    # but exist (temp. fix by David & Sally)
    info['bread'] = []
    info['properties2'] = set_gaga_properties(L)

    if L.Ltype == 'maass':
        if L.group == 'GL2':
            info['zeroeslink'] = ''
            info['plotlink'] = ''

    elif L.Ltype  == 'riemann':
        info['bread'] = [('L-function','/L'),('Riemann Zeta','/L/Riemann')]

    elif L.Ltype  == 'dirichlet':
        snum = str(L.characternumber)
        smod = str(L.charactermodulus)
        info['bread'] = [('L-function','/L'),('Dirichlet Character','/L/degree1#Dirichlet'),('Character Number '+snum+' of Modulus '+ smod,'/L/Character/Dirichlet/'+smod+'/'+snum)]
        charname = '\(\\chi_{%s}\\!\\!\\pmod{%s}\)' %(snum,smod)
        info['friends'] = [('Dirichlet Character '+str(charname), '/Character/Dirichlet/'+smod+'/'+snum)]
                

    elif L.Ltype  == 'ellipticcurve':
        label = L.label
        info['friends'] = [('Elliptic Curve', '/EllipticCurve/Q/' + str(label)),('Modular Form', url_for('not_yet_implemented'))]
        info['bread'] = [('L-function','/L'),('Elliptic Curve','/L/degree2#EllipticCurve_Q'),
                         (label,url_for('render_Lfunction',arg1='EllipticCurve',arg2='Q',arg3= label))]

    elif L.Ltype == 'ellipticmodularform':
        weight = str(L.weight)
        level = str(L.level)
        character = str(L.character)
        label = str(L.label)
        number = str(L.number)
        info['friends'] = [('Modular Form','/ModularForm/GL2/Q/holomorphic/?weight='+weight+'&level='+level+'&character='+character +'&label='+label+'&number='+number)]

    elif L.Ltype == 'db':
        info['bread'] = [('L-function','/L') ,
                         ('Degree ' + str(L.degree),'/L/degree' +
                          str(L.degree)),
                         (L.id, request.url )]

    info['dirichlet'] = lfuncDStex(L, "analytic")
    info['eulerproduct'] = lfuncEPtex(L, "abstract")
    info['functionalequation'] = lfuncFEtex(L, "analytic")
    #info['functionalequationAnalytic'] = lfuncFEtex(L, "analytic").replace('\\','\\\\').replace('\n','')
    info['functionalequationSelberg'] = lfuncFEtex(L, "selberg")

    
    info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
    if len(request.args)==0:
        lcalcUrl = request.url + '?download=lcalcfile'
    else:
        lcalcUrl = request.url + '&download=lcalcfile'
        
    info['downloads'] = [('Lcalcfile', lcalcUrl) ]
    
    info['check'] = [('Riemann hypothesis', '/L/TODO') ,('Functional equation', '/L/TODO') \
                       ,('Euler product', '/L/TODO')]
    return info

def set_gaga_properties(L):
    ans = [ ('Degree',    str(L.degree))]

    if L.selfdual:
        sd = 'Self dual'
    else:
        sd = 'Not self dual'
    ans.append((None,        sd))

    ans.append(('Level',     str(L.level)))
    ans.append(('Sign',      str(L.sign)))

    if L.primitive:
        prim = 'Primitive'
    else:
        prim = 'Not primitive'
    ans.append((None,        prim))

    return ans


def specialValueString(sageL, s, sLatex):
    number_of_decimals = 10
    val = sageL.value(s)
    return '\(L\left(' + sLatex + '\\right)\\approx ' + latex(round(val.real(), number_of_decimals)+round(val.imag(), number_of_decimals)*I) + '\)'


def parameterstringfromdict(dic):
    answer = ''
    for k, v in dic.iteritems():
        answer += k
        answer += '='
        answer += v
        answer += '&'
    return answer[0:len(answer)-1]
         

def plotLfunction(request, arg1, arg2, arg3, arg4, arg5):
    pythonL = generateLfunctionFromUrl(arg1, arg2, arg3, arg4, to_dict(request.args))
    L = pythonL.sageLfunction
    # HSY: I got exceptions that "L.hardy_z_function" doesn't exist
    # SL: Reason, it's not in the distribution of Sage
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

def render_plotLfunction(request, arg1, arg2, arg3, arg4, arg5):
    data = plotLfunction(request, arg1, arg2, arg3, arg4, arg5)
    if not data:
      # see note about missing "hardy_z_function" in plotLfunction()
      return abort(404)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response

def render_zeroesLfunction(request, arg1, arg2, arg3, arg4, arg5):
    L = generateLfunctionFromUrl(arg1, arg2, arg3, arg4, to_dict(request.args))

    if L.degree > 2 or L.Ltype()=="ellipticmodularform":  # Too slow to be rigorous here
        search_step = 0.05
        if L.selfdual:
            s = str(L.sageLfunction.find_zeros(-search_step/2 , 20,search_step))
        else:
            s = str(L.sageLfunction.find_zeros(-15,15,search_step))

    else:
        if L.selfdual:
            number_of_zeros = 6
        else:
            number_of_zeros = 8
        s = str(L.sageLfunction.find_zeros_via_N(number_of_zeros, not L.selfdual))

    return s[1:len(s)-1]

def render_browseGraph(args):
    logging.info(args)
    if 'sign' in args:
      data = LfunctionPlot.paintSvgFileAll([[args['group'], int(args['level']), args['sign']]])
    else:
      data = LfunctionPlot.paintSvgFileAll([[args['group'], int(args['level'])]])
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

def render_lcalcfile(L):
    try:
        response = make_response(L.lcalcfile)
    except:
        response = make_response(L.createLcalcfile_ver2())

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
