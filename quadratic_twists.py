# -*- coding: utf-8 -*-
import re

from pymongo import ASCENDING
import base
from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response


from utilities import ajax_more, image_src, web_latex, to_dict, parse_range
import sage.all 
from sage.all import ZZ, EllipticCurve, latex, matrix,srange
q = ZZ['x'].gen()

#########################
#   Utility functions
#########################

#########################
#    Top level
#########################


#@app.route("/quadratic_twists/")
#def QT_toplevel():
#    return redirect(url_for("quadratic_twists", **request.args))

#########################
#  Search/navigate
#########################

@app.route("/quadratic_twists/")
def quadratic_twists():

    isogeny_list=['11ar', '19ar', '43ar', '67ar', '79ar', '83ar', '131ar', '11ai', '17ai', '19ai', '37bi', '67ai', '73ai', '89bi', '109ai', '113ai', '139ai', '179ai', 
    '233ai', '307ai', '307bi', '307ci', '307di', '353ai', '389ai', '431bi', '139ar', '163ar', '179ar', '307ar', '307br', '307cr', '307dr', '331ar', '347ar', '359ar', 
    '359br', '431ar', '431br', '443ar', '443br', '443cr', '467ar', '433ai', '443ci', '503bi', '503ci', '557bi', '563ai', '571ai', '571bi', '593bi', '643ai', '659bi', 
    '701ai', '709ai', '733ai', '739ai', '997bi', '997ci', '1153ai', '1171ai', '1171bi', '1187ai', '1187bi', '1187ci', '1259bi', '1259ci', '1289ai', '1297ai', '1321ai', 
    '1373ai', '1433ai', '1483ai', '1531ai', '1613ai', '1613bi', '1621ai', '1627ai', '1867ai', '1873ai', '1901ai', '1907ai', '1907bi', '1913ai', '1913bi', '1933ai',
    '1979ai', '2027ai', '2089bi', '2089ci', '2089di', '2089ei', '2143ai', '2213ai', '2237ai', '2251ai', '2273ai', '2351ai', '2393ai', '2677ai', '2699bi', '2699ci', 
    '2797ai', '2837ai', '2843ai', '2917ai', '2939ai', '2953ai', '3089ai', '3181ai', '3203ai', '3257ai', '3259ci', '3313bi', '3331ai', '3371ai', '3371bi', '3467ai', 
    '3547bi', '3547ci', '3623ai', '3779ai', '3907ai', '3967ai', '4013ai', '4139ai', '4229ai', '4283ai', '4289ai', '4337ai', '4339ai', '4357ai', '4451ai', '4457ai', 
    '4481ci', '4547ai', '4733ai', '4799ci', '5021ai', '5171ai', '5197ai', '5303ai', '5393ai', '5419ai', '5443bi', '5651ai', '5689ai', '5741ai', '5813ai', '5987bi', 
    '5987ci', '6011bi', '6011ci', '6043ai', '6067ai', '6199bi', '6211ai', '6323ai', '6451ai', '6571ai', '6691bi', '6899ai', '6911ai', '7019bi', '7057ai', '7057bi', 
    '7057ci', '7057di', '7451ai', '7541ai', '7669ai', '7691ai', '7723bi', '7841ai', '7867ai', '8219ai', '8237ai', '8243ai', '8363ai', '8363bi', '8443ai', '8539ai', 
    '8543ai', '8623bi', '8699ai', '8713ai', '8731ai', '8747bi', '8747ci', '8747di', '8803bi', '8861ai', '8999ai', '9011ai', '9127bi', '9151ai', '9161ai', '9203ai', 
    '9277ai', '9323ai', '9341ai', '9467ai', '9473ai', '9479ai', '9551ai', '9661ai', '9811ci', '9829bi', '9829ci', '9901ai', '9923ai', '9967ai', '10079ai', '10091ai', 
    '10099ai', '10099bi', '10259ai', '10331ai', '10333ci', '10333di', '10333ei', '10357ai', '10427ai', '10499ai', '10567bi', '10597ai', '10639ai', '10691ai', '10957ai',
    '10979ai', '11003ai', '11059ai', '11171ai', '11177ai', '11251ai', '11321ci', '11467ai', '11483ai', '11731ai', '11909ai', '11939ci', '11971ai', '12011ai', '12101ai', 
    '12163bi', '12163ci', '12197ai', '12203ai', '12203bi', '12211ai', '12553ai', '12619bi', '12619ci', '12763ai', '13043bi', '13099ai', '13523bi', '13649ai', '13691ai', 
    '14107ai', '14149ai', '14347ai', '14389ai', '14411ai', '14821ai', '14891ai', '14957ai', '15173ai']
    info = {
        'isogeny_list': isogeny_list,
        }
    t = 'Quadratic Twists'
    bread = [('Quadratic Twist', url_for("quadratic_twists"))]
    return render_template("quadratic_twists/quadratic_twists.html", title=t, bread=bread, info=info)


##########################
#  Specific curve pages
##########################

@app.route("/quadratic_twists/<label>")
def render_isogeny_class(label):
    info = {}
    credit = ' '
    label = "%s" % label
    C = base.getDBConnection()
    data = C.quadratic_twists.isogeny.find_one({'label': label})
    if data is None:
        return "No such curves"
    data['download_Rub_data_100']=url_for('download_Rub_data', label=str(label), limit=100)
    data['download_Rub_data']=url_for('download_Rub_data', label=str(label))
    if data['type']=='r':
        type='real'
    else:
        type='imaginary'
    t="Quadratic Twist for isogeny class %s %s" % (data['iso_class'],type)
    return render_template("quadratic_twists/iso_class.html", info = data, title=t)


@app.route("/quadratic_twists/download_Rub_data")
def download_Rub_data():
    import gridfs
    label=(request.args.get('label'))
    limit=(request.args.get('limit'))        
    C = base.getDBConnection()
    fs = gridfs.GridFS(C.quadratic_twists,'isogeny' )
    isogeny=C.quadratic_twists.isogeny.files
    filename=isogeny.find_one({'label':label})['filename']
    d= fs.get_last_version(filename)
    if limit==None:
        limit=d.length
    else:
        limit=eval(limit)
    response = make_response(''.join(str(d.readline()) for i in srange(limit)))
    response.headers['Content-type'] = 'text/plain'
    return response