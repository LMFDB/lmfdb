import sys, os, json
HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'sage', 'lmfdb'))
from lmfdb import db

import base64

imdict = {}

# load the old images
for ent in db.modcurve_teximages.search():
    imdict[ent['label']] = ent['image']

# load the new ones, overwriting the old where applicable
with open("prettyindex", "r") as fn:
    for line in fn.readlines():
        l= json.loads(line)
        fn2 = 'images/eq%d.png'% l[0]
        imdict[l[1]] = 'data:image/png;base64,'+base64.b64encode(open(fn2, "rb").read()).decode("utf-8")

# Have all the image loaded

inps=[]
for key,value in imdict.items():
    inps.append({'label': key, 'image': value})

db.modcurve_teximages.delete({})
db.modcurve_teximages.insert_many(inps)
