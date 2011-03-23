from pymongo import Connection
import math
import datetime
from flask import url_for, make_response
import base
from classical_modular_forms.backend.web_modforms import *
#import runningWindow



## ============================================
## Returns the id for the L-function of given group, level, sign and
## spectral parameters. (Used for Maass forms and works for GL(n) and GSp(4).)
## This id is used in the database as '_id' of the L-function document.
## NOTE: SHOULD CHANGE THIS TO INCLUDE THE SIGN IN THE ID
## ============================================
def createLid(group, objectName, level, sign, parameters):
    ans = group + objectName + '_' + str(level) + '_' + str(sign)
    if group == 'GSp4':
        knownParameters = 2
    else:
        knownParameters = 1
    for index, item in enumerate(parameters):
        if index<len(parameters)-knownParameters:
            ans += '_'
            toAdd = str(item)
            ans += toAdd
    return ans

## ============================================
## Returns all the html including links to the svg-files for Maass forms
## of given degree (gives output for degree 3 and 4). Data is fetched from
## the database.
## ============================================
def getAllMaassGraphHtml(degree):
    conn = base.getDBConnection()
    db = conn.Lfunction
    collection = db.LemurellMaassHighDegree
    groups = collection.group(['group'],{ 'degree': degree },
                              {'csum': 0},
                              'function(obj,prev) { prev.csum += 1; }')

    ans = ""
    for docGroup in groups:
        g = docGroup['group']
##        print g
        ans += getGroupHtml(g)
        levels = collection.group(['level'],{ 'degree': degree ,'group': g },
                              {'csum': 0},
                              'function(obj,prev) { prev.csum += 1; }')
##        print levels
        for docLevel in levels:
            l = math.trunc(docLevel['level'])
            print l
            signs = collection.group(['sign'],{ 'degree': degree ,'group': g
                                                ,'level': l},
                              {'csum': 0},
                              'function(obj,prev) { prev.csum += 1; }')
            for docSign in signs:
                s = docSign['sign']
                print 'sign: ' + s
                ans += getOneGraphHtml(g,l,s)
                    
    return(ans)

## ============================================
## Returns the header and information about the Gamma-factors for the
## group with name group (in html and MathJax)
## ============================================
def getGroupHtml(group):
    if group == 'GSp4':
        ans = "<h3>Maass cusp forms for GSp(4)</h3>\n"
        ans += "<div>These satisfy a functional equation with \\(\\Gamma\\)-factors\n"
        ans += "\\begin{equation}"
        ans += "\\Gamma_R(s + i \\mu_1)"
        ans += "\\Gamma_R(s + i \\mu_2)"
        ans += "\\Gamma_R(s - i \\mu_1)"
        ans += "\\Gamma_R(s - i \\mu_2)"
        ans += "\\end{equation}\n"
        ans += "with \\(0 \\le \\mu_2 \\le \\mu_1\\).</div>\n"

    elif group == 'GL4':
        ans = "<h3>Maass cusp forms for GL(4)</h3>\n"
        ans += "<div>These satisfy a functional equation with \\(\\Gamma\\)-factors\n"
        ans += "\\begin{equation}"
        ans += "\\Gamma_R(s + i \\mu_1)"
        ans += "\\Gamma_R(s + i \\mu_2)"
        ans += "\\Gamma_R(s - i \\mu_3)"
        ans += "\\Gamma_R(s - i \\mu_4)"
        ans += "\\end{equation}\n"
        ans += "where \\(\\mu_1 + \\mu_2 = \\mu_3 + \\mu_4\\).</div>\n"

    elif group == 'GL3':
        ans = "<h3>Maass cusp forms for GL(3)</h3>\n"
        ans += "<div>These satisfy a functional equation with \\(\\Gamma\\)-factors\n"
        ans += "\\begin{equation}"
        ans += "\\Gamma_R(s + i \\mu_1)"
        ans += "\\Gamma_R(s + i \\mu_2)"
        ans += "\\Gamma_R(s - i \\mu_3)"
        ans += "\\end{equation}\n"
        ans += "where \\(\\mu_1 + \\mu_2 = \\mu_3\\).</div>\n"

    else:
        ans = ""
        
    return(ans)

## ============================================
## Returns the header, some information and the url for the svg-file for
## the L-functions of the Maass forms for given group, level and
## sign (of the functional equation) (in html and MathJax)
## ============================================
def getOneGraphHtml(group, level, sign):
    ans = ("<h4>Maass cusp forms of level " + str(level) + " and sign " 
          + str(sign) + "</h4>\n")
    ans += "<div>The dots in the plot correspond to \\((\\mu_1,\\mu_2)\\) "
    ans += "in the \\(\\Gamma\\)-factors. These have been found by a computer "
    ans += "search. Click on any of the dots to get detailed information about "
    ans += "the L-function.</div>\n<br />"
    graphInfo = getGraphInfo(group, level, sign)
    ans += ("<embed src='" + graphInfo['src'] + "' width='" + str(graphInfo['width']) + 
           "' height='" + str(graphInfo['height']) +
            "' type='image/svg+xml' " +
            "pluginspage='http://www.adobe.com/svg/viewer/install/'/>\n")
    ans += "<br/>\n"
        
    return(ans)
    
## ============================================
## Returns the url and width and height of the svg-file for
## the L-functions of the Maass forms for given group, level and
## sign (of the functional equation).
## ============================================
def getGraphInfo(group, level, sign):
    (width,height) = getWidthAndHeight(group, level, sign)
##    url = url_for('browseGraph',group=group, level=level, sign=sign)
    url = ('/browseGraph?group=' + group + '&level=' + str(level)
           + '&sign=' + sign)
    url =url.replace('+', '%2B')  ## + is a special character in urls
    ans = {'src': url}
    ans['width']= width
    ans['height']= height

    return(ans)

## ============================================
## Returns the url and width and height of the svg-file for
## the L-functions of holomorphic cusp form.
## ============================================
def getGraphInfoHolo(Nmin, Nmax, kmin, kmax):
#    (width,height) = getWidthAndHeight(group, level, sign)
    xfactor = 20
    yfactor = 20
    extraSpace = 30

    (width,height) = (extraSpace + xfactor*(Nmax), extraSpace + yfactor*(kmax))
##    url = url_for('browseGraph',group=group, level=level, sign=sign)
    url = ('/browseGraphHolo?Nmin=' + str(Nmin) + '&Nmax=' + str(Nmax)
           + '&kmin=' + str(kmin) + '&kmax=' + str(kmax))
#    url =url.replace('+', '%2B')  ## + is a special character in urls
    ans = {'src': url}
    ans['width']= width
    ans['height']= height

    return(ans)


## ============================================
## Returns the width and height of the svg-file for
## the L-functions of the Maass forms for given group, level and
## sign (of the functional equation).
## ============================================
def getWidthAndHeight(group, level, sign):
    conn = base.getDBConnection()
    db = conn.Lfunction
    collection = db.LemurellMaassHighDegree
    LfunctionList = collection.find({'group':group, 'level': level, 'sign': sign}
                                    , {'_id':True})
    index1 = 2
    index2 = 3

    xfactor = 20
    yfactor = 20
    extraSpace = 40

    xMax = 0
    yMax = 0
    for l in LfunctionList:
        splitId = l['_id'].split("_")
        if float(splitId[index1])>xMax:
            xMax = float(splitId[index1])
        if float(splitId[index2])>yMax:
            yMax = float(splitId[index2])

    xMax = math.ceil(xMax)
    yMax = math.ceil(yMax)
    width = int(xfactor *xMax + extraSpace)
    height = int(yfactor *yMax + extraSpace)

    return( (width, height) )


## ============================================
## Returns the contents (as a string) of the svg-file for
## the L-functions of the Maass forms for given group, level and
## sign (of the functional equation).
## ============================================
def paintSvgFile(group, level, sign):
    conn = base.getDBConnection()
    db = conn.Lfunction
    collection = db.LemurellMaassHighDegree
    LfunctionList = collection.find({'group':group, 'level': level, 'sign': sign}
                                    , {'_id':True})
    index1 = 2
    index2 = 3

    xfactor = 20
    yfactor = 20
    extraSpace = 20
    ticlength = 4
    radius = 3

    ans = "<svg  xmlns='http://www.w3.org/2000/svg'"
    ans += " xmlns:xlink='http://www.w3.org/1999/xlink'>\n"

    paralist = []
    xMax = 0
    yMax = 0
    for l in LfunctionList:
        splitId = l['_id'].split("_")
        paralist.append((splitId[index1],splitId[index2],l['_id']))
        if float(splitId[index1])>xMax:
            xMax = float(splitId[index1])
        if float(splitId[index2])>yMax:
            yMax = float(splitId[index2])

    xMax = int(math.ceil(xMax))
    yMax = int(math.ceil(yMax))
    width = xfactor *xMax + extraSpace
    height = yfactor *yMax + extraSpace

    ans += paintCS(width, height, xMax, yMax, xfactor, yfactor, ticlength)

    for (x,y,lid) in paralist:
        linkurl = "/L/ModularForm/" + group + "/Q/maass?source=db&amp;id=" + lid
        ans += "<a xlink:href='" + linkurl + "' target='_top'>\n"
        ans += "<circle cx='" + str(float(x)*xfactor)[0:7]
        ans += "' cy='" +  str(height- float(y)*yfactor)[0:7]
        ans += "' r='" + str(radius)
        ans += "' style='fill:rgb(0,204,0)'>"
        ans += "<title>" + str((x,y)).replace("u", "").replace("'", "") + "</title>"
        ans += "</circle></a>\n"

    ans += "</svg>"
    
    return(ans)

## ============================================
## Returns the svg-code for a simple coordinate system.
## width = width of the system
## height = height of the system
## xMax = maximum in first (x) coordinate
## yMax = maximum in second (y) coordinate
## xfactor = the number of pixels per unit in x
## yfactor = the number of pixels per unit in y
## ticlength = the length of the tickmarks
## ============================================
def paintCS(width, height, xMax, yMax, xfactor, yfactor,ticlength):
    xmlText = ("<line x1='0' y1='" + str(height) + "' x2='" +
               str(width) + "' y2='" + str(height) +
               "' style='stroke:rgb(0,0,0);'/>\n")
    xmlText = xmlText + ("<line x1='0' y1='" + str(height) +
                         "' x2='0' y2='0' style='stroke:rgb(0,0,0);'/>\n")
    for i in range( 1,  xMax + 1):
        xmlText = xmlText + ("<line x1='" + str(i*xfactor) + "' y1='" +
                             str(height - ticlength) + "' x2='" +
                             str(i*xfactor) + "' y2='" + str(height) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range( 5,  xMax + 1, 5):
        xmlText = xmlText + ("<text x='" + str(i*xfactor - 6) + "' y='" +
                             str(height - 2 * ticlength) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>"
                             + str(i) + "</text>\n")
        
        xmlText = xmlText + ("<line y1='0' x1='" + str(i*xfactor) +
                         "' y2='" + str(height) + "' x2='" +
                         str(i*xfactor) +
                         "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    for i in range( 1,  yMax + 1):
        xmlText = xmlText + ("<line x1='0' y1='" +
                             str(height - i*yfactor) + "' x2='" +
                             str(ticlength) + "' y2='" +
                             str(height - i*yfactor) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range( 5,  yMax + 1, 5):
        xmlText = xmlText + ("<text x='5' y='" +
                             str(height - i*yfactor + 3) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>" +
                             str(i) + "</text>\n")

        xmlText = xmlText + ("<line x1='0' y1='" +
                         str(height - i*yfactor) + "' x2='" + str(width) +
                         "' y2='" + str(height - i*yfactor) +
                         "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    return(xmlText)

## ============================================
## Returns the contents (as a string) of the svg-file for
## the L-functions of holomorphic cusp forms.
## ============================================
def paintSvgHolo(Nmin,Nmax,kmin,kmax):
    xfactor = 20
    yfactor = 20
    extraSpace = 20
    ticlength = 4
    radius = 3
    xdotspacing = 0.1  # horizontal spacing of dots
    ydotspacing = 0.08  # vertical spacing of dots

    ans = "<svg  xmlns='http://www.w3.org/2000/svg'"
    ans += " xmlns:xlink='http://www.w3.org/1999/xlink'>\n"

    xMax = int(Nmax)
    yMax = int(kmax)
    width = xfactor *xMax + extraSpace
    height = yfactor *yMax + extraSpace

    ans += paintCS(width, height, xMax, yMax, xfactor, yfactor, ticlength)

    alphabet = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
#loop over levels and weights
    for x in range(int(Nmin), int(Nmax) + 1):
        print "level = " + str(x)
        for y in range(int(kmin), int(kmax) + 1, 2):
           print "  weight = " + str(y)
           lid = "(" + str(x) + "," + str(y) + ")"
           linkurl = "/L/ModularForm/" + "GL2/Q/holomorphic?weight=" + str(y) +"&amp;level=" + str(x) + "&amp;character=0"
           WS = WebModFormSpace(y,x)
           numlabels = len(WS.galois_decomposition())
           thelabels = alphabet[0:numlabels]    # list of labels for the Galois orbits for weight y, level x
           print "   numlabels  = " + str(numlabels) + " thelabels = " + str(thelabels)
           countplus = 0   # count how many Galois orbits have sign Plus (+ 1)
           countminus = 0   # count how many Galois orbits have sign Minus (- 1)
           ybaseplus = y  # baseline y-coord for plus cases
           ybaseminus = y  # baseline y-coord for minus cases
           for label in thelabels:
               linkurl += "&amp;label=" + label
               MF = WebNewForm(y,x,0,label)   # one of the Galois orbits for weight y, level x
               numberwithlabel = MF.degree()  # number of forms in the Galois orbit
               print "           numberwithlabel = " + str(numberwithlabel)
               if x == 1: # For level 1, the sign is always plus
                  signfe = 1
               else:
                  frickeeigenvalue = MF.atkin_lehner_eigenvalues()[x] # gives Fricke eigenvalue
                  signfe = frickeeigenvalue * (-1)**float(y/2)  # sign of functional equation
               xbase = x 
               if signfe > 0:
                  ybase = ybaseplus
                  ybaseplus += ydotspacing
               else:
                  ybase = ybaseminus
                  ybaseminus += ydotspacing
               for number in range(0,numberwithlabel):
                   xbase += signfe * xdotspacing
                   ans += "<a xlink:href='" + linkurl + "&amp;number=" + str(number) + "' target='_top'>\n"
                   ans += "<circle cx='" + str(float(xbase)*xfactor)[0:7]
                  # ans += "<circle cx='" + str(float(x)*xfactor)[0:7]
                  # ans += "' cy='" +  str(height- float(y)*yfactor)[0:7]
                   ans += "' cy='" +  str(height- float(ybase)*yfactor)[0:7]
                   ans += "' r='" + str(radius)
                   ans += "' style='fill:rgb(0,204,0)'>"
                   ans += "<title>" + str((x,y)).replace("u", "").replace("'", "") + "</title>"
                   ans += "</circle></a>\n"

    ans += "</svg>"

    return(ans)

## ============================================
## Returns the header, some information and the url for the svg-file for
## the L-functions of holomorphic cusp forms.
## ============================================
def getOneGraphHtmlHolo(Nmin, Nmax, kmin, kmax):
    ans = ("<h4>L-functions of holomprphic cusp forms"
          + "</h4>\n")
    ans += "<div>The dots in the plot correspond to XXXXX "
    ans += "the L-function.</div>\n<br />"
    graphInfo = getGraphInfoHolo(Nmin, Nmax, kmin, kmax)
    ans += ("<embed src='" + graphInfo['src'] + "' width='" + str(graphInfo['width']) +
           "' height='" + str(graphInfo['height']) +
            "' type='image/svg+xml' " +
            "pluginspage='http://www.adobe.com/svg/viewer/install/'/>\n")
    ans += "<br/>\n"

    return(ans)
   

