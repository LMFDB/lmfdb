# Code for creating plots for browsing L-functions

import math
import cmath
import datetime
from flask import url_for, make_response
import lmfdb.base as base
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_newforms import WebNewForm
from lmfdb.characters.ListCharacters import get_character_modulus
from lmfdb.lfunctions import logger

###############################################################################
# Maass form for GL(n) n>2
###############################################################################

#============
# url to add all degree-3, level-4 dots on one plot
#   http://localhost:37777/L/browseGraph?group=GL3&level=4
#=========


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
        if index < len(parameters) - knownParameters:
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
    groups = collection.group(['group'], {'degree': degree},
                              {'csum': 0},
                              'function(obj,prev) { prev.csum += 1; }')

    ans = ""
    for docGroup in groups:
        g = docGroup['group']
        # logger.debug(g)
        ans += getGroupHtml(g)
        levels = collection.group(['level'], {'degree': degree, 'group': g},
                                  {'csum': 0},
                                  'function(obj,prev) { prev.csum += 1; }')
        # logger.debug(levels)
        for docLevel in levels:
            l = math.trunc(docLevel['level'])
            # logger.debug(l)
            ans += getOneGraphHtml([g, l])

    return(ans)

## ============================================
## Returns the header and information about the Gamma-factors for the
## group with name group (in html and MathJax)
## ============================================


def getGroupHtml(group):
    if group == 'GSp4':
        ans = "<h3 id='GSp4_Q_Maass'>Maass cusp forms for GSp(4)</h3>\n"
        ans += "<div>Currently in the LMFDB, we have data on L-functions associated "
        ans += "to Maass cusp forms for GSp(4) of level 1. "
        ans += "These satisfy a functional equation with \\(\\Gamma\\)-factors\n"
        ans += "\\begin{equation}"
        ans += "\\Gamma_\\R(s + i \\mu_1)"
        ans += "\\Gamma_\\R(s + i \\mu_2)"
        ans += "\\Gamma_\\R(s - i \\mu_1)"
        ans += "\\Gamma_\\R(s - i \\mu_2)"
        ans += "\\end{equation}\n"
        ans += "with \\(0 \\le \\mu_2 \\le \\mu_1\\).</div>\n"

    elif group == 'GL4':
        ans = "<h3 id='GL4_Q_Maass'>Maass cusp forms for GL(4)</h3>\n"
        ans += "<div>Currently in the LMFDB, we have data on L-functions associated "
        ans += "to Maass cusp forms for GL(4) of level 1. "
        ans += "These satisfy a functional equation with \\(\\Gamma\\)-factors\n"
        ans += "\\begin{equation}"
        ans += "\\Gamma_\R(s + i \\mu_1)"
        ans += "\\Gamma_\R(s + i \\mu_2)"
        ans += "\\Gamma_\R(s - i \\mu_3)"
        ans += "\\Gamma_\R(s - i \\mu_4)"
        ans += "\\end{equation}\n"
        ans += "where \\(\\mu_1 + \\mu_2 = \\mu_3 + \\mu_4\\).</div>\n"

# template code to generate a knowl
# {{ KNOWL('mf.maass.gl3',  title='Maass cusp forms for GL(3)') }}
# the rendered html
# <a title="Maass cusp forms for GL(3) [mf.maass.gl3]" knowl="mf.maass.gl3" kwargs="">Maass cusp forms for GL(3)</a>
# but this is for a knowl that exists.  if it doesn't yet exist, it should look something like
#      <div class="knowl knowl-error">
#      'mf.maass.gl3'
#      <a href="/knowledge/edit/mf.maass.gl3">Maass cusp forms for GL(3)</a>
#      </div>

    elif group == 'GL3':
        ans = "<h3 id='GL3_Q_Maass'>Maass cusp forms for GL(3)</h3>\n"
        ans += "<div>Currently in the LMFDB, we have data on L-functions associated "
        ans += "to Maass cusp forms for GL(3) of levels 1 and 4. "
        ans += "These satisfy a functional equation with \\(\\Gamma\\)-factors\n"
        ans += "\\begin{equation}"
        ans += "\\Gamma_\\R(s + i \\mu_1)"
        ans += "\\Gamma_\\R(s + i \\mu_2)"
        ans += "\\Gamma_\\R(s - i \\mu_3)"
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
def getOneGraphHtml(gls):
    if len(gls) > 2:
        ans = ("<h4>Maass cusp forms of level " + str(gls[1]) + " and sign "
               + str(gls[2]) + "</h4>\n")
    else:
        ans = ("<h4>Maass cusp forms of level " + str(gls[1]) + "</h4>\n")
    ans += "<div>The dots in the plot correspond to \\((\\mu_1,\\mu_2)\\) "
    ans += "in the \\(\\Gamma\\)-factors. These have been found by a computer "
    ans += "search. Click on any of the dots to get detailed information about "
    ans += "the L-function.</div>\n<br />"
    graphInfo = getGraphInfo(gls)
    ans += ("<embed src='" + graphInfo['src'] + "' width='" +
            str(graphInfo['width']) +
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


def getGraphInfo(gls):
    (width, height) = getWidthAndHeight(gls)
    if len(gls) > 2:
        url = url_for('.browseGraph', group=gls[0], level=gls[1],
                      sign=gls[2])
        url = url.replace('+', '%2B')  # + is a special character in urls
    else:
        url = url_for('.browseGraph', group=gls[0], level=gls[1])

    ans = {'src': url}
    ans['width'] = width
    ans['height'] = height

    return(ans)

## ============================================
## Returns the width and height of the svg-file for
## the L-functions of the Maass forms for given group, level and
## sign (of the functional equation).
## ============================================


def getWidthAndHeight(gls):
    conn = base.getDBConnection()
    db = conn.Lfunction
    collection = db.LemurellMaassHighDegree
    if len(gls) > 2:
        LfunctionList = collection.find({'group': group, 'level': level, 'sign':
                                        sign}, {'_id': True})
    else:
        LfunctionList = collection.find({'group': gls[0], 'level': gls[1]
                                         }, {'_id': True, 'sign': True})

    index1 = 2
    index2 = 3

    xfactor = 20
    yfactor = 20
    extraSpace = 40

    xMax = 0
    yMax = 0
    for l in LfunctionList:
        splitId = l['_id'].split("_")
        if float(splitId[index1]) > xMax:
            xMax = float(splitId[index1])
        if float(splitId[index2]) > yMax:
            yMax = float(splitId[index2])

    xMax = math.ceil(xMax)
    yMax = math.ceil(yMax)
    width = int(xfactor * xMax + extraSpace)
    height = int(yfactor * yMax + extraSpace)

    return((width, height))

## ============================================
## Returns the contents (as a string) of the svg-file for
## the L-functions of the Maass forms for a set of given groups, levels and
## signs (of the functional equation).
## ============================================


def paintSvgFileAll(glslist):  # list of group, level, and (maybe) sign
    from sage.misc.sage_eval import sage_eval
    index1 = 2
    index2 = 3

    xfactor = 20
    yfactor = 20
    extraSpace = 20
    ticlength = 4
    radius = 3

    ans = "<svg  xmlns='http://www.w3.org/2000/svg'"
    ans += " xmlns:xlink='http://www.w3.org/1999/xlink'>\n"

    conn = base.getDBConnection()
    db = conn.Lfunction
    collection = db.LemurellMaassHighDegree
    paralist = []
    xMax = 0
    yMax = 0
    for gls in glslist:
        if len(gls) > 2:
            LfunctionList = collection.find(
                {'group': gls[0], 'level': gls[1], 'sign': gls[2]}, {'_id': True, 'sign': True})
        else:
            LfunctionList = collection.find({'group': gls[0], 'level': gls[1]}, {'_id': True, 'sign': True})

        for l in LfunctionList:
            splitId = l['_id'].split("_")
            paralist.append((splitId[index1], splitId[index2], l['_id'], gls[0], gls[1], l['sign']))
            if float(splitId[index1]) > xMax:
                xMax = float(splitId[index1])
            if float(splitId[index2]) > yMax:
                yMax = float(splitId[index2])

    xMax = int(math.ceil(xMax))
    yMax = int(math.ceil(yMax))
    width = xfactor * xMax + extraSpace
    height = yfactor * yMax + extraSpace

    ans += paintCS(width, height, xMax, yMax, xfactor, yfactor, ticlength)

    for (x, y, lid, group, level, sign) in paralist:
        try:
            linkurl = url_for('.l_function_maass_gln_page', group=group, dbid=lid)
        except Exception as ex:  # catch when running a test
            linkurl = lid
        ans += "<a xlink:href='" + linkurl + "' target='_top'>\n"
        ans += "<circle cx='" + str(float(x) * xfactor)[0:7]
        ans += "' cy='" + str(height - float(y) * yfactor)[0:7]
        ans += "' r='" + str(radius)
        ans += "' style='fill:" + signtocolour(sage_eval(sign)) + "'>"
        ans += "<title>" + str((x, y)).replace("u", "").replace("'", "") + "</title>"
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
def paintCS(width, height, xMax, yMax, xfactor, yfactor, ticlength):
    xmlText = ("<line x1='0' y1='" + str(height) + "' x2='" +
               str(width) + "' y2='" + str(height) +
               "' style='stroke:rgb(0,0,0);'/>\n")
    xmlText = xmlText + ("<line x1='0' y1='" + str(height) +
                         "' x2='0' y2='0' style='stroke:rgb(0,0,0);'/>\n")
    for i in range(1, xMax + 1):
        xmlText = xmlText + ("<line x1='" + str(i * xfactor) + "' y1='" +
                             str(height - ticlength) + "' x2='" +
                             str(i * xfactor) + "' y2='" + str(height) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range(5, xMax + 1, 5):
        xmlText = xmlText + ("<text x='" + str(i * xfactor - 6) + "' y='" +
                             str(height - 2 * ticlength) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>"
                             + str(i) + "</text>\n")

        xmlText = xmlText + ("<line y1='0' x1='" + str(i * xfactor) +
                             "' y2='" + str(height) + "' x2='" +
                             str(i * xfactor) +
                             "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    for i in range(1, yMax + 1):
        xmlText = xmlText + ("<line x1='0' y1='" +
                             str(height - i * yfactor) + "' x2='" +
                             str(ticlength) + "' y2='" +
                             str(height - i * yfactor) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range(5, yMax + 1, 5):
        xmlText = xmlText + ("<text x='5' y='" +
                             str(height - i * yfactor + 3) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>" +
                             str(i) + "</text>\n")

        xmlText = xmlText + ("<line x1='0' y1='" +
                             str(height - i * yfactor) + "' x2='" + str(width) +
                             "' y2='" + str(height - i * yfactor) +
                             "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    return(xmlText)


###############################################################################
# GL(2) cusp forms
# This is normally picked from a static file created by this code.
###############################################################################

## ============================================
## Returns the header, some information and the url for the svg-file for
## the L-functions of holomorphic cusp forms.
## ============================================
def getOneGraphHtmlHolo(Nmin, Nmax, kmin, kmax):
    graphInfo = getGraphInfoHolo(Nmin, Nmax, kmin, kmax)
# To  generate the graph:    ans = ("<embed src='" + graphInfo['src'] + "'
# width='" + str(graphInfo['width']) +
    image_url = url_for('static', filename='images/browseGraphHolo_22_14_5a.svg')
    logger.debug(image_url)
    ans = ("<embed  src='%s' width='%s' height='%s' type='image/svg+xml' " % (image_url, str(graphInfo['width']), str(graphInfo['height'])) +
           "pluginspage='http://www.adobe.com/svg/viewer/install/'/>\n")
    ans += "<br/>\n"

    return(ans)


## ============================================
## Returns the url and width and height of the svg-file for
## the L-functions of holomorphic cusp form.
## ============================================
def getGraphInfoHolo(Nmin, Nmax, kmin, kmax):
    xfactor = 90
    yfactor = 30
    x_extraSpace = 50
    y_extraSpace = 80

    (width, height) = (x_extraSpace + xfactor * (Nmax), y_extraSpace + yfactor * (kmax))
    url = url_for('.browseGraphHolo', Nmin=str(Nmin), Nmax=str(Nmax),
                  kmin=str(kmin), kmax=str(kmax))

    ans = {'src': url}
    ans['width'] = width
    ans['height'] = height

    return(ans)

## ============================================
## Returns the contents (as a string) of the svg-file for
## the L-functions of holomorphic cusp forms.
## ============================================


def paintSvgHolo(Nmin, Nmax, kmin, kmax):
    xfactor = 90
    yfactor = 30
    extraSpace = 20
    ticlength = 4
    radius = 3.3
    xdotspacing = 0.11  # horizontal spacing of dots
    ydotspacing = 0.28  # vertical spacing of dots
    colourplus = signtocolour(1)
    colourminus = signtocolour(-1)
    maxdots = 5  # max number of dots to display

    ans = "<svg  xmlns='http://www.w3.org/2000/svg'"
    ans += " xmlns:xlink='http://www.w3.org/1999/xlink'>\n"

    xMax = int(Nmax)
    yMax = int(kmax)
    width = xfactor * xMax + extraSpace
    height = yfactor * yMax + extraSpace

    ans += paintCSHolo(width, height, xMax, yMax, xfactor, yfactor, ticlength)

    alphabet = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']

# loop over levels and weights
    for x in range(int(Nmin), int(Nmax) + 1):  # x is the level
        for y in range(int(kmin), int(kmax) + 1, 2):  # y is the weight
            lid = "(" + str(x) + "," + str(y) + ")"
            linkurl = "/L/ModularForm/GL2/Q/holomorphic/" + str(x) + "/" + str(y) + "/0/"
            WS = WebModFormSpace(N = x, k = y, chi = 0)
            numlabels = len(WS.galois_decomposition())  # one label per Galois orbit
            thelabels = alphabet[0:numlabels]    # list of labels for the Galois orbits for weight y, level x
            countplus = 0   # count how many Galois orbits have sign Plus (+ 1)
            countminus = 0   # count how many Galois orbits have sign Minus (- 1)
            ybaseplus = y  # baseline y-coord for plus cases
            ybaseminus = y  # baseline y-coord for minus cases
            numpluslabels = 0
            numminuslabels = 0
            for label in thelabels:  # looping over Galois orbit
                linkurl = "/L/ModularForm/GL2/Q/holomorphic/" + str(x) + "/" + str(y) + "/0/" + label
                MF = WebNewForm(N = x, k = y,chi = 0, label = label)   # one of the Galois orbits for weight y, level x
                numberwithlabel = MF.degree()  # number of forms in the Galois orbit
                if x == 1:  # For level 1, the sign is always plus
                    signfe = 1
                else:
                    frickeeigenvalue = MF.atkin_lehner_eigenvalues()[x]  # gives Fricke eigenvalue
                    signfe = frickeeigenvalue * (-1) ** float(y / 2)  # sign of functional equation
                xbase = x - signfe * (xdotspacing / 2.0)

                if signfe > 0:  # go to right in BLUE if plus
                    ybase = ybaseplus
                    ybaseplus += ydotspacing
                    thiscolour = colourplus
                    numpluslabels += 1
                else:  # go to the left in RED of minus
                    ybase = ybaseminus
                    ybaseminus += ydotspacing
                    thiscolour = colourminus
                    numminuslabels += 1

                if numberwithlabel > maxdots:  # if more than maxdots in orbit, use number as symbol
                    xbase += 1.5 * signfe * xdotspacing
                    if signfe < 0:   # move over more to position numbers on minus side.
                        xbase += signfe * xdotspacing
                    ybase += -0.5 * ydotspacing
                    if (signfe > 0 and numpluslabels > 1) or (signfe < 0 and numminuslabels > 1):
                        ybase += ydotspacing
                    ans += "<a xlink:href='" + url_for('not_yet_implemented') + "' target='_top'>\n"

#  TODO: Implement when there is more than maxdots forms

                    ans += ("<text x='" + str(float(xbase) * xfactor)[0:7] + "' y='" +
                            str(height - float(ybase) * yfactor)[0:7] +
                            "' style='fill:" + thiscolour + ";font-size:14px;font-weight:bold;'>"
                            + str(numberwithlabel) + "</text>\n")
                    ans += "</a>\n"
                    if signfe < 0:
                        ybaseminus += 1.5 * ydotspacing
                    else:
                        ybaseplus += 1.5 * ydotspacing
                else:  # otherwise, use one dot per form in orbit, connected with a line
                    if numberwithlabel > 1:  # join dots if there are at least two
# add lines first and then dots to prevent line from hiding link
                        firstcenterx = xbase + signfe * xdotspacing
                        firstcentery = ybase
                        lastcenterx = xbase + (numberwithlabel * signfe * xdotspacing)
                        lastcentery = ybase
                        ans += "<line x1='%s' " % str(float(firstcenterx) * xfactor)[0:7]
                        ans += "y1='%s' " % str(float(height - firstcentery * yfactor))[0:7]
                        ans += "x2='%s' " % str(float(lastcenterx) * xfactor)[0:7]
                        ans += "y2='%s' " % str(float(height - lastcentery * yfactor))[0:7]
                        ans += "style='stroke:%s;stroke-width:2.4'/>" % thiscolour
                    for number in range(0, numberwithlabel):
                        xbase += signfe * xdotspacing
                        ans += "<a xlink:href='" + linkurl + "/" + str(number) + "' target='_top'>\n"
                        ans += "<circle cx='" + str(float(xbase) * xfactor)[0:7]
                        ans += "' cy='" + str(height - float(ybase) * yfactor)[0:7]
                        ans += "' r='" + str(radius)
                        ans += "' style='fill:" + thiscolour + "'>"
                        ans += "<title>" + str((x, y)).replace("u", "").replace("'", "") + "</title>"
                        ans += "</circle></a>\n"

    ans += "</svg>"
    return ans


## ============================================
## Returns the svg-code for a simple coordinate system
## INCLUDING a grid at the even lattice points.
## width = width of the system
## height = height of the system
## xMax = maximum in first (x) coordinate
## yMax = maximum in second (y) coordinate
## xfactor = the number of pixels per unit in x
## yfactor = the number of pixels per unit in y
## ticlength = the length of the tickmarks
## ============================================
def paintCSHolo(width, height, xMax, yMax, xfactor, yfactor, ticlength):
    xmlText = ("<line x1='0' y1='" + str(height) + "' x2='" +
               str(width) + "' y2='" + str(height) +
               "' style='stroke:rgb(0,0,0);'/>\n")
    xmlText = xmlText + ("<line x1='0' y1='" + str(height) +
                         "' x2='0' y2='0' style='stroke:rgb(0,0,0);'/>\n")
    for i in range(1, xMax + 1):
        xmlText = xmlText + ("<line x1='" + str(i * xfactor) + "' y1='" +
                             str(height - ticlength) + "' x2='" +
                             str(i * xfactor) + "' y2='" + str(height) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range(1, xMax + 1, 1):
        digitoffset = 6
        if i < 10:
            digitoffset = 3
        xmlText = xmlText + ("<text x='" + str(i * xfactor - digitoffset) + "' y='" +
                             str(height - 2 * ticlength) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>"
                             + str(i) + "</text>\n")

        xmlText = xmlText + ("<line y1='0' x1='" + str(i * xfactor) +
                             "' y2='" + str(height) + "' x2='" +
                             str(i * xfactor) +
                             "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    for i in range(1, yMax + 1):
        xmlText = xmlText + ("<line x1='0' y1='" +
                             str(height - i * yfactor) + "' x2='" +
                             str(ticlength) + "' y2='" +
                             str(height - i * yfactor) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range(2, yMax + 1, 2):
        xmlText = xmlText + ("<text x='5' y='" +
                             str(height - i * yfactor + 3) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>" +
                             str(i) + "</text>\n")

        if i % 4 == 0:  # put dashes every four units
            xmlText = xmlText + ("<line x1='0' y1='" +
                                 str(height - i * yfactor) + "' x2='" + str(width) +
                                 "' y2='" + str(height - i * yfactor) +
                                 "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    return(xmlText)


## ===========================================
## THIS HASN'T BEEN FINISHED AND TESTED
## Returns the contents (as a string) of the svg-file for
## the L-functions of holomorphic cusp forms.
## General code to be used with plotsector routine.
## ============================================
def paintSvgHoloGeneral(Nmin, Nmax, kmin, kmax, imagewidth, imageheight):
    xfactor = 90
    yfactor = 30
    extraSpace = 20
    ticlength = 4
    radius = 3.3
    xdotspacing = 0.30  # horizontal spacing of dots
    ydotspacing = 0.11  # vertical spacing of dots
    colourplus = signtocolour(1)
    colourminus = signtocolour(-1)
    maxdots = 5  # max number of dots to display

    ans = "<svg  xmlns='http://www.w3.org/2000/svg'"
    ans += " xmlns:xlink='http://www.w3.org/1999/xlink'>\n"

    xMax = int(Nmax)
    yMax = int(kmax)
    width = xfactor * xMax + extraSpace
    height = yfactor * yMax + extraSpace

    # make the coordinate system
    ans += paintCSHoloTMP(width, height, xMax, yMax, xfactor, yfactor, ticlength)
    alphabet = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']

# create appearanceinfo, common to all points
    appearanceinfo = []

# loop over levels and weights, using plotsector to put the appropriate dots at each lattice point
    for x in range(int(Nmin), int(Nmax) + 1):  # x is the level
        for y in range(int(kmin), int(kmax) + 1, 2):  # y is the weight
            lid = "(" + str(x) + "," + str(y) + ")"
            linkurl = "/L/ModularForm/GL2/Q/holomorphic/" + str(y) + "/" + str(x) + "/0/"
            WS = WebModFormSpace(N = x, k = y,chi = 0)  # space of modular forms of weight y, level x
            galois_orbits = WS.galois_decomposition()   # make a list of Galois orbits
            numlabels = len(galois_orbits)  # one label per Galois orbit
            thelabels = alphabet[0:numlabels]    # list of labels for the Galois orbits for weight y, level x
            countplus = 0   # count how many Galois orbits have sign Plus (+ 1)
            countminus = 0   # count how many Galois orbits have sign Minus (- 1)
            ybaseplus = y  # baseline y-coord for plus cases
            ybaseminus = y  # baseline y-coord for minus cases
            numpluslabels = 0
            numminuslabels = 0
# plotsector requires three dictionaries: dimensioninfo, appearanceinfo, and urlinfo
# create dimensioninfo
            dimensioninfo = {}
            dimensioninfo['offset'] = [0, height]
            dimensioninfo['scale'] = [xfactor, -1 * yfactor]
            dimensioninfo['vertexlocation'] = [x, y]
            dimensioninfo['maxdots'] = maxdots
            dimensioninfo['dotspacing'] = [xdotspacing, ydotspacing]
            dimensioninfo['edge'] = [[0, 1], [1, 0]]     # unit vectors defining edges of sector
            # dimensioninfo['edgelength'] = [float(dimensioninfo['scale'][0])/float(Nmax), float(dimensioninfo['scale'][1])/float(kmax)] #add comment
            dimensioninfo['edgelength'] = [0.5, 0.5]
            dimensioninfo['dotradius'] = radius
            dimensioninfo['connectinglinewidth'] = dimensioninfo['dotradius'] / 1.5
            dimensioninfo['firstdotoffset'] = [0.0, 0.0]
#
            appearanceinfo = {}
            # appearanceinfo['edgewidth'] = dimensioninfo['dotspacing'][0]/1.0  #just a guess
            appearanceinfo['edgewidth'] = [0, 0]  # remove the sector edges
            appearanceinfo['edgestyle'] = 'stroke-dasharray:3,3'
            appearanceinfo['edgecolor'] = 'rgb(202,202,102)'
            appearanceinfo['fontsize'] = 'font-size:11px'
            appearanceinfo['fontweight'] = ""
#
            urlinfo = {'base': '/L/ModularForm/GL2/Q/holomorphic?'}
            urlinfo['space'] = {'weight': y}
            urlinfo['space']['level'] = x
            urlinfo['space']['character'] = 0
#
            scale = 1
            # Symmetry types: +1 or -1
            symmetrytype = [1, -1]
            for signtmp in symmetrytype:
                # urlinfo['space']['orbits'] = [ [] for label in thelabels ] # initialise
                # an empty list for each orbit
                urlinfo['space']['orbits'] = []
                for label in thelabels:  # looping over Galois orbit: one label per orbit
                    # do '+' case first
                    MF = WebNewForm(N = x, k = y, chi = 0, label = label)   # one of the Galois orbits for weight y, level x
                    numberwithlabel = MF.degree()  # number of forms in the Galois orbit
                    if x == 1:  # For level 1, the sign is always plus
                        signfe = 1
                    else:
                        # signfe = -1
                        frickeeigenvalue = MF.atkin_lehner_eigenvalues()[x]  # gives Fricke eigenvalue
                        signfe = frickeeigenvalue * (-1) ** float(y / 2)  # sign of functional equation
                    if signfe == signtmp:  # we find an orbit with sign of "signtmp"
                        if signfe == 1:
                            dimensioninfo['edge'] = [[0, 1], [1, 0]]
                                # unit vectors defining edges of sector for signfe positive
                        else:
                            # dimensioninfo['edge'] = [[0,1],[-1,0]]     # unit vectors defining edges
                            # of sector for signfe negative
                            dimensioninfo['edge'] = [[0, -1], [-1, 0]]
                                # unit vectors defining edges of sector for signfe negative
                        dimensioninfo['dotspacing'] = [signfe * xdotspacing, ydotspacing]
                        dimensioninfo['firstdotoffset'] = [0.5 * (dimensioninfo['dotspacing'][0] * dimensioninfo['edge'][0][0] + dimensioninfo['dotspacing'][1] * dimensioninfo['edge'][1][0]), 0]
                        signcolour = signtocolour(signfe)
                        appearanceinfo['edgecolor'] = signcolour
                        orbitdescriptionlist = []
                        for n in range(numberwithlabel):
                            orbitdescriptionlist.append({'label': label, 'number': n, 'color': signcolour})
                        urlinfo['space']['orbits'].append(orbitdescriptionlist)
                # urlinfo['space']['orbits'][0][0]['color'] = signtocolour(-1)
                # appearanceinfo['orbitcolor'] = 'rgb(102,102,102)'
                    ans += plotsector(dimensioninfo, appearanceinfo, urlinfo)

    ans += "</svg>"
    return(ans)

#=====================

## ============================================
#
#
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
# ============================================


def paintCSHoloTMP(width, height, xMax, yMax, xfactor, yfactor, ticlength):
    xmlText = ("<line x1='-50' y1='" + str(height) + "' x2='" +
               str(width) + "' y2='" + str(height) +
               "' style='stroke:rgb(0,0,0);'/>\n")   # draw horizontal axis
#     xmlText += mytext("level", [0,height], [xfactor, yfactor], [0.4, 0.7], "", "", "", 'rgb(0,0,0)')
#    xmlText += '<text x="18" y="395" style="stroke:none" font-style = "italic";>level</text>'
    xmlText = xmlText + ("<line x1='0' y1='" + str(
        height) + "' x2='0' y2='0' style='stroke:rgb(0,0,0);'/>\n")  # draw vertical axis
    xmlText += "<text x='50.0' y='491.0' font-style='italic'>level</text>"
#
    # xmlText += mytext("level", [0,height], [xfactor, yfactor], [0.2, 0.7],
    # "", 'font-size:11px', "", 'rgb(0,0,0)')
    xmlText += "<text x='33.0' y='411.0' transform='rotate(270 33, 411)' font-style='italic'>weight</text>"
    # xmlText += '<text x="118"  y="365" transform="rotate(90 118, 365)" style="stroke:none" font-style="italic";>weight</text>'
    # xmlText += '<text x="118"  y="365" transform="rotate(-90 118, 365)"
    # style="stroke:none" font-style = "italic";>weight</text>'
    for i in range(1, xMax + 1):
        xmlText = xmlText + ("<line x1='" + str(i * xfactor) + "' y1='" +
                             str(height - ticlength) + "' x2='" +
                             str(i * xfactor) + "' y2='" + str(height) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range(1, xMax + 1, 1):
        digitoffset = 6
        if i < 10:
            digitoffset = 3
        xmlText = xmlText + ("<text x='" + str(i * xfactor - digitoffset) + "' y='" +
                             str(height - 2 * ticlength) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>"
                             + str(i) + "</text>\n")

        # xmlText = xmlText + ("<line y1='0' x1='" + str(i*xfactor) +
        #                 "' y2='" + str(height) + "' x2='" +
        #                 str(i*xfactor) +
        #                 "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    for i in range(1, yMax + 1):
        xmlText = xmlText + ("<line x1='0' y1='" +
                             str(height - i * yfactor) + "' x2='" +
                             str(ticlength) + "' y2='" +
                             str(height - i * yfactor) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range(2, yMax + 1, 2):
        xmlText = xmlText + ("<text x='5' y='" +
                             str(height - i * yfactor + 3) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>" +
                             str(i) + "</text>\n")

        # if i%4==0 :  #  put dahes every four units
        #   xmlText = xmlText + ("<line x1='0' y1='" +
        #                 str(height - i*yfactor) + "' x2='" + str(width) +
        #                 "' y2='" + str(height - i*yfactor) +
        #                 "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    return(xmlText)

##================================================
#+++++++++++++++++++++++++++++++++++++++++++++++++
##
##================================================


def signtocolour(sign):
    argument = cmath.phase(sign)
    r = int(255.0 * (math.cos((1.0 * math.pi / 3.0) - (argument / 2.0))) ** 2)
    g = int(255.0 * (math.cos((2.0 * math.pi / 3.0) - (argument / 2.0))) ** 2)
    b = int(255.0 * (math.cos(argument / 2.0)) ** 2)
    return("rgb(" + str(r) + "," + str(g) + "," + str(b) + ")")

#=====================


###############################################################################
# Dirichlet characters
###############################################################################
## ============================================
## Returns the header, some information and the url for the svg-file for
## the Dirichlet L-functions.
## ============================================
def getOneGraphHtmlChar(min_cond, max_cond, min_order, max_order):
    graphInfo = getGraphInfoChar(min_cond, max_cond, min_order, max_order)
    ans = ("<embed id='charGraph' src='" + graphInfo['src'] + "' width='" + str(graphInfo['width']) +
           # ans = ("<embed src='/static/images/browseGraphChar_1_35.svg' width='" +
           # str(graphInfo['width']) +
           "' height='" + str(graphInfo['height']) +
           "' type='image/svg+xml' " +
           "pluginspage='http://www.adobe.com/svg/viewer/install/'/>\n")
    ans += "<br/>\n"

    return(ans)


## ============================================
## Returns the url and width and height of the svg-file for
## Dirichlet L-functions.
## ============================================
def getGraphInfoChar(min_cond, max_cond, min_order, max_order):
    xfactor = 50
    yfactor = 25
    extraSpace = 40
    (width, height) = (
        2 * extraSpace + xfactor * max_order, 2 * extraSpace + yfactor * (max_cond - min_cond + 1))
    logger.debug(width,height)
##    url = url_for('.browseGraph',group=group, level=level, sign=sign)
    url = url_for('.browseGraphChar', min_cond=str(min_cond),
                  max_cond=str(max_cond), min_order=str(min_order),
                  max_order=str(max_order))
    ans = {'src': url}
    ans['width'] = width
    ans['height'] = height
    return ans


## ============================================
## Returns the contents (as a string) of the svg-file for
## the Dirichlet L-functions.
## ============================================
def paintSvgChar(min_cond, max_cond, min_order, max_order):
    xfactor = 50
    yfactor = 25
    extraSpace = 40
    ticlength = 4
    radius = 3
    xdotspacing = 0.10  # horizontal spacing of dots
    ydotspacing = 0.16  # vertical spacing of dots
    colourplus = signtocolour(1)
    colourminus = signtocolour(-1)
    maxdots = 1  # max number of dots to display

    ans = "<svg  xmlns='http://www.w3.org/2000/svg'"
    ans += " xmlns:xlink='http://www.w3.org/1999/xlink'>\n"

    xMax = int(max_order)
    yMax = int(max_cond)
    yMin = int(min_cond)
##    width = xfactor * xMax + 3 * extraSpace
##    height = yfactor * (yMax - yMin) + 3 * extraSpace
    width = xfactor * xMax + 2 * extraSpace
    height = yfactor * (yMax - yMin + 1) + 2 * extraSpace

    ans += paintCSChar(width, height, xMax, yMax, yMin, xfactor, yfactor, ticlength)

    # loop over orders and conductors
    cd = reindex_characters(int(min_cond), int(max_cond), int(max_order))
    for (x, y) in cd:
        linkurl = "/L/" + "Character/Dirichlet/" + str(y)
        counteven = 0   # count how many characters are even
        countodd = 0   # count how many characters are odd
        xbaseplus = x - (xdotspacing / 2.0)
        xbaseminus = x + (xdotspacing / 2.0)
        for ii in range(len(cd[(x, y)])):
            current = cd[(x, y)][ii]
            if len(current) == 2:
                isEven = current[1]
                if isEven:
                    xbaseplus += xdotspacing
                    thiscolour = colourplus
                    counteven += 1
                    ans += "<a xlink:href='" + linkurl + "/" + str(current[0]) + "' target='_top'>\n"
                    ans += "<circle cx='" + str(float(xbaseplus) * xfactor)[0:7]
                    ans += "' cy='" + str(height - ((y - yMin + 1) * yfactor))[0:7]
                    ans += "' r='" + str(radius)
                    ans += "' style='fill:" + thiscolour + "'>"
                    ans += "<title>" + '(' + str(y) + ',' + str(current[0]) + ')' + "</title>"
                    ans += "</circle></a>\n"

                else:
                    xbaseminus -= xdotspacing
                    thiscolour = colourminus
                    countodd += 1
                    ans += "<a xlink:href='" + linkurl + "/" + str(current[0]) + "' target='_top'>\n"
                    ans += "<circle cx='" + str(float(xbaseminus) * xfactor)[0:7]
                    ans += "' cy='" + str(height - ((y - yMin + 1) * yfactor))[0:7]
                    ans += "' r='" + str(radius)
                    ans += "' style='fill:" + thiscolour + "'>"
                    ans += "<title>" + '(' + str(y) + ',' + str(current[0]) + ')' + "</title>"
                    ans += "</circle></a>\n"
            if len(current) == 3:
                isEven = current[2]
                if isEven:
                    xbaseplus += xdotspacing
                    thiscolour = colourplus
                    counteven += 1
                    ans += "<a xlink:href='" + linkurl + "/" + str(current[0]) + "' target='_top'>\n"
                    ans += "<circle cx='" + str(float(xbaseplus) * xfactor)[0:7]
                    ans += "' cy='" + str(height - ((y - yMin + 1) * yfactor) - 2 * radius)[0:7]
                    ans += "' r='" + str(radius)
                    ans += "' style='fill:" + thiscolour + "'>"
                    ans += "<title>" + '(' + str(y) + ',' + str(current[0]) + ')' + "</title>"
                    ans += "</circle></a>\n"
                    ans += "<a xlink:href='" + linkurl + "/" + str(current[1]) + "' target='_top'>\n"
                    ans += "<circle cx='" + str(float(xbaseplus) * xfactor)[0:7]
                    ans += "' cy='" + str(height - ((y - yMin + 1) * yfactor) + 2 * radius)[0:7]
                    ans += "' r='" + str(radius)
                    ans += "' style='fill:" + thiscolour + "'>"
                    ans += "<title>" + '(' + str(y) + ',' + str(current[1]) + ')' + "</title>"
                    ans += "</circle></a>\n"
                else:
                    xbaseminus -= xdotspacing
                    thiscolour = colourminus
                    countodd += 1
                    ans += "<a xlink:href='" + linkurl + "/" + str(current[0]) + "' target='_top'>\n"
                    ans += "<circle cx='" + str(float(xbaseminus) * xfactor)[0:7]
                    ans += "' cy='" + str(height - ((y - yMin + 1) * yfactor) - 2 * radius)[0:7]
                    ans += "' r='" + str(radius)
                    ans += "' style='fill:" + thiscolour + "'>"
                    ans += "<title>" + '(' + str(y) + ',' + str(current[0]) + ')' + "</title>"
                    ans += "</circle></a>\n"
                    ans += "<a xlink:href='" + linkurl + "/" + str(cd[(x, y)][ii][1]) + "' target='_top'>\n"
                    ans += "<circle cx='%s'" % str(float(xbaseminus) * xfactor)[0:7]
                    ans += " cy='%s'" % str(height - ((y - yMin + 1) * yfactor) + 2 * radius)[0:7]
                    ans += " r='%s'" % radius
                    ans += " style='fill:%s'>" % thiscolour
                    ans += "<title>" + '(' + str(y) + ',' + str(current[1]) + ')' + "</title>"
                    ans += "</circle></a>\n"

    ans += "</svg>"

    return ans


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
def paintCSChar(width, height, xMax, yMax, yMin, xfactor, yfactor, ticlength):
    xmlText = ("<line x1='0' y1='" + str(height) + "' x2='" +
               str(width) + "' y2='" + str(height) +
               "' style='stroke:rgb(0,0,0);'/>\n")
    xmlText = xmlText + ("<line x1='0' y1='" + str(height) +
                         "' x2='0' y2='0' style='stroke:rgb(0,0,0);'/>\n")
    for i in range(1, xMax + 1):
        xmlText = xmlText + ("<line x1='" + str(i * xfactor) + "' y1='" +
                             str(height - ticlength) + "' x2='" +
                             str(i * xfactor) + "' y2='" + str(height) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range(1, xMax + 1, 1):
        digitoffset = 6
        if i < 10:
            digitoffset = 3
        if i < xMax:
            textOrder = str(i)
        else:
            textOrder = '>' + str(xMax - 1)
            digitoffset += 6
        xmlText = xmlText + ("<text x='" + str(i * xfactor - digitoffset) + "' y='" +
                             str(height - 2 * ticlength) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>"
                             + textOrder + "</text>\n")

        xmlText = xmlText + ("<line y1='0' x1='" + str(i * xfactor) +
                             "' y2='" + str(height) + "' x2='" +
                             str(i * xfactor) +
                             "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    for i in range(yMin, yMax + 1):
        xmlText = xmlText + ("<line x1='0' y1='" +
                             str(height - (i - yMin + 1) * yfactor) + "' x2='" +
                             str(ticlength) + "' y2='" +
                             str(height - (i - yMin + 1) * yfactor) +
                             "' style='stroke:rgb(0,0,0);'/>\n")

    for i in range(yMin + yMin % 2, yMax + 1, 2):
        xmlText = xmlText + ("<text x='5' y='" +
                             str(height - (i - yMin + 1) * yfactor + 3) +
                             "' style='fill:rgb(102,102,102);font-size:11px;'>" +
                             str(i) + "</text>\n")

        if i % 2 == 0:  # put dashes every two units (this "if" is not needed after change from 4 to 2)
            xmlText = xmlText + ("<line x1='0' y1='" +
                                 str(height - (i - yMin + 1) * yfactor) + "' x2='" + str(width) +
                                 "' y2='" + str(height - (i - yMin + 1) * yfactor) +
                                 "' style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n")

    xmlText = xmlText + (
        "<text x='5' y='10' style='fill:rgb(102,102,102);font-size:11px;'>Conductor</text>\n")
    xmlText = xmlText + ("<text x='" + str(width - xfactor + 15) + "' y='" + str(height - 2 * ticlength) +
                         "' style='fill:rgb(102,102,102);font-size:11px;'>Order</text>\n")

    return xmlText

## =============================================
## helper function that organizes the Dirichlet characters
## by order.  It returns a dict of characters where each entry
## is a list of pairs. In particular char_dict[(N, order)] = [(ii,parity)]
## where N is the conductor of the character with index ii in Sage's
## ordering, and is even if parity is 0 and 1 otherwise.
## =============================================


def reindex_characters(min_mod, max_mod, order_limit=12):
    h, entries, rownrs, colnrs = get_character_modulus(min_mod, max_mod, order_limit)
##    These entries used for debugging when Conrey char not availble.
##    rownrs=range(1,21)
##    colnrs=range(1,12)
##    colnrs.append('more')
##    entries = {}
##    entries[(5,4)] = [((3, True, 4,True),(3, True, 4,True) ) ,((2,True,2,False),)]
##    entries[(17,'more')] = [((3, True, 16,True),(3, True, 16,True) ) ,((2,True,2,False),)]
    char_dict = {}
    for modulus in rownrs:
        for col in colnrs:
            entry = entries.get((modulus, col), [])
            for chi in entry:  # chi is either a real character or pair of complex conjugates
                if chi[0][1]:  # Primitiv
                    order = chi[0][2]
                    nr = chi[0][0]
                    isEven = chi[0][3]

                    if order > order_limit:
                        order = order_limit

                    # Add an entry to list with given order and modulus
                    dict_entry = char_dict.get((order, modulus), [])
                    if order < 3:  # Real
                        dict_entry.append((nr, isEven))
                    else:  # Complex
                        nrInv = chi[1][0]   # Number of the inverse character
                        dict_entry.append((nr, nrInv, isEven))
                    char_dict[(order, modulus)] = dict_entry

    logger.debug(char_dict)
    return char_dict


###############################################################################
# Uncompleted code to create a more elaborate graph for cusp forms
###############################################################################
## ============================================
## Plot the dots in a sector
##
## We work in "working coordinates" and then convert to screen coordinates
## via the scoord function
##
## ToDo: list of definitions/inputs, and check that they are called correctly
## ============================================
def plotsector(dimensioninfo, appearanceinfo, urlinfo):
    ans = ""
    scale = dimensioninfo['scale']
    vertexlocation = dimensioninfo['vertexlocation']
    offset = dimensioninfo['offset']
    maxdots = dimensioninfo['maxdots']
    dotspacing = dimensioninfo['dotspacing']
    parallelogramsize = [1, 1]
    # parallelogramsize = [1 + maxdots, 1 + maxdots]
    edge = dimensioninfo['edge']

    urlbase = urlinfo['base']
    for arg, val in urlinfo['space'].iteritems():   # this does things like: level=4&weight=8&character=0
        if type(val).__name__ != 'dict' and type(val).__name__ != 'list':
            urlbase += arg + "=" + str(val) + "&amp;"

# draw the edges of the sector (omit edge if edgelength is 0)
    edgelength = dimensioninfo['edgelength']
    # ans += myline(offset, scale, vertexlocation, lincomb(1, vertexlocation, parallelogramsize[0] * edgelength[0], edge[0]), appearanceinfo['edgewidth'], appearanceinfo['edgestyle'], appearanceinfo['edgecolor'])
    # ans += "\n"
    # ans += myline(offset, scale, vertexlocation, lincomb(1, vertexlocation, parallelogramsize[1] * edgelength[1], edge[1]), appearanceinfo['edgewidth'], appearanceinfo['edgestyle'], appearanceinfo['edgecolor'])
    # ans += "\n"

 # now iterate over the orbits
 # "orbitbase" is the starting point of an orbit, which initially is the "firstdotoffset"
    orbitbase = lincomb(1, vertexlocation, 1, dimensioninfo['firstdotoffset'])
    for orbit in urlinfo['space']['orbits']:
        # first determine if we should draw a line connecting the dots in an orbit, since want line beneath dots
        # no line if 1 dot or >maxdots
        if len(orbit) > 1 and len(orbit) <= maxdots:
            ans += myline(offset, scale, orbitbase, lincomb(1, orbitbase, (len(orbit) - 1) * dotspacing[1],
                          edge[1]), dimensioninfo['connectinglinewidth'], "", appearanceinfo['edgecolor'])
            ans += "\n"
        elif len(orbit) > maxdots:
            orbitelem = orbit[0]
            orbitcolor = orbitelem['color']
            ans += "<a xlink:href='/not_yet_implemented' target='_top'>"
            orbitbase = lincomb(1, orbitbase, -0.5 * dotspacing[0], edge[0])
            ans += mytext(len(orbit), offset, scale, orbitbase, "", appearanceinfo[
                          'fontsize'], appearanceinfo['fontweight'], orbitcolor)
            ans += "</a>"
            ans += "\n"
            break   # we are done with this orbit if there are more than maxdots cuspforms in the orbit (re-check)***
        dotlocation = orbitbase
        for orbitelem in orbit:  # loop through the elements in an orbit, drawing a dot and making a link
            orbitcolor = orbitelem['color']
            urlbase += 'label' + "='" + str(orbitelem['label']) + "'&amp;"
            urlbase += 'number' + "=" + str(orbitelem['number'])
            ans += '<a xlink:href="' + urlbase + '" target="_top">'
            ans += "\n"
            # ans += mydot(vertexlocation, scale, dotlocation,
            # dimensioninfo['dotradius'], orbitcolor,"",orbitelem['title'])
            # ans += mydot(offset, scale, dotlocation, dimensioninfo['dotradius'], orbitcolor,"","test title")
            ans += mydot(offset, scale, dotlocation, dimensioninfo['dotradius'], orbitcolor, "", "")
            ans += "</a>"
            ans += "\n"
            dotlocation = lincomb(1, dotlocation, dotspacing[1], edge[1])
        orbitbase = lincomb(1, orbitbase, dotspacing[0], edge[0])
    return(ans)

## ==================
## addlists:  adds two lists as if they were vectors
## ===================


def addlists(list1, list2):
    return([list1[j] + list2[j] for j in range(len(list1))])

## ==================
## lincomb:  adds a v1 + b v2 as if lists v1, v2 were vectors
## ===================


def lincomb(scalar1, list1, scalar2, list2):
    return([scalar1 * list1[j] + scalar2 * list2[j] for j in range(len(list1))])


## ============================================
## mydot: Draw a dot
## ============================================
def mydot(offset, scale, startpt, radius, color, shape, title):
    ans = "<circle "
    mystartpt = scoord(offset, scale, startpt)
    ans += "cx='" + str(mystartpt[0]) + "' "
    ans += "cy='" + str(mystartpt[1]) + "' "
    ans += "r='" + str(radius) + "' "
    ans += "style='fill: " + color + ";'"
    ans += ">"
    ans += "<title>" + str(title) + "</title>"
    ans += "</circle>"
    return(ans)


## ============================================
## mytext: Place text in an svg, taking as input the offset and scale of the
##    of the output coordinates, and the local coordinates of the
##    location of the text
## ============================================
def mytext(thetext, offset, scale, startpt, endpt, fontsize, fontweight, fontcolor):
    ans = "<text "
    mystartpt = scoord(offset, scale, startpt)
    ans += "x='" + str(mystartpt[0]) + "' "
    ans += "y='" + str(mystartpt[1]) + "' "
    ans += "style='fill: " + fontcolor + "; "
    ans += "font-size: " + str(fontsize) + "; "
    ans += "font-weight: " + fontweight + "; "
    ans += "'"
    ans += ">"
    ans += str(thetext)
    ans += "</text>"
    return(ans)


## ============================================
## myline: Draw a line, taking as input the offset and scale of the
##    of the output coordinates, and the local coordinates of the
##    start and end points, and some information about the appearance
##    of the line
## ============================================
def myline(offset, scale, startpt, endpt, width, style, color):
    if startpt == endpt:
        return("")
    ans = "<line "
    mystartpt = scoord(offset, scale, startpt)
    ans += "x1='" + str(mystartpt[0]) + "' "
    ans += "y1='" + str(mystartpt[1]) + "' "
    myendpt = scoord(offset, scale, endpt)
    ans += "x2='" + str(myendpt[0]) + "' "
    ans += "y2='" + str(myendpt[1]) + "' "
    ans += "style='stroke: " + color + "; "
    if width:
        ans += "stroke-width:  " + str(width) + "; "
    if style:
        ans += style + "; "
    ans += "'"
    ans += "/>"
    return(ans)


## =================
## scoord: convert from working coordinates to screen coordinates
##  base + scale * localcoord
##  since vec1 * vec2 does not do coordinatewise multiplication,
##  we have to do it by hand
## ================
def scoord(base, scale, wc):
    rescaled = [base[j] + scale[j] * wc[j] for j in range(len(scale))]
    return(rescaled)
