import sys, os, json
HOME=os.path.expanduser("~")
sys.path.append(os.path.join(HOME, 'lmfdb'))
from lmfdb import db

import base64

imdict = {}

# load the old images
for ent in db.gps_images.search():
    imdict[ent['label']] = ent['image']

print("Loaded old")

# load the new ones, overwriting the old where applicable
with open("prettyindex", "r") as fn:
    for line in fn.readlines():
        l= json.loads(line)
        fn2 = 'images/eq%d.png'% l[0]
        imdict[l[1]] = 'data:image/png;base64,'+base64.b64encode(open(fn2, "rb").read()).decode("utf-8")

print("Loaded new")
# Have all the image loaded

with open("imagereloader", "w") as afile:
    _ = afile.write('label|image\n')
    _ = afile.write('text|text\n\n')

    for key,value in imdict.items():
        afile.write(key.replace('\\','\\\\')+'|'+value.replace('\\','\\\\'))
        afile.write('\n')
        #inps.append({'label': key, 'image': value})
db.gps_images.reload('imagereloader')

inps=[]
#for key,value in imdict.items():
#    inps.append({'label': key, 'image': value})

#db.gps_images.delete({})
#db.gps_images.insert_many(inps)
