# Functions for fetching L-function data from databases

from lmfdb import base
import pymongo
import bson
from lmfdb.lfunctions import logger
from lmfdb.modular_forms.maass_forms.maass_waveforms.backend.maass_forms_db \
     import MaassDB


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
    coll = connection.Lfunctions.LfunctionsECtest
    try:
        Ldata = coll.find_one({'origin': label})
    except:
        Ldata = None
    return Ldata
    
def getGenus2Ldata(hash):
    connection = base.getDBConnection()
    g2 = connection.genus2_curves
    try:
        Ldata = g2.Lfunctions.find_one({'hash': hash})
    except:
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
    
