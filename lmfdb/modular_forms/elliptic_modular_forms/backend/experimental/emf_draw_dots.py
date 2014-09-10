from lmfdb import base

def paintSvgHolomorphic(min_level, max_level, min_weight, max_weight, char = 1,
                        width = 1000, heightfactor = 20):
    ''' Returns the contents (as a string) of the svg-file for
        all classical modular forms in the database.
        Takes all levels from min_level to max_level
        weight in min_weight,max_weight
    '''
    xMax = int(max_level)
    yMax = int(max_weight)
    xMin = int(min_level)
    yMin = int(min_weight)
    extraSpace = 40
    length_level = xMax - xMin
    length_weight = yMax - yMin
    if length_weight < 15:
        heightfactor = heightfactor * 2
    height = length_weight * heightfactor + extraSpace
    xfactor = (width - extraSpace)/length_level
    yfactor = (height - extraSpace)/length_weight
    ticlength = 4
    radius = 3
    xshift = extraSpace
    color_even = 'rgb(255,0,0)'
    color_odd = 'rgb(0,0,255)'
    color_neither = 'rgb(0,255,0)'

    # Start of file and add coordinate system
    ans = "<svg  xmlns='http://www.w3.org/2000/svg'"
    ans += " xmlns:xlink='http://www.w3.org/1999/xlink'"
    ans += " height='{0}' width='{1}'>\n".format(height + 20, width + 20)
    ans += paintCS(width, height, xMin, xMax, yMin, yMax,
                        xfactor, yfactor, ticlength, xshift)

    # Fetch Maass forms from database
    db = base.getDBConnection()['modularforms2']['webmodformspace_test']
    search = {'level': {"$gt": int(xMin-1),"$lt": int(xMax)},
              'weight': {"$gt": int(yMin),"$lt": int(yMax)}}
    if char == 1:
        search['character_orbit_rep']={"$lt":int(2)}

    fields = ['Level', 'Weight']
    dimensions = db.find(search)
    # Loop through all forms and add a clickable dot for each
    for f in dimensions:
        linkurl = "/ModularForm/GL2/Q/holomorhpic/{0}/{1}/".format(f['level'],f['weight'],f['character_orbit_rep'])
        x = (f['level'] - xMin) * xfactor + xshift
        y = (f['weight'] - yMin + 1) * yfactor
        
        color = color_neither
            
        ans += "<a xlink:href='{0}' target='_top'>".format(linkurl)
        ans += "<circle cx='{0}' cy='{1}' ".format(str(x)[0:6],str(y))
        ans += "r='{0}'  style='fill:{1}'>".format(str(radius),color)
        ans += "<title>{0}</title></circle></a>\n".format(f['galois_orbit_name'])
    ans += "</svg>"
    return ans


def paintCS(width, height, xMin, xMax, yMin, yMax, 
                 xfactor, yfactor, ticlength, xshift):
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
    for i in range(1, xMax -xMin + 1,5):
        ans += "<line x1='{0}' y1='{1}' ".format(str(i * xfactor + xshift),str(ticlength))
        ans += "x2='{0}' y2='0' ".format(str(i * xfactor + xshift))
        ans += "style='stroke:rgb(0,0,0);'/>\n"

    # ----------- Values and gridlines x axis
    for i in range(xMin + 1, xMax + 1, 5):
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
    for i in range(yMin , yMax + 1, 1):
        yvalue = (i - yMin + 1) * yfactor
        ans += "<text x='5' y='{0}' ".format(str(yvalue + 3)) 
        ans += "style='fill:rgb(102,102,102);font-size:11px;'>"
        ans += "{0}</text>\n".format(str(i))

        ans += "<line x1='{0}' y1='{1}' ".format(str(xshift),str(yvalue))
        ans += "x2='{0}' y2='{1}' ".format(str(width),str(yvalue))
        ans += "style='stroke:rgb(204,204,204);stroke-dasharray:3,3;'/>\n"

    # ----------- Axes labels
    ans += "<text x='5' y='{0}' ".format(str(height+5))
    ans += "style='fill:rgb(102,102,102);font-size:12px;'>Weight</text>\n"
    (xvalue, yvalue) = (str(width + 5) , 15)
    ans += "<text x='{0}' y='{1}' ".format(xvalue,yvalue)
    ans += "style='fill:rgb(102,102,102);font-size:14px;'>Level</text>\n"

    return ans
