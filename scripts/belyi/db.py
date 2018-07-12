import pymongo
import os
_C = None
#server = "belyi.lmfdb.xyz:27017"
server = "localhost:37010" # run warwick.sh first
def makeDBconnection():
    global _C
    _C = pymongo.MongoClient(server);
    _C.admin.authenticate("lmfdb","lmfdb")

def getDBconnection():
    if _C is None:
        makeDBconnection()
    return _C


_Cwrite = None
def makeDBconnection_write():
    global _Cwrite
    _Cwrite = pymongo.MongoClient(server);
    #_Cwrite.admin.authenticate("lmfdb","lmfdb")
    path = os.path.join(os.getcwd(), "../../passwords.yaml")
    import yaml
    pw_dict = yaml.load(path)
    try:
        pw_dict = yaml.load(open(path))
        username = pw_dict['name']
        password = pw_dict['password']
        db = pw_dict['db']
        _Cwrite[db].authenticate(username, password)
        print "Logged in as %s in %s!1!1!" % (username, db,)
    except:
        print "Failed to login"

def getDBconnection_write():
    if _Cwrite is None:
        makeDBconnection_write()
    return _Cwrite


