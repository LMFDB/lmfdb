
# -*- coding: utf-8 -*-

from lmfdb import db
from lmfdb.utils import signtocolour
from flask import url_for


def paintSvgMaass(min_level, max_level, min_R, max_R, width=1000, heightfactor=20, L=""):
    ''' Returns the contents (as a string) of the svg-file for
        all Maass forms in the database of the specified weight.
        Takes all levels from min_level to max_level
        Spectral parameter in [min_R, max_R]
        Set L="/L" to make link go to the L-function
    '''
    xMax = int(max_R)
    yMax = int(max_level)
    xMin = int(min_R)
    yMin = int(min_level)
    extraSpace = 40
    length_R = xMax - xMin
    length_level = yMax - yMin + 1
    if length_level < 30:
        heightfactor = heightfactor * 2
    height = length_level * heightfactor + extraSpace
    xfactor = (width - extraSpace)/length_R
    yfactor = (height - extraSpace)/length_level
    ticlength = 4
    radius = 3
    xshift = extraSpace

    # Start of file and add coordinate system
    ans = "<svg  xmlns='http://www.w3.org/2000/svg'"
    ans += " xmlns:xlink='http://www.w3.org/1999/xlink'"
    ans += " height='{0}' width='{1}'>\n".format(height + 20, width + 20)
    ans += paintCSMaass(width, height, xMin, xMax, yMin, yMax,
                        xfactor, yfactor, ticlength, xshift)

    # Fetch Maass forms from database
    forms = db.maass_newforms.search({'spectral_parameter':{'$gte':xMin,'$lte':xMax}, 'level':{'$gte':yMin,'$lte':yMax}},
                                     ["maass_id", "spectral_parameter", "level", "symmetry"], sort=[("level",1),("symmetry",-1),("spectral_parameter",1),("maass_id",1)])

    # Loop through all forms and add a clickable dot for each
    for f in forms:
        linkurl = L + url_for("maass.by_label",label=f['maass_id'])
        x = (f['spectral_parameter'] - xMin) * xfactor + xshift
        y = (f['level'] - yMin + 1) * yfactor
        s = f.get('symmetry',0)
        y -= s    # Shifting even slightly up and odd slightly down
        color = signtocolour(s)

        ans += "<a xlink:href='{0}' target='_top'>".format(linkurl)
        ans += "<circle cx='{0}' cy='{1}' ".format(str(x)[0:6],str(y))
        ans += "r='{0}'  style='fill:{1}'>".format(str(radius),color)
        ans += "<title>{0}</title></circle></a>\n".format(f['spectral_parameter'])

    ans += "</svg>"
    return ans


def paintCSMaass(width, height, xMin, xMax, yMin, yMax, xfactor, yfactor, ticlength, xshift):
    """  Returns the svg-code for a simple coordinate system.
         width = width of the system
         height = height of the system
         xMin, xMax = minimum/maximum in first (x) coordinate
         ymin, yMax = minimum/maximum in second (y) coordinate
         xfactor = the number of pixels per unit in x
         yfactor = the number of pixels per unit in y
         ticlength = the length of the tickmarks
    """
    # ----------- Coordinate axes
    ans = "<line x1='{1}' y1='0' x2='{0}' ".format(str(width),str(xshift))
    ans += "y2='0' style='stroke:rgb(0,0,0);'/>\n"
    ans += "<line x1='{0}' y1='{1}' ".format(str(xshift),str(height))
    ans += "x2='{0}' y2='0' style='stroke:rgb(0,0,0);'/>\n".format(str(xshift))
    # ----------- Tickmarks x axis
    for i in range(1, xMax -xMin + 1):
        ans += "<line x1='{0}' y1='{1}' ".format(str(i * xfactor + xshift),str(ticlength))
        ans += "x2='{0}' y2='0' ".format(str(i * xfactor + xshift))
        ans += "style='stroke:rgb(0,0,0);'/>\n"

    # ----------- Values and gridlines x axis
    for i in range(xMin + 1, xMax + 1, 1):
        if i > 999:
            digitoffset = 12
        elif i > 99:
            digitoffset = 9
        elif i > 9:
            digitoffset = 6
        else:
            digitoffset = 3
        xvalue = (i-xMin) * xfactor + xshift
        ans += "<text x='{0}' ".format(str(xvalue - digitoffset))
        ans += "y='{0}' ".format(str(4 * ticlength))
        ans += "style='fill:rgb(102,102,102);font-size:11px;'>"
        ans += "{0}</text>\n".format(str(i))

        ans += "<line y1='0' x1='{0}' ".format(str(xvalue))
        ans += "y2='{0}' x2='{1}' ".format(str(height), xvalue)
        ans += "style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n"

    # ----------- Tickmarks y axis
    for i in range(yMin, yMax + 1):
        yvalue = str((i - yMin + 1) * yfactor)
        ans += "<line x1='{1}' y1='{0}' ".format(yvalue, str(xshift))
        ans += "x2='{0}' y2='{1}' ".format(str(ticlength + xshift), yvalue)
        ans += "style='stroke:rgb(0,0,0);'/>\n"

    # ----------- Values and gridlines y axis
    for i in range(yMin, yMax + 1, 2):
        yvalue = (i - yMin + 1) * yfactor
        ans += "<text x='5' y='{0}' ".format(str(yvalue + 3))
        ans += "style='fill:rgb(102,102,102);font-size:11px;'>"
        ans += "{0}</text>\n".format(str(i))

        ans += "<line x1='{0}' y1='{1}' ".format(str(xshift),str(yvalue))
        ans += "x2='{0}' y2='{1}' ".format(str(width),str(yvalue))
        ans += "style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n"

    # ----------- Axes labels
    ans += "<text x='5' y='{0}' ".format(str(height-5))
    ans += "style='fill:rgb(102,102,102);font-size:12px;'>Level</text>\n"
    (xvalue, yvalue) = (str(width + 10), 15)
    ans += "<text x='{0}' y='{1}' ".format(xvalue,yvalue)
    ans += "style='fill:rgb(102,102,102);font-size:14px;'>R</text>\n"

    return ans
