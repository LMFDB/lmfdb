from flask import render_template, url_for, make_response
from sage.all import *
import tempfile, os
import pymongo
from WebLfunction import *
import LfunctionNavigationProcessing
import LfunctionPageProcessing
import LfunctionComp
#from elliptic_curve import by_cremona_label
# just testing

def render_webpage(args, arg1, arg2, arg3, arg4, arg5):
   # put different types of L-functions into here
    temp_args = {}
    info = {}
    for a in args:
        temp_args[a] = args[a]
    if arg1 == 'Riemann':
        temp_args['type'] = 'riemann'
    elif arg1 == 'Character' and arg2 == 'Dirichlet':
        info['title'] = 'Table of Dirichlet Characters'
        info['contents'] = processDirichletNavigation(args)
        return render_template("LfunctionTable.html",info=info, title=info['title'])
    elif arg1 == 'Character' and arg2 == 'Dirichlet' and args['characternumber'] and args['charactermodulus']:
        #print "inside if"
        temp_args['type'] = 'dirichlet'
    elif arg1 == 'EllipticCurve' and arg2 == 'Q' and arg3:
        temp_args['type'] = 'ellipticcurve'
        temp_args['label'] = str(arg3) 

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 == 'Q' and arg4 == 'holomorphic':
        temp_args['type'] = 'gl2holomorphic'

    elif args == {} and arg1 == None: #this means I'm at the basic navigation page
        info = set_info_for_start_page()
        #print  "here",arg1,arg2,arg3,arg4,arg5,temp_args
        #info = getNavigationFromDb(temp_args, arg1, arg2, arg3, arg4, arg5)
        #info = processNavigationContents(info, temp_args, arg1, arg2, arg3, arg4, arg5)
        #print "here!!!"
        
        return render_template("LfunctionNavigate.html", info = info, title = 'L-functions')
    L = WebLfunction(temp_args)
    #return "23423"
    info = initLfunction(L, temp_args)
    return render_template('Lfunction.html',info=info, title = info['title'], bread = info['bread'], properties = info['properties'])


def set_info_for_start_page():
    tl = [{'title':'Riemann','link':'Riemann'},
          {'title':'Dirichlet','link':'Character/Dirichlet'},
          {'title':'Elliptic Curve', 'link':'EllipticCurve/Q'}] #etc

    info = {
        'degree_list': range(1,6),
        #'signature_list': sum([[[d-2*r2,r2] for r2 in range(1+(d//2))] for d in range(1,11)],[]), 
        #'class_number_list': range(1,11)+['11-1000000'],
        #'discriminant_list': discriminant_list
        'type_list': tl
    }
    credit = ''	
    t = 'L-functions'
    info['bread'] = [('L-functions', url_for("render_Lfunction"))]
    info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-function')]
#         explain=['Further information']
#         explain.append(('Unique labels for number fields',url_for("render_labels_page")))
# 	explain.append(('Unique labels for Galois groups',url_for("render_groups_page")))
#         explain.append(('Discriminant ranges (not yet implemented)','/'))
#         sidebar = set_sidebar([explain])

    return info
#        return number_field_search(**args)


def getNavigationFromDb(args, family, group, field, objectName, level):
    print str(family), str(group), str(field)
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
    #print str(family), str(group), str(field)
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

    

def initLfunction(L,args):
    info = {'title': L.title}
    info['sv12'] = specialValueString(L.sageLfunction, 0.5, '\\frac12')
    info['sv1'] = specialValueString(L.sageLfunction, 1, '1')
    info['args'] = args
    info['objecttitle'] = 'L-function'
    try:
        info['credit'] = L.credit
    except:
        info['credit'] = ''
    info['degree'] = int(L.degree)
    try:
        info['url'] = L.url
    except:
        info['url'] =''

    if args['type'] == 'gl2maass':
        info['zeroeslink'] = ''
        info['plotlink'] = ''
    elif args['type'] == 'riemann':
        info['properties'] = L.properties
        info['bread'] = [('L-function','/L'),('Riemann Zeta','/L/Riemann')]
        info['zeroeslink'] = url_for('zeroesLfunction', **args)
        info['plotlink'] = url_for('plotLfunction', **args)
    elif args['type'] == 'dirichlet':
        info['properties'] = L.properties
        snum = str(L.characternumber)
        smod = str(L.charactermodulus)
        info['bread'] = [('L-function','/L'),('Dirichlet Character','/L/Character/Dirichlet'),('Character Number '+snum+' of Modulus '+ smod,'/L/Character/Dirichlet?charactermodulus='+smod+'&characternumber='+snum)]
        info['zeroeslink'] = url_for('zeroesLfunction', **args)
        info['plotlink'] = url_for('plotLfunction', **args)
    elif args['type'] == 'ellipticcurve':
        info['zeroeslink'] = url_for('zeroesLfunction', **args)
        info['plotlink'] = url_for('plotLfunction', **args)
        label = L.label
        info['friends'] = [('Elliptic Curve', url_for('by_cremona_label',label=label)),('Modular Form', url_for('not_yet_implemented'))]
        info['properties'] = L.properties
        info['bread'] = [('L-function','/L'),('Elliptic Curve','/L/EllipticCurve/Q'),(label,url_for('render_Lfunction',arg1='EllipticCurve',arg2='QQ',arg3= label))]
    elif args['type'] == 'gl2holomorphic':
        info['zeroeslink'] = url_for('zeroesLfunction', **args)
        info['plotlink'] = url_for('plotLfunction', **args)
        weight = str(L.weight)
        level = str(L.level)
        character = str(L.character)
        label = str(L.label)
        number = str(L.number)
        info['friends'] = [('Modular Form','/ModularForm/GL2/Q/holomorphic/?weight='+weight+'&level='+level+'&character='+character +'&label='+label+'&number='+number)]
    else:
        info['zeroeslink'] = url_for('zeroesLfunction', **args)
        info['plotlink'] = url_for('plotLfunction', **args)

    info['dirichlet'] = L.lfuncDStex("analytic")
    info['eulerproduct'] = L.lfuncEPtex("abstract")
    info['functionalequation'] = L.lfuncFEtex("analytic")
    info['functionalequationAnalytic'] = L.lfuncFEtex("analytic").replace('\\','\\\\').replace('\n','')
    info['functionalequationSelberg'] = L.lfuncFEtex("selberg").replace('\\','\\\\')

    
#LfunctionPageProcessing.setPageLinks(info, L, args)

    info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
    
    #if L.selfdual:
    #    dualtext = 'Selfdual'
    #else:
    #    dualtext = 'Non-selfdual'
    #primitivetext = 'Primitive'
    #info['properties'] = ['Degree = ' + str(info['degree']) , str(primitivetext)    , str(dualtext), \
    #                      specialValueString(L.sageLfunction, 0.5, '\\frac12'), specialValueString(L.sageLfunction, 1, '1')  ]

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
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response

def render_zeroesLfunction(args):
    WebL = WebLfunction(args)
    s = str(WebL.sageLfunction.find_zeros(-15,15,0.1))
    return s[1:len(s)-1]

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
    print str(args)
    try:
        print args['start']
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
            s += '<a href="Dirichlet?charactermodulus='
            s += str(i)
            s += '&characternumber='
            s += str(chars[j][1][k])
            s += '&numcoeff='
            s += str(numcoeff)
            s += '">'
            s += '\(\chi_{' + str(chars[j][1][k]) + '}\)</a> '
        s += '</td>\n</tr>\n'
    s += '</table>\n'
    return s
    #info['contents'] = s
    #return info
