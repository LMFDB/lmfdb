from flask import render_template, url_for, make_response
from sage.all import *
import tempfile, os
import pymongo
from WebLfunction import *
import LfunctionNavigationProcessing
import LfunctionPageProcessing

def render_webpage(args, family, group, field, objectName, level):
    if "type" in args:
        L = WebLfunction(args)
        info = initLfunction(L,args)
        return render_template('Lfunction.html',info=info)
    else:
        info = getNavigationFromDb(args, family, group, field, objectName, level)
        info = processNavigationContents(info, args, family, group, field, objectName, level)
        return render_template("LfunctionNavigate.html", info = info)

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

def processNavigationContents(info, args, family, group, field, objectName, level):
    print str(family), str(group), str(field)
    if objectName:
        None
    else:
        if field:
            None
        else:
            if group:
                if group.lower() == 'dirichlet':
                    info = LfunctionNavigationProcessing.processDirichletNavigation(info, args)
            else:
                if family:
                    None
                else:
                    None
                    #This is the top page
    return info

    

def initLfunction(L,args):
    info = {'title': L.title}
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
    else:
        info['zeroeslink'] = url_for('zeroesLfunction', **args)
        info['plotlink'] = url_for('plotLfunction', **args)

    info['dirichlet'] = L.lfuncDStex("analytic")
    info['eulerproduct'] = L.lfuncEPtex("abstract")
    info['functionalequation'] = L.lfuncFEtex("analytic")
    info['functionalequationAnalytic'] = L.lfuncFEtex("analytic").replace('\\','\\\\').replace('\n','')
    info['functionalequationSelberg'] = L.lfuncFEtex("selberg").replace('\\','\\\\')

    info = LfunctionPageProcessing.setPageLinks(info, L, args)
    if L.selfdual:
        dualtext = 'Selfdual'
    else:
        dualtext = 'Non-selfdual'
    primitivetext = 'Primitive'
    info['properties'] = ['Degree = ' + str(info['degree']) , str(primitivetext)    , str(dualtext), \
                          specialValueString(L.sageLfunction, 0.5, '\\frac12'), specialValueString(L.sageLfunction, 1, '1')  ]

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
