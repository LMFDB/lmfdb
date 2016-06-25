# Functions for fetching L-function data from databases

from lmfdb import base
import pymongo
import bson
from lmfdb.lfunctions import logger
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db \
     import MaassDB

from Lfunctionutilities import p2sage

def getLmaassByDatabaseId(dbid):
    collList = [('Lfunction','LemurellMaassHighDegree'),
                ('Lfunction','FarmerMaass'),
                ('Lfunction','LemurellTest')]
    dbName = ''
    dbColl = ''
    dbEntry = None
    i = 0
    # Go through all collections to find a Maass form with correct id
    while i < len(collList) and dbEntry is None:
        connection = base.getDBConnection()
        db = pymongo.database.Database(connection, collList[i][0])
        collection = pymongo.collection.Collection(db, collList[i][1])
        logger.debug(str(collection))
        logger.debug(dbid)
        
        dbEntry = collection.find_one({'_id': dbid})
        if dbEntry is None:
            i += 1
        else:
            (dbName,dbColl) = collList[i]

    return [dbName, dbColl, dbEntry]

def getEllipticCurveData(label):
    connection = base.getDBConnection()
    curves = connection.elliptic_curves.curves
    return curves.find_one({'lmfdb_label': label})

def getEllipticCurveLData(label):
    connection = base.getDBConnection()
    coll = connection.Lfunctions.Lfunctions
    try:
        Ldata = coll.find_one({'instances': label})
    except:
        Ldata = None
    return Ldata
    
def getGenus2Ldata(label,label_type="url"):
    connection = base.getDBConnection()
#    g2 = connection.genus2_curves
    db = connection.Lfunctions
    try:
    #    Ldata = g2.Lfunctions.find_one({'hash': hash})
   #     Lpointer = db.instances.find_one({'url': label})
        if label_type == "url":
            Lpointer = db.instances.find_one({'url': label})
            Lhash = Lpointer['Lhash']
            Ldata = db.Lfunctions.find_one({'Lhash': Lhash})
        elif label_type == "Lhash":
            Ldata = db.Lfunctions.find_one({'Lhash': label})
            # just return what we have, because
            # we are just filling in the dual data  
            return Ldata
            
        if Ldata['order_of_vanishing'] or 'leading_term' not in Ldata.keys():
            central_value = [0.5 + 0.5*Ldata['motivic_weight'], 0]
        else:
            central_value = [0.5 + 0.5*Ldata['motivic_weight'],Ldata['leading_term']]
        if 'values' not in Ldata:
            Ldata['values'] = [ central_value ]
        else:
            Ldata['values'] += [ central_value ]

        pos_plot = [ 
                  [j * Ldata['plot_delta'], Ldata['plot_values'][j]]
                          for j in range(min(200, len(Ldata['plot_values'])))]

        if Ldata['self_dual']:
            neg_zeros = ["-" + str(pos_zero) for pos_zero in Ldata['positive_zeros']]
            root_number = p2sage(Ldata['root_number'])
            neg_plot = [ [-1*pt[0], root_number * pt[1]] for pt in pos_plot ][1:]

        else:   # can't happen for genus 2 curves
            dual_L_label = Ldata['conjugate']
            dual_L_data = getGenus2Ldata(dual_L_label, label_type="Lhash")
            neg_zeros = ["-" + str(pos_zero) for pos_zero in dual_L_data['positive_zeros']]

            neg_plot = [
                  [-1 * j * dual_L_data['plot_delta'], dual_L_data['plot_values'][j]]
                          for j in range(1,min(200,len(dual_L_data['plot_values'])))]
#        if label.startswith('Character'):  # because those temporarily are missing the plot
#            Ldata['plot'] = ""
#        else:
#        pos_plot = [
#                  [j * Ldata['plot_delta'], Ldata['plot_values'][j]]
#                          for j in range(len(Ldata['plot_values']))]
#        if Ldata['self_dual']:
#            neg_plot = [ [-1*pt[0], Ldata['root_number'] * pt[1]] for pt in pos_plot ][1:]
#            neg_plot.reverse()
#        else:
#            pass  # need to add this case
#        Ldata['plot'] = neg_plot[:] + pos_plot[:]

        neg_zeros.reverse()
        Ldata['zeros'] = neg_zeros[:]
        Ldata['zeros'] += [0 for _ in range(Ldata['order_of_vanishing'])]
        Ldata['zeros'] += [str(pos_zero) for pos_zero in Ldata['positive_zeros']]

        neg_plot.reverse()
        Ldata['plot'] = neg_plot[:] + pos_plot[:]
        #print "Ldata['plot']",Ldata['plot']

    except ValueError:
        Ldata = None
    return Ldata
    
def getHmfData(label):
    connection = base.getDBConnection()
    try:
        f = connection.hmfs.forms.find_one({'label': label})
        F_hmf = connection.hmfs.fields.find_one({'label': f['field_label']})
    except:
        f = None
        F_hmf = None
    return (f, F_hmf)
    
def getGenus2IsogenyClass(label):
    connection = base.getDBConnection()
    g2 = connection.genus2_curves
    try:
        iso = g2.isogeny_classes.find_one({'label': label})
    except:
        iso = None
    return iso
    
def getHmfData(label):
    connection = base.getDBConnection()
    try:
        f = connection.hmfs.forms.find_one({'label': label})
        F_hmf = connection.hmfs.fields.find_one({'label': f['field_label']})
    except:
        f = None
        F_hmf = None
    return (f, F_hmf)

def getMaassDb():
    # NB although base.getDBConnection().PORT works it gives the
    # default port number of 27017 and not the actual one!
    if pymongo.version_tuple[0] < 3:
        host = base.getDBConnection().host
        port = base.getDBConnection().port
    else:
        host, port = base.getDBConnection().address
    return MaassDB(host=host, port=port)
    
def getHgmData(label):
    connection = base.getDBConnection()
    return connection.hgm.motives.find_one({'label': label})
    
